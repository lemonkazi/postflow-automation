import pandas as pd
from pathlib import Path
from kjc_cli import config
from kjc_cli.logger import get_logger

logger = get_logger("product_importer")

# sample CSV path
DEFAULT_CSV = Path("supplier_sample.csv")
OUT_DIR = config.PRODUCTS_DIR

def run_import(source: str = None):
    """
    Import products from CSV (expects columns: title, price, link, image)
    """
    path = Path(source) if source else DEFAULT_CSV
    if not path.exists():
        logger.warning(f"Product CSV {path} not found. Returning empty products list.")
        return []
    df = pd.read_csv(path)
    products = []
    for _, row in df.iterrows():
        products.append({
            "title": row.get("title", ""),
            "price": row.get("price", ""),
            "link": row.get("link", ""),
            "image": row.get("image", "")
        })
    logger.info(f"Imported {len(products)} products from {path}")
    return products
