import intake
import xarray as xr

def main():
    cat_path = "catalogs/imerg_intake_catalog.yaml"
    cat = intake.open_catalog(cat_path)
    print(f"Sources: {list(cat)}")
    
    source = cat["imerg_early"]
    ds = source.to_dask()
    print("Coordinates:", list(ds.coords))
    print("Dimensions:", list(ds.dims))
    print(ds)

if __name__ == "__main__":
    main()
