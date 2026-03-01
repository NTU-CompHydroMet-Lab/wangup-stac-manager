"""Event-based STAC collection aggregation.

Aggregates per-product STAC collections that share an event_id into a single
event collection with unified extent and a cross-asset fusion item.
"""

import json
from pathlib import Path
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from loguru import logger
import pystac

PRODUCT_ALIASES = [
    ("rainfall", "rain_forcing"),
    ("max_depth", "max_depth"),
    ("depth_timeseries", "depth_timeseries"),
    ("iot_validation", "iot_timeseries"),
]


def resolve_href(base_file: Path, href: str) -> Path:
    p = Path(href)
    if p.is_absolute():
        return p
    return (base_file.parent / p).resolve()


def union_extent(cols: list[pystac.Collection]) -> pystac.Extent:
    west, south, east, north = 180.0, 90.0, -180.0, -90.0
    has_bbox = False
    non_global_bbox = False
    starts = []
    ends = []

    for col in cols:
        for b in col.extent.spatial.bboxes:
            if not b or len(b) < 4:
                continue
            if [float(b[0]), float(b[1]), float(b[2]), float(b[3])] == [-180.0, -90.0, 180.0, 90.0]:
                continue
            has_bbox = True
            non_global_bbox = True
            west = min(west, float(b[0]))
            south = min(south, float(b[1]))
            east = max(east, float(b[2]))
            north = max(north, float(b[3]))
        for iv in col.extent.temporal.intervals:
            if not iv or len(iv) < 2:
                continue
            if iv[0] is not None:
                starts.append(iv[0])
            if iv[1] is not None:
                ends.append(iv[1])

    if not has_bbox and not non_global_bbox:
        west, south, east, north = -180.0, -90.0, 180.0, 90.0

    t0 = min(starts) if starts else None
    t1 = max(ends) if ends else None
    return pystac.Extent(
        pystac.SpatialExtent([[west, south, east, north]]),
        pystac.TemporalExtent([[t0, t1]]),
    )


def asset_ext(path: Path) -> str:
    if path.name.endswith(".zarr"):
        return ".zarr"
    return path.suffix or ""


def product_alias(collection_id: str) -> str:
    lid = collection_id.lower()
    for needle, alias in PRODUCT_ALIASES:
        if needle in lid:
            return alias
    return collection_id


def select_event_assets(alias: str, assets: dict) -> list[tuple[str, dict]]:
    """Select which assets should be carried into the event-level item."""
    if not isinstance(assets, dict):
        return []

    # For IoT validation, publish only a single parquet file.
    if alias == "iot_timeseries":
        preferred_keys = [
            "iot_validation_parquet",
            "iot_timeseries_parquet",
            "validation_parquet",
        ]
        for key in preferred_keys:
            asset = assets.get(key)
            if isinstance(asset, dict):
                return [("data", asset)]
        for _, asset in assets.items():
            href = ""
            if isinstance(asset, dict):
                href = str(asset.get("href", "")).lower()
            if href.endswith(".parquet"):
                return [("data", asset)]
        # Fallback to source asset if parquet is not available yet.
        fallback = assets.get("data")
        if isinstance(fallback, dict):
            return [("data", fallback)]
    return [(k, v) for k, v in assets.items() if isinstance(v, dict)]


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def to_iso_utc_z(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bbox_to_polygon(bbox: list[float]) -> dict:
    minx, miny, maxx, maxy = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [minx, miny],
                [maxx, miny],
                [maxx, maxy],
                [minx, maxy],
                [minx, miny],
            ]
        ],
    }


def build_event_fusion_item(
    stac_root: Path,
    event_dir: Path,
    event_rel: str,
    event_id: str,
    event_collection: pystac.Collection,
    product_items: dict[str, dict],
) -> dict | None:
    """Build one integrated multi-asset Item for cross-asset analysis."""
    required = {"depth_timeseries", "iot_timeseries"}
    if not required.issubset(set(product_items.keys())):
        return None

    items_dir = event_dir / "items"
    fusion_item_id = f"{event_id}__integrated"

    def _asset(alias: str, default_title: str, roles: list[str]) -> dict | None:
        p = product_items.get(alias)
        if not p:
            return None
        a = dict(p.get("asset", {}))
        if not a:
            return None
        a["title"] = default_title
        a["roles"] = roles
        return a

    assets: dict[str, dict] = {}
    depth_asset = _asset("depth_timeseries", "Simulated Depth Time Series (Mesh2d Zarr)", ["data", "simulation"])
    if depth_asset:
        assets["depth_simulation"] = depth_asset

    iot_asset = _asset("iot_timeseries", "IoT Validation Time Series (Parquet)", ["data", "observation", "validation"])
    if iot_asset:
        iot_asset["type"] = "application/vnd.apache.parquet"
        iot_asset["table:columns"] = [
            {"name": "time_utc", "type": "datetime"},
            {"name": "station_id", "type": "string"},
            {"name": "simulated_depth_m", "type": "number"},
            {"name": "observed_depth_m", "type": "number"},
            {"name": "station_x", "type": "number"},
            {"name": "station_y", "type": "number"},
            {"name": "mesh2d_face_index", "type": "integer"},
            {"name": "mesh2d_face_x", "type": "number"},
            {"name": "mesh2d_face_y", "type": "number"},
            {"name": "grid_id", "type": "string"},
            {"name": "pixel_index", "type": "integer"},
            {"name": "crs", "type": "string"},
        ]
        assets["depth_iot"] = iot_asset

    rain_asset = _asset("rain_forcing", "Rainfall Forcing (NetCDF)", ["data", "forcing"])
    if rain_asset:
        assets["rain_forcing"] = rain_asset

    max_depth_asset = _asset("max_depth", "Maximum Flood Depth (NetCDF)", ["data", "derived"])
    if max_depth_asset:
        assets["max_depth"] = max_depth_asset

    iot_source_path = (
        product_items.get("iot_timeseries", {})
        .get("properties", {})
        .get("source_path")
    )
    mapping_asset_key = None
    station_sim_csv_asset_key = None
    if iot_source_path:
        try:
            iot_file = Path(iot_source_path).resolve()
            event_data_root = iot_file.parent.parent
            mapping_src = event_data_root / "results" / "simulated_depth_timeseries_station_index.json"
            station_sim_csv_src = event_data_root / "results" / "simulated_depth_timeseries_at_iot_stations.csv"
            if mapping_src.exists():
                mapping_name = f"{fusion_item_id}__station_face_mapping.json"
                mapping_link = items_dir / mapping_name
                if mapping_link.exists() or mapping_link.is_symlink():
                    mapping_link.unlink()
                mapping_link.symlink_to(mapping_src)
                mapping_asset_key = "station_face_mapping"
                assets[mapping_asset_key] = {
                    "href": f"/stac/{event_rel}/items/{mapping_name}",
                    "type": "application/json",
                    "title": "IoT-to-Mesh2d Mapping Index",
                    "roles": ["metadata", "index", "mapping"],
                }
            if station_sim_csv_src.exists():
                csv_name = f"{fusion_item_id}__sim_depth_at_stations.csv"
                csv_link = items_dir / csv_name
                if csv_link.exists() or csv_link.is_symlink():
                    csv_link.unlink()
                csv_link.symlink_to(station_sim_csv_src)
                station_sim_csv_asset_key = "sim_depth_at_stations"
                assets[station_sim_csv_asset_key] = {
                    "href": f"/stac/{event_rel}/items/{csv_name}",
                    "type": "text/csv",
                    "title": "Simulation Time Series at IoT Stations (CSV)",
                    "roles": ["data", "simulation", "timeseries", "fallback"],
                }
        except Exception as e:
            logger.warning(f"Unable to attach station-face mapping asset for {event_id}: {e}")

    start_candidates: list[datetime] = []
    end_candidates: list[datetime] = []
    for p in product_items.values():
        props = p.get("properties", {}) or {}
        s = parse_iso_datetime(props.get("start_datetime"))
        e = parse_iso_datetime(props.get("end_datetime"))
        if s is not None:
            start_candidates.append(s)
        if e is not None:
            end_candidates.append(e)
    start_dt = min(start_candidates) if start_candidates else None
    end_dt = max(end_candidates) if end_candidates else None
    if start_dt is None or end_dt is None:
        event_iv = event_collection.extent.temporal.intervals[0]
        start_dt = start_dt or event_iv[0]
        end_dt = end_dt or event_iv[1]
    if start_dt is None:
        start_dt = datetime.now(timezone.utc)
    if end_dt is None:
        end_dt = start_dt
    mid_dt = start_dt + (end_dt - start_dt) / 2

    bbox = [-180.0, -90.0, 180.0, 90.0]
    if event_collection.extent.spatial.bboxes:
        b = event_collection.extent.spatial.bboxes[0]
        if b and len(b) >= 4:
            bbox = [float(b[0]), float(b[1]), float(b[2]), float(b[3])]

    item_path = items_dir / f"{fusion_item_id}.json"
    item_payload = {
        "type": "Feature",
        "stac_version": "1.1.0",
        "stac_extensions": [
            "https://stac-extensions.github.io/datacube/v2.2.0/schema.json",
            "https://stac-extensions.github.io/table/v1.2.0/schema.json",
        ],
        "id": fusion_item_id,
        "collection": event_id,
        "geometry": bbox_to_polygon(bbox),
        "bbox": bbox,
        "properties": {
            "datetime": to_iso_utc_z(mid_dt),
            "start_datetime": to_iso_utc_z(start_dt),
            "end_datetime": to_iso_utc_z(end_dt),
            "event_id": event_id,
            "product_key": "cross_asset_fusion",
            "cross_asset_mapping": {
                "mapping_method": "nearest_mesh2d_face",
                "sensor_id_field": "station_id",
                "time_field": "time_utc",
                "observed_depth_field": "observed_depth_m",
                "simulated_depth_field": "simulated_depth_m",
                "grid_id_field": "grid_id",
                "pixel_index_field": "pixel_index",
                "mesh_face_index_field": "mesh2d_face_index",
                "mapping_asset": mapping_asset_key,
                "sim_timeseries_fallback_asset": station_sim_csv_asset_key,
                "notes": "IoT station records map to simulation mesh faces by nearest Mesh2d face.",
            },
        },
        "cube:dimensions": {
            "time": {
                "type": "temporal",
                "extent": [to_iso_utc_z(start_dt), to_iso_utc_z(end_dt)],
            },
            "mesh2d_face": {
                "type": "spatial",
                "description": "Unstructured Mesh2d face index for simulation outputs.",
            },
            "station": {
                "type": "spatial",
                "description": "IoT station identifier dimension.",
            },
        },
        "cube:variables": {
            "sim_depth_mesh": {
                "description": "Model-simulated flood depth at mesh faces.",
                "unit": "m",
                "type": "data",
                "dimensions": ["time", "mesh2d_face"],
                "fusion:asset_key": "depth_simulation",
            },
            "sim_depth_iot": {
                "description": "Model-simulated flood depth sampled at IoT stations.",
                "unit": "m",
                "type": "data",
                "dimensions": ["time", "station"],
                "fusion:asset_key": "depth_iot",
            },
            "obs_depth_iot": {
                "description": "Observed IoT flood depth time series.",
                "unit": "m",
                "type": "data",
                "dimensions": ["time", "station"],
                "fusion:asset_key": "depth_iot",
            },
        },
        "assets": assets,
        "links": [
            {"rel": "root", "href": "/stac/catalog.json", "type": "application/json"},
            {"rel": "collection", "href": f"/stac/{event_rel}/collection.json", "type": "application/json"},
            {"rel": "parent", "href": f"/stac/{event_rel}/collection.json", "type": "application/json"},
        ],
    }

    related_titles = {
        "rain_forcing": "Rain Forcing Item",
        "depth_timeseries": "Depth Time Series Item",
        "max_depth": "Maximum Depth Item",
        "iot_timeseries": "IoT Time Series Item",
    }
    for alias, p in product_items.items():
        href = p.get("item_href")
        if not href:
            continue
        item_payload["links"].append(
            {
                "rel": "related",
                "href": href,
                "type": "application/json",
                "title": related_titles.get(alias, alias),
            }
        )

    item_path.write_text(json.dumps(item_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "id": fusion_item_id,
        "href": f"/stac/{event_rel}/items/{fusion_item_id}.json",
    }


def build_event_collection(
    stac_root: Path,
    event_dir: Path,
    event_id: str,
    event_title: str,
    event_desc: str,
    cols: list[pystac.Collection],
) -> pystac.Collection:
    # Rebuild event items from scratch for deterministic structure.
    items_dir = event_dir / "items"
    if items_dir.exists():
        shutil.rmtree(items_dir)
    items_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale event catalog file from previous design.
    stale_event_catalog = event_dir / "catalog.json"
    if stale_event_catalog.exists():
        stale_event_catalog.unlink()

    first = cols[0]
    event_collection = pystac.Collection(
        id=event_id,
        title=event_title,
        description=event_desc,
        license=first.license or "CC-BY-4.0",
        extent=union_extent(cols),
        providers=first.providers or [],
        keywords=first.keywords or [],
    )
    event_collection.set_self_href(str(event_dir / "collection.json"))
    event_collection.extra_fields["aggregation_type"] = "event_collection"
    if first.extra_fields.get("group_id"):
        event_collection.extra_fields["group_id"] = first.extra_fields.get("group_id")
    event_collection.extra_fields["event_id"] = event_id
    event_rel = event_dir.relative_to(stac_root).as_posix()
    alias_count: dict[str, int] = defaultdict(int)
    product_items: dict[str, dict] = {}

    for col in sorted(cols, key=lambda c: c.id):
        # Prefer explicit item links from collection, fallback to items/*.json.
        item_paths: list[Path] = []
        col_file = Path(col.get_self_href())
        for l in col.links:
            if l.rel == "item" and l.href:
                item_paths.append(resolve_href(col_file, l.href))

        if not item_paths:
            item_paths = sorted((col_file.parent / "items").glob("*.json"))

        for src_item_path in item_paths:
            if not src_item_path.exists():
                continue
            src = json.loads(src_item_path.read_text(encoding="utf-8"))
            alias = product_alias(col.id)
            alias_count[alias] += 1
            suffix = "" if alias_count[alias] == 1 else f"_{alias_count[alias]}"
            item_id = f"{event_id}__{alias}{suffix}"

            # Rewrite core links to point to the event collection.
            src["id"] = item_id
            src["collection"] = event_id
            src["links"] = [
                {"rel": "root", "href": "../../../catalog.json", "type": "application/json"},
                {"rel": "collection", "href": "../collection.json", "type": "application/json"},
                {"rel": "parent", "href": "../collection.json", "type": "application/json"},
            ]
            src.setdefault("properties", {})
            src["properties"]["event_id"] = event_id
            src["properties"]["product_collection_id"] = col.id
            src["properties"]["product_key"] = alias

            # Re-link assets into event/items for stable browsing.
            new_assets = {}
            selected_assets = select_event_assets(alias, src.get("assets", {}))
            for key, asset in selected_assets:
                href = asset.get("href")
                if not href:
                    continue
                abs_asset = resolve_href(src_item_path, href)
                ext = asset_ext(abs_asset)
                new_name = f"{item_id}__{key}{ext}"
                new_link = items_dir / new_name
                if new_link.exists() or new_link.is_symlink():
                    new_link.unlink()
                try:
                    new_link.symlink_to(abs_asset)
                    a = dict(asset)
                    a["href"] = f"/stac/{event_rel}/items/{new_name}"
                    if alias == "iot_timeseries":
                        a["title"] = "IoT Validation Time Series (Parquet)"
                        a["type"] = "application/vnd.apache.parquet"
                        a["roles"] = ["data", "validation"]
                    new_assets[key] = a
                except Exception:
                    a = dict(asset)
                    a["href"] = str(abs_asset)
                    new_assets[key] = a
            src["assets"] = new_assets

            out_item = items_dir / f"{item_id}.json"
            out_item.write_text(json.dumps(src, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            item_href = f"/stac/{event_rel}/items/{item_id}.json"
            event_collection.add_link(
                pystac.Link(
                    rel="item",
                    target=item_href,
                    media_type="application/json",
                )
            )
            if alias not in product_items and "data" in new_assets:
                product_items[alias] = {
                    "item_id": item_id,
                    "item_href": item_href,
                    "asset": dict(new_assets.get("data", {})),
                    "properties": dict(src.get("properties", {})),
                }

    fusion_entry = build_event_fusion_item(
        stac_root=stac_root,
        event_dir=event_dir,
        event_rel=event_rel,
        event_id=event_id,
        event_collection=event_collection,
        product_items=product_items,
    )
    if fusion_entry:
        event_collection.add_link(
            pystac.Link(
                rel="item",
                target=fusion_entry["href"],
                media_type="application/json",
            )
        )

    (event_dir / "collection.json").write_text(
        json.dumps(event_collection.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return event_collection


def postprocess_event_collection_links(stac_output_dir: Path, strategy: str = "absolute") -> None:
    """Force event collection/item links to /stac absolute paths for browser routing compatibility."""
    if strategy == "relative":
        # PySTAC's SELF_CONTAINED mode already writes relative links.
        return

    for event_col_path in stac_output_dir.rglob("collection.json"):
        try:
            payload = json.loads(event_col_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("aggregation_type") != "event_collection":
            continue

        event_dir = event_col_path.parent
        event_rel = event_dir.relative_to(stac_output_dir).as_posix()
        event_col_url = f"/stac/{event_rel}/collection.json"
        group_id = payload.get("group_id", "ungrouped")
        group_cat_url = f"/stac/{group_id}/catalog.json"

        # Rewrite event collection links
        new_links = []
        for l in payload.get("links", []):
            rel = l.get("rel")
            if rel == "item":
                href = l.get("href", "")
                item_name = Path(href).name
                l["href"] = f"/stac/{event_rel}/items/{item_name}"
            elif rel == "root":
                l["href"] = "/stac/catalog.json"
            elif rel == "parent":
                l["href"] = group_cat_url
            elif rel == "collection":
                l["href"] = event_col_url
            new_links.append(l)
        payload["links"] = new_links
        event_col_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Rewrite each event item links/assets
        items_dir = event_dir / "items"
        if not items_dir.exists():
            continue
        for item_json in items_dir.glob("*.json"):
            try:
                item = json.loads(item_json.read_text(encoding="utf-8"))
            except Exception:
                continue

            item_links = []
            for l in item.get("links", []):
                rel = l.get("rel")
                if rel == "root":
                    l["href"] = "/stac/catalog.json"
                elif rel in ("collection", "parent"):
                    l["href"] = event_col_url
                item_links.append(l)
            item["links"] = item_links

            assets = item.get("assets", {})
            for _, a in assets.items():
                href = a.get("href", "")
                # Convert local relative asset links to /stac absolute paths.
                if href.startswith("./"):
                    a["href"] = f"/stac/{event_rel}/items/{href[2:]}"
            item["assets"] = assets
            item_json.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
