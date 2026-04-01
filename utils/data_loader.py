from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def load_sales_data() -> pd.DataFrame:
    """Load sales.csv from data/processed/. Parses the date column as datetime."""
    sales_path = PROCESSED_DIR / "sales.csv"
    sales = pd.read_csv(sales_path, parse_dates=["date"])
    return sales


def load_products_data() -> pd.DataFrame:
    """Load products.csv from data/processed/."""
    products_path = PROCESSED_DIR / "products.csv"
    products = pd.read_csv(products_path)
    return products


def load_inventory_data() -> pd.DataFrame:
    """Load inventory.csv from data/processed/."""
    inventory_path = PROCESSED_DIR / "inventory.csv"
    inventory = pd.read_csv(inventory_path)
    return inventory


def load_all_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and return all three processed tables as (sales_df, products_df, inventory_df)."""
    sales = load_sales_data()
    products = load_products_data()
    inventory = load_inventory_data()
    return sales, products, inventory