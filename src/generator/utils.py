from __future__ import annotations
import pandas as pd
import xarray as xr
import warnings
from typing import Dict, List, Tuple, Optional, Any
import pystac
from shapely.geometry import Polygon, mapping
import antimeridian

def format_datetime(dt) -> str:
    """Format a datetime object/string to RFC 3339 string (Z-suffixed)."""
    return pd.to_datetime(dt).strftime('%Y-%m-%dT%H:%M:%SZ')

import cf_xarray

def get_spatial_dims(ds: xr.Dataset) -> Tuple[Optional[xr.DataArray], Optional[xr.DataArray]]:
    """Helper to get longitude and latitude arrays using CF conventions."""
    # Use cf-xarray directly
    try:
        lon = ds.cf["longitude"]
    except KeyError:
        lon = None
        
    try:
        lat = ds.cf["latitude"]
    except KeyError:
        lat = None
        
    return lon, lat

def compute_item_geometry(bbox: List[float]) -> Optional[Dict[str, Any]]:
    """
    Compute a valid GeoJSON Geometry from a BBox, handling Antimeridian splitting.
    
    Args:
        bbox: [west, south, east, north]
    
    Returns:
        GeoJSON dict (Polygon or MultiPolygon) or None.
    """
    try:
        west, south, east, north = bbox
        
        # If west > east, it crosses the Antimeridian (e.g. 80, -60, -160, 60)
        # We construct a Polygon in 0-360 space (unwrapped) or handle splitting.
        # Ideally, we create a Polygon that might exceed 180, then use antimeridian to fix.
        
        if west > east:
            # Shift east coordinate to be > 180 (e.g. -160 -> 200)
            # This makes a valid contiguous box in "unwrapped" space
            east_unwrapped = east + 360
            poly = Polygon([
                (west, south),
                (east_unwrapped, south),
                (east_unwrapped, north),
                (west, north),
                (west, south)
            ])
        else:
            poly = Polygon([
                (west, south),
                (east, south),
                (east, north),
                (west, north),
                (west, south)
            ])
            
        # Fix using Antimeridian package
        # This splits it into a MultiPolygon [-180, east] and [west, 180] if needed
        fixed_poly = antimeridian.fix_polygon(poly)
        
        return mapping(fixed_poly)
        
    except Exception as e:
        warnings.warn(f"Failed to compute geometry: {e}")
        return None

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

from loguru import logger

def fix_pacific_bbox(collection: pystac.Collection, ds: xr.Dataset) -> None:
    """
    Detects if the dataset is Pacific-centered (crossing Antimeridian) and fixes the BBox.
    xstac often defaults to [-180, 180] when it sees values at both ends.
    We want [West(Pos), South, East(Neg), North].
    """
    try:
        # 1. Identify Longitude Coord
        lon_name = None
        if "longitude" in ds.coords: lon_name = "longitude"
        elif "lon" in ds.coords: lon_name = "lon"
        
        if not lon_name: return

        lons = ds[lon_name]
        # Ensure we are working with numpy array for coords (usually cheap)
        if hasattr(lons.data, "compute"):
            lons_vals = lons.values
        else:
            lons_vals = lons.data

        # 2. Check for Pacific View Pattern
        # Data exists at edges (-180..-90) AND (90..180)
        has_neg_edge = (lons_vals < -90).any()
        has_pos_edge = (lons_vals > 90).any()
        # BUT Data is missing in the middle (Prime Meridian)
        has_center = ((lons_vals > -20) & (lons_vals < 20)).any()
        
        if has_neg_edge and has_pos_edge and not has_center:
            logger.info(f"Detected Pacific View for {collection.id}. Correcting BBox...")
            
            # West = Min of Positive Segment
            # We must use masking to find the min of the positive side
            west = float(lons.where(lons > 0, drop=True).min())
            
            # East = Max of Negative Segment
            east = float(lons.where(lons < 0, drop=True).max())
            
            # Get Latitudes
            lat_name = "latitude" if "latitude" in ds.coords else "lat"
            south = float(ds[lat_name].min())
            north = float(ds[lat_name].max())
            
            # Update Collection Extent
            # STAC requires [west, south, east, north]
            # If west > east, it acts as Antimeridian crossing.
            new_bbox = [west, south, east, north]
            
            logger.info(f"Overriding BBox: {new_bbox}")
            collection.extent.spatial.bbox = [new_bbox]
            
    except Exception as e:
        logger.warning(f"Failed to fix Pacific BBox: {e}")
