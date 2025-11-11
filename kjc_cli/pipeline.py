"""
Pipeline orchestrator for KJC Threads Automation
This module holds the main workflow logic (used by both CLI and scheduler)
"""

from kjc_cli.logger import get_logger
from kjc_cli.modules import (
    background_collector,
    hook_generator,
    image_composer,
    product_importer,
    content_assembler,
    buffer_poster,
    monitor,
)

logger = get_logger("pipeline")

def run_pipeline():
    """Run the full pipeline once"""
    logger.info("Starting full run of KJC Threads Automation pipeline")
    try:
        background_collector.run_collect()
        # hooks = hook_generator.run_generate()
        # products = product_importer.run_import()
        # composed_images = image_composer.run_compose(hooks)
        # posts = content_assembler.run_assemble(hooks, composed_images, products)
        #buffer_poster.run_post_many(posts)
        monitor.log_event("Full run completed", status="SUCCESS")
        logger.info("Full run completed successfully.")
    except Exception as e:
        monitor.log_event(f"Run failed: {e}", status="ERROR")
        logger.exception("Pipeline failed")
