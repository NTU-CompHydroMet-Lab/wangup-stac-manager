# 🌍 Intake-to-STAC Static Generator

**Automated CLI pipeline to convert Intake catalogs (Zarr, NetCDF) into compliant static STAC catalogs with built-in validation and browser UI.**

This tool bridges the gap between human-curated data definitions (Intake) and machine-readable geospatial indexes (STAC). It generates a fully static, serverless STAC API that can be hosted on any object storage (S3, GCS) or standard web server.

---

## 🚀 Key Features

*   **Intake as Source of Truth**: Define your datasets once in `catalogs/*.yaml`.
*   **Static Generation**: Converts dynamic data (Zarr, NetCDF) into static JSON files (`Collection`, `Item`).
*   **Automatic Validation**: Validates every generated item against STAC specifications using `pystac`.
*   **Dynamic Metadata**: Automatically extracts Bounding Box, Time Range, and GSD (Ground Sample Distance) from the actual data.
*   **Built-in Viewer**: Includes a pre-configured [STAC Browser](https://github.com/radiantearth/stac-browser) for immediate visualization.

---

## 📂 Project Structure

| Directory | Description |
| :--- | :--- |
| **`catalogs/`** | **Input**. Intake YAML files defining datasets (e.g., `era5_intake_catalog.yaml`). This is where you add new data. |
| **`scripts/`** | **Tools**. CLI scripts for generation and validation. |
| &nbsp;&nbsp;`generate_stac.py` | Main ETL script. Reads Intake -> Writes STAC JSON. |
| &nbsp;&nbsp;`generate_root_catalog.py` | Organizes generated collections into a hierarchy (Root -> Group -> Collection). |
| &nbsp;&nbsp;`validate_stac.py` | Recursively validates the entire output folder. |
| **`src/`** | **Core Logic**. Python package containing the generator engine. |
| &nbsp;&nbsp;`generator/` | Logic for extracting metadata from Xarray/Intake and creating STAC objects. |
| &nbsp;&nbsp;`server.py` | Lightweight FastAPI server for hosting the static files and Browser UI. |
| **`stac_output/`** | **Output**. The generated static STAC JSON files. **Do not edit manually.** |
| **`static/`** | **Assets**. Contains the built STAC Browser frontend (`dist/`). |

---

## 🛠️ Quick Start

### 1. Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

```bash
# Initialize environment and install dependencies
uv sync
```

### 2. Generate STAC Catalog

This reads all catalogs in `catalogs/` and generates JSON files in `stac_output/`.

```bash
# Generate all datasets
python scripts/generate_stac.py --source all --catalog catalogs
```

### 3. Build Hierarchy

Link all generated collections into a unified Root Catalog.

```bash
python scripts/generate_root_catalog.py
```

### 4. Serve & Browse

Start the local server to view your catalog.

```bash
python src/server.py
```

Open **[http://localhost:8001](http://localhost:8001)** in your browser.

---

## 🔄 Workflow

1.  **Add Data**: Create a new entry in `catalogs/your_catalog.yaml`.
2.  **Generate**: Run `scripts/generate_stac.py`.
3.  **Link**: Run `scripts/generate_root_catalog.py`.
4.  **Deploy**: Upload the `stac_output/` folder to any web server or S3 bucket.

---

## 🧪 Validation

To ensure your catalog complies with STAC standards:

```bash
python scripts/validate_stac.py
```
