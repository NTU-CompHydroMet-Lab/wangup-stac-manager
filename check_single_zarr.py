#!/usr/bin/env python3
"""
Check a single zarr file directly
"""
import xarray as xr
from rich.console import Console

console = Console()

# Open a single year zarr
zarr_path = "/home/NAS/homes/isaac-10009/Data/_bronze_data/IMERG_v07_monthly/imerg_V07_yearly_zarr/2023"

console.print(f"[yellow]Opening single zarr:[/yellow] {zarr_path}")

ds = xr.open_zarr(zarr_path)

console.print("\n[bold]Dataset Info:[/bold]")
console.print(ds)

console.print("\n[bold]Time coordinate:[/bold]")
console.print(f"  Length: {len(ds.time)}")
console.print(f"  First: {ds.time.values[0]}")
console.print(f"  Last: {ds.time.values[-1]}")
console.print(f"  Values: {ds.time.values}")

console.print("\n[bold]Precipitation variable:[/bold]")
console.print(f"  Shape: {ds.precipitation.shape}")
console.print(f"  Attrs: {ds.precipitation.attrs}")
