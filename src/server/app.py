import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from src.settings import settings

app = FastAPI(title="Static STAC Catalog Server")

from fastapi.staticfiles import StaticFiles

# Mount the STAC output directory as static files
# This allows accessing files exactly as they are on disk, preserving relative links.
# e.g. /stac/era5/collection.json
stac_dir = Path(__file__).parent.parent.parent / settings.filesystem.output_dir
app.mount("/stac", StaticFiles(directory=stac_dir, follow_symlink=True), name="stac")

# Serve the STAC‑Browser UI (static files)
# We mount the built 'dist' directory at the root.
# html=True means it will serve index.html for the root path.
browser_dist = Path(__file__).parent.parent.parent / settings.filesystem.static_dir / "dist"
app.mount("/", StaticFiles(directory=browser_dist, html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Add project root to sys.path so 'src.server' can be resolved
    # This is needed when running 'python src/server.py' directly
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Run the FastAPI app; host 0.0.0.0 makes it reachable from Docker or other hosts
    uvicorn.run("src.server.app:app", host=settings.server.host, port=settings.server.port, reload=True)
