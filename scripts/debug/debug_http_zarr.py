import xarray as xr
import requests
import time

# URL construction (mimicking what user copies + domain)
# Item: era5_east_asia-2019
# Href from STAC: ./era5_east_asia-2019.zarr -> /stac/era5_east_asia/items/era5_east_asia-2019.zarr
BASE_URL = "http://localhost:8001"
ZARR_PATH = "/stac/era5_east_asia/items/era5_east_asia-2019.zarr"
FULL_URL = f"{BASE_URL}{ZARR_PATH}"

print(f"Testing access to: {FULL_URL}")

# 1. Simple connectivity check
try:
    # Zarr roots usually have .zgroup
    r = requests.get(f"{FULL_URL}/.zgroup")
    print(f"GET .zgroup status: {r.status_code}")
    if r.status_code != 200:
        print("Failed to reach Zarr root. Is server running?")
        print(r.text[:200])
except Exception as e:
    print(f"Connection failed: {e}")

# 2. Xarray Open
try:
    print("Attempting xr.open_dataset...")
    ds = xr.open_dataset(FULL_URL, engine="zarr", chunks={})
    print("Success!")
    print(ds)
except Exception as e:
    print(f"Xarray failed: {e}")
