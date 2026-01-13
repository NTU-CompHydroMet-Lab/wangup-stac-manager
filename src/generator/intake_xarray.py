"""Concrete STAC generator that reads an Intake‑Xarray source.

The class implements the abstract methods defined in ``src.generator.base.StacGenerator``
so that the high‑level generation logic can be reused for any source type (e.g. a
database, a remote API, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import intake
import xarray as xr
import shutil
from loguru import logger

from .utils import compute_extent, format_datetime, get_spatial_dims, fix_pacific_bbox
from .model import DatasetMetadata

import pystac
import xstac
import cf_xarray

from .base import StacGenerator


class IntakeXarrayGenerator(StacGenerator):
    """Generator for Intake-Xarray sources (NetCDF, Zarr).

    Parameters
    ----------
    output_dir:
        Directory where ``collection.json`` and ``items/`` will be written.
    catalog_path:
        Path to the Intake catalog YAML file.
    """

    def __init__(self, output_dir: Path, catalog_path: Path, catalog_metadata: Dict[str, Any] = None) -> None:
        super().__init__(output_dir)
        self.catalog_path = catalog_path
        self.catalog_metadata = catalog_metadata or {}

    # ------------------------------------------------------------------
    # Abstract API implementation
    # ------------------------------------------------------------------
    def process_source(self, source_name: str) -> None:
        """Process a single source from the catalog."""
        logger.info(f"Processing source: {source_name}")
        source = self.load_source(source_name)

    def load_source(self, source_name: str) -> Any:
        """Open the Intake catalog and return the requested source entry.

        Raises
        ------
        ValueError
        If ``source_name`` is not present in the catalog.
        """
        cat = intake.open_catalog(str(self.catalog_path))
        if source_name not in cat:
            raise ValueError(
                f"Source '{source_name}' not found in {self.catalog_path}"
            )
        return cat[source_name]

    def extract_metadata(self, source: Any) -> Dict[str, Any]:
        """Extract a flat metadata dictionary from an Intake source.

        ``source.metadata`` may be a dict or a nested dict containing a ``metadata``
        key – the method normalises both cases.
        """
        meta = {}
        # Try to get metadata from the source object itself
        if hasattr(source, "metadata") and source.metadata:
            meta = source.metadata
        # Try to get metadata from the catalog entry (common in Intake v2)
        elif hasattr(source, "_entry") and hasattr(source._entry, "_metadata"):
            meta = source._entry._metadata
        # Try to get metadata via describe()
        elif hasattr(source, "describe"):
            try:
                desc = source.describe()
                if "metadata" in desc:
                    meta = desc["metadata"]
            except Exception:
                pass

        if "metadata" in meta:
            meta = meta["metadata"]

        # Map 'collection_name' to 'title' if present (User Request)
        if "collection_name" in meta and "title" not in meta:
             meta["title"] = meta["collection_name"]

            
        # Merge Global Catalog Metadata (e.g. catalog_name -> group_id)
        # Priority: Source > Catalog
        if "group_id" not in meta:
            # Check for direct group_id in catalog
            if "group_id" in self.catalog_metadata:
                 meta["group_id"] = self.catalog_metadata["group_id"]
            # Check for catalog_name alias (User Request)
            elif "catalog_name" in self.catalog_metadata:
                 # Normalize: lowercase, replace spaces with underscores
                 raw_name = self.catalog_metadata["catalog_name"]
                 meta["group_id"] = raw_name.strip().lower().replace(" ", "_").replace("-", "_")
                 meta["group_title"] = raw_name.strip() # Preserve original casing for display
            
            # Extract Group Description from Catalog Metadata
            if "description" in self.catalog_metadata:
                meta["group_description"] = self.catalog_metadata["description"]

        # Merge Global Catalog Keywords
        if "group_keywords" not in meta:
            if "catalogs_keywords" in self.catalog_metadata:
                meta["group_keywords"] = self.catalog_metadata["catalogs_keywords"]

        return meta

    def get_dataset(self, source: Any) -> xr.Dataset:
        """Return a lazy ``xarray.Dataset`` for the source.

        ``to_dask`` is used so that the dataset is not fully loaded into memory
        until we slice it per year. 
        Auto-normalizes coordinates (e.g., 0-360 -> -180/180) to ensure STAC compliance.
        """
        ds = source.to_dask()
        return self._normalize_dataset(ds)

    def _normalize_dataset(self, ds: xr.Dataset) -> xr.Dataset:
        """Normalize coordinates to standard standards (EPSG:4326 -180/180)."""
        try:
            # 1. Detect Longitude coordinate
            lon_name = None
            if "longitude" in ds.coords:
                lon_name = "longitude"
            elif "lon" in ds.coords:
                lon_name = "lon"
            
            if lon_name:
                # Check if it needs wrapping (e.g. 0-360 range)
                # We use .max() compute because coords are usually small / loaded
                if ds[lon_name].max() > 180:
                    logger.info(f"Normalizing {lon_name} from 0-360 to -180/180 range...")
                    ds.coords[lon_name] = (ds.coords[lon_name] + 180) % 360 - 180
                    ds = ds.sortby(lon_name)
        except Exception as e:
            logger.warning(f"Coordinate normalization failed: {e}")
        
        return ds


    def _enrich_collection_metadata(self, collection: pystac.Collection, ds: xr.Dataset) -> pystac.Collection:
        """Enrich collection metadata using xstac to extract datacube info."""
        # Removed try-except for debugging
        logger.info(f"ENTER _enrich_collection_metadata for {collection.id}")
        
        logger.info("Running xstac to extract rich metadata...")
        
        # xstac expects the template to be a pystac.Collection
        kw = {"reference_system": "EPSG:4326"}
        
        # Use cf-xarray to detect dimensions
        try:
            if ds.cf["time"].name in ds.dims:
                kw["temporal_dimension"] = ds.cf["time"].name
        except KeyError:
            pass

        try:
            if ds.cf["longitude"].name in ds.dims:
                kw["x_dimension"] = ds.cf["longitude"].name
            elif ds.cf["X"].name in ds.dims:
                    kw["x_dimension"] = ds.cf["X"].name
        except KeyError:
            pass
            
        try:
            if ds.cf["latitude"].name in ds.dims:
                kw["y_dimension"] = ds.cf["latitude"].name
            elif ds.cf["Y"].name in ds.dims:
                kw["y_dimension"] = ds.cf["Y"].name
        except KeyError:
            pass
        
        logger.debug(f"xstac config: {kw}")

        # xstac returns a NEW collection object enriched with cube extensions
        enriched = xstac.xarray_to_stac(ds, collection, **kw)
        
        # Check if we need to fix the BBox for Pacific-centered views (Antimeridian crossing)
        fix_pacific_bbox(enriched, ds)
        
        return enriched


    def _enrich_item_metadata(self, item: pystac.Item, ds: xr.Dataset) -> pystac.Item:
        """Enrich item metadata using xstac to extract datacube info."""
        try:
            # For Items, xstac needs a Collection template to run against, 
            # then we extract the properties back to the Item.
            
            # Create a dummy template from the item's geometry/time
            template = pystac.Collection(
                id="dummy",
                description="dummy",
                extent=pystac.Extent(
                    pystac.SpatialExtent([item.bbox]),
                    pystac.TemporalExtent([[item.datetime, item.datetime]])
                ),
                license="proprietary"
            )
            
            kw = {"reference_system": "EPSG:4326"}
            try:
                if ds.cf["time"].name in ds.dims: kw["temporal_dimension"] = ds.cf["time"].name
            except KeyError: pass
            
            try:
                if ds.cf["longitude"].name in ds.dims: kw["x_dimension"] = ds.cf["longitude"].name
            except KeyError: pass
            
            try:
                if ds.cf["latitude"].name in ds.dims: kw["y_dimension"] = ds.cf["latitude"].name
            except KeyError: pass
                
            out_col = xstac.xarray_to_stac(ds, template, **kw)
            
            # Now we transfer the extensions and properties from the temporary collection to our Item
            # 1. datacube extension
            if "cube:dimensions" in out_col.extra_fields:
                item.properties["cube:dimensions"] = out_col.extra_fields["cube:dimensions"]
            if "cube:variables" in out_col.extra_fields:
                item.properties["cube:variables"] = out_col.extra_fields["cube:variables"]
                
            # 2. Add schema
            for ext in out_col.stac_extensions:
                item.stac_extensions.append(ext)
            
            return item
            
        except Exception as e:
            logger.warning(f"Item xstac enrichment failed: {e}")
            return item
