# Deployment Guide

This project is container-ready and supports both **Docker** and **Podman**.

## Prerequisites
- **Docker**: `docker` and `docker-compose` installed.
- **Podman**: `podman` and `podman-compose` installed.

## Quick Start

### Option A: Podman (Recommended for Rootless)
1. **Build and Run**:
   ```bash
   podman-compose up -d --build
   ```
2. **View Logs**:
   ```bash
   podman-compose logs -f
   ```
3. **Stop**:
   ```bash
   podman-compose down
   ```

### Option B: Docker
1. **Build and Run**:
   ```bash
   docker-compose up -d --build
   ```

## Configuration
edit `docker-compose.yml` if needed:
- **NAS Mount**: Ensure `/home/sungche/NAS` matches your real NAS path.
- **SELinux**: If on RHEL/CentOS/Fedora, you might need to append `:z` to the volume mount:
  ```yaml
  - /home/sungche/NAS:/home/sungche/NAS:ro,z
  ```

## Running Tests (Inside Container)
To verify the environment is correct (GDAL, NetCDF, etc.), run the tests **inside** the container:

```bash
# Podman
podman exec -it stac-server pytest tests/

# Docker
docker exec -it stac-server pytest tests/
```

## Updating Data (Regeneration)
To update the catalog without stopping the server:

```bash
# Podman
podman exec stac-server uv run src/cli.py build --source imerg_final_v07

# Docker
docker exec stac-server uv run src/cli.py build --source imerg_final_v07
```
