# Progress Log: Internal Deployment & Refactoring (2026-01-09)

## 1. Objectives & Context
**Goal**: Transition the STAC Catalog from a "local prototype" to a **robust internal service** for the NTU CompHydroMet Lab.
**Constraints**:
- **Data Privacy**: Data resides on NAS and must not be exposed publicly.
- **Intranet Access**: Users access via VPN/Internal IP.
- **Usability**: Must support search (keywords) and direct data access without manual mounting.

## 2. Changes Implemented

### A. Documentation & Searchability
- **Added `keywords` Support**:
    - Updated `imerg_intake_catalog.yaml` to include "keywords" fields.
    - Updated `base.py` to extract these keywords into the STAC Collection JSON.
    - **Result**: Users can now filter by `[Precipitation, Satellite, GPM]` in the STAC Browser.
- **Standardized Templates**:
    - Created `catalogs/template_zarr.yaml` as a copy-paste standard for team members.
    - Heavily commented `imerg_intake_catalog.yaml` to serve as a user manual.

### B. Internal Deployment Architecture
- **Problem**: STAC Items pointed to absolute file paths (`file:///home/NAS/...`). Remote users (on laptops) cannot open these links.
- **Solution**: "Symlink Strategy".
    - `server.py` hosts the `stac_output` folder.
    - Generator now creates a **Local Symlink** inside `items/` for every Zarr dataset.
    - **Asset Href**: Changed from `/home/NAS/x.zarr` to `./x.zarr` (Relative).
    - **Result**: The Server acts as a proxy/host for the data. Users download data directly from the server URL, no local mounting required.

### C. Code Refactoring
- **Problem**: `src/generator/base.py` became "bloated" and hard to review.
- **Solution**: Extracted logic into modular files.
    - `src/generator/utils.py`: Time, Extent, Spatial helpers.
    - `src/generator/thumbnails.py`: Visualization logic (Matplotlib).
    - `src/generator/assets.py`: Asset linking, Symlink logic, Notebooks.
    - **Result**: `base.py` is now a clean orchestrator, importing logic from these modules.

### D. Source Cleanup
- **Removed Unused Code**: Deleted `src/adapters` as it was legacy/unused.
- **Added Documentation**: Created `src/README.md` explaining the directory structure and file responsibilities.

## 3. Next Steps
- [x] **Verification**: Confirm the "Symlink Strategy" works for a real remote user (simulation).
- [ ] **Code Review**: Review the new modular structure.
- [ ] **Data Handling**: Verify that huge Zarr files are served correctly via `server.py` (FastAPI).
