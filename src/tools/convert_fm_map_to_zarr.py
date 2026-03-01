from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import xarray as xr


DEFAULT_VARS = [
    "time",
    "Mesh2d_face_x",
    "Mesh2d_face_y",
    "mesh1d_node_x",
    "mesh1d_node_y",
    "Mesh2d_waterdepth",
    "mesh1d_waterdepth",
]


def convert_fm_map_to_zarr(
    input_nc: Path,
    output_zarr: Path,
    include_vars: list[str] | None = None,
    overwrite: bool = False,
) -> dict:
    if output_zarr.exists():
        if not overwrite:
            raise FileExistsError(f"Output exists: {output_zarr}")
        shutil.rmtree(output_zarr)

    vars_wanted = include_vars or DEFAULT_VARS
    # Keep decode_times=False to preserve native numeric time and speed up conversion.
    ds = xr.open_dataset(
        input_nc,
        engine="netcdf4",
        decode_times=False,
        chunks={
            "time": 1,
            "Mesh2d_nFaces": 100_000,
            "mesh1d_nNodes": 10_000,
            "Mesh2d_nEdges": 100_000,
            "mesh1d_nEdges": 10_000,
        },
    )

    existing = [v for v in vars_wanted if v in ds.variables]
    if not existing:
        raise RuntimeError("None of the requested variables were found.")

    ds_out = ds[existing]
    ds_out.to_zarr(output_zarr, mode="w", consolidated=True)

    stat = {
        "input_nc": str(input_nc),
        "output_zarr": str(output_zarr),
        "included_variables": existing,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return stat


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert FM_model_map.nc core variables to Zarr.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/flood_modelling_20210604/輸出成果/output/FM_model_map.nc"),
        help="Input NetCDF path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/flood_modelling_products/event_20210604/results/fm_map_core.zarr"),
        help="Output Zarr directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output directory if it already exists.",
    )
    args = parser.parse_args()

    stat = convert_fm_map_to_zarr(args.input, args.output, overwrite=args.overwrite)
    summary_path = args.output.parent / "fm_map_core_zarr_summary.json"
    summary_path.write_text(json.dumps(stat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**stat, "summary_path": str(summary_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
