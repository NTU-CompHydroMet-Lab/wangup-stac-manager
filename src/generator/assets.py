from __future__ import annotations
import shutil
from pathlib import Path
from typing import Optional
from loguru import logger
import pystac

def process_example_notebook(nb_path: str, output_dir: Path) -> Optional[pystac.Asset]:
    """Copy example notebook to output and return Asset object."""
    try:
        src_path = Path(nb_path)
        if not src_path.exists():
            logger.warning(f"Example notebook not found: {src_path}")
            return None
            
        examples_dir = output_dir / "examples"
        examples_dir.mkdir(exist_ok=True)
        
        dest_path = examples_dir / src_path.name
        shutil.copy2(src_path, dest_path)
        
        return pystac.Asset(
            href=f"./examples/{src_path.name}",
            media_type="application/x-ipynb+json",
            roles=["example", "docs"],
            title="Example Usage Notebook"
        )
    except Exception as e:
        logger.error(f"Failed to process example notebook: {e}")
        return None

def create_data_asset(source_path: str, item_id: str, items_dir: Path) -> pystac.Asset:
    """Create a local symlink to the data source and return the pystac.Asset."""
    # --- Local Symlink Strategy ---
    src_path_obj = Path(source_path)
    
    # Determine extension
    ext = ".zarr" if str(source_path).endswith(".zarr") else ".nc"
    if src_path_obj.suffix:
        ext = src_path_obj.suffix
        
    # Asset filename in the items folder
    asset_filename = f"{item_id}{ext}"
    asset_link_path = items_dir / asset_filename
    
    # Create Symlink if not exists (or update)
    if asset_link_path.exists() or asset_link_path.is_symlink():
        asset_link_path.unlink()
    
    media_type = "application/vnd+zarr" if ext == ".zarr" else "application/x-netcdf"
    
    try:
        # Check if source exists? If it's on a mounted drive, it should.
        asset_link_path.symlink_to(src_path_obj)
        logger.info(f"Created symlink: {asset_link_path.name} -> {src_path_obj}")
        
        return pystac.Asset(
            href=f"./{asset_filename}",
            media_type=media_type,
            roles=["data"],
            title=f"Data for {item_id}"
        )
    except Exception as e:
        logger.error(f"Failed to symlink asset {src_path_obj}: {e}")
        # Fallback to absolute path
        return pystac.Asset(
            href=str(src_path_obj),
            media_type=media_type,
            roles=["data"],
            title=f"Data for {item_id} (Absolute Path)"
        )
