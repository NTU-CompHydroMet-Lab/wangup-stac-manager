
import intake
import xarray as xr
import matplotlib.pyplot as plt
from pathlib import Path

# Mock Generator Context
class MockGen:
    def __init__(self):
        self.items_dir = Path("stac_output/imerg_early/items")
        self.items_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_spatial_dims(self, ds):
        lon = ds.longitude if "longitude" in ds.coords else ds.lon if "lon" in ds.coords else None
        lat = ds.latitude if "latitude" in ds.coords else ds.lat if "lat" in ds.coords else None
        return lon, lat

def test_thumbnail():
    print("🚀 Testing Thumbnail Generation for IMERG Early...")
    cat = intake.open_catalog("catalogs/imerg_intake_catalog.yaml")
    source = cat["imerg_early"]
    ds = source.to_dask()
    
    target_var = "precipitation"
    print(f"Dataset vars: {list(ds.data_vars)}")
    
    if target_var not in ds.data_vars:
        print(f"❌ Variable {target_var} not found!")
        return

    gen = MockGen()
    lon, lat = gen._get_spatial_dims(ds)
    print(f"Dimensions: lon={lon.name if lon is not None else 'None'}, lat={lat.name if lat is not None else 'None'}")
    
    try:
        if "time" in ds.dims:
            print("Aggregating time (max of first 48)...")
            da = ds[target_var].isel(time=slice(0, 48)).max(dim="time", keep_attrs=True)
        else:
            da = ds[target_var]
            
        print("Plotting...")
        fig, ax = plt.subplots(figsize=(4, 4))
        da.plot(ax=ax, x=lon.name, y=lat.name, add_colorbar=False, add_labels=False, cmap='viridis', robust=True)
        ax.set_axis_off()
        plt.savefig("test_thumb.png")
        print("✅ Thumbnail saved to test_thumb.png")
    except Exception as e:
        print(f"❌ Generation failed: {e}")

if __name__ == "__main__":
    test_thumbnail()
