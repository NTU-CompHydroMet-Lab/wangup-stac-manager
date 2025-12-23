import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse

app = FastAPI(title="Static ERA5 STAC Catalog")

from fastapi.staticfiles import StaticFiles

# Mount the STAC output directory as static files
# This allows accessing files exactly as they are on disk, preserving relative links.
# e.g. /stac/era5/collection.json
stac_dir = Path(__file__).parent.parent / "stac_output"
app.mount("/stac", StaticFiles(directory=stac_dir), name="stac")

# Serve the STAC‑Browser UI (static files)
# We mount the built 'dist' directory at the root.
# html=True means it will serve index.html for the root path.
browser_dist = Path(__file__).parent.parent / "static" / "stac-browser" / "dist"
app.mount("/", StaticFiles(directory=browser_dist, html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    # Run the FastAPI app; host 0.0.0.0 makes it reachable from Docker or other hosts
    uvicorn.run("src.server:app", host="0.0.0.0", port=8001, reload=True)
