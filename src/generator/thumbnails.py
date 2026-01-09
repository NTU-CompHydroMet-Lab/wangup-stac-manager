from __future__ import annotations
import matplotlib.pyplot as plt
import xarray as xr
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
from .utils import get_spatial_dims

# Set non-interactive backend for matplotlib
plt.switch_backend('Agg')

def generate_thumbnail(ds: xr.Dataset, item_id: str, items_dir: Path, target_var: Optional[str] = None) -> Optional[Dict[str, object]]:
    """Generate a simple map thumbnail (PNG) for the dataset."""
    logger.info(f"Generating thumbnail for {item_id}...")
    try:
        # 1. Select variable
        if not target_var:
            return None
            
        if target_var not in ds.data_vars:
            logger.warning(f"Targeted variable '{target_var}' not found in dataset. Skipping thumbnail.")
            return None
        
        var_name = target_var
        
        # 2. Compute mean over time to get 2D field
        lon, lat = get_spatial_dims(ds)
        if lon is None or lat is None:
            return None
            
        # Use max to ensure signal visibility and avoid blanks
        if "time" in ds.dims:
            da = ds[var_name].isel(time=slice(0, 48)).max(dim="time", keep_attrs=True)
        else:
            da = ds[var_name]
            
        # 3. Plot
        fig, ax = plt.subplots(figsize=(4, 4))
        
        # Explicitly specify x/y to ensure correct orientation
        x_name = lon.name
        y_name = lat.name
        
        # Use robust=True to handle outliers and scale colormap appropriately
        da.plot(ax=ax, x=x_name, y=y_name, add_colorbar=False, add_labels=False, cmap='viridis', robust=True)
        ax.set_axis_off()
        plt.tight_layout(pad=0)
        
        # 4. Save
        thumb_name = f"{item_id}_thumb.png"
        thumb_path = items_dir / thumb_name
        plt.savefig(thumb_path, transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        
        return {
            "href": f"./items/{thumb_name}",
            "type": "image/png",
            "roles": ["thumbnail"],
            "title": f"Thumbnail for {item_id}"
        }
    except Exception as e:
        logger.error(f"Thumbnail generation failed for {item_id}: {e}")
        return None
