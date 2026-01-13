import json
from pathlib import Path
import shutil
from loguru import logger
import pystac
from src.settings import settings

def update_root_catalog(stac_output_dir: Path) -> None:
    """
    Generate a root STAC Catalog linking to all available Collections using PySTAC.
    """
    root_catalog_path = stac_output_dir / "catalog.json"
    
    # Create Root Catalog
    root = pystac.Catalog(
        id=settings.project.id,
        title=settings.project.title,
        description=settings.project.description
    )
    
    # Find all collection.json files
    # We look for immediate children of stac_output_dir AND children of sub-directories (if already moved)
    # But during first run, they are at root.
    # To be safe, we list ALL collection.json files recursively but exclude root catalog.json if it were named so (it's not).
    # Actually, glob("*/collection.json") only finds immediate children. 
    # If we re-run, they might be in group folders.
    # So we should search recursively.
    collection_paths = list(stac_output_dir.rglob("collection.json"))
    
    # Config for groups
    groups = {}
    
    # 1. Group Collections
    for col_path in collection_paths:
        try:
            col = pystac.Collection.from_file(str(col_path))
            
            # Use explicit group_id from metadata (injected by Generator from Intake 'catalog_name')
            # Fallback to 'ungrouped' if not set, preventing random splitting behavior.
            group_name = col.extra_fields.get("group_id", "ungrouped")
            
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(col)
        except Exception as e:
            logger.warning(f"Failed to load collection {col_path}: {e}")

    # 2. Build Hierarchy & Move Files
    for group_name, cols in groups.items():
        # Create Group Catalog
        group_dir = stac_output_dir / group_name
        group_dir.mkdir(exist_ok=True)
        
        first_col = cols[0]
        
        # 1. Group Keywords
        group_keywords = first_col.extra_fields.get("group_keywords", [])
        
        # 2. Group Title (Original Casing)
        group_title = first_col.extra_fields.get("group_title", group_name.replace("_", " ").title())
        
        # 3. Group Description (From Intake YAML metadata)
        group_desc = first_col.extra_fields.get("group_description", f"Group Catalog for {group_name}")
        
        # Create Group Catalog
        group_cat = pystac.Catalog(
            id=group_name,
            description=group_desc,
            title=group_title
        )
        if group_keywords:
            group_cat.extra_fields["keywords"] = group_keywords

        group_cat.set_self_href(str(group_dir / "catalog.json"))
        group_cat.save(catalog_type=pystac.CatalogType.SELF_CONTAINED) # matches directory name
        
        for col in cols:
            # Move collection directory if it's currently at root
            # Current location based on col.self_href
            old_col_dir = Path(col.self_href).parent
            if old_col_dir.parent == stac_output_dir and old_col_dir.name != group_name:
                new_col_dir = group_dir / old_col_dir.name
                if not new_col_dir.exists():
                    try:
                        shutil.move(str(old_col_dir), str(new_col_dir))
                        logger.info(f"Moved {old_col_dir.name} to {group_name}/")
                        # Update collection href to new location
                        col.set_self_href(str(new_col_dir / "collection.json"))
                    except Exception as e:
                        logger.error(f"Failed to move {old_col_dir} to {new_col_dir}: {e}")

            group_cat.add_child(col)
        
        root.add_child(group_cat)

    # 3. Save
    # Normalize hrefs to ensure links are strictly relative to basic structure
    root.normalize_hrefs(str(stac_output_dir))
    root.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    
    logger.info(f"Root Catalog written to {root_catalog_path}")
