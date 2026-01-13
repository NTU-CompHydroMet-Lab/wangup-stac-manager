# Generator Engine

The **Generator Engine** (`src/generator`) is the core component responsible for ingesting data from Intake sources and transforming them into valid STAC Items and Collections.

## Architecture

The generator follows a pipeline approach:
1.  **Load Source**: Reads metadata and opens the dataset using `Intake`.
2.  **Extract Metadata**: Parses attributes from the source driver.
3.  **Enrich Metadata (`xstac`)**: Uses `xstac` to extract Data Cube dimensions (Reference System, Temporal, Spatial) compatible with STAC extensions.
4.  **Geometry correction (`antimeridian`, `shapely`)**: Computes valid GeoJSON geometries, handling complex cases like Antimeridian crossing (Pacific-centered views).
5.  **Generate Items**: Iterates through time slices (e.g., yearly) to create STAC Items.
6.  **Thumbnail Generation**: Creates visual previews using `matplotlib`, with special handling for coordinate wrapping.

## Key Libraries & Responsibilities

### `intake-xarray` & `intake`
-   **Role**: Data Abstraction Layer.
-   **Function**: Configuration-driven access to NetCDF, Zarr, and GRIB files. Allows us to treat local files and remote objects uniformly.

### `xstac`
-   **Role**: STAC Metadata Enrichment.
-   **Function**: Analyzes `xarray.Dataset` objects to auto-populate `cube:dimensions` and `summaries`. It ensures we have standardized DescribeCoverage-like metadata without manual config.

### `cf_xarray`
-   **Role**: Climate and Forecast (CF) Convention Parsing.
-   **Function**: Used by `xstac` and our internal utils to reliably detect logical axes (Latitude vs Longitude, Time) regardless of variable naming (`lat`, `LATITUDE`, `y`, etc.).

### `antimeridian` & `shapely`
-   **Role**: Geometry Construction & Correction.
-   **Function**: 
    -   `shapely`: Constructs raw Polygons from Bounding Boxes.
    -   `antimeridian`: Splits Polygons that cross the 180th meridian (datateline) into properties MultiPolygons. This is critical for Pacific-centered datasets (e.g., Himawari) to be valid in STAC/GeoJSON.

## Key Modules

-   **`intake_xarray.py`**: The main driver for NetCDF/Zarr sources. Handles normalization (0-360 -> -180/180) and calls enrichment hooks.
-   **`utils.py`**: Shared logic for:
    -   `compute_extent`: Smart BBox calculation (detects Pacific view).
    -   `compute_item_geometry`: Generating valid split geometries (using `antimeridian`).
    -   `get_spatial_dims`: Robust coordinate extraction.
-   **`thumbnails.py`**: Visual generation.

## Usage

The generator is typically invoked by the `src.core.builder` module only, not directly by CLI.

```python
from src.generator.intake_xarray import IntakeXarrayGenerator

gen = IntakeXarrayGenerator(output_dir=Path("./out"), catalog_path=Path("cat.yaml"))
gen.generate("source_id")
```
