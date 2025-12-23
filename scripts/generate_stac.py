import typer
from pathlib import Path
from src.generator.intake_xarray import IntakeXarrayGenerator
import intake

app = typer.Typer()

@app.command()
def main(
    source: str = typer.Option("era5_east_asia", help="Intake source name (e.g. era5_east_asia or era5_global_cj). Use 'all' to process all sources in the catalog(s)."),
    catalog: str = typer.Option(
        str(Path(__file__).parent.parent / "catalogs" / "era5_intake_catalog.yaml"),
        help="Path to the Intake catalog YAML file or a directory containing catalog YAML files."
    ),
) -> None:
    """
    Generate a static ERA5 STAC collection + per‑year items.
    """
    catalog_path = Path(catalog)
    catalogs_to_process = []
    
    if catalog_path.is_dir():
        catalogs_to_process = list(catalog_path.glob("*.yaml"))
    else:
        catalogs_to_process = [catalog_path]

    base_output_dir = Path(__file__).parent.parent / "stac_output"

    for cat_file in catalogs_to_process:
        print(f"📂 Opening catalog: {cat_file}")
        try:
            cat = intake.open_catalog(str(cat_file))
            
            sources_to_process = []
            if source == "all":
                sources_to_process = list(cat)
            else:
                if source in cat:
                    sources_to_process = [source]
                else:
                    # If specific source requested but not in this catalog, skip
                    print(f"  ⚠️ Source '{source}' not found in catalog '{cat_file}'. Skipping this catalog for this source.")
                    continue

            for src_name in sources_to_process:
                print(f"  🚀 Processing source: {src_name}")
                output_dir = base_output_dir / src_name
                
                try:
                    generator = IntakeXarrayGenerator(output_dir=output_dir, catalog_path=cat_file)
                    generator.generate(source_name=src_name)
                except Exception as e:
                    print(f"  ⚠️ Failed to generate STAC for {src_name} from catalog {cat_file}: {e}")
                    
        except Exception as e:
            print(f"⚠️ Failed to open catalog {cat_file}: {e}")

if __name__ == "__main__":
    app()
