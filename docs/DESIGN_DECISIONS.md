# Design Decisions & Key Strategies

This document captures the "Decision Path" — the reasoning behind critical architectural and design choices in the NTU CompHydroMet Lab Data Catalog pipeline.

## 1. Core Philosophy: "Configuration as Code"

**Decision:** Use Intake YAML catalogs as the single source of truth for all metadata and configuration.

**Reasoning:**
*   **Version Control:** YAML files can be committed to Git, allowing tracking of dataset changes over time.
*   **Separation of Concerns:** Scientists/Data Engineers can update YAMLs to add datasets without touching the Python generation code.
*   **Interoperability:** Intake is a standard Python ecosystem tool, making the catalog usable by data scientists even without the STAC interface.

## 2. Architecture: Static Generation vs. Dynamic API

**Decision:** Adopt a **Static STAC** approach (generating JSON files) rather than running a dynamic database-backed STAC API (like stac-fastapi + pgstac).

**Reasoning:**
*   **Maintenance:** No database to manage, backup, or migrate.
*   **Performance:** Static JSON files can be served by any web server (Apache, Nginx) or CDN with extremely low latency.
*   **Portability:** The entire catalog is just a folder of files. It can be moved to S3, a USB drive, or another server without complex setup.
*   **Scale:** Our dataset update frequency (daily/monthly) fits well with a batch regeneration process (`clean-build`).

## 3. Data Strategy: Virtual Access (Zero-Copy)

**Decision:** Use Symlinks and direct file references instead of copying data.

**Reasoning:**
*   **Storage Efficiency:** We deal with multi-TB datasets (ERA5, Himawari). Duplicating them for a "web access layer" is prohibitively expensive.
*   **Speed:** "Ingestion" is instantaneous (creating a synlink/JSON) vs. hours of data copying.
*   **Consistency:** The catalog always points to the authoritative data source on the NAS.

## 4. UX Strategy: Explicit Grouping & Hierarchy

**Decision:** Enforce `catalog_name` in Intake YAMLs to drive folder structure, rejecting automatic splitting.

**Reasoning:**
*   **Predictability:** Users (and the code) know exactly where files enable. `catalog_name: "IMERG"` -> `stac_catalog/imerg/`.
*   **Organization:** Prevents the "flat list of thousands of items" problem. Grouping by logical dataset (e.g., "ERA5", "Himawari") creates a clean navigation experience in the STAC Browser.

## 5. Visualization: Event-Based Thumbnails

**Decision:** Generate thumbnails based on specific "Event Times" (e.g., Typoon Haikui) rather than generic statistical aggregates (Mean/Max).

**Reasoning:**
*   **Relevance:** Weather data is often characterized by extreme events. A "mean" image often looks like a blur. A specific typhoon capture demonstrates the dataset's resolution and quality instantly.
*   **Impact:** Users judge datasets visually. Showing a high-impact event creates a stronger first impression of data quality.

## 6. Standardization: Tiered Metadata

**Decision:** Structure Intake YAMLs into 4 distinct tiers: `Core Identity`, `Display & UI`, `Scientific Context`, `Providers`.

**Reasoning:**
*   **Completeness:** Ensures every dataset has the minimum required info for both machines (ID, processing level) and humans (Description, Citation).
*   **Automation:** The Generator code can blindly trust this structure to populate the UI without complex "if/else" guessing logic.
