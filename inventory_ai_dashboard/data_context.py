"""
data_context.py
---------------
Loads executive_view_enriched.xlsx and builds a compact,
structured context string to inject into every Groq API call.

Why compact? Groq has token limits. We don't send 1000 raw rows —
we send a smart summary that gives the AI everything it needs
to answer business questions accurately.
"""

import pandas as pd
from pathlib import Path

def load_data(filepath: str = None) -> pd.DataFrame:
    if filepath is None:
        filepath = Path(__file__).parent / "executive_view_enriched.xlsx"
    df = pd.read_excel(filepath)
    return df


def build_ai_context(df: pd.DataFrame) -> str:
    """
    Build a compact, structured context string from the DataFrame.
    This string will be injected into every Groq API call so the AI
    can answer grounded, data-specific questions.
    """

    # --- Priority distribution ---
    priority_counts = df["priority_level"].value_counts()

    # --- Store-level CRITICAL count ---
    store_critical = (
        df[df["priority_level"] == "CRITICAL"]
        .groupby("store_id")
        .size()
        .sort_values(ascending=False)
    )

    # --- Top 10 most urgent CRITICAL SKUs (lowest days of stock remaining) ---
    top_urgent = (
        df[df["priority_level"] == "CRITICAL"]
        .nsmallest(10, "days_of_stock_remaining")[
            [
                "store_id",
                "product_id",
                "days_of_stock_remaining",
                "recommended_action",
                "category",
            ]
        ]
        .reset_index(drop=True)
    )

    # --- Action distribution ---
    action_counts = df["recommended_action"].value_counts()

    # --- Category-level risk (CRITICAL count per category) ---
    category_critical = (
        df[df["priority_level"] == "CRITICAL"]
        .groupby("category")
        .size()
        .sort_values(ascending=False)
    )

    # --- Build the context string ---
    context = f"""
=== INVENTORY SNAPSHOT ===
Total SKU-store combinations: {len(df)}
Stores: {df['store_id'].nunique()} | Products: {df['product_id'].nunique()}

--- Priority Distribution ---
CRITICAL : {priority_counts.get('CRITICAL', 0)} SKUs (top 10% risk — immediate action required)
HIGH     : {priority_counts.get('HIGH', 0)} SKUs (next 20% — monitor closely)
MEDIUM   : {priority_counts.get('MEDIUM', 0)} SKUs (next 30% — plan ahead)
LOW      : {priority_counts.get('LOW', 0)} SKUs (bottom 40% — no immediate concern)

--- CRITICAL SKUs by Store (most at-risk first) ---
{store_critical.to_string()}

--- Top 10 Most Urgent Items (CRITICAL, fewest days of stock left) ---
{top_urgent.to_string(index=False)}

--- Recommended Actions Distribution ---
{action_counts.to_string()}

--- CRITICAL SKUs by Product Category ---
{category_critical.to_string()}

=== SYSTEM CONTEXT ===
- Priority scores use weights: 0.45 reorder urgency, 0.30 demand pressure, 0.15 coverage risk, 0.10 stockout history
- days_of_stock_remaining uses long-term avg_daily_sales (conservative estimate)
- blended_daily_demand = 0.7 × avg_daily_sales + 0.3 × recent 7-day sales
- Zero-demand items are suppressed from all risk escalation
- smart_reorder_point accounts for lead time + 2 buffer days
""".strip()

    return context


def get_full_data_for_query(df: pd.DataFrame) -> str:
    """
    For detailed Q&A queries, return a more complete (but still compact)
    view of CRITICAL and HIGH items only — to keep tokens manageable.
    """
    action_items = df[df["priority_level"].isin(["CRITICAL", "HIGH"])][
        [
            "store_id",
            "product_id",
            "category",
            "priority_level",
            "days_of_stock_remaining",
            "stock_level",
            "blended_daily_demand",
            "recommended_action",
            "decision_context",
        ]
    ].sort_values(["priority_level", "days_of_stock_remaining"])

    return action_items.to_string(index=False)

if __name__ == "__main__":
    df = load_data()
    print(f"✅ Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    print()
    ctx = build_ai_context(df)
    print(ctx)