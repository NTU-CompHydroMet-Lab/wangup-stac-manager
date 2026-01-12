import intake
import xarray as xr
import sys

try:
    cat = intake.open_catalog("catalogs/radar_intake_catalog.yaml")
    ds = cat.QPESUMS_tw.to_dask()
    print("Dimensions:", list(ds.dims))
    print("Coordinates:", list(ds.coords))
    print("Data Vars:", list(ds.data_vars))
except Exception as e:
    print("Error opening QPESUMS:", e)
