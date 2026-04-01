# Retail Inventory Decision Engine

A portfolio project that turns raw grocery sales data into operational inventory decisions — using a Python scoring pipeline, an AI-powered dashboard, automated email alerts, and a Tableau executive view.

Built on the [Kaggle Corporación Favorita dataset](https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting), scoped to 10 stores × 100 products from 2016 onward.

**Live demos:**
- Streamlit AI Dashboard → https://retail-inventory-ai.streamlit.app/
- Tableau Dashboard → https://public.tableau.com/app/profile/ilham.den.fatah/viz/dashboard_17714436693350/DashboardFixed?publish=yes

---

## What it does

The pipeline scores every store–product combination daily across five inventory health metrics, assigns a priority level (CRITICAL / HIGH / MEDIUM / LOW), and surfaces the results in three ways:

1. **AI Dashboard** — auto-generated executive summary, natural language Q&A, and one-click reorder briefing (Streamlit + Groq Llama 3.3 70B)
2. **Executive Dashboard** — KPI strip, stockout exposure chart, demand heatmap, priority breakdown (Tableau Public)
3. **Automated Alerts** — daily email digest of CRITICAL items, triggered at 07:00 (n8n + Gmail)

---

## Architecture

```
data/raw/                        ← Kaggle source files
└── train.csv, items.csv, stores.csv, ...
notebooks/
├── 01_data_preparation.ipynb    ← subset + clean + build inventory
└── 02_metrics_development.ipynb ← develop + validate scoring logic
utils/data_loader.py             ← loads processed CSVs
engine/metrics.py                ← computes 5 inventory health metrics
engine/scoring.py                ← assigns priority score + level + action
data/processed/
└── executive_view_enriched.xlsx ← 1,000 rows, 15 columns (pipeline output)
inventory_ai_dashboard/          ← Streamlit app (deployed)
├── app.py
├── groq_client.py
└── data_context.py
n8n/                             ← workflow runs locally, exports as JSON
```

**Data flow:** `01_data_preparation.ipynb` → `02_metrics_development.ipynb` → `executive_view_enriched.xlsx` → dashboard + n8n (independently)

---

## Scoring logic

Each store–product pair gets a `priority_score` from four weighted components:

| Component | Weight | What it measures |
|---|---|---|
| Reorder urgency | 45% | How far stock has dropped below the reorder point |
| Demand pressure | 30% | How fast current stock is being drawn down |
| Coverage risk | 15% | Days of stock remaining relative to lead time |
| Stockout history | 10% | Historical frequency of stockout events |

Priority levels use quantile-based thresholds: top 10% → CRITICAL, next 20% → HIGH, next 30% → MEDIUM, bottom 40% → LOW.

Zero-demand items are suppressed from all risk escalation.

---

## Tech stack

| Layer | Tools |
|---|---|
| Data prep | Python, pandas, numpy |
| Scoring pipeline | Python (engine/metrics.py, engine/scoring.py) |
| AI dashboard | Streamlit, Groq API (Llama 3.3 70B) |
| Executive dashboard | Tableau Public |
| Automation | n8n (self-hosted), Gmail API |
| Data | Kaggle Corporación Favorita (scoped subset) |

---

## How to run locally

**1. Clone and install**
```bash
git clone https://github.com/ilhamdenfatah/retail-inventory-ai.git
cd retail-inventory-ai
pip install -r inventory_ai_dashboard/requirements.txt
```

**2. Set up environment**
```bash
cp .env.example inventory_ai_dashboard/.env
# Add your GROQ_API_KEY to inventory_ai_dashboard/.env
```

**3. Run the dashboard**
```bash
cd inventory_ai_dashboard
streamlit run app.py
```

**4. Regenerate the pipeline output** (optional)

Run the notebooks in order:
- `notebooks/01_data_preparation.ipynb`
- `notebooks/02_metrics_development.ipynb`

Note: `train.csv` is not included in the repo (125M rows). Download it from Kaggle and place it in `data/raw/`.

---

## n8n automation

The Daily Stock Risk Digest workflow runs on a schedule, pulls `executive_view_enriched.xlsx` from Google Drive, filters CRITICAL rows, and sends a formatted email digest.

To use it: import the workflow JSON from `n8n/` into your n8n instance and configure Google Drive + Gmail credentials.

For enterprise-scale deployments with millions of daily transactions, the architecture would separate concerns: n8n as orchestrator only, with heavy transformations handled by dbt/Spark on a cloud warehouse (BigQuery/Snowflake), and n8n triggering on aggregated summary outputs rather than raw data.

---

## Dataset

**Source:** [Corporación Favorita Grocery Sales Forecasting](https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting) (Kaggle)

**Scope:** 10 stores × 100 products, 2016-01-01 onward (~395K sales rows)

**Why this scope:** Full dataset is 125M+ rows. The 10×100 subset preserves real sales patterns, seasonality, and store-level variance while keeping the pipeline fast enough to run on a laptop.

**Inventory data:** Stock levels, reorder points, and lead times are synthetically generated (numpy, seed=42) because the original dataset does not include warehouse stock data.

---

## License

MIT
