import json
from pathlib import Path
import typer

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
            parts = col_id.split('_')
            group_name = parts[0] if len(parts) > 1 else "other"
            
            # Special case for QPESUMS or others if needed
            if col_id.startswith("QPSUMS"):
                group_name = "radar"
            
            if group_name not in groups:
                groups[group_name] = []
            
            groups[group_name].append({
                "path": col_path,
                "data": col_data,
                "id": col_id
            })
        except Exception as e:
            print(f"⚠️ Failed to read collection {col_path}: {e}")
    
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
            
        group_catalog = {
            "type": "Catalog",
            "id": f"{group_name}-catalog",
            "stac_version": "1.0.0",
            "description": f"Catalog for {group_name} datasets",
            "links": group_links
        }
        group_catalog_path.write_text(json.dumps(group_catalog, indent=2))
        print(f"📂 Created Group Catalog: {group_catalog_path}")
        
        # Link Root to Group
        root_links.append({
            "rel": "child",
            "href": f"./{group_name}_catalog.json",
            "type": "application/json",
            "title": f"{group_name} Data"
        })
        
    catalog = {
        "type": "Catalog",
        "id": "stac-root-catalog",
        "stac_version": "1.0.0",
        "description": "Root Catalog for Research Lab Data",
        "links": root_links
    }
    
    root_catalog_path.write_text(json.dumps(catalog, indent=2))
    print(f"🗂  Root Catalog written to {root_catalog_path}")

if __name__ == "__main__":
    app()
