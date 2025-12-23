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
