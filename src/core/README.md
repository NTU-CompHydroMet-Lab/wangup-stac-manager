# Core Module

The `src.core` module handles the orchestration of the STAC catalog generation process.

## Key Components

### `builder.py`
The main entry point for building specific collections. It:
1.  Reads the Catalog Configuration (YAML).
2.  Instantiates the appropriate Generator (e.g. `IntakeXarrayGenerator`).
3.  Executes the generation pipeline.

### `root_catalog.py`
Responsible for maintaining the root `catalog.json`. It:
1.  Scans the output directory for generated Collections.
2.  Groups them based on `group_id` metadata.
3.  Updates the hierarchical structure (Root -> Group -> Collection).

### `validator.py`
Provides utility functions to validate generated STAC objects against the specification using `pystac.validate`.
