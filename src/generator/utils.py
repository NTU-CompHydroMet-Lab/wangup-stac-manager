from __future__ import annotations
import pandas as pd
import xarray as xr
import warnings
from typing import Dict, List, Tuple, Optional
import pystac

def format_datetime(dt) -> str:
    """Format a datetime object/string to RFC 3339 string (Z-suffixed)."""
    return pd.to_datetime(dt).strftime('%Y-%m-%dT%H:%M:%SZ')

import cf_xarray

def get_spatial_dims(ds: xr.Dataset) -> Tuple[Optional[xr.DataArray], Optional[xr.DataArray]]:
    """Helper to get longitude and latitude arrays using CF conventions."""
    try:
        lon = ds.cf["longitude"]
    except KeyError:
        lon = None
        
    try:
        lat = ds.cf["latitude"]
    except KeyError:
        lat = None
        
    return lon, lat

def compute_extent(ds: xr.Dataset) -> pystac.Extent:
    """Compute spatial bbox and temporal interval from an ``xarray`` dataset.

    Returns a pystac.Extent object.
    """
    try:
        lon, lat = get_spatial_dims(ds)
        if lon is not None and lat is not None:
            lon_min = float(lon.min())
            lon_max = float(lon.max())
            lat_min = float(lat.min())
            lat_max = float(lat.max())
            spatial_bbox = [lon_min, lat_min, lon_max, lat_max]
        else:
            warnings.warn("Could not find longitude/latitude coordinates.")
            spatial_bbox = [-180.0, -90.0, 180.0, 90.0]
    except Exception as exc:  # pragma: no cover
        warnings.warn(f"Unable to compute spatial bbox: {exc}")
        spatial_bbox = [-180.0, -90.0, 180.0, 90.0]

    try:
        # Use cf-xarray to find time dimension
        try:
            times = ds.cf["time"]
            start = pd.to_datetime(times.min().values)
            end = pd.to_datetime(times.max().values)
            temporal_interval = [[start, end]]
        except KeyError:
             # Fallback if CF time not found (or simplistic check)
             if "time" in ds.dims:
                 start = pd.to_datetime(ds.time.min().values)
                 end = pd.to_datetime(ds.time.max().values)
                 temporal_interval = [[start, end]]
             else:
                 raise ValueError("No time coordinate found.")
    except Exception as exc:  # pragma: no cover
        warnings.warn(f"Unable to compute temporal interval: {exc}")
        # Default to 1970 if failure
        default = pd.to_datetime("1970-01-01T00:00:00Z")
        temporal_interval = [[default, default]]

    return pystac.Extent(
        spatial=pystac.SpatialExtent([spatial_bbox]),
        temporal=pystac.TemporalExtent(temporal_interval)
    )
