# ========== Time Windows ==========

# Full sales history window used for long-term avg_daily_sales baseline.
# Note: metrics.py uses the entire available history (~591 days) for
# avg_daily_sales, not a rolling 30-day window. This constant is retained
# as a reference value and may be used in future rolling-window implementations.
SALES_WINDOW_DAYS = 30

# Recent demand window used for short-term signal (recent_sales_7d).
RECENT_WINDOW_DAYS = 7


# ========== Priority Score Weights ==========
# These weights are defined here for reference documentation only.
# The active weights used in the pipeline are defined inline in:
#   - engine/metrics.py  : stockout_risk_score weights (0.40, 0.35, 0.15, 0.10)
#   - engine/scoring.py  : priority_score weights       (0.45, 0.30, 0.15, 0.10)
#
# The two scores serve different purposes:
#   - stockout_risk_score : risk-focused diagnostic metric
#   - priority_score      : action-prioritization metric
#
# TODO: consolidate weights into this file and import them in both modules.

REORDER_URGENCY_WEIGHT   = 0.45   # dominant driver: reorder threshold breach
DEMAND_PRESSURE_WEIGHT   = 0.30   # short-term demand relative to stock
COVERAGE_RISK_WEIGHT     = 0.15   # inventory coverage (days of stock remaining)
STOCKOUT_HISTORY_WEIGHT  = 0.10   # historical stockout frequency


# ========== Priority Score Thresholds ==========
# Priority level assignment uses quantile-based thresholds computed at runtime
# in engine/scoring.py (assign_priority_level). These are NOT used directly.
#
# Documented here for reference only:
#   top 10% of scores  -> CRITICAL  (approx. score >= 0.20)
#   next 20%           -> HIGH      (approx. score >= 0.14)
#   next 30%           -> MEDIUM    (approx. score >= 0.08)
#   bottom 40%         -> LOW
#
# Score scale: continuous decimal in approx. range [0.0, 0.80].
# NOT a 0-100 percentage scale.

CRITICAL_QUANTILE = 0.90
HIGH_QUANTILE     = 0.70
MEDIUM_QUANTILE   = 0.40


# ========== Priority Level Labels ==========

PRIORITY_CRITICAL = "CRITICAL"
PRIORITY_HIGH     = "HIGH"
PRIORITY_MEDIUM   = "MEDIUM"
PRIORITY_LOW      = "LOW"


# ========== Restock Action Labels ==========

RESTOCK_URGENT  = "RESTOCK_URGENT"
RESTOCK_SOON    = "RESTOCK_SOON"
MONITOR_CLOSELY = "MONITOR_CLOSELY"
NO_ACTION       = "NO_ACTION"


# ========== Restock Buffer Days ==========
# Buffer days are added to supplier lead time when computing smart_reorder_point.
# Currently, engine/metrics.py uses a single fixed BUFFER_DAYS = 2.
# These per-level constants are defined for a future priority-adaptive
# buffer implementation where CRITICAL items carry a larger safety margin.

BUFFER_DAYS_DEFAULT  = 2   # active value used in metrics.py
BUFFER_DAYS_CRITICAL = 5
BUFFER_DAYS_HIGH     = 3
BUFFER_DAYS_MEDIUM   = 1
BUFFER_DAYS_LOW      = 0


# ========== AI Decision Labels ==========
# Reserved for the AI reasoning layer (not yet implemented).
# Will be used when the LLM decision engine is integrated in a future phase.

AI_DECISION_RESTOCK = "RESTOCK"
AI_DECISION_HOLD    = "HOLD"
AI_DECISION_MONITOR = "MONITOR"


# ========== AI Defaults ==========
# Reserved for the AI reasoning layer (not yet implemented).

DEFAULT_AI_CONFIDENCE = 0.5
