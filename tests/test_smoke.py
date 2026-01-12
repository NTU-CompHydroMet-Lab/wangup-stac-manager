import sys
import pytest

def test_python_version():
    """Ensure we are running on a compatible Python version (>=3.9)."""
    assert sys.version_info >= (3, 9)

def test_imports():
    """Verify critical dependencies are installed and accessible."""
    try:
        import xarray
        import pandas
        import dask
        import pystac
        import intake
        import fastapi
        import uvicorn
        # GDAL is often the trickiest
        from osgeo import gdal
    except ImportError as e:
        pytest.fail(f"Dependency missing: {e}")

def test_gdal_version():
    """Check GDAL version (optional but good for debugging)."""
    from osgeo import gdal
    version = gdal.VersionInfo("RELEASE_NAME")
    print(f"GDAL Version: {version}")
    assert version is not None
