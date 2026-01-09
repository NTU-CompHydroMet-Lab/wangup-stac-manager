from __future__ import annotations
import pandas as pd
import xarray as xr
import warnings
from typing import Dict, List, Tuple, Optional

def format_datetime(dt) -> str:
    """Format a datetime object/string to RFC 3339 string (Z-suffixed)."""
    return pd.to_datetime(dt).strftime('%Y-%m-%dT%H:%M:%SZ')

def get_spatial_dims(ds: xr.Dataset) -> Tuple[Optional[xr.DataArray], Optional[xr.DataArray]]:
    """Helper to get longitude and latitude arrays regardless of name."""
    lon = ds.longitude if "longitude" in ds.coords else ds.lon if "lon" in ds.coords else None
    lat = ds.latitude if "latitude" in ds.coords else ds.lat if "lat" in ds.coords else None
    return lon, lat

def compute_extent(ds: xr.Dataset) -> Dict[str, List]:
    """Compute spatial bbox and temporal interval from an ``xarray`` dataset.

    Returns a dict matching the STAC ``extent`` schema.
    """
    try:
        lon, lat = get_spatial_dims(ds)
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
        start = format_datetime(ds.time.min().values)
        end = format_datetime(ds.time.max().values)
        temporal_interval = [[start, end]]
    except Exception as exc:  # pragma: no cover
        warnings.warn(f"Unable to compute temporal interval: {exc}")
        temporal_interval = [["1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z"]]

    return {"spatial": {"bbox": spatial_bbox}, "temporal": {"interval": temporal_interval}}
