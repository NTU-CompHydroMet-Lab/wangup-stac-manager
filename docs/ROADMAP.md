# Project Roadmap & Agent Context

> **Note to Agents**: This file is the Source of Truth for the project's development direction. Read this first to understand the current state and what needs to be done next.

## 🟢 Current Status (2026-01-08)
- **Phase**: Documentation & Standardization.
- **Completed**:
  - Project structure cleanup (docs/ folder created).
  - Basic CLI implementation (`src/main.py`).
  - Initial Prototype for ERA5 & Himawari.
- **Pending**: Standardization of intake catalogs and automation.

---

## 🚀 Immediate Next Step (Priority)

**Goal**: Standardize the "Adding Dataset" workflow so specific metadata requirements are clear.

**Action Items for Agent**:
1.  **Checkout Branch**: `docs/standardization`
2.  **Source Material**: Read `docs/concepts/stac_hierarchy_design.md` (contains the draft checklist).
3.  **Target File**: Edit `docs/guides/adding_datasets.md`.
4.  **Tasks**:
    -   [ ] Migrate the "Checklist" from `stac_hierarchy_design.md` into `adding_datasets.md`.
    -   [ ] Define a explicit table of **Required** vs **Optional** metadata fields for `catalogs/*.yaml`.
    -   [ ] Create a "Template" snippet that users can copy-paste.
    -   [ ] Once migrated, verify if `stac_hierarchy_design.md` is still needed or can be deleted/archived.

---

## 📅 Roadmap (Future Items)

### Phase 2: Dataset Migration & Gap Analysis
*Branching*: `data/{dataset-name}` (e.g., `data/qpesums`)

-   **QPESUMS**: Full history scan, verify `gsd` and coordinate system.
-   **ERA5**: Split into strictly defined Collections (Tier differentiation).
-   **Gap Report**: Create a status table of missing metadata for existing datasets.

### Phase 3: Automation (Auto-trigger)
*Branching*: `feat/auto-trigger`

-   **Watchdog Script**: Python script to monitor file changes and trigger `main.py build`.
-   **Incremental Build**: Modify `Generator` to check file mtime (Idempotency). Only rebuild changed items.

### Phase 4: Operational Workflow
*Branching*: `feat/intranet-preview`

-   **Deployment**: Systemd service or Docker container for `server.py`.
-   **Workflow**: Establish the "Edit YAML -> Auto Preview" loop.

---

## 🛠 Branching Strategy Reminder

-   **Docs/Standards**: `docs/standardization`
-   **Features**: `feat/{feature-name}`
-   **Data Migration**: `data/{dataset-name}`
-   **Fixes**: `fix/{issue-name}`
