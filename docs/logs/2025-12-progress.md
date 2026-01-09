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
    - Build script `start.sh` now supports `./start.sh build`.
    - Integrated `tmux` for robust background server management.

## 2026-01-09
- **Visuals & Metadata Refinement**:
    - **Thumbnails**: Optimized logic to use `max()` of first 24h (48 steps) instead of `mean()` to avoid washing out sparse signals (Precipitation/Radar).
    - **ERA5**: Fixed missing visuals by setting `sea_surface_temperature` and ensuring correct xstac dimension mapping.
    - **QPESUMS**: Fixed missing xstac metadata by implementing explicit `latitude`/`longitude` detection in `intake_xarray.py`.
    - **Clean build**: Fixed `base.py` to remove hardcoded ERA5 paths, solving the "phantom item thumbnail" 404 issue in IMERG.
    - **UX**: Added human-readable titles (`title` field) to ERA5 catalogs for better Browser display.

### Design Proposal: Generator Refactoring
User suggested splitting `IntakeXarrayGenerator` into domain-specific classes (e.g., `Era5Generator`, `RadarGenerator`).

**Why? (Impact Analysis)**
- **Current State**: Single `IntakeXarrayGenerator` handles generic logic but is getting complex with specific "quirks" (e.g., MaxDBZ vs SST, specific xstac mappings).
- **Pros (Benefits)**:
    - **Decoupling**: Changes to Radar logic wont break ERA5.
    - **Specialization**: Can hardcode domain knowledge (e.g., "Radar always has MaxDBZ", "ERA5 always needs these extensions") without pollution.
    - **Stricter Schemas**: Can enforce different validation rules per dataset type.
- **Cons (Trade-offs)**:
    - **Boilerplate**: Might repeat some "load catalog" logic (mitigated by good Base class).
    - **Migration**: Need to update `main.py` to select the right generator class based on config.

**Plan**: Move this to ROADMAP as a priority items.

## Next Steps
- Verify generated catalogs in STAC Browser.
- Refine Root Catalog to include all generated collections.
- Discuss Intake YAML descriptions with the team.
