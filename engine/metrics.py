from __future__ import annotations

import numpy as np
import pandas as pd

from utils.data_loader import load_all_data


# =========================
# Config / tunable defaults
# =========================

# Number of days used for the recent demand window.
RECENT_WINDOW_DAYS = 7

# Safety-stock buffer added on top of lead time when computing smart reorder point.
# Represents the number of additional days of demand to hold as buffer stock.
BUFFER_DAYS = 2

# Weights for blending long-term and short-term demand signals.
# avg_daily_sales (long-term baseline) weighted higher for stability.
BLEND_AVG_WEIGHT = 0.7
BLEND_RECENT_WEIGHT = 0.3

# Sentinel value assigned to days_of_stock_remaining when avg_daily_sales == 0.
# Represents "effectively infinite coverage" for zero-demand items.
ZERO_DEMAND_COVERAGE_CAP = 999.0


# =========================
# Demand metric builders
# =========================

def compute_avg_daily_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the long-term average daily sales per (store_id, product_id).

    Mean of all daily unit_sales rows for this store-product pair across the full
    history (Jan 2016 - Aug 2017, ~591 days). Used as the stable baseline in
    blended_daily_demand.
    """
    avg_sales = (
        sales_df
        .groupby(["store_nbr", "item_nbr"])["unit_sales"]
        .mean()
        .reset_index()
        .rename(columns={
            "store_nbr": "store_id",
            "item_nbr": "product_id",
            "unit_sales": "avg_daily_sales",
        })
    )
    return avg_sales


def compute_recent_sales_7d(
    sales_df: pd.DataFrame,
    recent_window_days: int = RECENT_WINDOW_DAYS,
) -> pd.DataFrame:
    """
    Compute total unit sales for each (store_id, product_id) over the
    most recent `recent_window_days` days (exclusive of the boundary date,
    giving exactly `recent_window_days` calendar days).
    """
    latest_date = sales_df["date"].max()
    recent_start = latest_date - pd.Timedelta(days=recent_window_days)

    recent_sales = (
        sales_df[sales_df["date"] > recent_start]
        .groupby(["store_nbr", "item_nbr"])["unit_sales"]
        .sum()
        .reset_index()
        .rename(columns={
            "store_nbr": "store_id",
            "item_nbr": "product_id",
            "unit_sales": "recent_sales_7d",
        })
    )
    return recent_sales


# =========================
# Base builder
# =========================

def build_metrics_base(
    sales_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join inventory with demand signals to build the base metrics table.
    Grain: one row per (store_id, product_id).
    """
    base = inventory_df.copy()

    recent_sales = compute_recent_sales_7d(sales_df)
    avg_sales = compute_avg_daily_sales(sales_df)

    base = base.merge(
        recent_sales,
        on=["store_id", "product_id"],
        how="left",
    )
    base["recent_sales_7d"] = base["recent_sales_7d"].fillna(0)

    base = base.merge(
        avg_sales,
        on=["store_id", "product_id"],
        how="left",
    )
    base["avg_daily_sales"] = base["avg_daily_sales"].fillna(0)

    return base


# =========================
# Feature engineering
# =========================

def add_zero_demand_flag(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag items with no historical demand signal (avg_daily_sales == 0).
    Zero-demand items are suppressed from risk escalation throughout
    the metrics and scoring pipeline.
    """
    metrics_df = metrics_df.copy()
    metrics_df["is_zero_demand"] = (metrics_df["avg_daily_sales"] == 0).astype(int)
    return metrics_df


def add_recent_avg_daily_sales(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the average daily sales rate over the recent 7-day window.
    Formula: recent_sales_7d / RECENT_WINDOW_DAYS
    """
    metrics_df = metrics_df.copy()
    metrics_df["recent_avg_daily_sales_7d"] = (
        metrics_df["recent_sales_7d"] / RECENT_WINDOW_DAYS
    )
    return metrics_df


def add_blended_daily_demand(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a blended demand signal combining long-term and short-term rates.

    Formula: 0.7 * avg_daily_sales + 0.3 * recent_avg_daily_sales_7d

    70% long-term average, 30% recent 7-day average. Heavier weight on the
    long-term side keeps the signal from overreacting to a single busy week.
    """
    metrics_df = metrics_df.copy()
    metrics_df["blended_daily_demand"] = (
        BLEND_AVG_WEIGHT * metrics_df["avg_daily_sales"]
        + BLEND_RECENT_WEIGHT * metrics_df["recent_avg_daily_sales_7d"]
    )
    return metrics_df


def add_days_of_stock_remaining(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimate how many days the current stock will last given current demand.

    Formula: stock_level / avg_daily_sales (when avg_daily_sales > 0)
    Fallback: ZERO_DEMAND_COVERAGE_CAP (999) when avg_daily_sales == 0

    DESIGN NOTE:
    Intentionally uses avg_daily_sales (long-term baseline) rather than
    blended_daily_demand. This gives a conservative, stable coverage estimate
    that is less sensitive to short-term demand spikes. The blended signal
    is used separately in smart_reorder_point calculation.
    """
    metrics_df = metrics_df.copy()

    metrics_df["days_of_stock_remaining"] = np.where(
        metrics_df["avg_daily_sales"] > 0,
        metrics_df["stock_level"] / metrics_df["avg_daily_sales"],
        ZERO_DEMAND_COVERAGE_CAP,
    )

    return metrics_df


def add_smart_reorder_point(
    metrics_df: pd.DataFrame,
    buffer_days: int = BUFFER_DAYS,
) -> pd.DataFrame:
    """
    Compute an adaptive reorder point based on current demand and lead time.

    Formula: ceil(blended_daily_demand * (supplier_lead_time_days + buffer_days))

    This is a simplified reorder point model:
      - demand_during_lead_time = blended_daily_demand * lead_time_days
      - safety_stock_buffer     = blended_daily_demand * buffer_days
    Combined: total stock needed to cover the full replenishment cycle plus buffer.

    Note: does not include statistical safety stock (Z * sigma * sqrt(LT)).
    Buffer days provide a deterministic safety margin suitable for v1.
    """
    metrics_df = metrics_df.copy()

    metrics_df["smart_reorder_point"] = np.ceil(
        metrics_df["blended_daily_demand"]
        * (metrics_df["supplier_lead_time_days"] + buffer_days)
    ).astype(int)

    return metrics_df


def add_adjusted_reorder_gap(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute how far current stock is from the adaptive reorder threshold.

    Formula: smart_reorder_point - stock_level
    Positive value -> stock is below smart reorder point (reorder needed).
    Negative value -> stock is above smart reorder point (adequate coverage).
    """
    metrics_df = metrics_df.copy()
    metrics_df["adjusted_reorder_gap"] = (
        metrics_df["smart_reorder_point"] - metrics_df["stock_level"]
    )
    return metrics_df


def add_demand_pressure_score(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute short-term demand pressure relative to available stock.

    Formula: recent_sales_7d / (stock_level + 1)
    The +1 prevents division-by-zero for zero-stock items.

    Interpretation: how many units were sold in the last 7 days per unit
    currently in stock. Higher values indicate faster depletion relative
    to available inventory.

    Returns 0.0 for zero-demand items.
    """
    metrics_df = metrics_df.copy()

    metrics_df["demand_pressure_score"] = np.where(
        metrics_df["is_zero_demand"] == 1,
        0.0,
        metrics_df["recent_sales_7d"] / (metrics_df["stock_level"] + 1),
    )

    return metrics_df


def add_demand_acceleration_ratio(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the ratio of recent demand rate to long-term average demand rate.

    Formula: recent_avg_daily_sales_7d / avg_daily_sales
    Values > 1.0 indicate demand is accelerating relative to historical baseline.
    Values < 1.0 indicate demand is decelerating.

    Returns 0.0 for zero-demand items.
    """
    metrics_df = metrics_df.copy()

    metrics_df["demand_acceleration_ratio"] = np.where(
        metrics_df["avg_daily_sales"] > 0,
        metrics_df["recent_avg_daily_sales_7d"] / metrics_df["avg_daily_sales"],
        0.0,
    )

    return metrics_df


def add_reorder_urgency_score(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute how urgently a reorder is needed based on the reorder gap magnitude.

    Formula: adjusted_reorder_gap / (smart_reorder_point + 1)  when gap > 0
    Returns 0.0 when stock is above smart reorder point (no urgency).

    Range: naturally bounded in [0, 1) because:
      max(gap) = smart_reorder_point (when stock = 0)
      urgency  = srp / (srp + 1) < 1 always
    The +1 in the denominator also prevents division-by-zero when srp = 0.
    """
    metrics_df = metrics_df.copy()

    metrics_df["reorder_urgency_score"] = np.where(
        metrics_df["adjusted_reorder_gap"] > 0,
        metrics_df["adjusted_reorder_gap"] / (metrics_df["smart_reorder_point"] + 1),
        0.0,
    )

    return metrics_df


def add_inventory_coverage_risk_score(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute inventory coverage risk as the inverse of days of stock remaining.

    Formula: 1 / (days_of_stock_remaining + 1)
    Higher score = fewer days of stock = higher depletion risk.

    Representative values:
      7 days  -> 1/8  = 0.125  (high risk)
      15 days -> 1/16 = 0.063  (moderate)
      30 days -> 1/31 = 0.032  (low risk)

    Returns 0.0 for zero-demand items (coverage is not meaningful without demand).
    """
    metrics_df = metrics_df.copy()

    metrics_df["inventory_coverage_risk_score"] = np.where(
        metrics_df["is_zero_demand"] == 1,
        0.0,
        1 / (metrics_df["days_of_stock_remaining"] + 1),
    )

    return metrics_df


def add_stockout_risk_score(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a composite stockout risk score as a weighted sum of risk components.

    Formula:
      0.40 * reorder_urgency_score
    + 0.35 * demand_pressure_score
    + 0.15 * inventory_coverage_risk_score
    + 0.10 * stockout_frequency

    Kept as a standalone diagnostic -- not fed into priority_score directly.
    The scoring engine (scoring.py) builds its own composite from the same
    raw signals with different weights.

    Returns 0.0 for zero-demand items.
    """
    metrics_df = metrics_df.copy()

    metrics_df["stockout_risk_score"] = np.where(
        metrics_df["is_zero_demand"] == 1,
        0.0,
        (
            0.40 * metrics_df["reorder_urgency_score"]
            + 0.35 * metrics_df["demand_pressure_score"]
            + 0.15 * metrics_df["inventory_coverage_risk_score"]
            + 0.10 * metrics_df["stockout_frequency"]
        ),
    )

    return metrics_df


# =========================
# Orchestrator
# =========================

def build_metrics_df(
    sales_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the full metrics table from raw sales and inventory data.

    Pipeline order matters — each function depends on columns
    produced by earlier steps.

    Output grain : one row per (store_id, product_id)
    Output shape : (n_inventory_rows, 20 columns)
    """
    metrics_df = build_metrics_base(sales_df, inventory_df)
    metrics_df = add_zero_demand_flag(metrics_df)
    metrics_df = add_recent_avg_daily_sales(metrics_df)
    metrics_df = add_blended_daily_demand(metrics_df)
    metrics_df = add_days_of_stock_remaining(metrics_df)
    metrics_df = add_smart_reorder_point(metrics_df)
    metrics_df = add_adjusted_reorder_gap(metrics_df)
    metrics_df = add_demand_pressure_score(metrics_df)
    metrics_df = add_demand_acceleration_ratio(metrics_df)
    metrics_df = add_reorder_urgency_score(metrics_df)
    metrics_df = add_inventory_coverage_risk_score(metrics_df)
    metrics_df = add_stockout_risk_score(metrics_df)

    return metrics_df


def load_and_build_metrics_df() -> pd.DataFrame:
    """Load canonical data files and build the full metrics table."""
    sales_df, _, inventory_df = load_all_data()
    return build_metrics_df(sales_df, inventory_df)
