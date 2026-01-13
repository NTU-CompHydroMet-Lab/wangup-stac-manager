import asyncio
import sys
import json
import socket
import subprocess
import os
import shutil
from pathlib import Path

# Setup Path immediately for local imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Now we can import from src safely if needed, though they are usually distinct.
# Standard Libs continued
from typing import List, Optional, Annotated
from concurrent.futures import ProcessPoolExecutor, as_completed

# Third Party
import typer
from pydantic import BaseModel, ValidationError
from beartype import beartype
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

# Import Core Modules (Local)
from src.core.builder import build_collection
from src.core.root_catalog import update_root_catalog
from src.settings import settings

STAC_OUTPUT_DIR = PROJECT_ROOT / settings.filesystem.output_dir

# Rich Console
console = Console()

# --- 1. Pydantic Models for Configuration ---
class CatalogConfig(BaseModel):
    catalog_path: Path
    source_id: str

    model_config = {
        "frozen": True  # Immutable
    }

# --- 2. Build Wrapper for ProcessPool ---
# Must be top-level for pickling
def _build_wrapper(config: CatalogConfig, output_dir: Path) -> str:
    """Wrapper to run build_collection in a separate process."""
    try:
        # Pydantic path might be absolute or relative, ensure absolute for safety
        full_cat_path = PROJECT_ROOT / config.catalog_path
        build_collection(full_cat_path, config.source_id, output_dir)
        return config.source_id
    except Exception as e:
        # Re-raise with source info
        raise RuntimeError(f"Build failed for {config.source_id}: {e}")

# --- 3. CLI Application ---
app = typer.Typer(
    help="[bold green]Research Lab STAC Manager CLI[/bold green] (v2.1 - Core Integrated)",
    rich_markup_mode="rich"
)

@app.command()
def build(
    catalog: Annotated[Optional[Path], typer.Option(help="Specific catalog YAML path")] = None,
    source: Annotated[Optional[str], typer.Option(help="Specific source ID")] = None,
    clean: Annotated[bool, typer.Option(help="Clean output directory before building")] = False,
    update_root: Annotated[bool, typer.Option(help="Update root catalog after building")] = True,
    parallel: Annotated[bool, typer.Option(help="Run builds in parallel")] = True,
    validate: Annotated[bool, typer.Option(help="Run STAC validation after build")] = False,
):
    """
    [bold yellow]Build STAC catalogs[/bold yellow] from Intake sources.
    
    If no arguments provided, builds [bold]ALL[/bold] catalogs defined in `config/main.yaml`.
    """
    # Clean output if requested
    if clean:
        if STAC_OUTPUT_DIR.exists():
            logger.warning(f"Cleaning output directory: {STAC_OUTPUT_DIR}")
            shutil.rmtree(STAC_OUTPUT_DIR)
        STAC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Determine what to build
    targets: List[CatalogConfig] = []
    
    if catalog and source:
        targets.append(CatalogConfig(catalog_path=catalog, source_id=source))
    elif catalog or source:
        console.print("[bold red]Error:[/bold red] You must provide BOTH --catalog and --source, or NEITHER.")
        raise typer.Exit(code=1)
    else:
        # Load from settings
        if not settings or not settings.build.targets:
            console.print("[yellow]No targets found in config/main.yaml[/yellow]")
            return
            
        targets = [
            CatalogConfig(catalog_path=Path(t.catalog), source_id=t.source)
            for t in settings.build.targets
        ]

    # Execution Logic
    logger.info(f"Queuing {len(targets)} build tasks...")
    
    failed_tasks = []
    # Use config default for parallel workers, or 1 if linear
    max_workers = settings.concurrency.max_workers if parallel else 1
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=False
    ) as progress:
        task_id = progress.add_task("Building Catalogs...", total=len(targets))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_source = {
                executor.submit(_build_wrapper, t, STAC_OUTPUT_DIR): t.source_id 
                for t in targets
            }
            
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    result = future.result()
                    logger.success(f"[{source_name}] Completed.")
                except Exception as exc:
                    logger.error(f"[{source_name}] Failed: {exc}")
                    failed_tasks.append(source_name)
                finally:
                    progress.advance(task_id)

    if failed_tasks:
        console.print(f"[bold red]Build failed for {len(failed_tasks)} sources:[/bold red] {', '.join(failed_tasks)}")
        # Don't exit yet, might want to update root catalog for partially successful ones?
        # Typically we shouldn't unless requested. But let's check update_root.

    # Update Root Catalog
    if update_root:
        logger.info("Updating Root Catalog...")
        try:
            update_root_catalog(STAC_OUTPUT_DIR)
            logger.success("Root Catalog updated.")
        except Exception as e:
            logger.error(f"Failed to update root catalog: {e}")
            
    # Optional Validation
    if validate:
        from src.core.validator import validate_catalog
        logger.info("Running post-build validation...")
        if not validate_catalog(STAC_OUTPUT_DIR / "catalog.json"):
            logger.warning("Catalog validation failed. Check logs for details.")
        else:
            logger.success("Catalog validation passed.")

@app.command()
def serve(
    port: Annotated[int, typer.Option(help="Port to run the server on")] = settings.server.port,
    host: Annotated[str, typer.Option(help="Host address")] = settings.server.host
):
    """
    [bold green]Start the static STAC server.[/bold green]
    Checks for port availability before starting Uvicorn.
    """
    # Port Check
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    
    if result == 0:
        console.print(f"[bold red]Error:[/bold red] Port {port} is already in use.")
        raise typer.Exit(code=1)
        
    console.print(Panel(f"Starting STAC Server at http://{host}:{port}", title="Server Launch", border_style="green"))
    
    # Run Uvicorn via subprocess (uvicorn is an app, easier to run as subprocess for reloading)
    # We could run programmatically, but reloading is tricky programmatically.
    cmd = [sys.executable, "-m", "uvicorn", "src.server.app:app", "--host", host, "--port", str(port), "--reload"]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")

if __name__ == "__main__":
    app()
