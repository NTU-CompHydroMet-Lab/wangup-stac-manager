
import xarray as xr
import intake
from pathlib import Path

# Path from catalog
zarr_path = "/home/sungche/NAS/dataset/himawari/CLP_zarr/2023_01_clp_5km.zarr"

try:
    print(f"Opening {zarr_path}...")
    ds = xr.open_zarr(zarr_path, consolidated=False)
    
    print("\n--- Dimensions ---")
    print(ds.dims)
    
    print("\n--- Coordinates ---")
    print(ds.coords)
    
    print("\n--- Coordinate Values (Min/Max) ---")
    for c in ds.coords:
        try:
            val = ds[c]
            # Print first few and min/max
            print(f"{c}: min={val.min().values}, max={val.max().values}, shape={val.shape}")
        except Exception as e:
            print(f"{c}: Could not compute min/max: {e}")

    print("\n--- Attributes ---")
    print(ds.attrs)
    
    # --- Test xstac ---
    import xstac
    import pystac
    
    print("\n--- Testing xstac with wrapping ---")
    
    template = pystac.Collection(
        id="test",
        description="test",
        extent=pystac.Extent(pystac.SpatialExtent([[-180,-90,180,90]]), pystac.TemporalExtent([[None, None]])),
        license="CC-BY-4.0"
    )

    # Wrap longitude to -180/180
    ds_wrapped = ds.copy()
    ds_wrapped.coords["longitude"] = (ds_wrapped.coords["longitude"] + 180) % 360 - 180
    ds_wrapped = ds_wrapped.sortby("longitude") # Sort helps xstac?
    
    kw = {
        "reference_system": "EPSG:4326",
        "temporal_dimension": "time",
        "x_dimension": "longitude",
        "y_dimension": "latitude"
    }
    
    enriched = xstac.xarray_to_stac(ds_wrapped, template, **kw)

    print("Enriched Extent:")
    print(enriched.extent.spatial.bboxes)

except Exception as e:
    print(f"Failed to inspect: {e}")
