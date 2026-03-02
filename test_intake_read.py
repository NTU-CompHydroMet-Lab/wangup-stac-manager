#!/usr/bin/env python3
"""
Test reading through intake catalog directly
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import intake
from rich.console import Console

console = Console()

# Open the intake catalog
catalog_path = "config/catalogs/imerg_intake_catalog.yaml"
console.print(f"[yellow]Opening intake catalog:[/yellow] {catalog_path}\n")

cat = intake.open_catalog(catalog_path)

# List available sources
console.print("[bold]Available sources:[/bold]")
for source_name in cat:
    console.print(f"  • {source_name}")

console.print("\n" + "="*80 + "\n")

# Read imerg_monthly_v07 through intake
console.print("[yellow]Reading imerg_monthly_v07 through intake...[/yellow]\n")

source = cat.imerg_monthly_v07
console.print(f"[cyan]Source metadata:[/cyan]")
console.print(f"  Type: {type(source).__name__}")
console.print(f"  Description: {source.description}")

console.print(f"\n[yellow]Loading to dask...[/yellow]")
ds = source.to_dask()

console.print(f"\n[bold green]✓ Dataset loaded![/bold green]\n")
console.print(ds)

console.print("\n[bold]Dimensions:[/bold]")
for dim, size in ds.sizes.items():
    console.print(f"  {dim}: {size}")

console.print("\n[bold]Time coordinate info:[/bold]")
if 'time' in ds.coords:
    time = ds.time
    console.print(f"  Length: {len(time)}")
    console.print(f"  Start: {time.values[0]}")
    console.print(f"  End: {time.values[-1]}")
    console.print(f"  Frequency: {time.values[1] - time.values[0] if len(time) > 1 else 'N/A'}")

    # Check if monthly by sampling
    if len(time) > 2:
        console.print(f"\n  [cyan]First 5 timestamps:[/cyan]")
        for t in time.values[:5]:
            console.print(f"    {t}")
        console.print(f"  [cyan]Last 5 timestamps:[/cyan]")
        for t in time.values[-5:]:
            console.print(f"    {t}")

console.print("\n[bold]Variables:[/bold]")
for var in ds.data_vars:
    console.print(f"  {var}: {ds[var].shape} ({ds[var].dtype})")
    if hasattr(ds[var], 'units'):
        console.print(f"    units: {ds[var].units}")
    if hasattr(ds[var], 'long_name'):
        console.print(f"    long_name: {ds[var].long_name}")
