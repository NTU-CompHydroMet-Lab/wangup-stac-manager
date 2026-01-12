import intake
import xarray as xr

def check_imerg_early():
    cat = intake.open_catalog("catalogs/imerg_intake_catalog.yaml")
    source = cat["imerg_early"]
    ds = source.to_dask()
    print("Variables in imerg_early:")
    for var in ds.data_vars:
        print(f" - {var}")

if __name__ == "__main__":
    check_imerg_early()
