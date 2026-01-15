# =============================================================================
# Multi-stage Build for NTU CompHydroMet Lab STAC Manager
# Supports both Docker and Podman
# =============================================================================

# Stage 1: Build STAC Browser
FROM node:18-slim AS browser-builder

WORKDIR /browser

# Copy STAC Browser source
COPY stac_browser/package*.json ./
RUN npm ci --only=production

COPY stac_browser/ ./

# Ensure config.js is set correctly for production
RUN echo 'window.STAC_BROWSER_CONFIG = { \
  catalogUrl: "/stac/catalog.json", \
  catalogTitle: "NTU CompHydroMet Lab Data Catalog" \
};' > public/config.js

# Build production bundle
RUN npm run build

# Stage 2: Python Application
FROM python:3.11-slim

LABEL maintainer="NTU CompHydroMet Lab <wangup@caece.net>"
LABEL description="STAC Catalog Manager with Static Browser UI"
LABEL version="0.1.0-alpha"

# Install system dependencies
# Note: GDAL is critical for geospatial operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    g++ \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security (Podman-friendly)
RUN useradd -m -u 1000 -s /bin/bash stacuser

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy and install Python dependencies
COPY --chown=stacuser:stacuser pyproject.toml ./
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Copy application source
COPY --chown=stacuser:stacuser src/ ./src/
COPY --chown=stacuser:stacuser config/ ./config/
COPY --chown=stacuser:stacuser start.sh stop.sh ./

# Copy built STAC Browser from stage 1
COPY --from=browser-builder --chown=stacuser:stacuser /browser/dist ./stac_browser/dist

# Create output directories
RUN mkdir -p stac_catalog && \
    chown -R stacuser:stacuser /app

# Make scripts executable
RUN chmod +x start.sh stop.sh

# Switch to non-root user
USER stacuser

# Expose server port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/stac/catalog.json || exit 1

# Default command: Start the server
# Override with: docker run <image> uv run src/cli.py build --clean
CMD ["/bin/bash", "-c", "source .venv/bin/activate && uv run src/cli.py serve"]
