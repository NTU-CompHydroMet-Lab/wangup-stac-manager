"""
Generate static STAC catalog for han_slope_landslide GeoTIFF dataset.

Usage:
    uv run python scripts/generate_han_slope_stac.py [--skip-cog] [--clean]

- Converts each tiff to COG (unless --skip-cog)
- Reads bbox/projection from each COG via rasterio
- Converts AOI shapefile to GeoParquet
- Outputs pystac Catalog > Catalog > Collection > 15 Items (14 COG + 1 AOI GeoParquet)
"""

import json
import shutil
from datetime import datetime, timezone
from typing import Annotated

import typer
from pathlib import Path

import pystac
import rioxarray
from loguru import logger
from pyproj import Transformer
from rasterio.crs import CRS

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = Path("/home/NAS/homes/cytseng-10012/datacube/han_slope_data")
OUT_DIR = Path("stac_catalog/han_slope")
COLLECTION_ID = "han_slope_landslide"
ROOT_CATALOG = Path("stac_catalog/catalog.json")

GROUP_CATALOG_TITLE = "坡地崩塌單元"
COLLECTION_TITLE = "布唐布那溪崩塌事件"
SHAPEFILE_DIR = DATA_DIR / "slope unit"

# Capture date of the data (from file mtime: 2025-08-25)
DATA_DATETIME = datetime(2025, 8, 25, tzinfo=timezone.utc)

# Maps filename prefix -> (asset_key, english_title, zh_description)
ASSET_MAP = {
    "slope_slope unit": (
        "slope",
        "Slope Gradient",
        "坡度：坡面傾斜程度，以正切函數計算，單位為度。",
    ),
    "aspect_slope unit": (
        "aspect",
        "Slope Aspect",
        "坡向：坡面法線在水平面的投影方向，以正北為0度/360度。",
    ),
    "curvaure_slope unit": (
        "curvature",
        "Profile Curvature",
        "剖面曲率：邊坡坡度沿傾斜方向的變化程度。",
    ),
    "altitude_sslope unit": (
        "altitude",
        "Altitude / Elevation",
        "高程：20公尺數值地形模型高程數值，單位為公尺。",
    ),
    "dipslope_slope unit": (
        "dipslope",
        "Dip Slope Index",
        "順向坡指標：斜坡單元內順向坡面積比值（容易崩塌地區）。",
    ),
    "fault_distance_slope unit": (
        "fault_distance",
        "Distance to Fault",
        "斷層距：各單元邊界至斷層的最短距離，單位為公尺。",
    ),
    "fold_slope unit": (
        "fold",
        "Fold Density",
        "褶皺度：計算單元內所經過的褶皺數目。",
    ),
    "gradient_asc_slope unit": (
        "gradient_asc",
        "InSAR Gradient (Ascending)",
        "InSAR年變位速度梯度（升軌），透過TIN內插後做梯度計算。",
    ),
    "gradient_des_slope unit": (
        "gradient_des",
        "InSAR Gradient (Descending)",
        "InSAR年變位速度梯度（降軌）。",
    ),
    "ndvi_slope unit": (
        "ndvi",
        "NDVI",
        "植生指標（NDVI）：衛星遙測影像計算，評估地表植被覆蓋。",
    ),
    "river_distance_slope unit": (
        "river_distance",
        "Distance to River",
        "水系距：各單元邊界至水系的最短距離，單位為公尺。",
    ),
    "road_distance_slope unit": (
        "road_distance",
        "Distance to Road",
        "道路距：各單元邊界至道路的最短距離，單位為公尺。",
    ),
    "rough_slope unit": (
        "roughness",
        "Terrain Roughness",
        "地形粗糙度：圓形罩窗內網格高程標準差，描述地形起伏。",
    ),
    "sensitivity_slope unit": (
        "sensitivity",
        "Geological Sensitivity Index",
        "地質敏感區指標：斜坡單元內地質敏感區面積比值。",
    ),
}

# Per-item Traditional Chinese metadata: asset_key -> (zh_title, zh_description)
ITEM_META = {
    "slope":          ("坡度",              "斜坡坡面傾斜程度的地形屬性圖層（單位：度）。"),
    "aspect":         ("坡向",              "坡面法線在水平面投影方向的地形屬性圖層。"),
    "curvature":      ("剖面曲率",           "沿坡面傾斜方向的邊坡彎曲程度屬性圖層。"),
    "altitude":       ("高程",              "20公尺數值地形模型高程數值圖層（單位：公尺）。"),
    "dipslope":       ("順向坡指標",         "斜坡單元內順向坡面積比值屬性圖層。"),
    "fault_distance": ("斷層距",            "各單元邊界至斷層最短距離圖層（單位：公尺）。"),
    "fold":           ("褶皺度",            "斜坡單元內褶皺數目屬性圖層。"),
    "gradient_asc":   ("InSAR速度梯度（升軌）", "升軌InSAR年變位速度梯度圖層。"),
    "gradient_des":   ("InSAR速度梯度（降軌）", "降軌InSAR年變位速度梯度圖層。"),
    "ndvi":           ("植生指標",           "NDVI植被覆蓋指標衛星遙測圖層。"),
    "river_distance": ("水系距",            "各單元邊界至水系最短距離圖層（單位：公尺）。"),
    "road_distance":  ("道路距",            "各單元邊界至道路最短距離圖層（單位：公尺）。"),
    "roughness":      ("地形粗糙度",         "圓形罩窗內網格高程標準差地形屬性圖層。"),
    "sensitivity":    ("地質敏感區指標",      "斜坡單元內地質敏感區面積比值屬性圖層。"),
}

COG_MIME = "image/tiff; application=geotiff; profile=cloud-optimized"
TIFF_MIME = "image/tiff; application=geotiff"
GEOPARQUET_MIME = "application/x-parquet"

PROJ_EXT = "https://stac-extensions.github.io/projection/v2.0.0/schema.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tiff_to_cog(src: Path, dst: Path) -> None:
    """Convert src tiff to COG at dst using rio_cogeo."""
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    profile = cog_profiles.get("deflate")
    cog_translate(str(src), str(dst), profile, quiet=True, overview_level=4)
    logger.info(f"COG: {src.name} -> {dst.name}")


def tiff_info(path: Path) -> dict:
    """Read tiff metadata using rasterio."""
    import rasterio

    with rasterio.open(path) as ds:
        crs = ds.crs
        transform = list(ds.transform)[:6]
        shape = [ds.height, ds.width]
        dtype = str(ds.dtypes[0])
        nodata = ds.nodata
        left, bottom, right, top = ds.bounds

    src_epsg = crs.to_epsg()
    if src_epsg == 4326:
        bbox_wgs84 = [left, bottom, right, top]
    else:
        t = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        x_min, y_min = t.transform(left, bottom)
        x_max, y_max = t.transform(right, top)
        bbox_wgs84 = [x_min, y_min, x_max, y_max]

    return {
        "epsg": src_epsg or crs.to_wkt(),
        "proj_code": f"EPSG:{src_epsg}" if src_epsg else crs.to_wkt(),
        "transform": transform,
        "shape": shape,
        "dtype": dtype,
        "nodata": nodata,
        "bbox_wgs84": [round(v, 6) for v in bbox_wgs84],
    }


def bbox_to_polygon(bbox: list) -> dict:
    west, south, east, north = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
        ],
    }


# ---------------------------------------------------------------------------
# Thumbnail
# ---------------------------------------------------------------------------


def generate_thumbnail(items_dir: Path, source_asset_key: str = "slope") -> Path:
    """Render a PNG thumbnail from a COG tiff using matplotlib."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio

    src_path = items_dir / f"{source_asset_key}.cog.tif"
    out_path = items_dir / f"{COLLECTION_ID}_thumb.png"

    with rasterio.open(src_path) as ds:
        data = ds.read(1).astype(float)
        nodata = ds.nodata

    if nodata is not None:
        data = np.ma.masked_equal(data, nodata)

    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.imshow(data, cmap="terrain", interpolation="bilinear")
    ax.set_axis_off()
    fig.patch.set_facecolor("black")
    plt.tight_layout(pad=0)
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0, dpi=100, facecolor="black")
    plt.close()
    logger.info(f"Thumbnail: {out_path.name}")
    return out_path


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------


def collect_assets(items_dir: Path, skip_cog: bool) -> dict:
    """Match tiff files to ASSET_MAP, convert to COG, read metadata.

    Returns asset_infos: {asset_key: (file_path, info, title, description, mime)}
    """
    tiff_files = {p.stem: p for p in DATA_DIR.glob("*.tif")}
    logger.info(f"Found {len(tiff_files)} tiff files")

    asset_infos = {}
    for stem, (asset_key, title, description) in ASSET_MAP.items():
        src = tiff_files.get(stem)
        if src is None:
            logger.warning(f"Missing tiff for key '{stem}', skipping")
            continue

        cog_path = items_dir / f"{asset_key}.cog.tif"

        if skip_cog:
            logger.info(f"Skipping COG for {src.name}, reading original")
            info = tiff_info(src)
            asset_infos[asset_key] = (src, info, title, description, TIFF_MIME)
        else:
            tiff_to_cog(src, cog_path)
            info = tiff_info(cog_path)
            asset_infos[asset_key] = (cog_path, info, title, description, COG_MIME)

    return asset_infos


def build_items(asset_infos: dict, items_dir: Path, skip_cog: bool) -> list[pystac.Item]:
    """Build and write one pystac.Item per terrain attribute (14 total)."""
    items = []

    for asset_key, (file_path, info, _en_title, asset_desc_zh, mime) in asset_infos.items():
        item_id = f"{COLLECTION_ID}_{asset_key}"
        bbox = info["bbox_wgs84"]
        proj_code = info["proj_code"]

        zh_title, zh_desc = ITEM_META.get(asset_key, (_en_title, asset_desc_zh))

        item = pystac.Item(
            id=item_id,
            geometry=bbox_to_polygon(bbox),
            bbox=bbox,
            datetime=DATA_DATETIME,
            properties={
                "datetime": DATA_DATETIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "title": zh_title,
                "description": zh_desc,
                "gsd": 20,
                "proj:code": proj_code,
                "processing:level": "Analysis Ready",
                "platform": "Multi-source (DEM, InSAR, satellite)",
            },
            stac_extensions=[PROJ_EXT],
            collection=COLLECTION_ID,
        )

        rel_href = f"./{file_path.name}" if not skip_cog else str(file_path)
        item.add_asset(
            "data",
            pystac.Asset(
                href=rel_href,
                media_type=mime,
                title=f"{zh_title} COG",
                roles=["data"],
                extra_fields={
                    "description": asset_desc_zh,
                    "data_type": info["dtype"],
                    "proj:shape": info["shape"],
                    "proj:transform": info["transform"],
                    "nodata": info["nodata"],
                },
            ),
        )

        item.add_link(pystac.Link(rel="root", target="../../../catalog.json", media_type="application/json"))
        item.add_link(pystac.Link(rel="collection", target="../collection.json", media_type="application/json", title=COLLECTION_TITLE))
        item.add_link(pystac.Link(rel="parent", target="../collection.json", media_type="application/json"))

        item_path = items_dir / f"{item_id}.json"
        item_path.write_text(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
        logger.success(f"Item written: {item_path}")
        items.append(item)

    return items


def convert_shapefile_to_geoparquet(items_dir: Path) -> Path | None:
    """Convert AOI shapefile to a single GeoParquet file in items_dir."""
    import geopandas as gpd

    shp_path = SHAPEFILE_DIR / "AOI_slope unit.shp.shp"
    if not shp_path.exists():
        logger.warning(f"Shapefile not found: {shp_path}")
        return None

    out_path = items_dir / "AOI_slope_unit.parquet"
    gdf = gpd.read_file(str(shp_path))
    gdf.to_parquet(str(out_path))
    logger.info(f"GeoParquet written: {out_path.name}")
    return out_path


def build_aoi_item(parquet_path: Path, items_dir: Path) -> pystac.Item | None:
    """Build a STAC Item for the AOI GeoParquet with actual shapefile geometry."""
    import geopandas as gpd
    from shapely.geometry import mapping

    if parquet_path is None or not parquet_path.exists():
        return None

    gdf = gpd.read_parquet(str(parquet_path))
    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    union_geom = gdf_wgs84.union_all()
    bounds = gdf_wgs84.total_bounds  # [minx, miny, maxx, maxy]
    bbox_wgs84 = [round(float(v), 6) for v in bounds]

    item_id = f"{COLLECTION_ID}_aoi"
    item = pystac.Item(
        id=item_id,
        geometry=mapping(union_geom),
        bbox=bbox_wgs84,
        datetime=DATA_DATETIME,
        properties={
            "datetime": DATA_DATETIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "title": "斜坡單元邊界（AOI）",
            "description": "布唐布那溪流域坡地崩塌研究區域的斜坡單元邊界向量資料。",
            "proj:code": "EPSG:3826",
            "processing:level": "Analysis Ready",
        },
        stac_extensions=[PROJ_EXT],
        collection=COLLECTION_ID,
    )
    item.add_asset(
        "data",
        pystac.Asset(
            href=f"./{parquet_path.name}",
            media_type=GEOPARQUET_MIME,
            title="斜坡單元邊界 GeoParquet",
            roles=["data"],
            extra_fields={
                "description": "布唐布那溪流域坡地崩塌研究區域的斜坡單元邊界（TWD97, EPSG:3826）。",
                "proj:code": "EPSG:3826",
            },
        ),
    )
    item.add_link(pystac.Link(rel="root", target="../../../catalog.json", media_type="application/json"))
    item.add_link(pystac.Link(rel="collection", target="../collection.json", media_type="application/json", title=COLLECTION_TITLE))
    item.add_link(pystac.Link(rel="parent", target="../collection.json", media_type="application/json"))

    item_path = items_dir / f"{item_id}.json"
    item_path.write_text(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
    logger.success(f"AOI item written: {item_path}")
    return item


def build_collection(asset_infos: dict, items: list[pystac.Item], parquet_path: Path | None = None) -> pystac.Collection:
    """Build and write the pystac.Collection."""
    shared_bbox = next(iter(asset_infos.values()))[1]["bbox_wgs84"]

    extent = pystac.Extent(
        spatial=pystac.SpatialExtent(bboxes=[shared_bbox]),
        temporal=pystac.TemporalExtent(intervals=[[DATA_DATETIME, None]]),
    )
    collection = pystac.Collection(
        id=COLLECTION_ID,
        title=COLLECTION_TITLE,
        description=(
            "**布唐布那溪崩塌事件地形屬性資料集**\n\n"
            "以斜坡單元為基礎的地形與地質屬性圖層，用於台灣布唐布那溪流域崩塌潛勢分析。\n\n"
            "- **地形屬性**：14 個圖層（坡度、坡向、剖面曲率、高程、植生指標、InSAR速度梯度、"
            "斷層距、水系距、道路距、地形粗糙度、順向坡指標、褶皺度、地質敏感區指標）\n"
            "- **坐標系統**：TWD97（EPSG:3826）\n"
            "- **格式**：Cloud Optimized GeoTIFF（COG）\n"
            "- **資料來源**：數值地形模型（20公尺）、InSAR、衛星影像、地質調查資料\n"
        ),
        extent=extent,
        license="proprietary",
        providers=[pystac.Provider(name="NTU CompHydroMet Lab", roles=["host", "processor"], url="https://wangup.caece.net/")],
        keywords=["崩塌", "坡地", "GeoTIFF", "台灣", "TWD97", "地形", "InSAR"],
    )
    collection.stac_extensions = [PROJ_EXT]
    collection.extra_fields.update({
        "group_id": "han_slope",
        "group_title": GROUP_CATALOG_TITLE,
        "group_description": "坡地崩塌單元地形屬性資料",
        "group_keywords": ["崩塌", "坡地", "台灣"],
    })
    collection.summaries = pystac.Summaries({
        "processing:level": ["Analysis Ready"],
        "platform": ["Multi-source"],
        "category": ["TERRAIN"],
    })

    # Link to all items (14 COG + 1 AOI)
    for item in items:
        asset_key = item.id[len(COLLECTION_ID) + 1:]  # e.g. "slope", "aoi"
        zh_title = ITEM_META.get(asset_key, ("", ""))[0] or item.properties.get("title", "")
        collection.add_link(pystac.Link(
            rel="item",
            target=f"./items/{item.id}.json",
            media_type="application/json",
            title=zh_title,
        ))

    collection.add_link(pystac.Link(rel="root", target="../../catalog.json", media_type="application/json", title="NTU CompHydroMet Lab Data Catalog"))
    collection.add_link(pystac.Link(rel="parent", target="../catalog.json", media_type="application/json", title=GROUP_CATALOG_TITLE))

    # Thumbnail
    items_dir = OUT_DIR / COLLECTION_ID / "items"
    thumb_path = generate_thumbnail(items_dir)
    collection.add_asset(
        "thumbnail",
        pystac.Asset(
            href=f"./items/{thumb_path.name}",
            media_type="image/png",
            title=f"{COLLECTION_TITLE} 縮圖",
            roles=["thumbnail"],
        ),
    )

    # AOI boundary asset at collection level (same parquet as the AOI item)
    if parquet_path is not None:
        collection.add_asset(
            "boundary",
            pystac.Asset(
                href=f"./items/{parquet_path.name}",
                media_type=GEOPARQUET_MIME,
                title="研究區域邊界（AOI）",
                roles=["overview"],
                extra_fields={
                    "description": "布唐布那溪流域坡地崩塌研究區域的斜坡單元邊界（TWD97, EPSG:3826）。",
                    "proj:code": "EPSG:3826",
                },
            ),
        )

    collection_path = OUT_DIR / COLLECTION_ID / "collection.json"
    collection_path.write_text(json.dumps(collection.to_dict(), indent=2, ensure_ascii=False))
    logger.success(f"Collection written: {collection_path}")
    return collection


def build_group_catalog() -> None:
    """Write the group-level catalog.json for han_slope."""
    catalog = {
        "type": "Catalog",
        "id": "han_slope",
        "stac_version": "1.1.0",
        "title": GROUP_CATALOG_TITLE,
        "description": "坡地崩塌單元地形屬性資料",
        "links": [
            {"rel": "root",   "href": "../catalog.json",                    "type": "application/json", "title": "NTU CompHydroMet Lab Data Catalog"},
            {"rel": "child",  "href": f"./{COLLECTION_ID}/collection.json", "type": "application/json", "title": COLLECTION_TITLE},
            {"rel": "parent", "href": "../catalog.json",                    "type": "application/json", "title": "NTU CompHydroMet Lab Data Catalog"},
        ],
        "keywords": ["崩塌", "坡地", "台灣"],
    }
    path = OUT_DIR / "catalog.json"
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))
    logger.success(f"Group catalog written: {path}")


def patch_root_catalog() -> None:
    """Add/update han_slope child link in root catalog.json."""
    root = json.loads(ROOT_CATALOG.read_text())
    han_link = {
        "rel": "child",
        "href": "./han_slope/catalog.json",
        "type": "application/json",
        "title": GROUP_CATALOG_TITLE,
    }
    existing = next((lk for lk in root["links"] if lk.get("href") == han_link["href"]), None)
    if existing is None:
        root["links"].append(han_link)
        ROOT_CATALOG.write_text(json.dumps(root, indent=2, ensure_ascii=False))
        logger.success("Root catalog updated with han_slope link")
    elif existing.get("title") != han_link["title"]:
        existing["title"] = han_link["title"]
        ROOT_CATALOG.write_text(json.dumps(root, indent=2, ensure_ascii=False))
        logger.success("Root catalog: updated han_slope title")
    else:
        logger.info("Root catalog already has han_slope link")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = typer.Typer()


@app.command()
def main(
    skip_cog: Annotated[bool, typer.Option(help="Skip COG conversion, use original tiff.")] = False,
    clean: Annotated[bool, typer.Option(help="Remove old single-item JSON before building.")] = False,
) -> None:
    """Generate static STAC catalog for han_slope_landslide GeoTIFF dataset."""
    items_dir = OUT_DIR / COLLECTION_ID / "items"
    items_dir.mkdir(parents=True, exist_ok=True)

    if clean:
        old_item = items_dir / "han_slope_landslide-2025.json"
        if old_item.exists():
            old_item.unlink()
            logger.info(f"Removed old item: {old_item.name}")

    asset_infos = collect_assets(items_dir, skip_cog)
    if not asset_infos:
        logger.error("No assets found, aborting")
        raise typer.Exit(code=1)

    parquet_path = convert_shapefile_to_geoparquet(items_dir)

    items = build_items(asset_infos, items_dir, skip_cog)
    aoi_item = build_aoi_item(parquet_path, items_dir)
    if aoi_item:
        items.append(aoi_item)

    build_collection(asset_infos, items, parquet_path)
    build_group_catalog()
    patch_root_catalog()
    logger.success(f"Done! {len(items)} items written.")


if __name__ == "__main__":
    app()
