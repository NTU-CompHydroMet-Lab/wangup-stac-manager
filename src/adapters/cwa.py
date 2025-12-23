from typing import Generator, List, Dict, Any, Optional
import pystac
import duckdb
from .base import BaseAdapter
from datetime import datetime
import os

class CwaGaugeAdapter(BaseAdapter):
    def get_items(self) -> Generator[pystac.Item, None, None]:
        # Get file path from Intake source
        urlpath = self.source.args.get('urlpath')
        if not urlpath:
            raise ValueError(f"No urlpath found for source {self.entry_name}")

        # Connect to DuckDB
        con = duckdb.connect(database=':memory:')
        
        # Check if file exists
        if not os.path.exists(urlpath):
             print(f"Warning: File {urlpath} not found.")
             return

        try:
            con.execute(f"INSTALL sqlite; LOAD sqlite;")
            con.execute(f"ATTACH '{urlpath}' AS cwa (TYPE SQLITE);")
            
            # Get table name
            tables = con.execute("SELECT name FROM cwa.sqlite_master WHERE type='table'").fetchall()
            if not tables:
                print("No tables found in SQLite DB")
                return
            
            table_name = tables[0][0] # Use the first table
            
            # Get temporal and spatial extent
            # Assuming columns 'time', 'lon', 'lat' exist. 
            # In a real scenario, we might need to map these from the schema.
            
            query = f"""
                SELECT 
                    MIN(time) as min_time, MAX(time) as max_time,
                    MIN(lon) as min_lon, MAX(lon) as max_lon,
                    MIN(lat) as min_lat, MAX(lat) as max_lat,
                    COUNT(*) as count
                FROM cwa.{table_name}
            """
            
            stats = con.execute(query).fetchone()
            min_time, max_time, min_lon, max_lon, min_lat, max_lat, count = stats
            
            if min_time is None:
                return

            # Create STAC Item
            item_id = f"{self.collection_id}-source"
            
            # Bbox
            bbox = [min_lon, min_lat, max_lon, max_lat]
            
            # Geometry
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
            
            # Properties
            properties = self.metadata.copy()
            properties.update({
                "station_count": count,
                "start_datetime": str(min_time),
                "end_datetime": str(max_time)
            })
            
            # Datetime (use start time)
            dt = datetime.fromisoformat(str(min_time).replace("Z", ""))
            
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
                    href=urlpath,
                    media_type="application/vnd.sqlite3",
                    roles=["data"],
                    title="CWA Gauge Station Data"
                )
            )
            
            yield item

        except Exception as e:
            print(f"Error processing CWA data: {e}")
        finally:
            con.close()
