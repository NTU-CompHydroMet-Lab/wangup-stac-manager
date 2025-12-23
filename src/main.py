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

@app.command()
def sync(
    dataset: str = typer.Option("all", help="Dataset to sync: 'qpesums', 'era5', 'cwa', or 'all'"),
    dry_run: bool = typer.Option(False, help="Run without making changes to the API")
):
    """
    Synchronize datasets from Intake Catalog to STAC API.
    """
    console.print(f"[bold green]Starting sync for dataset: {dataset}[/bold green]")
    if dry_run:
        console.print("[yellow]DRY RUN MODE: No changes will be made to the API[/yellow]")

    # 1. Load Intake Catalog
    try:
        cat = intake.open_catalog("catalog.yaml")
    except Exception as e:
        console.print(f"[bold red]Failed to load catalog.yaml: {e}[/bold red]")
        raise typer.Exit(code=1)

    # 2. Iterate through sources
    for entry_name, source in cat.items():
        if dataset != "all" and dataset not in entry_name:
            continue
            
        console.print(f"Processing {entry_name}...")
        
        # Determine Collection ID (using entry name as ID for simplicity, or from metadata)
        collection_id = entry_name
        
        # Check if collection exists
        if not CLIENT.collection_exists(collection_id):
            console.print(f"[yellow]Collection {collection_id} does not exist. Please run init-db first.[/yellow]")
            continue

        # 3. Apply adapters
        try:
            adapter = get_adapter(entry_name, source, collection_id)
            
            for item in adapter.get_items():
                item_dict = item.to_dict()
                
                # 4. Post to STAC API
                if not dry_run:
                    if CLIENT.item_exists(collection_id, item.id):
                        console.print(f"  Item {item.id} exists. Skipping (or updating if implemented).")
                        # Optional: Check if update is needed
                    else:
                        if CLIENT.create_item(collection_id, item_dict):
                            console.print(f"  [green]Created item {item.id}[/green]")
                        else:
                            console.print(f"  [red]Failed to create item {item.id}[/red]")
                else:
                    console.print(f"  [dim]Would create item {item.id}[/dim]")
                    
        except Exception as e:
            logger.exception(f"Error processing {entry_name}: {e}")
            continue

    console.print(f"[bold blue]Sync complete for {dataset}[/bold blue]")

@app.command()
def init_db():
    """
    Initialize STAC Collections in the database.
    """
    console.print("[bold green]Initializing STAC Collections...[/bold green]")
    
    try:
        cat = intake.open_catalog("catalog.yaml")
    except Exception as e:
        console.print(f"[bold red]Failed to load catalog.yaml: {e}[/bold red]")
        raise typer.Exit(code=1)

    for entry_name, source in cat.items():
        metadata = source.metadata
        description = source.description or entry_name
        
        # Define Collection
        collection = {
            "id": entry_name,
            "type": "Collection",
            "stac_version": "1.0.0",
            "description": description,
            "license": "proprietary",
            "extent": {
                "spatial": {
                    "bbox": [[-180, -90, 180, 90]] # Default global, should be refined
                },
                "temporal": {
                    "interval": [["2000-01-01T00:00:00Z", None]] # Default open-ended
                }
            },
            "links": []
        }
        
        # Add extra properties from Intake metadata
        # STAC Collection doesn't have 'properties' field at top level like Item, 
        # but we can put them in 'summaries' or just rely on description.
        # For now, we keep it simple.
        
        if CLIENT.create_collection(collection):
            console.print(f"[green]Initialized collection: {entry_name}[/green]")
        else:
            console.print(f"[red]Failed to initialize collection: {entry_name}[/red]")

    console.print("[bold blue]Initialization complete[/bold blue]")

if __name__ == "__main__":
    app()
