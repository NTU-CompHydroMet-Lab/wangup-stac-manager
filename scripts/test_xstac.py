import xstac
import intake
import xarray as xr
import pystac
import json
import sys
from pathlib import Path

def main():
    print("🚀 Starting xstac test...")
    
    # 1. Load Source (ERA5)
    catalog_path = "catalogs/era5_intake_catalog.yaml"
    source_name = "era5_east_asia"
    
    print(f"📂 Opening catalog: {catalog_path}")
    cat = intake.open_catalog(catalog_path)
    source = cat[source_name]
    
    print(f"📦 Loading dataset (lazy)...")
    ds = source.to_dask()
    
    # Slice for one year to test item generation
    ds_2019 = ds.sel(time="2019")
    
    print("⚙️ Generating STAC Item using xstac...")
    
    # xstac template
    # item_template = pystac.Item(...) # Removed to avoid validation error
    
    print("⚙️ Generating STAC Collection using xstac...")
    
    collection_template = pystac.Collection(
        id="era5_east_asia",
        description="ERA5 East Asia Test",
        extent=pystac.Extent(
            pystac.SpatialExtent([[-180, -90, 180, 90]]),
            pystac.TemporalExtent([[None, None]])
        ),
        license="CC-BY-4.0"
    )
    
    # Run xstac
    # reference_system is often needed if no CRS in dataset
    try:
        out_col = xstac.xarray_to_stac(
            ds_2019, 
            collection_template,
            reference_system="EPSG:4326",
            temporal_dimension="time",
            x_dimension="longitude",
            y_dimension="latitude"
        )
        
        out_col.normalize_hrefs("./xstac_output")
        
        print("\n✅ xstac Generation Successful!")
        print("-" * 40)
        print(json.dumps(out_col.to_dict(), indent=2))
        print("-" * 40)
        
        # Check for datacube extension
        print("\n🔍 Checking for extensions:")
        for ext in out_col.stac_extensions:
            print(f"  - {ext}")
            
        # Check summaries (variables)
        print("\n📊 Summaries (Variables):")
        if out_col.summaries:
            for key, val in out_col.summaries.lists.items():
                print(f"  - {key}: {val}")
        
    except Exception as e:
        print(f"❌ xstac failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
