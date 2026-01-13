from typing import Any, Dict, Optional, Union
import logging
import requests
import pystac
from pystac_client import Client

logger = logging.getLogger("stac-cli")

class StacClient:
    """
    A client for interacting with a STAC API.
    
    Uses `pystac-client` for reading (search/get) and `requests` for writing (Transaction API).
    Note: The local static server is read-only and does not support create_* methods.
    """
    def __init__(self, api_url: str = "http://localhost:8001/stac/catalog.json"):
        self.api_url = api_url.rstrip("/")
        # Initialize pystac-client for reading
        try:
            self.client = Client.open(self.api_url)
        except Exception as e:
            logger.warning(f"Could not initialize pystac-client: {e}")
            self.client = None

    def collection_exists(self, collection_id: str) -> bool:
        """Check if a collection exists using pystac-client."""
        if not self.client:
            return False
        try:
            return self.client.get_collection(collection_id) is not None
        except Exception:
            return False

    def item_exists(self, collection_id: str, item_id: str) -> bool:
        """Check if an item exists within a collection."""
        if not self.client:
            return False
        try:
            coll = self.client.get_collection(collection_id)
            if not coll:
                return False
            return coll.get_item(item_id) is not None
        except Exception:
            return False

    def create_collection(self, collection: Union[pystac.Collection, Dict[str, Any]]) -> bool:
        """
        Create a collection via STAC Transaction API (POST /collections).
        Note: Requires a writable STAC API server.
        """
        if isinstance(collection, pystac.Collection):
            payload = collection.to_dict()
            col_id = collection.id
        else:
            payload = collection
            col_id = payload.get("id", "unknown")

        target_url = self.api_url.replace("catalog.json", "collections") # Heuristic for API root
        if target_url.endswith("/stac/collections"): # Adjust for static URL quirk
             # For a real API, the root is usually not .../catalog.json. 
             # We assume api_url is the root.
             target_url = f"{self.api_url}/collections"

        try:
            response = requests.post(target_url, json=payload)
            if response.status_code in [200, 201]:
                logger.info(f"Created collection: {col_id}")
                return True
            elif response.status_code == 409:
                logger.info(f"Collection already exists: {col_id}")
                return True
            else:
                logger.error(f"Failed to create collection {col_id}: {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error creating collection: {e}")
            return False

    def create_item(self, collection_id: str, item: Union[pystac.Item, Dict[str, Any]]) -> bool:
        """
        Create an item via STAC Transaction API (POST /collections/{id}/items).
        Note: Requires a writable STAC API server.
        """
        if isinstance(item, pystac.Item):
            payload = item.to_dict()
            item_id = item.id
        else:
            payload = item
            item_id = payload.get("id", "unknown")

        # Heuristic URL construction
        base = self.api_url.replace("/catalog.json", "")
        target_url = f"{base}/collections/{collection_id}/items"

        try:
            response = requests.post(target_url, json=payload)
            if response.status_code in [200, 201]:
                logger.info(f"Created item: {item_id}")
                return True
            elif response.status_code == 409:
                logger.info(f"Item already exists: {item_id}")
                return True
            else:
                logger.error(f"Failed to create item {item_id}: {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error creating item: {e}")
            return False
