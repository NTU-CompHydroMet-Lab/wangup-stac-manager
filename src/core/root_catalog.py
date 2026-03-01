from pathlib import Path
import shutil
from collections import defaultdict
from loguru import logger
import pystac
from src.settings import settings
from src.core.event_collection import (
    build_event_collection,
    postprocess_event_collection_links,
)


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

    # groups[group_id] = {"event_map": {event_id: [col, ...]}, "plain": [col, ...]}
    groups = defaultdict(lambda: {"event_map": defaultdict(list), "plain": []})

    loaded_cols: list[pystac.Collection] = []
    for col_path in collection_paths:
        try:
            col = pystac.Collection.from_file(str(col_path))
            loaded_cols.append(col)
        except Exception as e:
            logger.warning(f"Failed to load collection {col_path}: {e}")

    aggregated_ids = {
        c.id for c in loaded_cols if c.extra_fields.get("aggregation_type") == "event_collection"
    }

    # 1. Group Collections
    for col in loaded_cols:
        # Skip already-aggregated event collections to avoid re-grouping loops.
        if col.extra_fields.get("aggregation_type") == "event_collection":
            continue
        # Skip stale non-aggregated duplicates when an aggregated event collection with same ID exists.
        if col.id in aggregated_ids:
            continue

        # Use explicit group_id from metadata (injected by Generator from Intake 'catalog_name')
        # Fallback to 'ungrouped' if not set, preventing random splitting behavior.
        group_name = col.extra_fields.get("group_id", "ungrouped")

        event_id = col.extra_fields.get("event_id")
        if event_id:
            groups[group_name]["event_map"][event_id].append(col)
        else:
            groups[group_name]["plain"].append(col)

    # 2. Build Hierarchy & Move Files
    for group_name, payload in groups.items():
        all_cols = []
        for _, lst in payload["event_map"].items():
            all_cols.extend(lst)
        all_cols.extend(payload["plain"])
        if not all_cols:
            continue

        event_col_ids = {
            c.id for cols in payload["event_map"].values() for c in cols
        }
        plain_cols = [c for c in payload["plain"] if c.id not in event_col_ids]

        # Create Group Catalog
        group_dir = stac_output_dir / group_name
        group_dir.mkdir(exist_ok=True)

        first_col = all_cols[0]

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

        # 2a. Event-based sub-collections under each group
        for event_id, cols in payload["event_map"].items():
            # De-duplicate same collection id from mixed locations; prefer shallower path (fresh root-level output).
            by_id = {}
            for c in cols:
                cur = by_id.get(c.id)
                if cur is None or len(Path(c.self_href).parts) < len(Path(cur.self_href).parts):
                    by_id[c.id] = c
            cols = list(by_id.values())

            event_dir = group_dir / event_id
            event_dir.mkdir(exist_ok=True)

            first_event_col = cols[0]
            event_title = first_event_col.extra_fields.get(
                "event_title", event_id.replace("_", " ").title()
            )
            event_desc = first_event_col.extra_fields.get(
                "event_description", f"Event catalog for {event_id}"
            )

            for col in cols:
                old_col_dir = Path(col.self_href).parent
                new_col_dir = event_dir / old_col_dir.name
                try:
                    if old_col_dir.resolve() != new_col_dir.resolve():
                        if new_col_dir.exists():
                            logger.info(f"Removing stale collection directory: {new_col_dir}")
                            shutil.rmtree(new_col_dir)
                        shutil.move(str(old_col_dir), str(new_col_dir))
                        logger.info(f"Moved {old_col_dir.name} to {group_name}/{event_id}/")
                    col.set_self_href(str(new_col_dir / "collection.json"))
                except Exception as e:
                    logger.error(f"Failed to move {old_col_dir} to {new_col_dir}: {e}")
            # Create one event collection that aggregates all product items.
            event_collection = build_event_collection(
                stac_root=stac_output_dir,
                event_dir=event_dir,
                event_id=event_id,
                event_title=event_title,
                event_desc=event_desc,
                cols=cols,
            )
            group_cat.add_child(event_collection)

        # 2b. Non-event collections remain directly under group
        for col in plain_cols:
            old_col_dir = Path(col.self_href).parent
            new_col_dir = group_dir / old_col_dir.name
            try:
                if old_col_dir.resolve() != new_col_dir.resolve():
                    if new_col_dir.exists():
                        logger.info(f"Removing stale collection directory: {new_col_dir}")
                        shutil.rmtree(new_col_dir)
                    shutil.move(str(old_col_dir), str(new_col_dir))
                    logger.info(f"Moved {old_col_dir.name} to {group_name}/")
                col.set_self_href(str(new_col_dir / "collection.json"))
            except Exception as e:
                logger.error(f"Failed to move {old_col_dir} to {new_col_dir}: {e}")

            group_cat.add_child(col)

        root.add_child(group_cat)

    # 3. Save
    # Keep explicit self_hrefs so event-based hierarchy is preserved.
    root.set_self_href(str(root_catalog_path))
    root.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    strategy = settings.filesystem.link_strategy if settings else "absolute"
    postprocess_event_collection_links(stac_output_dir, strategy=strategy)

    logger.info(f"Root Catalog written to {root_catalog_path}")
