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

import pystac
import xstac

from .base import StacGenerator


class IntakeXarrayGenerator(StacGenerator):
    """Generate a static STAC catalog from an Intake‑Xarray source.

    Parameters
    ----------
    output_dir:
        Directory where ``collection.json`` and ``items/`` will be written.
    catalog_path:
        Path to the Intake catalog YAML file.
    """

    def __init__(self, output_dir: Path, catalog_path: Path) -> None:
        super().__init__(output_dir)
        self.catalog_path = catalog_path

    # ------------------------------------------------------------------
    # Abstract API implementation
    # ------------------------------------------------------------------
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
        return meta

    def get_dataset(self, source: Any) -> xr.Dataset:
        """Return a lazy ``xarray.Dataset`` for the source.

        ``to_dask`` is used so that the dataset is not fully loaded into memory
        until we slice it per year.
        """
        return source.to_dask()

    def _enrich_collection_metadata(self, collection: Dict[str, Any], ds: xr.Dataset) -> Dict[str, Any]:
        """Enrich collection metadata using xstac to extract datacube info."""
        try:
            print("  ✨ Running xstac to extract rich metadata...")
            
            # Create a temporary pystac Collection template from our current dict
            # We need to handle extent objects properly
            spatial_bbox = collection["extent"]["spatial"]["bbox"]
            temporal_interval = collection["extent"]["temporal"]["interval"]
            
            # Convert string timestamps to datetime objects for pystac/xstac
            # xstac might expect datetime objects to perform comparisons
            import pandas as pd
            parsed_interval = []
            for interval in temporal_interval:
                start = pd.to_datetime(interval[0])
                end = pd.to_datetime(interval[1]) if interval[1] else None
                parsed_interval.append([start, end])

            template = pystac.Collection(
                id=collection["id"],
                description=collection["description"],
                extent=pystac.Extent(
                    pystac.SpatialExtent(spatial_bbox),
                    pystac.TemporalExtent(parsed_interval)
                ),
                license=collection.get("license", "proprietary")
            )
            
            # Run xstac
            # We explicitly map dimensions if possible, or let xstac guess
            # For ERA5/Climate data, usually: time, latitude, longitude
            kw = {
                "reference_system": "EPSG:4326"
            }
            
            # Simple heuristic for dimension mapping
            if "time" in ds.dims:
                kw["temporal_dimension"] = "time"
            if "longitude" in ds.dims:
                kw["x_dimension"] = "longitude"
            if "latitude" in ds.dims:
                kw["y_dimension"] = "latitude"
                
            out_col = xstac.xarray_to_stac(ds, template, **kw)
            
            # Convert back to dict
            out_dict = out_col.to_dict()
            
            # Merge relevant fields back into our collection dict
            # We want to keep our ID, description, etc. but take summaries and extensions
            if "summaries" in out_dict:
                # Merge summaries (don't overwrite existing ones like platform if they exist)
                current_summaries = collection.get("summaries", {})
                new_summaries = out_dict["summaries"]
                current_summaries.update(new_summaries)
                collection["summaries"] = current_summaries
                
            if "stac_extensions" in out_dict:
                current_exts = set(collection.get("stac_extensions", []))
                current_exts.update(out_dict["stac_extensions"])
                collection["stac_extensions"] = list(current_exts)
                
            # Copy datacube fields (cube:dimensions, cube:variables)
            for key, value in out_dict.items():
                if key.startswith("cube:"):
                    collection[key] = value
            
            return collection
            
        except Exception as e:
            print(f"  ⚠️ xstac enrichment failed: {e}")
            return collection

    def _enrich_item_metadata(self, item: Dict[str, Any], ds: xr.Dataset) -> Dict[str, Any]:
        """Enrich item metadata using xstac to extract datacube info."""
        try:
            # We use xstac to generate a temporary Collection from this Item's dataset
            # Then we copy the relevant metadata into the Item's properties.
            
            # Create a dummy template collection
            # xstac needs a template to work with
            spatial_bbox = item["bbox"]
            start = item["properties"]["start_datetime"]
            end = item["properties"]["end_datetime"]
            
            # Convert strings to datetime
            import pandas as pd
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            
            template = pystac.Collection(
                id="dummy",
                description="dummy",
                extent=pystac.Extent(
                    pystac.SpatialExtent([spatial_bbox]),
                    pystac.TemporalExtent([[start_dt, end_dt]])
                ),
                license="proprietary"
            )
            
            # Run xstac
            kw = {
                "reference_system": "EPSG:4326"
            }
            if "time" in ds.dims:
                kw["temporal_dimension"] = "time"
            if "longitude" in ds.dims:
                kw["x_dimension"] = "longitude"
            if "latitude" in ds.dims:
                kw["y_dimension"] = "latitude"
                
            out_col = xstac.xarray_to_stac(ds, template, **kw)
            out_dict = out_col.to_dict()
            
            # Copy datacube fields into properties
            # STAC Items store extensions in 'properties', not top-level
            props = item.get("properties", {})
            
            # 1. Copy cube:dimensions and cube:variables
            for key, value in out_dict.items():
                if key.startswith("cube:"):
                    props[key] = value
                    
            # 2. Copy summaries as 'variables' (if we want detailed variable info)
            # Standard STAC doesn't have a 'variables' property in Item, but we can add it
            # or we can rely on cube:variables which is the standard way.
            # The base generator adds a simple list of variable names.
            # xstac provides 'summaries' which contains variable metadata.
            # We can merge this into a custom 'variables_detail' property or just rely on cube:variables.
            # Let's stick to cube:variables as it is the standard extension.
            
            # 3. Add datacube extension schema
            extensions = item.get("stac_extensions", [])
            if "stac_extensions" in out_dict:
                for ext in out_dict["stac_extensions"]:
                    if ext not in extensions:
                        extensions.append(ext)
            item["stac_extensions"] = extensions
            
            item["properties"] = props
            return item
            
        except Exception as e:
            print(f"  ⚠️ Item xstac enrichment failed: {e}")
            return item
