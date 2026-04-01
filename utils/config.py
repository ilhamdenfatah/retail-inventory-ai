from pathlib import Path
import os

# ========== Project Root ==========

BASE_DIR = Path(__file__).resolve().parent.parent

# ========== Data Directories ==========

DATA_DIR      = BASE_DIR / "data"
RAW_DATA_DIR  = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_DIR        = DATA_DIR / "db"

# ========== Canonical Processed Tables ==========
# These are the active data files used by the pipeline.
# Source: Favorita Grocery Sales Forecasting dataset (Kaggle),
# subsetted to 10 stores x 100 products from 2016-01-01 onwards.

SALES_DATA_PATH     = PROCESSED_DIR / "sales.csv"
INVENTORY_DATA_PATH = PROCESSED_DIR / "inventory.csv"
PRODUCTS_DATA_PATH  = PROCESSED_DIR / "products.csv"

# ========== Executive Output ==========

EXECUTIVE_VIEW_PATH = PROCESSED_DIR / "executive_view.parquet"

# ========== Database ==========

DATABASE_PATH = DB_DIR / "retail.db"

# ========== Prompt Templates ==========

PROMPTS_DIR               = BASE_DIR / "prompts"
SYSTEM_PROMPT_PATH        = PROMPTS_DIR / "system_prompt.txt"
USER_PROMPT_TEMPLATE_PATH = PROMPTS_DIR / "user_prompt_template.txt"

# ========== Environment Variables ==========

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
