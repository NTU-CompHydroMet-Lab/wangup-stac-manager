import intake
from pathlib import Path
from loguru import logger
from src.generator.intake_xarray import IntakeXarrayGenerator

def build_collection(catalog_path: Path, source_id: str, output_dir: Path) -> None:
    """
    Generate a static STAC collection + per‑year items for a single source.
    """
    logger.info(f"Opening catalog: {catalog_path}")
    try:
        cat = intake.open_catalog(str(catalog_path))
        
        if source_id not in cat:
            raise ValueError(f"Source '{source_id}' not found in catalog '{catalog_path}'.")

        logger.info(f"Processing source: {source_id}")
        source_output_dir = output_dir / source_id
        
        try:
            # Extract global catalog metadata (e.g. catalog_name)
            cat_meta = cat.metadata if hasattr(cat, 'metadata') else {}
            
            generator = IntakeXarrayGenerator(
                output_dir=source_output_dir, 
                catalog_path=catalog_path,
                catalog_metadata=cat_meta
            )
            generator.generate(source_name=source_id)
        except Exception as e:
            logger.error(f"Failed to generate STAC for {source_id} from catalog {catalog_path}: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Failed to open catalog {catalog_path}: {e}")
        raise
