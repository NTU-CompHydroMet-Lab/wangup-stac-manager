import intake
import xarray as xr
import sys
import numpy as np

def check_radar():
    print("\n--- Checking QPESUMS ---")
    try:
        cat = intake.open_catalog("catalogs/radar_intake_catalog.yaml")
        ds = cat.QPESUMS_tw.to_dask()
        print("Dimensions:", list(ds.dims))
        print("Variables:", list(ds.data_vars))
        
        # Check first time step
        da = ds.MaxDBZ.isel(time=0)
        print(f"MaxDBZ (t=0) min: {da.min().values}, max: {da.max().values}")
        print(f"MaxDBZ (t=0) non-nan count: {da.count().values}")
    except Exception as e:
        print("Error checking Radar:", e)

def check_era5():
    print("\n--- Checking ERA5 East Asia ---")
    try:
        cat = intake.open_catalog("catalogs/era5_intake_catalog.yaml")
        ds = cat.era5_east_asia.to_dask()
        print("Variables:", list(ds.data_vars))
        
        if "sea_surface_temperature" in ds.data_vars:
            print("✅ 'sea_surface_temperature' found.")
        elif "sst" in ds.data_vars:
            print("⚠️ 'sea_surface_temperature' NOT found, but 'sst' found.")
        else:
            print("❌ Target variable NOT found.")
            
    except Exception as e:
        print("Error checking ERA5:", e)

if __name__ == "__main__":
    check_radar()
    check_era5()
