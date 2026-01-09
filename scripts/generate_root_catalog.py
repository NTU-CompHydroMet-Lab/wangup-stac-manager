import json
from pathlib import Path
import typer
from loguru import logger

app = typer.Typer()

@app.command()
def main() -> None:
    """
    Generate a root STAC Catalog linking to all available Collections.
    """
    stac_output_dir = Path(__file__).parent.parent / "stac_output"
    root_catalog_path = stac_output_dir / "catalog.json"
    
    # Find all collection.json files in subdirectories
    collections = list(stac_output_dir.glob("*/collection.json"))

    # Group collections by prefix
    groups = {}
    for col_path in collections:
        try:
            col_data = json.loads(col_path.read_text())
            col_id = col_data.get("id", col_path.parent.name)
            
            # Determine group based on prefix (e.g. era5_east_asia -> era5)
            # If no underscore, use 'other' or the id itself
            # Determine group based on prefix
            parts = col_id.split('_')
            group_name = parts[0] if len(parts) > 1 else "other"
            
            if group_name not in groups:
                groups[group_name] = []
            
            groups[group_name].append({
                "path": col_path,
                "data": col_data,
                "id": col_id
            })
        except Exception as e:
            logger.warning(f"Failed to read collection {col_path}: {e}")
    
    root_links = [
        {"rel": "root", "href": "./catalog.json", "type": "application/json"},
        {"rel": "self", "href": "./catalog.json", "type": "application/json"},
    ]
    
    for group_name, cols in groups.items():
        # If only one collection in group and it matches group name (unlikely with prefix logic but possible), 
        # or if we want flat structure for 'other', handle here. 
        # For now, create a sub-catalog for each group.
        
        group_catalog_path = stac_output_dir / f"{group_name}_catalog.json"
        
        group_links = [
            {"rel": "root", "href": "./catalog.json", "type": "application/json"},
            {"rel": "parent", "href": "./catalog.json", "type": "application/json"},
            {"rel": "self", "href": f"./{group_name}_catalog.json", "type": "application/json"},
        ]
        
        for col in cols:
            # Link from Group Catalog to Collection
            col_rel_path = f"./{col['path'].parent.name}/collection.json"
            group_links.append({
                "rel": "child",
                "href": col_rel_path,
                "type": "application/json",
                "title": col['data'].get("description", col['id'])
            })
            
            # Update Collection to point to Group Catalog as parent
            # Note: This modifies the generated collection.json!
            # We need to be careful. Ideally generator handles this, but here we are post-processing.
            # Let's just update the parent link in the collection.
            col_data = col['data']
            new_links = [l for l in col_data['links'] if l['rel'] != 'parent' and l['rel'] != 'root']
            new_links.append({"rel": "root", "href": "../catalog.json", "type": "application/json"})
            new_links.append({"rel": "parent", "href": f"../{group_name}_catalog.json", "type": "application/json"})
            col_data['links'] = new_links
            col['path'].write_text(json.dumps(col_data, indent=2))
            
        # Get category from first collection's summaries
        # We assume consistent category per group
        first_col_data = cols[0]['data']
        summaries = first_col_data.get("summaries", {})
        categories = summaries.get("category", ["DATA"])
        category = categories[0] if categories else "DATA"
        
        # User requested uppercase name only, no tags
        display_title = group_name.upper()

        group_catalog = {
            "type": "Catalog",
            "id": f"{group_name}-catalog",
            "title": display_title,
            "stac_version": "1.0.0",
            "description": f"Catalog for {group_name} datasets",
            "links": group_links
        }
        group_catalog_path.write_text(json.dumps(group_catalog, indent=2))
        logger.info(f"Created Group Catalog: {group_catalog_path}")
        
        # Link Root to Group
        root_links.append({
            "rel": "child",
            "href": f"./{group_name}_catalog.json",
            "type": "application/json",
            "title": display_title
        })
        
    catalog = {
        "type": "Catalog",
        "id": "stac-root-catalog",
        "title": "NTU CompHydroMet Lab Data Catalog",
        "stac_version": "1.0.0",
        "description": (
            "The [NTU CompHydroMet Lab](https://wangup.caece.net/) Data Catalog.\n\n"
            "See also:\n\n"
            "- [Lab Website](https://wangup.caece.net/)\n"
            "- [GitHub Repository](https://github.com/NTU-CompHydroMet-Lab)\n"
        ),
        "links": root_links
    }

    
    root_catalog_path.write_text(json.dumps(catalog, indent=2))
    logger.info(f"Root Catalog written to {root_catalog_path}")

if __name__ == "__main__":
    app()
