# Use official Python image
FROM python:3.11-slim

# Install system dependencies (GDAL is critical for Intake/Rasterio)
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    g++ \
    gcc \
    git \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Set Environment Variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Working Directory
WORKDIR /app

# Install uv
RUN pip install uv

# Install Dependencies
COPY pyproject.toml .
# Create venv and install dependencies
RUN uv venv && uv pip install .

# Copy Source Code and Config
COPY src/ ./src/
COPY config/ ./config/
COPY stac_browser/ ./stac_browser/
COPY start.sh stop.sh ./

# Create output directories
RUN mkdir -p stac_catalog

# Expose Server Port
EXPOSE 8001

# Default Command: Start the server using the normalized script
# or directly execute the CLI
CMD ["./start.sh", "serve"]
