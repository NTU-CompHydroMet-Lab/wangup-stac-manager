Here is the consolidated PRD (Version 1.2). I have integrated the **Intake → STAC workflow** and added a specific **Mapping Specification** section. This aligns the "Human Consensus" (Intake) with the "Machine Implementation" (STAC) so the Agent knows exactly how to map `Catalog`, `Collection`, `Item`, and `Asset`.

---

# 📝 PRD: Research Lab STAC Manager (CLI Edition)

**Version**: 1.2
**Date**: 2025-12-20
**Target**: Build an automated CLI tool to convert multi-source heterogeneous data (Zarr, NetCDF, SQLite) on NAS into STAC standard format, sync to API, and enforce an **Intake Catalog → STAC JSON** workflow.

---

## 1. Tech Stack

* **Language**: Python 3.12+
* **Package Manager**: **`uv`** (Strict requirement. No pip/conda)
* **CLI Framework**: `typer` (Supports Rich output)
* **Data Processing**:
* DB/CSV: `duckdb` (OLAP Engine)
* Array: `xarray`, `zarr`, `netcdf4`
* **Metadata**: `pystac`, `stactools`, `intake`
* **Server**: Static File Server (FastAPI) + STAC Browser

---

## 2. Functional Requirements

### 2.1 Core CLI (`src/main.py`)

* Must be a `Typer` application.
* **Commands**:
* `sync`: Execute synchronization. Argument `--dataset [cwa|qpesums|era5|all]` (default: all).
* `init-db`: Initialize STAC Collections (execute once).


* **Error Handling**: Failure in reading a single file/item must NOT crash the program. Log the error and proceed to the next item.

### 2.2 Intake → STAC Workflow (Metadata Master Strategy)

This system uses Intake as the "Source of Truth" for human curation, and STAC as the "Machine Index".

1. **Intake Catalog as Metadata Master**
* All datasets are first defined in `catalog.yaml` (defining paths, chunks, variables, and custom metadata like `tier`).
* **Role**: Team members use Intake to verify dataset integrity and usability *before* STAC generation.


2. **Adapter Logic (Intake Reader)**
* Adapters do not hardcode paths; they read from the Intake Catalog definition.
* **Mapping Rule**:
* **STAC Collection**  Intake Entry (The Dataset).
* **STAC Item**  Logical Slice (e.g., 1 Year of Zarr, or 1 SQLite DB).
* **STAC Asset**  Physical Resource (The Zarr store path, the `.db` file).
* **Properties**  Intake metadata (tier, source, description).




3. **Sync to STAC API**
* CLI compares calculated Item IDs with existing records.
* Perform `POST /items` only if the Item is new or metadata has changed.
* **Idempotency**: Item IDs must be deterministic (e.g., `qpesums-2023`).



---

### 2.3 Adapter Modules (`src/adapters/`)

Agents must implement adapters inheriting from `BaseAdapter`, following the Mapping Specifications in Section 5.

#### A. `CwaGaugeAdapter` (Tabular Data)

* **Source**: Intake entry for CWA Rain Gauge (SQLite).
* **Logic**:
* Use DuckDB to query `min/max(time)` and `min/max(lon/lat)` for STAC `extent`.
* **Aggregation**: Do not load all data into Pandas; use SQL aggregation.


* **Output**: Single STAC Item for the entire station history (Snapshot approach).

#### B. `GriddedDataAdapter` (Array Data: QPESUMS, ERA5, Himawari)

* **Source**: Intake entry for Zarr/NetCDF roots.
* **Logic**:
* Recursively scan storage or read Zarr consolidated metadata.
* Use `xarray` to extract spatial bbox and time range.
* **Splitting**: If filenames/stores are organized by year, generate **one STAC Item per Year**.


* **Properties**: Inject `processing:level` (bronze/silver/gold) from Intake config.

---

### 2.4 Static Server
* `src/server.py`: FastAPI application serving static STAC JSON and STAC Browser.
* **Port**: 8001



---

## 3. Reference Commands

```bash
# 1. Environment Init
uv init
uv add typer pystac pystac-client xarray zarr netcdf4 duckdb rich requests intake fastapi uvicorn

# 2. Generate STAC Catalog
# Generate all sources from all catalogs
python scripts/generate_stac.py --source all --catalog catalogs

# 3. Generate Root Catalog (Hierarchy)
python scripts/generate_root_catalog.py

# 4. Start Static Server
python src/server.py
```

---

## 4. Development Guidelines

1. **DuckDB is Mandatory**: For CWA/Tabular data, aggregations must happen at the SQL level to prevent OOM.
2. **Idempotency**: The `sync` command must be idempotent.
3. **Path Mapping**: Currently using Host Absolute Paths.
4. **Error Handling**: Log failures, don't crash.
5. **Strict Hierarchy**: Do not create "Catalog" folders for data types. Follow the STAC specification: `Catalog -> Collection -> Item -> Asset`.

---

## 5. Intake → STAC Mapping Specifications (Implementation Rules)

This section defines how the Agent must map Lab concepts to STAC objects.

### 5.1 General STAC Hierarchy Logic

| STAC Level | Lab Concept | Responsibility | Rules |
| --- | --- | --- | --- |
| **Catalog** | Lab Data Root | System | Only one root catalog. Do not use for "Data Type" classification. |
| **Collection** | **The Dataset** | **Intake** | Defines scientific boundary (e.g., "QPESUMS"). Holds the aggregate Bbox/Time. |
| **Item** | **Logical Unit** | Adapter | **1 Item = 1 Year** (for Zarr) or **1 Item = 1 Snapshot** (for DB). Avoid daily items to reduce noise. |
| **Asset** | **Physical File** | Adapter | Points to the actual Zarr store or SQLite file. |
| **Property** | Metadata | Intake | `processing:level` (tier), `data:source`, `gsd`. |

### 5.2 Specific Dataset Mapping Table

Agent usage: Implement adapters to satisfy these mappings.

| Dataset (Collection) | Item Strategy (Granularity) | Asset Media Type | Processing Level | Key Metadata Fields |
| --- | --- | --- | --- | --- |
| **QPESUMS** | **Yearly** (`qpesums-2023`) | `application/vnd+zarr` | Silver | `constellation`: "radar"<br>

<br>`gsd`: 1300m |
| **ERA5 Convection** | **Yearly** or Multi-Year | `application/vnd+zarr` | Bronze/Silver | `source`: "ECMWF"<br>

<br>`variables`: ["u", "v", "w"] |
| **Himawari L2** | **Yearly** | `application/vnd+zarr` | Silver | `platform`: "himawari-8"<br>

<br>`gsd`: 500m |
| **CWA Rain Gauge** | **Single Item** (Snapshot) | `application/vnd.sqlite3` | Gold | `source`: "CWA"<br>

<br>`station_count`: (calc from db) |

### 5.3 STAC Item ID Naming Convention

To ensure idempotency, Item IDs must follow:

* **Gridded**: `{collection_id}-{year}` (e.g., `qpesums-2023`)
* **Static/DB**: `{collection_id}-source` (e.g., `cwa-gauge-sqlite`)

---

### Summary for the Agent

* **Input**: `catalog.yaml` (Intake)
* **Process**: Iterate entries -> Apply Adapter -> Generate STAC Item JSON.
* **Output**: `POST` to STAC API.

### Static ERA5 STAC Example

A static STAC Collection and a sample Item have been generated for the **ERA5 Convection** dataset using the intake catalog `catalogs/era5_intake_catalog.yaml`.

- Collection JSON: `stac_output/era5/collection.json`
- Sample Item (2020) JSON: `stac_output/era5/items/era5_convection-2020.json`

These files conform to the STAC 1.0.0 specification and can be inspected directly or uploaded to a STAC API for testing.