#!/usr/bin/env python3
"""
Inspect IMERG datasets to extract actual metadata
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import intake
import xarray as xr
from rich.console import Console
from rich.table import Table
import traceback

console = Console()

def inspect_dataset(catalog_path: str, source_id: str):
    """Inspect a single dataset and extract metadata"""
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold yellow]Inspecting: {source_id}[/bold yellow]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")

    try:
        # Open catalog
        catalog = intake.open_catalog(catalog_path)

        # Get source
        if source_id not in catalog:
            console.print(f"[red]Error: Source '{source_id}' not found in catalog[/red]")
            return

        source = catalog[source_id]
        console.print(f"[green]✓[/green] Catalog loaded: {catalog_path}")
        console.print(f"[green]✓[/green] Source found: {source_id}")

        # Read dataset
        console.print(f"\n[yellow]Loading dataset...[/yellow]")
        ds = source.to_dask()
        console.print(f"[green]✓[/green] Dataset loaded successfully\n")

        # Extract metadata
        console.print("[bold]📊 Dataset Information:[/bold]\n")

        # 1. Dimensions
        table = Table(title="Dimensions", show_header=True, header_style="bold magenta")
        table.add_column("Dimension", style="cyan")
        table.add_column("Size", style="green")
        for dim, size in ds.dims.items():
            table.add_row(dim, str(size))
        console.print(table)

        # 2. Coordinates
        console.print("\n[bold]📍 Coordinates:[/bold]")
        for coord in ds.coords:
            coord_data = ds.coords[coord]
            if coord == 'time' and len(coord_data) > 0:
                start = str(coord_data.values[0])
                end = str(coord_data.values[-1])
                console.print(f"  • [cyan]{coord}[/cyan]: {start[:10]} to {end[:10]} ({len(coord_data)} timesteps)")
            elif len(coord_data) > 0:
                min_val = float(coord_data.min().values)
                max_val = float(coord_data.max().values)
                console.print(f"  • [cyan]{coord}[/cyan]: {min_val:.2f} to {max_val:.2f}")

        # 3. Data Variables
        console.print("\n[bold]📦 Data Variables:[/bold]")
        for var in ds.data_vars:
            var_data = ds[var]
            console.print(f"  • [cyan]{var}[/cyan]")
            console.print(f"    - Shape: {var_data.shape}")
            console.print(f"    - Dtype: {var_data.dtype}")
            if 'long_name' in var_data.attrs:
                console.print(f"    - Long name: {var_data.attrs['long_name']}")
            if 'units' in var_data.attrs:
                console.print(f"    - Units: {var_data.attrs['units']}")

        # 4. Global Attributes
        console.print("\n[bold]🏷️  Global Attributes:[/bold]")
        if ds.attrs:
            for key, value in list(ds.attrs.items())[:10]:  # Show first 10
                console.print(f"  • [cyan]{key}[/cyan]: {value}")
        else:
            console.print("  [dim]No global attributes found[/dim]")

        # 5. Time Range Summary
        if 'time' in ds.coords and len(ds.coords['time']) > 0:
            time_coord = ds.coords['time']
            start_time = str(time_coord.values[0])[:10]
            end_time = str(time_coord.values[-1])[:10]
            n_timesteps = len(time_coord)

            console.print(f"\n[bold green]✓ Time Coverage:[/bold green]")
            console.print(f"  Start: {start_time}")
            console.print(f"  End: {end_time}")
            console.print(f"  Total timesteps: {n_timesteps}")

        # 6. Spatial Coverage
        if 'lat' in ds.coords and 'lon' in ds.coords:
            lat_min = float(ds.coords['lat'].min().values)
            lat_max = float(ds.coords['lat'].max().values)
            lon_min = float(ds.coords['lon'].min().values)
            lon_max = float(ds.coords['lon'].max().values)

            console.print(f"\n[bold green]✓ Spatial Coverage:[/bold green]")
            console.print(f"  Latitude: {lat_min:.2f}° to {lat_max:.2f}°")
            console.print(f"  Longitude: {lon_min:.2f}° to {lon_max:.2f}°")

        console.print(f"\n[bold green]{'='*80}[/bold green]")
        console.print(f"[bold green]✓ Inspection completed for: {source_id}[/bold green]")
        console.print(f"[bold green]{'='*80}[/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error inspecting {source_id}:[/bold red]")
        console.print(f"[red]{str(e)}[/red]\n")
        console.print("[dim]Full traceback:[/dim]")
        console.print(traceback.format_exc())


if __name__ == "__main__":
    catalog_path = PROJECT_ROOT / "config/catalogs/imerg_intake_catalog.yaml"

    # Inspect both datasets
    datasets = ["imerg_monthly_v07"]

    for source_id in datasets:
        inspect_dataset(str(catalog_path), source_id)
