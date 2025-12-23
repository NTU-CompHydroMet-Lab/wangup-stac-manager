import typer
from pathlib import Path
import pystac
import sys

app = typer.Typer()

@app.command()
def main(
    catalog_path: str = typer.Option(
        str(Path(__file__).parent.parent / "stac_output" / "catalog.json"),
        help="Path to the root STAC catalog.json"
    )
) -> None:
    """
    Validate a STAC Catalog and all its children using pystac.
    """
    path = Path(catalog_path)
    if not path.exists():
        print(f"❌ Catalog not found: {path}")
        sys.exit(1)

    print(f"🔍 Validating STAC Catalog: {path}")
    
    try:
        # Read the catalog
        catalog = pystac.read_file(str(path))
        
        # Validate the root catalog itself
        catalog.validate()
        print(f"✅ Root Catalog '{catalog.id}' is valid.")
        
        # Walk through all children and items
        validated_count = 1 # Root is already validated
        
        # pystac.Catalog.walk() yields (catalog, children, items)
        for root, children, items in catalog.walk():
            for child in children:
                try:
                    child.validate()
                    print(f"  ✅ Collection '{child.id}' is valid.")
                    validated_count += 1
                except Exception as e:
                    print(f"  ❌ Collection '{child.id}' validation failed: {e}")
            
            for item in items:
                try:
                    item.validate()
                    # print(f"    ✅ Item '{item.id}' is valid.") # Comment out to reduce noise
                    validated_count += 1
                except Exception as e:
                    print(f"    ❌ Item '{item.id}' validation failed: {e}")
                    
        print(f"\n🎉 Validation Complete! Checked {validated_count} STAC objects.")
        
    except Exception as e:
        print(f"❌ Fatal Error during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    app()
