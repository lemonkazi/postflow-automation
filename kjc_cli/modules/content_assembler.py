import json
from pathlib import Path
from kjc_cli import config
from kjc_cli.logger import get_logger
from kjc_cli.utils import save_json
import random

logger = get_logger("content_assembler")
OUT_FILE = config.DATA_DIR / "posts_payload.json"

def run_assemble(hooks, images, products):
    """
    Combine hooks + composed images + products into posting payloads.
    - rotates products if fewer than hooks
    - returns list of dicts suitable for posting
    """
    logger.info("Assembling content for posts")
    posts = []
    if not images:
        logger.warning("No composed images available")
    for idx, hook in enumerate(hooks):
        product = products[idx % len(products)] if products else {}
        image = images[idx % len(images)] if images else ""
        text = f"{hook}\n\nPrice: {product.get('price','')}\nShop: {product.get('link','')}"
        post = {
            "text": text,
            "image_path": image,
            "product": product
        }
        posts.append(post)
    save_json(OUT_FILE, posts)
    logger.info(f"Saved {len(posts)} posts payload to {OUT_FILE}")
    return posts
