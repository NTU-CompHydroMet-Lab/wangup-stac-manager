import requests
from typing import Dict, Any
import logging

logger = logging.getLogger("stac-cli")


class StacClient:
    def __init__(self, api_url: str = "http://localhost:8080"):
        self.api_url = api_url.rstrip("/")

    def collection_exists(self, collection_id: str) -> bool:
        try:
            response = requests.get(f"{self.api_url}/collections/{collection_id}")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def create_collection(self, collection: Dict[str, Any]) -> bool:
        try:
            response = requests.post(f"{self.api_url}/collections", json=collection)
            if response.status_code in [200, 201]:
                logger.info(f"Created collection: {collection['id']}")
                return True
            elif response.status_code == 409:
                logger.info(f"Collection already exists: {collection['id']}")
                return True
            else:
                logger.error(f"Failed to create collection {collection['id']}: {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error creating collection: {e}")
            return False

    def item_exists(self, collection_id: str, item_id: str) -> bool:
        try:
            response = requests.get(f"{self.api_url}/collections/{collection_id}/items/{item_id}")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def create_item(self, collection_id: str, item: Dict[str, Any]) -> bool:
        try:
            # Ensure collection link is present
            if not any(link.get('rel') == 'collection' for link in item.get('links', [])):
                item.setdefault('links', []).append({
                    "rel": "collection",
                    "href": f"{self.api_url}/collections/{collection_id}"
                })
            response = requests.post(f"{self.api_url}/collections/{collection_id}/items", json=item)
            if response.status_code in [200, 201]:
                logger.info(f"Created item: {item['id']}")
                return True
            elif response.status_code == 409:
                logger.info(f"Item already exists: {item['id']}")
                return True
            else:
                logger.error(f"Failed to create item {item['id']}: {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error creating item: {e}")
            return False
