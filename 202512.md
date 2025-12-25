# 2025-12 Project Progress Log

## 2025-12-23
- **Architecture Shift**: Transitioned from a dynamic STAC API (FastAPI + PostGIS) to a **Static STAC** architecture.
    - Removed `docker-compose.yml` and dynamic API code.
    - Implemented `StacGenerator` for static JSON generation.
    - Created `src/server.py` to serve static files and STAC Browser.
- **ERA5 Integration**:
    - Successfully generated STAC Catalog for ERA5 dataset (Yearly Items).
    - Integrated **`xstac`** for automated, rich metadata extraction (Datacube Extension).
    - Refactored pipeline: Script handles structure/links, `xstac` handles internal metadata (dimensions, variables).
- **GitHub Integration**:
    - Configured remote repository `NTU-CompHydroMet-Lab/wangup-stac-manager`.
    - Pushed `main` branch with all recent changes.

## 2025-12-25
- **Himawari Integration**:
    - Created `catalogs/himawari_intake_catalog.yaml`.
    - Resolved file path issues (`_clp_5km.zarr`).
    - Successfully generated STAC Catalog for `himawri_clp_2023`.
- **IMERG Integration**:
    - Created `catalogs/imerg_intake_catalog.yaml`.
    - Resolved file path issues (`Level` directory removed).
    - Updated generator to support `lon`/`lat` coordinate names (IMERG uses these instead of `longitude`/`latitude`).
    - Successfully generated STAC Catalog for `imerg_early` (Silver/Zarr).
    - Attempted generation for `imerg_bronze` (Bronze/HDF5) - *In Progress*.
- **CLI & Tooling**:
    - Created unified CLI `src/main.py` with `build` and `serve` commands.
    - Fixed STAC Browser configuration issue by injecting `config.js` into `index.html`.
    - Updated `README.md` with new workflow instructions.

## Next Steps
- Verify generated catalogs in STAC Browser.
- Refine Root Catalog to include all generated collections.
- Discuss Intake YAML descriptions with the team.
