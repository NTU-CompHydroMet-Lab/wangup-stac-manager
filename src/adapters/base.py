from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator
import pystac
from intake.source.base import DataSource

class BaseAdapter(ABC):
    def __init__(self, entry_name: str, source: DataSource, collection_id: str):
        self.entry_name = entry_name
        self.source = source
        self.collection_id = collection_id
        self.metadata = source.metadata

    @abstractmethod
    def get_items(self) -> Generator[pystac.Item, None, None]:
        """
        Yields STAC Items from the datasource.
        """
        pass

    def _create_base_item(self, item_id: str, geometry: Dict[str, Any], bbox: List[float], datetime: Any, properties: Dict[str, Any]) -> pystac.Item:
        """
        Helper to create a basic pystac.Item
        """
        return pystac.Item(
            id=item_id,
            geometry=geometry,
            bbox=bbox,
            datetime=datetime,
            properties=properties,
            collection=self.collection_id
        )
