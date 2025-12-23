from typing import Generator, List, Dict, Any
import pystac
import xarray as xr
from .base import BaseAdapter
import os
import glob
import re
from datetime import datetime
import pandas as pd

class GriddedDataAdapter(BaseAdapter):
    def get_items(self) -> Generator[pystac.Item, None, None]:
        urlpath_pattern = self.source.args.get('urlpath')
        if not urlpath_pattern:
            raise ValueError(f"No urlpath found for source {self.entry_name}")

        # Expand glob pattern
        files = sorted(glob.glob(urlpath_pattern))
        
        for file_path in files:
            try:
                # Extract year from filename if possible
                filename = os.path.basename(file_path)
                match = re.search(r'(\d{4})', filename)
                year = match.group(1) if match else None
                
                # Open dataset to get metadata
                ds = xr.open_dataset(file_path, engine='zarr', chunks={})
                
                # Get spatial extent
                if 'lon' in ds.coords:
                    min_lon = float(ds.lon.min())
                    max_lon = float(ds.lon.max())
                elif 'longitude' in ds.coords:
                    min_lon = float(ds.longitude.min())
                    max_lon = float(ds.longitude.max())
                else:
                    min_lon, max_lon = -180.0, 180.0

                if 'lat' in ds.coords:
                    min_lat = float(ds.lat.min())
                    max_lat = float(ds.lat.max())
                elif 'latitude' in ds.coords:
                    min_lat = float(ds.latitude.min())
                    max_lat = float(ds.latitude.max())
                else:
                    min_lat, max_lat = -90.0, 90.0

                bbox = [min_lon, min_lat, max_lon, max_lat]
                geometry = {
                    "type": "Polygon",
                    "coordinates": [[
                        [min_lon, min_lat],
                        [max_lon, min_lat],
                        [max_lon, max_lat],
                        [min_lon, max_lat],
                        [min_lon, min_lat]
                    ]]
                }

                # Get temporal extent
                if 'time' in ds.coords:
                    min_time = str(ds.time.min().values)
                    max_time = str(ds.time.max().values)
                else:
                    if year:
                        min_time = f"{year}-01-01T00:00:00"
                        max_time = f"{year}-12-31T23:59:59"
                    else:
                        continue 
                
                # Create Item ID
                if year:
                    item_id = f"{self.collection_id}-{year}"
                else:
                    item_id = f"{self.collection_id}-{os.path.splitext(filename)[0]}"

                properties = self.metadata.copy()
                properties.update({
                    "start_datetime": min_time,
                    "end_datetime": max_time
                })
                
                # Handle numpy/pandas timestamp conversion
                try:
                    dt = pd.to_datetime(min_time).to_pydatetime()
                except:
                    dt = datetime.fromisoformat(min_time.replace("Z", ""))

                item = self._create_base_item(
                    item_id=item_id,
                    geometry=geometry,
                    bbox=bbox,
                    datetime=dt,
                    properties=properties
                )

                # Add Asset
                item.add_asset(
                    key="data",
                    asset=pystac.Asset(
                        href=file_path,
                        media_type="application/vnd+zarr",
                        roles=["data"],
                        title=f"{self.collection_id} Data {year}"
                    )
                )
                
                yield item
                
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
