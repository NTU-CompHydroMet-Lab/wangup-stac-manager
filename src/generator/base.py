from __future__ import annotations

import abc
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import warnings
from loguru import logger

import pandas as pd
import xarray as xr

# Import refactored modules
from .utils import compute_extent, format_datetime, get_spatial_dims
from .thumbnails import generate_thumbnail
from .assets import process_example_notebook, create_data_asset


class StacGenerator(abc.ABC):
    """Base class that defines the workflow for generating a static STAC catalog."""

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
        """Extract a dictionary of metadata from the source."""

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
    # Helper methods
    # ------------------------------------------------------------------
    def _load_or_create_collection(self, meta: Dict[str, object], ds: xr.Dataset) -> Dict[str, object]:
        """Load an existing collection.json or create a minimal one.

        ``meta`` is the metadata dict extracted from the source.
        ``ds`` is used to compute the real extent.
        """
        # NOTE: We do NOT load existing collection.json here anymore (Force Refresh)
        
        level = meta.get("processing:level")
        if isinstance(level, str):
            level = [level]
        if not level:
            level = ["bronze", "silver"]

        extent = compute_extent(ds)
        
        collection = {
            "type": "Collection",
            "id": meta.get("id", "generated_collection"),
            "title": meta.get("title", meta.get("id", "generated_collection")),
            "stac_version": "1.0.0",
            "description": meta.get(
                "description",
                "Generated STAC collection (static) via intake‑xarray",
            ),
            "keywords": meta.get("keywords", []),
            "license": "CC-BY-4.0",
            "stac_extensions": [],
            "extent": extent,
            "summaries": {
                "processing:level": level,
                "platform": [meta.get("platform", "unknown")],
                "category": [meta.get("category", "DATA")],
            },
            "links": [],
            "providers": meta.get("providers", []),
        }
        
        # --- Handle Scientific Extension & Top-level Props ---
        sci_ext_url = "https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
        for key, value in meta.items():
            if key.startswith("sci:"):
                collection[key] = value
                if sci_ext_url not in collection["stac_extensions"]:
                    collection["stac_extensions"].append(sci_ext_url)
            if key == "terms_of_use" or key == "gee:terms_of_use":
                 collection["terms_of_use"] = value

        # --- Example Notebook Handling (Refactored) ---
        example_nb = meta.get("example_notebook")
        if example_nb:
            logger.info(f"Processing example notebook: {example_nb}")
            nb_asset = process_example_notebook(example_nb, self.output_dir)
            if nb_asset:
                if "assets" not in collection:
                    collection["assets"] = {}
                collection["assets"]["example_notebook"] = nb_asset

        # --- Collection Thumbnail Generation (Refactored) ---
        thumb_path_cfg = meta.get("thumbnail_path")
        thumb_var = meta.get("thumbnail_variable")
        
        if thumb_path_cfg:
            try:
                src_thumb = Path(thumb_path_cfg)
                if src_thumb.exists():
                    logger.info(f"Using provided thumbnail: {src_thumb}")
                    dest_thumb = self.items_dir / f"{collection['id']}_thumb{src_thumb.suffix}"
                    shutil.copy2(src_thumb, dest_thumb)
                    if "assets" not in collection:
                        collection["assets"] = {}
                    collection["assets"]["thumbnail"] = {
                        "href": f"./items/{dest_thumb.name}",
                        "type": "image/png" if src_thumb.suffix == ".png" else "image/jpeg",
                        "roles": ["thumbnail"],
                        "title": f"Thumbnail for {collection['id']}"
                    }
                else:
                    logger.warning(f"Provided thumbnail path not found: {src_thumb}")
            except Exception as e:
                logger.error(f"Failed to copy provided thumbnail: {e}")

        elif thumb_var:
            thumb_asset = generate_thumbnail(ds, collection["id"], self.items_dir, target_var=thumb_var)
            if thumb_asset:
                if "assets" not in collection:
                    collection["assets"] = {}
                collection["assets"]["thumbnail"] = thumb_asset

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
    # Public entry point
    # ------------------------------------------------------------------
    def generate(self, source_name: str) -> None:
        """Generate the collection and per‑year items for ``source_name``."""
        source = self.load_source(source_name)
        meta = self.extract_metadata(source)
        ds = self.get_dataset(source)

        # Cleanup
        if self.items_dir.exists():
            logger.info(f"Cleaning existing items: {self.items_dir}")
            shutil.rmtree(self.items_dir)
        self.items_dir.mkdir(parents=True, exist_ok=True)
            
        if self.collection_path.exists():
            self.collection_path.unlink()
        
        # Ensure Collection ID
        if "id" not in meta:
            meta["id"] = source_name
            
        collection = self._load_or_create_collection(meta, ds)

        collection["links"] = [
            {"rel": "root", "href": "./collection.json", "type": "application/json"},
            {"rel": "self", "href": "./collection.json", "type": "application/json"},
        ]

        years = sorted(set(pd.DatetimeIndex(ds.time.values).year))
        for yr in years:
            ds_year = ds.sel(time=str(yr))
            item = self._make_item(ds_year, yr, meta)
            
            collection["links"].append({
                "rel": "item",
                "href": f"./items/{item['id']}.json",
                "type": "application/json"
            })
            
            self._write_item(item)
            logger.info(f"Generated Item for year {yr}")

        self._write_collection(collection)
        logger.info(f"Collection written to {self.collection_path}")

    # ------------------------------------------------------------------
    # Item creation
    # ------------------------------------------------------------------
    def _make_item(self, ds_year: xr.Dataset, year: int, meta: Dict[str, object]) -> Dict[str, object]:
        lon, lat = get_spatial_dims(ds_year)
        if lon is not None and lat is not None:
            lon_min = float(lon.min())
            lon_max = float(lon.max())
            lat_min = float(lat.min())
            lat_max = float(lat.max())
            bbox = [lon_min, lat_min, lon_max, lat_max]
        else:
            bbox = [-180.0, -90.0, 180.0, 90.0]
        
        start = format_datetime(ds_year.time.min().values)
        end = format_datetime(ds_year.time.max().values)
        
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
            "assets": {},
            "links": [
                {"rel": "root", "href": "../collection.json", "type": "application/json"},
                {"rel": "collection", "href": "../collection.json", "type": "application/json"},
                {"rel": "parent", "href": "../collection.json", "type": "application/json"},
                {"rel": "self", "href": f"./{item_id}.json", "type": "application/json"},
            ],
        }

        # --- Dynamic Asset Generation (Refactored) ---
        source_path = ds_year.encoding.get("source")
        if source_path:
             # Store strict absolute path for user reference (e.g. Copy Path)
             item["properties"]["source_path"] = str(source_path)
             item["assets"]["data"] = create_data_asset(source_path, item_id, self.items_dir)
        else:
             # Fallback
             item["assets"]["zarr"] = {
                "href": f"./{item_id}.zarr", # Placeholder
                "type": "application/vnd+zarr",
                "roles": ["data"],
                "title": f"Data Store for {item_id}",
             }

        item = self._enrich_item_metadata(item, ds_year)
        
        return item
