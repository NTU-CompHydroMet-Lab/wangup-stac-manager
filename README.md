# Research Lab STAC Manager

![Version](https://img.shields.io/badge/version-2.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

An **enterprise-grade, configuration-driven** pipeline to transform raw scientific data (NetCDF, Zarr) into compliant [SpatioTemporal Asset Catalog (STAC)](https://stacspec.org/) indexes. Designed for reproducibility, scalability, and ease of use in research environments.

---

## Key Features

*   **Modular Architecture**: Fully decoupled logic. Configuration lives in `config/`, code in `src/`, and data in `stac_catalog/`.
*   **Configuration-First**: Control **server ports**, **directory paths**, **grouping logic**, and **build targets** entirely via `config/main.yaml`. No code changes required.
*   **Smart Hierarchy**: Automatically groups collections (e.g., `imerg_early`, `imerg_final`) into logical sub-catalogs (`stac_catalog/imerg/`) based on ID prefixes.
*   **Intake Integration**: Uses [Intake](https://intake.readthedocs.io/) as the "Source of Truth" for dataset definitions.
*   **Automated Thumbnails**: Generates representative maps from data variables, with configurable strategies (`middle` timestep, `max` projection, etc.).
*   **Built-in Visualization**: Bundles a pre-configured **STAC Browser** for immediate local viewing.
*   **Robust Geometry**: Automatically handles complex geospatial cases like **antimeridian crossing** (Pacific View) and **CF-convention** dimension detection.

---

## System Architecture

| Directory | Role | Description |
| :--- | :--- | :--- |
| **`config/`** | **Control Plane** | **User-editable**. Contains `main.yaml` (system settings) and `catalogs/` (dataset definitions). |
| **`src/`** | **Logic Plane** | **Internal**. Python source code. Includes `cli` (entry point), `core` (builders), and `generator` (metadata extraction). |
| **`stac_catalog/`** | **Data Plane** | **Output**. The generated static JSON catalog. Ready for S3/Web deployment. |
| **`stac_browser/`** | **View Plane** | **Static Assets**. The web frontend (`dist/`) served by the application. |

---

## Getting Started

### 1. Installation

This project uses [uv](https://github.com/astral-sh/uv) for lightning-fast dependency management.

```bash
# Install dependencies
uv sync
```

### 2. Quick Usage

We provide a robust management script `start.sh` for common operations:

```bash
# Start Server (Background via tmux)
# Serves catalog at http://localhost:8001 (configurable)
./start.sh

# Build All Catalogs (Incremental)
./start.sh build

# Clean & Rebuild (Recommended for production releases)
# Wipes 'stac_catalog/' and regenerates from scratch to ensure consistency.
./start.sh clean-build

# Stop Background Server
./start.sh stop
```

---

## Configuration Guide

The system is controlled by `config/main.yaml`. See `config/README.md` for deep dive details.

### System Settings (`config/main.yaml`)
```yaml
filesystem:
  output_dir: "stac_catalog"  # Where JSONs are saved
  static_dir: "stac_browser"  # Where UI assets live

server:
  host: "0.0.0.0"
  port: 8001

grouping:
  strategy: "prefix"          # Groups 'imerg_early' -> 'imerg/imerg_early'
  separator: "_"
```

### Dataset Definition (`config/catalogs/*.yaml`)
Define your data sources using standard Intake YAML syntax, plus a `metadata` block for STAC properties.

```yaml
sources:
  my_dataset:
    driver: zarr
    args: { urlpath: "s3://bucket/*.zarr" }
    metadata:
      id: "my_dataset_v1"
      category: "SATELLITE"
      thumbnail_method: "max"  # Options: middle (default), mean, max
```

---

## Workflow

1.  **Define**: Add a new block to `config/catalogs/my_data.yaml`.
2.  **Register**: Add the source to `build.targets` in `config/main.yaml`.
3.  **Build**: Run `./start.sh clean-build`.
4.  **Verify**: Visit `http://localhost:8001` to see your new dataset.

---

## Docker Support

Build and deploy anywhere using the provided container.

```bash
docker build -t stac-manager .
docker run -d -p 8001:8001 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/stac_catalog:/app/stac_catalog \
  stac-manager
```
