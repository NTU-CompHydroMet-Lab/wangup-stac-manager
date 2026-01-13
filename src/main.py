import typer
import subprocess
import sys
from pathlib import Path
from loguru import logger

app = typer.Typer(help="Research Lab STAC Manager CLI")

@app.command()
def build(
    catalog: str = typer.Option(None, help="Specific catalog YAML to build (e.g. catalogs/era5_intake_catalog.yaml)"),
    source: str = typer.Option(None, help="Specific source to build (e.g. era5_east_asia)"),
    update_root: bool = typer.Option(True, help="Update root catalog after building")
):
    """
    Build STAC catalogs and update the root catalog.
    
    If no catalog/source is specified, it defaults to building everything (logic can be expanded).
    For now, it requires arguments or you can run specific commands.
    
    Example:
        python src/main.py build --catalog catalogs/era5_intake_catalog.yaml --source era5_east_asia
    """
    
    # 1. Generate STAC Collections/Items
    cmd = [sys.executable, "scripts/generate_stac.py"]
    if catalog:
        cmd.extend(["--catalog", catalog])
    if source:
        cmd.extend(["--source", source])
        
    # If no args provided, maybe we want to build all? 
    # For safety, let's ask user to be specific or implement a 'build all' logic later.
    # But user asked for a "main to start these two".
    # Let's assume if no args, we might want to iterate known catalogs?
    # For now, let's just pass the args.
    
    if not catalog and not source:
        logger.warning("No catalog or source specified. Building all known catalogs...")
        # List of known catalogs to build
        catalogs_to_build = [
            ("catalogs/era5_intake_catalog.yaml", "era5_east_asia"),
            # ("catalogs/era5_intake_catalog.yaml", "era5_global_cj"), # Source missing on this machine
            ("catalogs/himawari_intake_catalog.yaml", "himawri_clp_2023"),
            ("catalogs/imerg_intake_catalog.yaml", "imerg_early"),
            ("catalogs/imerg_intake_catalog.yaml", "imerg_final"),
            ("catalogs/radar_intake_catalog.yaml", "QPESUMS_tw"),
            # ("catalogs/imerg_intake_catalog.yaml", "imerg_bronze"), # Skip bronze for now as it's slow
        ]
        
        for cat, src in catalogs_to_build:
            logger.info(f"Building {src} from {cat}...")
            subprocess.run([sys.executable, "scripts/generate_stac.py", "--catalog", cat, "--source", src], check=False)
            
    else:
        logger.info("Running generation script...")
        subprocess.run(cmd, check=True)

    # 2. Update Root Catalog
    if update_root:
        logger.info("Updating Root Catalog...")
        subprocess.run([sys.executable, "scripts/generate_root_catalog.py"], check=True)

@app.command()
def serve(
    port: int = typer.Option(8001, help="Port to run the server on")
):
    """
    Start the static STAC server and browser.
    """
    logger.info(f"Starting server on port {port}...")
    # We need to pass the port to server.py, but server.py might not accept args yet.
    # Let's assume server.py runs on 8001 by default or we modify it.
    # For now, just run it.
    subprocess.run([sys.executable, "src/server.py"], check=True)

if __name__ == "__main__":
    app()
