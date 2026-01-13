# Contributing to NTU CompHydroMet STAC Manager

Thank you for your interest in contributing! This project follows modern open-science standards (Pangeo-style).

## Getting Started

1.  **Environment**: We use `uv` for dependency management.
    ```bash
    ./start.sh clean-build  # Builds the environment and catalog
    ```

2.  **Architecture**: Please read [src/README.md](src/README.md) to understand the Core/Generator split.

## Adding a New Dataset

1.  **Do NOT edit Python code** unless necessary.
2.  Add a new YAML file in `config/catalogs/` (e.g., `new_dataset.yaml`).
3.  Follow the **4-Tier Metadata Structure**:
    *   [1] Core Identity (`id`, `collection_name`)
    *   [2] Display (`thumbnail_datetime`, `description`)
    *   [3] Scientific (`platform`, `citation`)
    *   [4] Providers (`name`, `roles`)

## Code Style

-   We use `ruff` (via `uv`) for linting.
-   Run `clean-build` to trigger auto-validation (`stac-validator`).

## Release Process

We follow a modular git flow.
-   **Main Branch**: Stable releases.
-   **Feature Branches**: Use `feature/name`.
