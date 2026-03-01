from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from netCDF4 import Dataset


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _file_entry(path: Path, role: str, media_type: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "role": role,
        "media_type": media_type,
        "size_bytes": path.stat().st_size,
        "modified_utc": _iso_mtime(path),
    }


def _inspect_rainfall_nc(path: Path) -> dict[str, Any]:
    with Dataset(path) as ds:
        var = ds.variables["precipitation_observed"]
        time = ds.variables["time"]
        crs = ds.variables.get("crs")
        epsg = getattr(crs, "epsg_code", None) if crs is not None else None

        return {
            "dataset_kind": "forcing_rainfall",
            "extraction_ready": True,
            "time_steps": int(var.shape[0]),
            "shape": list(var.shape),
            "variables": ["precipitation_observed"],
            "time_units": getattr(time, "units", ""),
            "time_start_raw": float(time[0]),
            "time_end_raw": float(time[-1]),
            "crs": epsg or "unknown",
        }


def _inspect_map_nc(path: Path) -> dict[str, Any]:
    with Dataset(path) as ds:
        wd = ds.variables["Mesh2d_waterdepth"]
        time = ds.variables["time"]
        pcs = ds.variables.get("projected_coordinate_system")
        epsg = getattr(pcs, "EPSG_code", None) or str(getattr(pcs, "epsg", "unknown"))

        cov_start = getattr(ds, "time_coverage_start", "")
        cov_end = getattr(ds, "time_coverage_end", "")

        return {
            "source_file": str(path),
            "crs": epsg,
            "shape": list(wd.shape),
            "time_steps": int(wd.shape[0]),
            "face_count": int(wd.shape[1]),
            "time_units": getattr(time, "units", ""),
            "time_coverage_start": cov_start,
            "time_coverage_end": cov_end,
        }


def _inspect_iot_shp(path: Path) -> dict[str, Any]:
    cmd = ["ogrinfo", "-al", "-so", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = proc.stdout

    feature_count = None
    geometry = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Feature Count:"):
            feature_count = int(line.split(":", 1)[1].strip())
        if line.startswith("Geometry:"):
            geometry = line.split(":", 1)[1].strip()

    crs = "unknown"
    if "ID[\"EPSG\",3826]" in out:
        crs = "EPSG:3826"

    return {
        "dataset_kind": "validation_iot_points",
        "extraction_ready": feature_count is not None and geometry is not None,
        "feature_count": feature_count,
        "geometry": geometry,
        "crs": crs,
        "fields": ["Name", "x", "y", "field_4"],
    }


def _inspect_validation_xlsx(path: Path) -> dict[str, Any]:
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    with zipfile.ZipFile(path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}

        sheet_names = []
        for sh in wb.findall("m:sheets/m:sheet", ns):
            sheet_names.append(sh.attrib["name"])

        has_sim_obs = False
        target = None
        for sh in wb.findall("m:sheets/m:sheet", ns):
            if sh.attrib["name"] == "20210604":
                rid = sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = "xl/" + relmap[rid]
                break

        if target and target in zf.namelist():
            shared_strings = []
            if "xl/sharedStrings.xml" in zf.namelist():
                sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in sroot.findall("m:si", ns):
                    shared_strings.append("".join((t.text or "") for t in si.findall(".//m:t", ns)))

            sroot = ET.fromstring(zf.read(target))
            row2 = sroot.findall(".//m:sheetData/m:row[@r='2']/m:c", ns)
            labels = []
            for c in row2:
                t = c.attrib.get("t")
                v = c.find("m:v", ns)
                if v is None:
                    continue
                val = v.text or ""
                if t == "s" and val.isdigit():
                    idx = int(val)
                    if idx < len(shared_strings):
                        val = shared_strings[idx]
                labels.append(val)
            has_sim_obs = ("模擬值" in labels) and ("觀測值" in labels)

    return {
        "dataset_kind": "validation_iot_timeseries",
        "extraction_ready": has_sim_obs,
        "sheet_names": sheet_names,
        "required_labels_found": has_sim_obs,
    }


def build_manifest(event_dir: Path) -> dict[str, Any]:
    rainfall_path = next((event_dir / "輸入雨量" / "WGS84").glob("*.nc"))
    map_path = event_dir / "輸出成果" / "output" / "FM_model_map.nc"
    iot_shp = event_dir / "IOT_catch" / "IOT_shpfile" / "YS_IOT.shp"
    validation_xlsx = event_dir / "IOT_catch" / "20210604比對分析.xlsx"

    event_id = event_dir.name.replace("flood_modelling_", "event_")

    rainfall = _inspect_rainfall_nc(rainfall_path)
    map_meta = _inspect_map_nc(map_path)
    iot_points = _inspect_iot_shp(iot_shp)
    iot_ts = _inspect_validation_xlsx(validation_xlsx)

    return {
        "manifest_version": "0.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "event_dir": str(event_dir),
        "core_products": [
            {
                "product_id": "forcing_rainfall",
                "description": "Event rainfall forcing (WGS84).",
                "source": _file_entry(rainfall_path, "forcing", "application/netcdf"),
                "summary": rainfall,
            },
            {
                "product_id": "result_max_depth",
                "description": "Maximum water depth derived from Mesh2d_waterdepth over time.",
                "source": _file_entry(map_path, "model_output", "application/netcdf"),
                "summary": {
                    "dataset_kind": "result_max_depth",
                    "extraction_ready": True,
                    "derived_from": "Mesh2d_waterdepth(time, Mesh2d_nFaces)",
                    "derivation": "max_over_time_per_face",
                    "map_metadata": map_meta,
                },
            },
            {
                "product_id": "result_depth_timeseries",
                "description": "Water depth time series from Mesh2d/mesh1d.",
                "source": _file_entry(map_path, "model_output", "application/netcdf"),
                "summary": {
                    "dataset_kind": "result_depth_timeseries",
                    "extraction_ready": True,
                    "variables": ["Mesh2d_waterdepth", "mesh1d_waterdepth"],
                    "map_metadata": map_meta,
                },
            },
            {
                "product_id": "validation_iot",
                "description": "IoT station points and simulation-observation comparison workbook.",
                "sources": [
                    _file_entry(iot_shp, "validation_points", "application/vnd.shp"),
                    _file_entry(validation_xlsx, "validation_table", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ],
                "summary": {
                    "points": iot_points,
                    "timeseries_table": iot_ts,
                },
            },
        ],
        "recommendations": [
            "Keep only core products in STAC. Retain remaining model outputs as archive links.",
            "Convert validation workbook to CSV/Parquet for stable downstream automation.",
            "Consider transforming FM_model_map.nc into chunked Zarr for serving time-series queries.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract core flood-event product manifest.")
    parser.add_argument(
        "--event-dir",
        type=Path,
        default=Path("data/flood_modelling_20210604"),
        help="Event directory path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("metadata/event_20210604_extract_manifest.json"),
        help="Output manifest JSON path.",
    )
    args = parser.parse_args()

    manifest = build_manifest(args.event_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {args.output}")


if __name__ == "__main__":
    main()
