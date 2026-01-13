# Project Roadmap: STAC Catalog & Internal Deployment

## Phase 1: Foundation (Completed) ✅
- [x] **Core Refactoring**: Modularized `base.py`, `assets.py`, `utils.py`.
- [x] **Deployment Config**: Dockerfile, Podman support, `docker-compose.yml`.
- [x] **Intranet Access**: Symbolic links strategy & `server.py` modification.
- [x] **Documentation**: `DEPLOY.md`, `src/README.md`.

## Phase 2: Architecture Optimization (Next Priority) 🏗️
**Goal**: Automate the workflow and ensure robustness.

### 2.1 CI/CD (GitHub Actions)
- **Automated Testing**: Run `pytest tests/` on every push.
- **Docker Build**: Build and push image to GitHub Container Registry (ghcr.io) on tag/push.
- **Linting**: Ruff/Black enforce code style.

### 2.2 Container Optimization
- **Multi-stage Build**: Reduce image size (currently uses `python:3.11-slim`, can be optimized).
- **Health Checks**: Add `HEALTHCHECK` to Dockerfile for production reliability.

## Phase 2.5: PySTAC Migration (Highest Priority) 🛡️# Implementation Plan (COMPLETED)
**Goal**: Eliminate "dict-bashing" and ensure strict STAC compliance.
- **Refactoring Strategy**:
    1.  Modify `assets.py` to return `pystac.Asset`.
    2.  Modify `base.py` to instantiate `pystac.Item` and `pystac.Collection` instead of dicts.
    3.  Use `pystac.validate()` in the test suite to catch schema errors immediately.
- **Benefit**: 
    - Type safety.
    - Automatic validation of required fields.
    - Easier integration with `stac-fastapi` later.

## Phase 3: User Experience (New Features) ✨
**Goal**: Make it easier for researchers to Add Data and Use Data.

### 3.1 Metadata Editor (Web Form)
*Problem*: Editing YAML by hand is error-prone.
*Solution*: A lightweight Web UI (Streamlit or FastAPI+React) to:
- Input dataset details (Source path, Description, Time range).
- **Preview**: Real-time STAC Item preview.
- **Generate**: Download/Save valid `intake_catalog.yaml`.

### 3.2 "Copy Code" Feature
*Problem*: Users see the data in STAC Browser but don't know the exact Python lines to load it.
*Solution*:
- **Enhancement**: Add a "Usage" tab or button in the Web UI.
- **Output**:
    ```python
    # Auto-generated snippet
    import xarray as xr
    # Direct HTTP Access (Internal)
    ds = xr.open_dataset("http://stac.lab.internal/...", engine="zarr")
    ```
#### [NEW] [utils.py](file:///home/sungche/stac/src/generator/utils.py)
#### [NEW] [intake_xarray.py](file:///home/sungche/stac/src/generator/intake_xarray.py)

---

# Phase 3: Architecture Restructuring (Current)

## Goal Description
Consolidate configuration into a single YAML file and reorganize the project structure for better modularity and cleanliness.

## Proposed Changes

### Configuration
1.  **Merge `catalogs.json` and `config.yaml`** into `config/main.yaml`.
2.  **Move Catalog YAMLs** to `config/catalogs/`.
3.  **Update `src/settings.py`** to reflect the new structure.

### File Structure
```text
.
├── config/                 # <--- Centralized Configuration
│   ├── main.yaml           # Combined settings and build targets
│   └── catalogs/           # Intake catalog definitions
├── src/
│   ├── core/               # Workflow logic
│   ├── generator/          # STAC generation logic
│   ├── server/             # Server application (moved from src/server.py)
│   ├── cli.py              # CLI entry point (moved from src/main.py)
│   └── settings.py
├── stac_output/
└── pyproject.toml
```

### Component Updates
#### [MODIFY] [server.py](file:///home/sungche/stac/src/server.py) -> [src/server/app.py](file:///home/sungche/stac/src/server/app.py)
#### [MODIFY] [main.py](file:///home/sungche/stac/src/main.py) -> [src/cli.py](file:///home/sungche/stac/src/cli.py)
#### [MODIFY] [settings.py](file:///home/sungche/stac/src/settings.py)

## Verification Plan
1.  Verify `uv run src/cli.py build --clean` works with new paths.
2.  Verify `uv run src/cli.py serve` works.
- **Action**: Generator needs to template these snippets into the Asset metadata (or the UI generates them dynamically).

## Phase 4: Data Services (Future) 🚀
- **Dynamic API**: `stac-fastapi` for advanced search (not just static JSON).
- **On-demand Tiling**: `titiler` for visualizing huge NetCDF/Zarr without pre-generating PNGs.
