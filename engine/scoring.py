from __future__ import annotations

import pandas as pd

from engine.metrics import load_and_build_metrics_df


# =========================
# Config / tunable defaults
# =========================

WEIGHT_PRIORITY_REORDER = 0.45
WEIGHT_PRIORITY_DEMAND = 0.30
WEIGHT_PRIORITY_COVERAGE = 0.15
WEIGHT_PRIORITY_HISTORY = 0.10


# =========================
# Priority score builder
# =========================

def add_priority_score(metrics_df: pd.DataFrame) -> pd.DataFrame:
    df = metrics_df.copy()

    df["priority_score"] = (
        WEIGHT_PRIORITY_REORDER * df["reorder_urgency_score"]
        + WEIGHT_PRIORITY_DEMAND * df["demand_pressure_score"]
        + WEIGHT_PRIORITY_COVERAGE * df["inventory_coverage_risk_score"]
        + WEIGHT_PRIORITY_HISTORY * df["stockout_frequency"]
    )

    # zero-demand should not escalate
    df.loc[df["is_zero_demand"] == 1, "priority_score"] = 0.0

    return df


# =========================
# Priority level labeling
# =========================

def assign_priority_level(
    df: pd.DataFrame,
    score_col: str = "priority_score",
) -> pd.DataFrame:
    df = df.copy()

    q90 = df[score_col].quantile(0.90)
    q70 = df[score_col].quantile(0.70)
    q40 = df[score_col].quantile(0.40)

    def label(score: float) -> str:
        if score >= q90:
            return "CRITICAL"
        elif score >= q70:
            return "HIGH"
        elif score >= q40:
            return "MEDIUM"
        else:
            return "LOW"

    df["priority_level"] = df[score_col].apply(label)

    # force zero-demand rows to LOW
    df.loc[df["is_zero_demand"] == 1, "priority_level"] = "LOW"

    # keep thresholds for debugging / explainability
    df["priority_q90"] = q90
    df["priority_q70"] = q70
    df["priority_q40"] = q40

    return df


# =========================
# Rank & action flags
# =========================

def add_priority_rank(
    df: pd.DataFrame,
    score_col: str = "priority_score",
) -> pd.DataFrame:
    df = df.copy()

    df["priority_rank"] = df[score_col].rank(
        ascending=False,
        method="dense",
    )

    return df


def add_needs_action(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["needs_action"] = df["priority_level"].isin(
        ["CRITICAL", "HIGH", "MEDIUM"]
    )

    # zero-demand should not trigger action
    df.loc[df["is_zero_demand"] == 1, "needs_action"] = False

    return df


# =========================
# Optional explainability
# =========================

def add_recommended_action(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def decide_action(row: pd.Series) -> str:
        if row["is_zero_demand"] == 1:
            return "NO_ACTION_ZERO_DEMAND"
        if row["priority_level"] == "CRITICAL":
            return "RESTOCK_URGENT"
        if row["priority_level"] == "HIGH":
            return "RESTOCK_SOON"
        if row["priority_level"] == "MEDIUM":
            return "MONITOR_CLOSELY"
        return "NO_ACTION"

    df["recommended_action"] = df.apply(decide_action, axis=1)

    return df


def add_decision_context(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the decision_context string based on priority level and which
    risk component scored highest.
    """
    df = df.copy()

    def _dominant_driver(row: pd.Series) -> str:
        """Return the label of the component with the highest weighted contribution."""
        contributions = {
            "reorder":  WEIGHT_PRIORITY_REORDER  * row["reorder_urgency_score"],
            "demand":   WEIGHT_PRIORITY_DEMAND   * row["demand_pressure_score"],
            "coverage": WEIGHT_PRIORITY_COVERAGE * row["inventory_coverage_risk_score"],
            "history":  WEIGHT_PRIORITY_HISTORY  * row["stockout_frequency"],
        }
        return max(contributions, key=contributions.get)

    def build_context(row: pd.Series) -> str:
        # --- Zero demand: always suppressed, regardless of priority ---
        if row["is_zero_demand"] == 1:
            return "Zero demand — risk intentionally suppressed."

        priority = row["priority_level"]
        reorder  = row["reorder_urgency_score"]
        demand   = row["demand_pressure_score"]
        coverage = row["inventory_coverage_risk_score"]
        stockout = row["stockout_frequency"]
        recent   = row["recent_avg_daily_sales_7d"]
        blended  = row["blended_daily_demand"]

        # -------------------------------------------------------
        # CRITICAL — always explain the specific reason
        # -------------------------------------------------------
        if priority == "CRITICAL":
            if reorder > 0 and demand > 0.5:
                return (
                    "Stock below adaptive reorder point with active demand pressure — "
                    "immediate replenishment needed."
                )
            if reorder > 0:
                return (
                    "Stock has fallen below adaptive reorder threshold — "
                    "replenishment required before next lead-time cycle."
                )
            if demand > 0.5 and _dominant_driver(row) == "demand":
                return (
                    "Strong short-term demand relative to current stock — "
                    "depletion risk is elevated."
                )
            if coverage > 0.08 and _dominant_driver(row) == "coverage":
                return (
                    "Low inventory coverage — stock may be exhausted before the "
                    "next replenishment cycle arrives."
                )
            if stockout > 0.10 and _dominant_driver(row) == "history":
                return (
                    "Recurring stockout history detected — high probability of "
                    "recurrence without proactive restocking."
                )
            # Score is high but no single dominant driver — explain the combined risk
            return (
                "Elevated risk driven by a combination of demand pressure, "
                "inventory coverage, and stockout history — restock recommended."
            )

        # -------------------------------------------------------
        # HIGH — lead with the main risk driver
        # -------------------------------------------------------
        if priority == "HIGH":
            if reorder > 0 and demand > 0.3:
                return (
                    "Stock approaching or below adaptive reorder point with "
                    "sustained demand — schedule replenishment soon."
                )
            if reorder > 0:
                return (
                    "Stock has fallen below adaptive reorder threshold — "
                    "replenishment should be scheduled promptly."
                )
            if demand > 0.3 and _dominant_driver(row) == "demand":
                return (
                    "Demand rate is elevated relative to available stock — "
                    "monitor closely and prepare replenishment order."
                )
            if coverage > 0.07 and _dominant_driver(row) == "coverage":
                return (
                    "Inventory coverage is tightening — stock may not last "
                    "through the full replenishment lead time."
                )
            if stockout > 0.08 and _dominant_driver(row) == "history":
                return (
                    "Above-average stockout history — elevated risk of disruption "
                    "warrants early replenishment planning."
                )
            return (
                "Multiple risk indicators are moderately elevated — "
                "replenishment should be planned in the near term."
            )

        # -------------------------------------------------------
        # MEDIUM — flag what to monitor
        # -------------------------------------------------------
        if priority == "MEDIUM":
            if reorder > 0:
                return (
                    "Stock is approaching the adaptive reorder threshold — "
                    "monitor daily and prepare to reorder."
                )
            if demand > 0.2:
                return (
                    "Moderate short-term demand detected — watch for acceleration "
                    "that could trigger faster stock depletion."
                )
            if coverage > 0.06:
                return (
                    "Inventory coverage is tightening — track daily sales and "
                    "compare against replenishment lead time."
                )
            if stockout > 0.05:
                return (
                    "Mild stockout history on record — maintain awareness of "
                    "stock position and seasonal demand shifts."
                )
            if recent == 0 and blended > 0:
                return (
                    "No sales recorded in the past 7 days despite positive "
                    "historical demand — monitor for demand revival."
                )
            return (
                "Moderate risk across multiple indicators — "
                "keep stock position under regular review."
            )

        # -------------------------------------------------------
        # LOW — no immediate action needed
        # -------------------------------------------------------
        if recent == 0 and blended > 0:
            return (
                "No recent sales in the past 7 days; historical demand exists — "
                "no action needed but watch for revival."
            )

        return "No immediate operational concern."

    df["decision_context"] = df.apply(build_context, axis=1)

    return df


# =========================
# Orchestrator
# =========================

def build_scoring_df(metrics_df: pd.DataFrame) -> pd.DataFrame:
    df = metrics_df.copy()

    df = add_priority_score(df)
    df = assign_priority_level(df)
    df = add_priority_rank(df)
    df = add_needs_action(df)
    df = add_recommended_action(df)
    df = add_decision_context(df)

    return df


def load_and_build_scoring_df() -> pd.DataFrame:
    metrics_df = load_and_build_metrics_df()
    return build_scoring_df(metrics_df)


# =========================
# Build Final View
# =========================

def build_executive_view(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "product_id",
        "store_id",
        "stock_level",
        "reorder_point",
        "smart_reorder_point",
        "recent_avg_daily_sales_7d",
        "blended_daily_demand",
        "days_of_stock_remaining",
        "priority_score",
        "priority_level",
        "priority_rank",
        "needs_action",
        "recommended_action",
        "decision_context",
    ]

    return df[cols].copy()
