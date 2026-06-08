import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = PROJECT_ROOT / "config" / "products"


def list_products():
    products = []

    if not PRODUCT_DIR.exists():
        return products

    for file in PRODUCT_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            config = json.load(f)

        products.append({
            "id": file.stem,
            "file": file.name,
            "product_name": config.get("product_name", file.stem),
            "product_code": config.get("product_code", file.stem),
            "version": config.get("version", "")
        })

    return products


def get_product(product):
    product_file = PRODUCT_DIR / f"{product}.json"

    if not product_file.exists():
        raise FileNotFoundError(f"Product config not found: {product_file}")

    with open(product_file, "r", encoding="utf-8") as f:
        return json.load(f)