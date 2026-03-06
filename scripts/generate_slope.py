"""
Generate static STAC catalog for han_slope_landslide GeoTIFF dataset.

Usage:
    uv run python scripts/generate_han_slope_stac.py [--skip-cog]

- Converts each tiff to COG (unless --skip-cog)
- Reads bbox/projection from each COG via rioxarray
- Outputs pystac Catalog > Catalog > Collection > single Item (14 assets)
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

# Capture date of the data (from file mtime: 2025-08-25)
DATA_DATETIME = datetime(2025, 8, 25, tzinfo=timezone.utc)

# Maps filename prefix -> (asset_key, human title, description)
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

COG_MIME = "image/tiff; application=geotiff; profile=cloud-optimized"
TIFF_MIME = "image/tiff; application=geotiff"

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
    """Read tiff metadata using rioxarray + rasterio."""
    import rasterio

    with rasterio.open(path) as ds:
        crs = ds.crs
        transform = list(ds.transform)[:6]
        shape = [ds.height, ds.width]
        dtype = str(ds.dtypes[0])
        nodata = ds.nodata
        # native bbox in source CRS
        left, bottom, right, top = ds.bounds

    # Reproject bbox to WGS84
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


def build_item(asset_infos: dict, items_dir: Path, skip_cog: bool) -> pystac.Item:
    """Build and write a single pystac.Item with all 14 GeoTIFF assets."""
    sample_info = next(iter(asset_infos.values()))[1]
    shared_bbox = sample_info["bbox_wgs84"]
    proj_code = sample_info["proj_code"]

    item_id = f"{COLLECTION_ID}-2025"
    item = pystac.Item(
        id=item_id,
        geometry=bbox_to_polygon(shared_bbox),
        bbox=shared_bbox,
        datetime=DATA_DATETIME,
        properties={
            "datetime": DATA_DATETIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": (
                "Slope unit-based landslide susceptibility features for the Han slope area, Taiwan. "
                "14 terrain/geological attributes derived from DEM, InSAR, and ancillary data. "
                "Coordinate system: TWD97 (EPSG:3826)."
            ),
            "gsd": 20,
            "proj:code": proj_code,
            "processing:level": "Analysis Ready",
            "platform": "Multi-source (DEM, InSAR, satellite)",
        },
        stac_extensions=[PROJ_EXT],
        collection=COLLECTION_ID,
    )

    for asset_key, (file_path, info, title, description, mime) in asset_infos.items():
        rel_href = f"./{file_path.name}" if not skip_cog else str(file_path)
        item.add_asset(
            asset_key,
            pystac.Asset(
                href=rel_href,
                media_type=mime,
                title=title,
                roles=["data"],
                extra_fields={
                    "description": description,
                    "data_type": info["dtype"],
                    "proj:shape": info["shape"],
                    "proj:transform": info["transform"],
                    "nodata": info["nodata"],
                },
            ),
        )

    item.add_link(pystac.Link(rel="root", target="../../../catalog.json", media_type="application/json"))
    item.add_link(pystac.Link(rel="collection", target="../collection.json", media_type="application/json", title="Han Slope Landslide Features"))
    item.add_link(pystac.Link(rel="parent", target="../collection.json", media_type="application/json"))

    item_path = items_dir / f"{item_id}.json"
    item_path.write_text(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
    logger.success(f"Item written: {item_path}")
    return item


def build_collection(shared_bbox: list, item_id: str) -> pystac.Collection:
    """Build and write the pystac.Collection."""
    extent = pystac.Extent(
        spatial=pystac.SpatialExtent(bboxes=[shared_bbox]),
        temporal=pystac.TemporalExtent(intervals=[[DATA_DATETIME, None]]),
    )
    collection = pystac.Collection(
        id=COLLECTION_ID,
        title="Han Slope Landslide Susceptibility Features",
        description=(
            "**Han Slope Landslide Susceptibility Feature Dataset**\n\n"
            "Slope unit-based terrain and geological attributes for landslide susceptibility analysis "
            "in the Han slope area, Taiwan.\n\n"
            "- **Features**: 14 attributes (slope, aspect, curvature, altitude, NDVI, InSAR gradient, "
            "fault/river/road distance, roughness, dip slope, fold, geological sensitivity)\n"
            "- **Coordinate System**: TWD97 (EPSG:3826)\n"
            "- **Format**: Cloud Optimized GeoTIFF (COG)\n"
            "- **Source**: DEM (20m), InSAR, satellite imagery, geological survey data\n"
        ),
        extent=extent,
        license="proprietary",
        providers=[pystac.Provider(name="NTU CompHydroMet Lab", roles=["host", "processor"], url="https://wangup.caece.net/")],
        keywords=["landslide", "slope", "GeoTIFF", "Taiwan", "TWD97", "terrain", "InSAR"],
    )
    collection.stac_extensions = [PROJ_EXT]
    collection.extra_fields.update({
        "group_id": "han_slope",
        "group_title": "Han Slope",
        "group_description": "Han Slope Landslide Susceptibility Data",
        "group_keywords": ["landslide", "slope", "Taiwan"],
    })
    collection.summaries = pystac.Summaries({
        "processing:level": ["Analysis Ready"],
        "platform": ["Multi-source"],
        "category": ["TERRAIN"],
    })
    collection.add_link(pystac.Link(rel="item", target=f"./items/{item_id}.json", media_type="application/json"))
    collection.add_link(pystac.Link(rel="root", target="../../catalog.json", media_type="application/json", title="NTU CompHydroMet Lab Data Catalog"))
    collection.add_link(pystac.Link(rel="parent", target="../catalog.json", media_type="application/json", title="Han Slope"))

    # Thumbnail
    items_dir = OUT_DIR / COLLECTION_ID / "items"
    thumb_path = generate_thumbnail(items_dir)
    collection.add_asset(
        "thumbnail",
        pystac.Asset(
            href=f"./items/{thumb_path.name}",
            media_type="image/png",
            title=f"Thumbnail for {COLLECTION_ID}",
            roles=["thumbnail"],
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
        "title": "Han Slope",
        "description": "Han Slope Landslide Susceptibility Data",
        "links": [
            {"rel": "root", "href": "../catalog.json", "type": "application/json", "title": "NTU CompHydroMet Lab Data Catalog"},
            {"rel": "child", "href": f"./{COLLECTION_ID}/collection.json", "type": "application/json", "title": "Han Slope Landslide Features"},
            {"rel": "parent", "href": "../catalog.json", "type": "application/json", "title": "NTU CompHydroMet Lab Data Catalog"},
        ],
        "keywords": ["landslide", "slope", "Taiwan"],
    }
    path = OUT_DIR / "catalog.json"
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))
    logger.success(f"Group catalog written: {path}")


def patch_root_catalog() -> None:
    """Add han_slope child link to root catalog.json if not already present."""
    root = json.loads(ROOT_CATALOG.read_text())
    han_link = {"rel": "child", "href": "./han_slope/catalog.json", "type": "application/json", "title": "Han Slope"}
    if not any(lk.get("href") == han_link["href"] for lk in root["links"]):
        root["links"].append(han_link)
        ROOT_CATALOG.write_text(json.dumps(root, indent=2, ensure_ascii=False))
        logger.success("Root catalog updated with han_slope link")
    else:
        logger.info("Root catalog already has han_slope link")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = typer.Typer()


@app.command()
def main(
    skip_cog: Annotated[bool, typer.Option(help="Skip COG conversion, use original tiff.")] = False,
) -> None:
    """Generate static STAC catalog for han_slope_landslide GeoTIFF dataset."""
    items_dir = OUT_DIR / COLLECTION_ID / "items"
    items_dir.mkdir(parents=True, exist_ok=True)

    asset_infos = collect_assets(items_dir, skip_cog)
    if not asset_infos:
        logger.error("No assets found, aborting")
        raise typer.Exit(code=1)

    item = build_item(asset_infos, items_dir, skip_cog)
    shared_bbox = next(iter(asset_infos.values()))[1]["bbox_wgs84"]
    build_collection(shared_bbox, item.id)
    build_group_catalog()
    patch_root_catalog()
    logger.success("Done!")


if __name__ == "__main__":
    app()

