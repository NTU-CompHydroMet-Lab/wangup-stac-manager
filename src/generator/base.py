"""Abstract base class for STAC generation.

The idea is to provide a common interface that can be implemented for different
metadata sources (e.g. Intake‑Xarray, a database, a remote API).  Concrete
implementations only need to provide the methods defined below.
"""

from __future__ import annotations

import abc
import json
from pathlib import Path
from typing import Dict, List
import warnings

import pandas as pd
import xarray as xr


class StacGenerator(abc.ABC):
    """Base class that defines the workflow for generating a static STAC catalog.

    Sub‑classes must implement the abstract methods to load a source, extract the
    required metadata and write the resulting Collection and Item JSON files.
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.collection_path = self.output_dir / "collection.json"
        self.items_dir = self.output_dir / "items"
        self.items_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Abstract API – concrete implementations must provide these
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def load_source(self, source_name: str) -> object:
        """Return the raw source object (e.g. an Intake entry)."""

    @abc.abstractmethod
    def extract_metadata(self, source: object) -> Dict[str, object]:
        """Extract a dictionary of metadata from the source.

        Expected keys (optional): ``variables``, ``processing:level``, ``gsd``,
        ``platform`` and any custom fields the user wishes to propagate.
        """

    @abc.abstractmethod
    def get_dataset(self, source: object) -> xr.Dataset:
        """Return an ``xarray.Dataset`` (lazy) for the source."""

    def _enrich_collection_metadata(self, collection: Dict[str, object], ds: xr.Dataset) -> Dict[str, object]:
        """Hook to enrich collection metadata. Default implementation does nothing."""
        return collection

    def _enrich_item_metadata(self, item: Dict[str, object], ds: xr.Dataset) -> Dict[str, object]:
        """Hook to enrich item metadata. Default implementation does nothing."""
        return item


    # ------------------------------------------------------------------
    # Helper methods – can be overridden but have a default implementation
    # ------------------------------------------------------------------
    def _format_datetime(self, dt) -> str:
        """Format a datetime object/string to RFC 3339 string (Z-suffixed)."""
        return pd.to_datetime(dt).strftime('%Y-%m-%dT%H:%M:%SZ')

    # _compute_gsd removed as requested


    def _get_spatial_dims(self, ds: xr.Dataset):
        """Helper to get longitude and latitude arrays regardless of name."""
        lon = ds.longitude if "longitude" in ds.coords else ds.lon if "lon" in ds.coords else None
        lat = ds.latitude if "latitude" in ds.coords else ds.lat if "lat" in ds.coords else None
        return lon, lat

    def _compute_extent(self, ds: xr.Dataset) -> Dict[str, List]:
        """Compute spatial bbox and temporal interval from an ``xarray`` dataset.

        Returns a dict matching the STAC ``extent`` schema.
        """
        try:
            lon, lat = self._get_spatial_dims(ds)
            if lon is not None and lat is not None:
                lon_min = float(lon.min())
                lon_max = float(lon.max())
                lat_min = float(lat.min())
                lat_max = float(lat.max())
                spatial_bbox = [[lon_min, lat_min, lon_max, lat_max]]
            else:
                warnings.warn("Could not find longitude/latitude coordinates.")
                spatial_bbox = [[-180.0, -90.0, 180.0, 90.0]]
        except Exception as exc:  # pragma: no cover
            warnings.warn(f"Unable to compute spatial bbox: {exc}")
            spatial_bbox = [[-180.0, -90.0, 180.0, 90.0]]

        try:
            start = self._format_datetime(ds.time.min().values)
            end = self._format_datetime(ds.time.max().values)
            temporal_interval = [[start, end]]
        except Exception as exc:  # pragma: no cover
            warnings.warn(f"Unable to compute temporal interval: {exc}")
            temporal_interval = [["1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z"]]

        return {"spatial": {"bbox": spatial_bbox}, "temporal": {"interval": temporal_interval}}

    def _load_or_create_collection(self, meta: Dict[str, object], ds: xr.Dataset) -> Dict[str, object]:
        """Load an existing collection.json or create a minimal one.

        ``meta`` is the metadata dict extracted from the source.
        ``ds`` is used to compute the real extent.
        """
        if self.collection_path.is_file():
            return json.loads(self.collection_path.read_text())

        level = meta.get("processing:level")
        if isinstance(level, str):
            level = [level]
        if not level:
            # TODO: In the future, remove this default and raise an error if 'processing:level' is missing.
            # We want to enforce strict metadata validation to ensure all collections have proper levels.
            level = ["bronze", "silver"]

        extent = self._compute_extent(ds)
        
        collection = {
            "type": "Collection",
            "id": meta.get("id", "generated_collection"),
            "stac_version": "1.0.0",
            "description": meta.get(
                "description",
                "Generated STAC collection (static) via intake‑xarray",
            ),
            "license": "CC-BY-4.0",
            "extent": extent,
            "summaries": {
                "processing:level": level,
                "platform": [meta.get("platform", "unknown")],
            },
            "links": [],
        }

        # Hook for subclasses to enrich metadata (e.g. using xstac)
        collection = self._enrich_collection_metadata(collection, ds)


        self.collection_path.parent.mkdir(parents=True, exist_ok=True)
        self.collection_path.write_text(json.dumps(collection, indent=2))
        return collection

    def _write_collection(self, collection: Dict[str, object]) -> None:
        self.collection_path.write_text(json.dumps(collection, indent=2))

    def _write_item(self, item: Dict[str, object]) -> None:
        item_path = self.items_dir / f"{item['id']}.json"
        item_path.write_text(json.dumps(item, indent=2))

    # ------------------------------------------------------------------
    # Public entry point – orchestrates the whole generation process
    # ------------------------------------------------------------------
    def generate(self, source_name: str) -> None:
        """Generate the collection and per‑year items for ``source_name``."""
        source = self.load_source(source_name)
        meta = self.extract_metadata(source)
        ds = self.get_dataset(source)
        
        # Ensure we have a valid ID for the collection
        if "id" not in meta:
            meta["id"] = source_name
            
        collection = self._load_or_create_collection(meta, ds)

        # Add root and self links to collection
        # Note: In a real static catalog, these should be absolute URLs or relative paths.
        # For this generator, we'll use relative paths assuming the catalog root is the collection.
        collection["links"] = [
            {"rel": "root", "href": "./collection.json", "type": "application/json"},
            {"rel": "self", "href": "./collection.json", "type": "application/json"},
        ]

        years = sorted(set(pd.DatetimeIndex(ds.time.values).year))
        for yr in years:
            ds_year = ds.sel(time=str(yr))
            item = self._make_item(ds_year, yr, meta)
            
            # Add link from Collection to Item
            collection["links"].append({
                "rel": "item",
                "href": f"./items/{item['id']}.json",
                "type": "application/json"
            })
            
            # if "variables" not in collection["summaries"]:
            #     collection["summaries"]["variables"] = item["properties"]["variables"]
            self._write_item(item)
            print(f"✅ Generated Item for year {yr}")

        self._write_collection(collection)
        print(f"🗂  Collection written to {self.collection_path}")

    # ------------------------------------------------------------------
    # Item creation – can be overridden by subclasses if needed
    # ------------------------------------------------------------------
    def _make_item(self, ds_year: xr.Dataset, year: int, meta: Dict[str, object]) -> Dict[str, object]:
        lon, lat = self._get_spatial_dims(ds_year)
        if lon is not None and lat is not None:
            lon_min = float(lon.min())
            lon_max = float(lon.max())
            lat_min = float(lat.min())
            lat_max = float(lat.max())
            bbox = [lon_min, lat_min, lon_max, lat_max]
        else:
            bbox = [-180.0, -90.0, 180.0, 90.0]
        
        start = self._format_datetime(ds_year.time.min().values)
        end = self._format_datetime(ds_year.time.max().values)
        
        variables: List[str] = list(ds_year.data_vars)
        
        collection_id = meta.get('id', 'generated_collection')
        item_id = f"{collection_id}-{year}"
        item = {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": item_id,
            "collection": collection_id,
            "geometry": None,
            "bbox": bbox,
            "properties": {
                "start_datetime": start,
                "end_datetime": end,
                "platform": meta.get("platform", "unknown"),
                "variables": variables,
            },
            "assets": {
                "zarr": {
                    "href": f"/NAS/dataset/era5_rechunked/era5_{year}_10N40N_100E140E_rechunked.zarr",
                    "type": "application/vnd+zarr",
                    "roles": ["data"],
                    "title": f"ERA5 {year} Zarr Store",
                }
            },
            "links": [
                {"rel": "root", "href": "../collection.json", "type": "application/json"},
                {"rel": "collection", "href": "../collection.json", "type": "application/json"},
                {"rel": "parent", "href": "../collection.json", "type": "application/json"},
                {"rel": "self", "href": f"./{item_id}.json", "type": "application/json"},
            ],
        }
        
        # Hook for subclasses to enrich metadata (e.g. using xstac)
        item = self._enrich_item_metadata(item, ds_year)
        
        return item
