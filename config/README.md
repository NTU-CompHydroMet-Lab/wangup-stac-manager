# Configuration Guide

This directory contains the "Control Plane" for the STAC Manager. The system is designed to be **configuration-driven**, meaning you rarely need to touch the Python code in `src/`.

---

## 1. Main Configuration (`main.yaml`)

This is the global configuration file. It controls **how** the application runs and **what** it builds.

### Structure

#### `project`
Global metadata for the Root Catalog.
```yaml
project:
  title: "My Data Catalog"
  description: "A description provided to the STAC root."
```

#### `filesystem`
Controls input/output paths.
```yaml
filesystem:
  output_dir: "stac_catalog"  # Destination for generated JSONs
  static_dir: "stac_browser"  # Source of STAC Browser UI assets
```

#### `server`
Settings for the FastAPI web server.
```yaml
server:
  host: "0.0.0.0" # Listen on all interfaces
  port: 8001      # Port number
```

#### `grouping`
Controls how collections are organized in the hierarchy.
```yaml
grouping:
  strategy: "prefix"  # Currently the only supported strategy
  separator: "_"      # Delimiter (e.g., 'imerg_early' -> Group 'imerg')
```

#### `concurrency`
Performance tuning.
```yaml
concurrency:
  max_workers: 5  # Number of parallel build processes. Increase if you have many cores.
```

#### `build.targets`
The list of datasets to generate.
```yaml
build:
  targets:
    # 'catalog': Path to the Intake YAML file
    # 'source': The key name inside that YAML file
    - catalog: "config/catalogs/imerg.yaml"
      source: "imerg_early_v07"
```

---

## 2. Dataset Catalogs (`catalogs/*.yaml`)

These are standard **Intake** catalog files. We use the `metadata` section to inject STAC-specific properties.

### Global Metadata (Required)

Every Intake YAML **MUST** start with a `metadata` block defining the catalog name. This name determines the sub-directory in the output (e.g., `stac_catalog/IMERG/`).

```yaml
metadata:
  catalog_name: "IMERG"  # -> stac_catalog/imerg/
  catalogs_keywords:     # Search tags for the folder
    - "satellite"
    - "satellite"
    - "precipitation"
  description: "Detailed description of this catalog (Markdown supported)."
  version: 1
```

### Dataset Fields

| Field | Description |
| :--- | :--- |
| `description` | Human-readable summary. Supports Markdown. |
| `driver` | `netcdf` or `zarr`. |
| `metadata.id` | **Unique** identifier (e.g., `imerg_final_v07`). |
| `metadata.category` | Grouping tag (e.g., `SATELLITE`, `RADAR`). |

### Optional / Advanced Fields

| Field | Description | Default |
| :--- | :--- | :--- |
| `metadata.thumbnail_variable` | Name of the data variable to map (e.g., `precipitation`). | `None` |
| `metadata.thumbnail_method` | Strategy for selecting time slice: `middle`, `mean`, `max`. | `middle` |
| `metadata.keywords` | List of search tags. | `[]` |
| `metadata.providers` | List of `{name, url, roles}` objects. | `[]` |

### Example

```yaml
sources:
  my_dataset:
    description: "Global Precipitation Measurement"
    driver: zarr
    args:
      urlpath: "s3://my-bucket/data.zarr"
    metadata:
      id: "gpm_imerg"
      category: "SATELLITE"
      thumbnail_variable: "precipitation"
      thumbnail_method: "max"  # Use maximum value projection for thumbnails
      keywords: ["rain", "nasa", "global"]
```
