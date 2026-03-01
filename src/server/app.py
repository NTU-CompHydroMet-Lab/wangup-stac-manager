from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse

from src.settings import settings

app = FastAPI(title="Static STAC Catalog Server")

from fastapi.staticfiles import StaticFiles

# Mount the STAC output directory as static files
# This allows accessing files exactly as they are on disk, preserving relative links.
# e.g. /stac/era5/collection.json
stac_dir = Path(__file__).parent.parent.parent / settings.filesystem.output_dir
app.mount("/stac", StaticFiles(directory=stac_dir, follow_symlink=True), name="stac")

# Compatibility aliases for direct static-STAC paths:
# - /catalog.json -> /stac/catalog.json
# - /<group>/...  -> /stac/<group>/...
@app.get("/catalog.json")
async def root_catalog_alias():
    return FileResponse(stac_dir / "catalog.json", media_type="application/json")

if stac_dir.exists():
    for child in sorted(stac_dir.iterdir()):
        if child.is_dir():
            app.mount(
                f"/{child.name}",
                StaticFiles(directory=child, follow_symlink=True),
                name=f"stac-{child.name}",
            )

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
