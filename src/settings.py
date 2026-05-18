from pathlib import Path
import yaml
from typing import List
from pydantic import BaseModel, Field
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "main.yaml"

class ProjectSettings(BaseModel):
    title: str
    id: str
    description: str

class BuildTarget(BaseModel):
    catalog: str
    source: str

class BuildSettings(BaseModel):
    targets: List[BuildTarget] = Field(default_factory=list)

class FilesystemSettings(BaseModel):
    output_dir: str = "stac_catalog"
    static_dir: str = "stac_browser"
    link_strategy: str = "absolute"  # "absolute" or "relative"

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8001

class GroupingSettings(BaseModel):
    strategy: str = "prefix"
    separator: str = "_"

class ConcurrencySettings(BaseModel):
    max_workers: int = 5

class ProductAliasEntry(BaseModel):
    match: str
    alias: str

class EventAggregationSettings(BaseModel):
    product_aliases: list[ProductAliasEntry] = Field(default_factory=list)

class StacSettings(BaseModel):
    project: ProjectSettings
    build: BuildSettings
    filesystem: FilesystemSettings = Field(default_factory=FilesystemSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    grouping: GroupingSettings = Field(default_factory=GroupingSettings)
    concurrency: ConcurrencySettings = Field(default_factory=ConcurrencySettings)
    event_aggregation: EventAggregationSettings = Field(default_factory=EventAggregationSettings)

def load_settings() -> StacSettings:
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text())
        return StacSettings(**data)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

# Singleton assignment
try:
    settings = load_settings()
except Exception:
    # Allow import even if config fails, but logging happened
    settings = None
