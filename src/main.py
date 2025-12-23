import typer
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
import logging
import sys
import intake
from .client.stac_client import StacClient
from .adapters.cwa import CwaGaugeAdapter
from .adapters.gridded import GriddedDataAdapter

# Configure logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("stac-cli")

app = typer.Typer(help="Research Lab STAC Manager CLI")
console = Console()

CLIENT = StacClient()

def get_adapter(entry_name: str, source: intake.DataSource, collection_id: str):
    """Factory to get the correct adapter based on source driver or metadata."""
    driver = source.container
    
    # Check specific drivers or metadata
    if driver == 'dataframe' or source.driver == 'csv': # simplified check
         return CwaGaugeAdapter(entry_name, source, collection_id)
    elif driver == 'xarray' or source.driver == 'zarr':
         return GriddedDataAdapter(entry_name, source, collection_id)
    else:
        # Fallback based on name or other metadata
        if 'gauge' in entry_name:
             return CwaGaugeAdapter(entry_name, source, collection_id)
        return GriddedDataAdapter(entry_name, source, collection_id)

# @app.command()
# def sync(
#     dataset: str = typer.Option("all", help="Dataset to sync: 'qpesums', 'era5', 'cwa', or 'all'"),
#     dry_run: bool = typer.Option(False, help="Run without making changes to the API")
# ):
#     """
#     [DEPRECATED] Synchronize datasets from Intake Catalog to STAC API.
#     This command requires a running STAC API (e.g. stac-fastapi), which has been removed from the default setup.
#     """
#     console.print("[red]This command is deprecated as the dynamic API infrastructure has been removed.[/red]")
#     console.print("Please use [bold]scripts/generate_stac.py[/bold] to generate static STAC files instead.")

# @app.command()
# def init_db():
#     """
#     [DEPRECATED] Initialize STAC Collections in the database.
#     """
#     console.print("[red]This command is deprecated as the dynamic API infrastructure has been removed.[/red]")

if __name__ == "__main__":
    app()
