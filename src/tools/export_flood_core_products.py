from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
from netCDF4 import Dataset


def _excel_serial_to_iso(value: str) -> str:
    serial = float(value)
    dt = datetime(1899, 12, 30) + timedelta(days=serial)
    return dt.isoformat()


def _parse_xlsx_20210604_to_tidy_csv(xlsx_path: Path, output_csv: Path) -> dict[str, Any]:
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    rows_written = 0
    station_count = 0

    with zipfile.ZipFile(xlsx_path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sroot.findall("m:si", ns):
                shared_strings.append("".join((t.text or "") for t in si.findall(".//m:t", ns)))

        target = None
        for sh in wb.findall("m:sheets/m:sheet", ns):
            if sh.attrib["name"] == "20210604":
                rid = sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = "xl/" + relmap[rid]
                break
        if target is None:
            raise RuntimeError("Sheet '20210604' not found in workbook.")

        ws = ET.fromstring(zf.read(target))
        row_nodes = ws.findall(".//m:sheetData/m:row", ns)
        if len(row_nodes) < 3:
            raise RuntimeError("Unexpected worksheet structure in validation workbook.")

        # Row 1: station names (duplicated for 模擬值/觀測值)
        # Row 2: type labels (模擬值/觀測值)
        def cell_val(cell: ET.Element) -> str:
            t = cell.attrib.get("t")
            v = cell.find("m:v", ns)
            if v is None:
                return ""
            raw = v.text or ""
            if t == "s" and raw.isdigit():
                idx = int(raw)
                if idx < len(shared_strings):
                    return shared_strings[idx]
            return raw

        header_cells = row_nodes[0].findall("m:c", ns)
        type_cells = row_nodes[1].findall("m:c", ns)

        station_pairs: list[tuple[int, str]] = []
        # column 0 is time serial; from col1 onward, paired sim/obs
        for col in range(1, min(len(header_cells), len(type_cells))):
            station_name = cell_val(header_cells[col]).strip()
            label = cell_val(type_cells[col]).strip()
            if station_name and label == "模擬值":
                # expect next column to be 觀測值
                station_pairs.append((col, station_name))
        station_count = len(station_pairs)

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "station", "simulated_depth_m", "observed_depth_m"])

            for row in row_nodes[2:]:
                cells = row.findall("m:c", ns)
                if not cells:
                    continue
                t_raw = cell_val(cells[0]).strip()
                if not t_raw:
                    continue
                try:
                    t_iso = _excel_serial_to_iso(t_raw)
                except Exception:
                    continue

                for sim_col, station_name in station_pairs:
                    obs_col = sim_col + 1
                    if sim_col >= len(cells) or obs_col >= len(cells):
                        continue
                    sim_val = cell_val(cells[sim_col]).strip()
                    obs_val = cell_val(cells[obs_col]).strip()
                    if not sim_val and not obs_val:
                        continue
                    writer.writerow([t_iso, station_name, sim_val or "", obs_val or ""])
                    rows_written += 1

    return {
        "path": str(output_csv),
        "rows": rows_written,
        "stations_detected": station_count,
    }


def _export_iot_points(shp_path: Path, out_dir: Path) -> dict[str, Any]:
    gpkg_path = out_dir / "iot_stations.gpkg"
    csv_path = out_dir / "iot_stations.csv"

    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ogr2ogr", "-f", "GPKG", str(gpkg_path), str(shp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["ogr2ogr", "-f", "CSV", str(csv_path), str(shp_path), "-lco", "GEOMETRY=AS_WKT"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {"gpkg": str(gpkg_path), "csv": str(csv_path)}


def _read_stations_from_csv(csv_path: Path) -> list[dict[str, Any]]:
    stations = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or "").strip()
            wkt = (row.get("WKT") or "").strip()
            if not name or not wkt:
                continue
            # CSV exported by ogr2ogr with GEOMETRY=AS_WKT, e.g. "POINT (175133.62 2546684.40)"
            if not wkt.startswith("POINT"):
                continue
            coord_txt = wkt[wkt.find("(") + 1 : wkt.find(")")].strip()
            parts = coord_txt.split()
            if len(parts) != 2:
                continue
            stations.append({"name": name, "x": float(parts[0]), "y": float(parts[1])})
    return stations


def _build_station_face_mapping(map_nc_path: Path, stations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map each station point to its nearest Mesh2d face."""
    if not stations:
        return []

    with Dataset(map_nc_path, "r") as ds:
        face_x = np.array(ds.variables["Mesh2d_face_x"][:], dtype=np.float64)
        face_y = np.array(ds.variables["Mesh2d_face_y"][:], dtype=np.float64)

    mapping_rows: list[dict[str, Any]] = []
    for st in stations:
        dx = face_x - st["x"]
        dy = face_y - st["y"]
        idx = int(np.argmin(dx * dx + dy * dy))
        mapping_rows.append(
            {
                "station": st["name"],
                "station_x": st["x"],
                "station_y": st["y"],
                "nearest_face_index": idx,
                "nearest_face_x": float(face_x[idx]),
                "nearest_face_y": float(face_y[idx]),
                "grid_id": f"mesh2d_face_{idx}",
                "pixel_index": idx,
            }
        )
    return mapping_rows


def _write_max_depth_netcdf(map_nc_path: Path, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with Dataset(map_nc_path, "r") as src:
        wd = src.variables["Mesh2d_waterdepth"]
        face_x = np.array(src.variables["Mesh2d_face_x"][:], dtype=np.float64)
        face_y = np.array(src.variables["Mesh2d_face_y"][:], dtype=np.float64)
        src_time = np.array(src.variables["time"][:], dtype=np.float64)
        src_time_units = getattr(src.variables["time"], "units", "seconds since 1970-01-01 00:00:00 +00:00")
        fill = getattr(wd, "_FillValue", -999.0)

        n_time, n_face = wd.shape
        max_depth = np.full(n_face, -np.inf, dtype=np.float32)

        for t_idx in range(n_time):
            slab = np.array(wd[t_idx, :], dtype=np.float32)
            slab[slab == fill] = np.nan
            max_depth = np.fmax(max_depth, np.nan_to_num(slab, nan=-np.inf))

        max_depth[max_depth == -np.inf] = np.nan

        with Dataset(out_path, "w", format="NETCDF4") as dst:
            dst.createDimension("time", 1)
            dst.createDimension("face", n_face)

            v_t = dst.createVariable("time", "f8", ("time",))
            v_x = dst.createVariable("face_x", "f8", ("face",))
            v_y = dst.createVariable("face_y", "f8", ("face",))
            v_d = dst.createVariable("max_depth", "f4", ("time", "face"), fill_value=np.float32(np.nan))

            v_t[:] = [float(src_time[-1])]
            v_x[:] = face_x
            v_y[:] = face_y
            v_d[0, :] = max_depth

            v_t.units = src_time_units
            v_t.standard_name = "time"
            v_t.axis = "T"
            v_x.units = "m"
            v_y.units = "m"
            v_x.standard_name = "projection_x_coordinate"
            v_y.standard_name = "projection_y_coordinate"
            v_d.units = "m"
            v_d.long_name = "Maximum water depth over all time steps"
            v_d.grid_mapping = "EPSG:3826"

            dst.title = "Flood event max depth derived from FM_model_map.nc"
            dst.source_file = str(map_nc_path)
            dst.crs = "EPSG:3826"
            dst.time_steps = int(n_time)
            dst.face_count = int(n_face)
            dst.created_at_utc = datetime.now(timezone.utc).isoformat()

    return {"path": str(out_path), "time_steps": int(n_time), "face_count": int(n_face)}


def _write_iot_validation_netcdf(
    tidy_csv_path: Path, station_csv_path: Path, out_path: Path
) -> dict[str, Any]:
    stations = _read_stations_from_csv(station_csv_path)
    station_index = {s["name"]: i for i, s in enumerate(stations)}

    times: list[str] = []
    rows: list[tuple[str, str, float, float]] = []
    with tidy_csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = (r.get("time") or "").strip()
            st = (r.get("station") or "").strip()
            if not t or st not in station_index:
                continue
            sim_s = (r.get("simulated_depth_m") or "").strip()
            obs_s = (r.get("observed_depth_m") or "").strip()
            try:
                sim = float(sim_s) if sim_s else np.nan
                obs = float(obs_s) if obs_s else np.nan
            except ValueError:
                sim, obs = np.nan, np.nan
            times.append(t)
            rows.append((t, st, sim, obs))

    uniq_times = sorted(set(times))
    time_index = {t: i for i, t in enumerate(uniq_times)}

    sim_arr = np.full((len(uniq_times), len(stations)), np.nan, dtype=np.float32)
    obs_arr = np.full((len(uniq_times), len(stations)), np.nan, dtype=np.float32)
    for t, st, sim, obs in rows:
        ti = time_index[t]
        si = station_index[st]
        sim_arr[ti, si] = sim
        obs_arr[ti, si] = obs

    # seconds since unix epoch UTC
    epoch = datetime(1970, 1, 1)
    tsec = np.array(
        [(datetime.fromisoformat(t) - epoch).total_seconds() for t in uniq_times],
        dtype=np.float64,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with Dataset(out_path, "w", format="NETCDF4") as ds:
        ds.createDimension("time", len(uniq_times))
        ds.createDimension("station", len(stations))
        ds.createDimension("name_strlen", 128)

        v_time = ds.createVariable("time", "f8", ("time",))
        v_x = ds.createVariable("station_x", "f8", ("station",))
        v_y = ds.createVariable("station_y", "f8", ("station",))
        v_sim = ds.createVariable("simulated_depth", "f4", ("time", "station"), fill_value=np.float32(np.nan))
        v_obs = ds.createVariable("observed_depth", "f4", ("time", "station"), fill_value=np.float32(np.nan))
        v_name = ds.createVariable("station_name", "S1", ("station", "name_strlen"))

        v_time[:] = tsec
        v_x[:] = np.array([s["x"] for s in stations], dtype=np.float64)
        v_y[:] = np.array([s["y"] for s in stations], dtype=np.float64)
        v_sim[:, :] = sim_arr
        v_obs[:, :] = obs_arr

        name_bytes = np.zeros((len(stations), 128), dtype="S1")
        for i, s in enumerate(stations):
            b = s["name"].encode("utf-8")[:128]
            name_bytes[i, : len(b)] = np.frombuffer(b, dtype="S1")
        v_name[:, :] = name_bytes

        v_time.units = "seconds since 1970-01-01 00:00:00"
        v_time.standard_name = "time"
        v_time.axis = "T"
        v_x.standard_name = "projection_x_coordinate"
        v_x.units = "m"
        v_y.standard_name = "projection_y_coordinate"
        v_y.units = "m"
        v_sim.units = "m"
        v_obs.units = "m"
        v_sim.long_name = "Simulated flood depth at IoT stations"
        v_obs.long_name = "Observed flood depth at IoT stations"

        ds.title = "Flood event IoT validation timeseries"
        ds.crs = "EPSG:3826"
        ds.created_at_utc = datetime.now(timezone.utc).isoformat()

    return {
        "path": str(out_path),
        "time_steps": len(uniq_times),
        "stations": len(stations),
        "rows_ingested": len(rows),
    }


def _write_iot_validation_parquet(
    tidy_csv_path: Path, station_csv_path: Path, map_nc_path: Path, out_path: Path
) -> dict[str, Any]:
    station_rows = _read_stations_from_csv(station_csv_path)
    station_xy = {s["name"]: (s["x"], s["y"]) for s in station_rows}
    station_face_mapping = _build_station_face_mapping(map_nc_path, station_rows)
    station_face = {r["station"]: r for r in station_face_mapping}

    df = pd.read_csv(tidy_csv_path)
    if "station" not in df.columns or "time" not in df.columns:
        raise RuntimeError("IoT tidy CSV missing required columns: station/time")

    # Normalize canonical schema for downstream analytics.
    df = df.rename(
        columns={
            "time": "time_utc",
            "station": "station_id",
        }
    )
    df["time_utc"] = pd.to_datetime(df["time_utc"], errors="coerce", utc=True)
    df["simulated_depth_m"] = pd.to_numeric(df.get("simulated_depth_m"), errors="coerce")
    df["observed_depth_m"] = pd.to_numeric(df.get("observed_depth_m"), errors="coerce")

    df["station_x"] = df["station_id"].map(lambda s: station_xy.get(s, (np.nan, np.nan))[0])
    df["station_y"] = df["station_id"].map(lambda s: station_xy.get(s, (np.nan, np.nan))[1])
    df["mesh2d_face_index"] = df["station_id"].map(
        lambda s: station_face.get(s, {}).get("nearest_face_index", np.nan)
    )
    df["mesh2d_face_x"] = df["station_id"].map(
        lambda s: station_face.get(s, {}).get("nearest_face_x", np.nan)
    )
    df["mesh2d_face_y"] = df["station_id"].map(
        lambda s: station_face.get(s, {}).get("nearest_face_y", np.nan)
    )
    df["pixel_index"] = df["mesh2d_face_index"]
    df["grid_id"] = df["mesh2d_face_index"].map(
        lambda v: f"mesh2d_face_{int(v)}" if pd.notna(v) else None
    )
    df["mesh2d_face_index"] = pd.to_numeric(df["mesh2d_face_index"], errors="coerce").astype("Int64")
    df["pixel_index"] = pd.to_numeric(df["pixel_index"], errors="coerce").astype("Int64")
    df["crs"] = "EPSG:3826"
    df = df.sort_values(["time_utc", "station_id"]).reset_index(drop=True)
    ordered_cols = [
        "time_utc",
        "station_id",
        "simulated_depth_m",
        "observed_depth_m",
        "station_x",
        "station_y",
        "mesh2d_face_index",
        "mesh2d_face_x",
        "mesh2d_face_y",
        "grid_id",
        "pixel_index",
        "crs",
    ]
    df = df[[c for c in ordered_cols if c in df.columns]]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False, compression="zstd")

    return {
        "path": str(out_path),
        "rows": int(len(df)),
        "stations": int(df["station_id"].nunique(dropna=True)),
        "time_steps": int(df["time_utc"].nunique(dropna=True)),
        "columns": list(df.columns),
    }


def _write_depth_timeseries_at_stations(
    map_nc_path: Path, station_csv_path: Path, out_csv_path: Path, index_json_path: Path
) -> dict[str, Any]:
    stations = _read_stations_from_csv(station_csv_path)
    if not stations:
        raise RuntimeError("No station points found in station CSV.")
    mapping_rows = _build_station_face_mapping(map_nc_path, stations)
    face_index_by_station = {row["station"]: int(row["nearest_face_index"]) for row in mapping_rows}
    station_face_idx = [face_index_by_station[st["name"]] for st in stations]

    with Dataset(map_nc_path, "r") as ds:
        wd = ds.variables["Mesh2d_waterdepth"]
        fill = getattr(wd, "_FillValue", -999.0)
        tvals = np.array(ds.variables["time"][:], dtype=np.float64)
        tunits = getattr(ds.variables["time"], "units", "")

        ts = np.array(wd[:, station_face_idx], dtype=np.float32)
        ts[ts == fill] = np.nan

    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with out_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_raw", "time_units", "station", "face_index", "simulated_depth_m"])
        for ti, tv in enumerate(tvals):
            for si, st in enumerate(stations):
                val = ts[ti, si]
                writer.writerow([f"{tv}", tunits, st["name"], station_face_idx[si], "" if np.isnan(val) else f"{val:.6f}"])

    index_json_path.parent.mkdir(parents=True, exist_ok=True)
    index_payload = {
        "source_file": str(map_nc_path),
        "time_units": tunits,
        "mapping_method": "nearest_mesh2d_face",
        "grid_id_format": "mesh2d_face_{nearest_face_index}",
        "station_face_mapping": mapping_rows,
    }
    index_json_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_csv_path),
        "rows": int(ts.shape[0] * ts.shape[1]),
        "time_steps": int(ts.shape[0]),
        "stations": int(ts.shape[1]),
        "index_path": str(index_json_path),
    }


def export_core_products(event_dir: Path, out_root: Path) -> dict[str, Any]:
    rain_src = next((event_dir / "輸入雨量" / "WGS84").glob("*.nc"))
    map_nc = event_dir / "輸出成果" / "output" / "FM_model_map.nc"
    shp = event_dir / "IOT_catch" / "IOT_shpfile" / "YS_IOT.shp"
    xlsx = event_dir / "IOT_catch" / "20210604比對分析.xlsx"

    event_id = event_dir.name.replace("flood_modelling_", "event_")
    base = out_root / event_id
    forcing_dir = base / "forcing"
    result_dir = base / "results"
    validation_dir = base / "validation"

    forcing_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    rain_out = forcing_dir / "rainfall_wgs84.nc"
    shutil.copy2(rain_src, rain_out)

    max_depth_meta = _write_max_depth_netcdf(map_nc, result_dir / "max_depth_faces.nc")
    iot_export_meta = _export_iot_points(shp, validation_dir)
    iot_tidy_meta = _parse_xlsx_20210604_to_tidy_csv(xlsx, validation_dir / "iot_validation_timeseries_tidy.csv")
    iot_nc_meta = _write_iot_validation_netcdf(
        Path(iot_tidy_meta["path"]),
        Path(iot_export_meta["csv"]),
        validation_dir / "iot_validation_timeseries.nc",
    )
    iot_parquet_meta = _write_iot_validation_parquet(
        Path(iot_tidy_meta["path"]),
        Path(iot_export_meta["csv"]),
        map_nc,
        validation_dir / "iot_validation_timeseries.parquet",
    )
    depth_ts_meta = _write_depth_timeseries_at_stations(
        map_nc,
        Path(iot_export_meta["csv"]),
        result_dir / "simulated_depth_timeseries_at_iot_stations.csv",
        result_dir / "simulated_depth_timeseries_station_index.json",
    )

    summary = {
        "event_id": event_id,
        "output_root": str(base),
        "products": {
            "forcing_rainfall": str(rain_out),
            "result_max_depth": max_depth_meta,
            "result_depth_timeseries": depth_ts_meta,
            "validation_iot_points": iot_export_meta,
            "validation_iot_tidy_timeseries": iot_tidy_meta,
            "validation_iot_netcdf": iot_nc_meta,
            "validation_iot_parquet": iot_parquet_meta,
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = base / "export_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Export core flood-event products into STAC-ready files.")
    parser.add_argument(
        "--event-dir",
        type=Path,
        default=Path("data/flood_modelling_20210604"),
        help="Event directory path.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/flood_modelling_products"),
        help="Root folder for exported files.",
    )
    args = parser.parse_args()

    summary = export_core_products(args.event_dir, args.output_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
