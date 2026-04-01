# System Architecture
AI-Powered Retail Inventory Decision Engine

This document describes the high-level architecture of the **Retail Inventory Decision Engine**, a system that analyzes retail sales and inventory data to generate intelligent restocking recommendations using analytical scoring and AI reasoning.

The system is designed to demonstrate how business analytics and AI can be combined to support operational decision-making in retail environments.

---

# 1. System Overview

The system processes retail operational data and transforms it into actionable restocking decisions through several processing layers.

```
Pipeline flow:

Raw Retail Data  
↓  
Data Loader  
↓  
Business Metrics Computation  
↓  
Priority Scoring Engine  
↓  
Decision Engine  
↓  
AI Reasoning Layer  
↓  
Interactive Dashboard

Each layer has a specific responsibility to keep the system modular and maintainable.
```

---

# 2. System Layers

## 2.1 Data Layer

The data layer stores the raw retail datasets used by the system.

Datasets include:

- sales data
- inventory levels
- product metadata

Example structure:
- data/
- sample/
- sales.csv
- inventory.csv
- products.csv


The system loads these datasets using **Pandas**.

Primary purpose of this layer:

- store operational data
- serve as input to the analytics pipeline

---

## 2.2 Processing Layer

The processing layer computes business metrics used to understand product demand and inventory risk.

This layer is implemented in: 

engine/metrics.py


Metrics computed include:

Demand metrics
- average daily sales
- recent sales (7 days)
- demand trend score

Inventory metrics
- days of stock remaining
- reorder gap

Risk metrics
- stockout risk score
- demand pressure score

These metrics transform raw operational data into interpretable signals for decision making.

---

## 2.3 Priority Scoring Layer

The priority scoring layer converts multiple business metrics into a **single priority score** representing restocking urgency.

Implemented in:

engine/scoring.py


Priority score formula:

priority_score =

0.4 × normalized_demand
- 0.4 × stockout_risk
- 0.2 × demand_trend


The score is scaled from **0–100** and mapped to priority levels:

| Score | Priority Level | Decision       |
|-------|----------------|----------------|
| 80+   | CRITICAL       | RESTOCK URGENT |
| 60–80 | HIGH           | RESTOCK SOON   |
| 40–60 | MEDIUM         | MONITOR        |
| <40   | LOW            | NO ACTION      |

This layer represents the **core analytical logic of the decision engine**.

---

## 2.4 Decision Engine Layer

The decision engine orchestrates the analytical pipeline and generates structured decision records for each product-store combination.

Implemented in:

engine/decision_engine.py


Responsibilities:

- combine metrics and scoring results
- determine recommended actions
- calculate quantity to order
- generate structured decision output
- prepare input for the AI reasoning layer

Each output record represents:

- 1 product
- 1 store
- 1 decision


Example decision object:

```json
{
  "product_name": "Wireless Mouse",
  "store_id": "S001",
  "priority_score": 84,
  "priority_level": "CRITICAL",
  "recommended_action": "RESTOCK_URGENT",
  "quantity_to_order": 120
}
```

## AI Reasoning Layer

The AI layer enhances the analytical output by generating natural-language explanations of operational risks and recommended actions.

Implemented in:

- ai/
- llm_client.py
- prompt_builder.py

The AI receives structured input from the decision engine, including:
- demand metrics
- inventory metrics
- risk indicators
- priority score
- recommended action

Example AI output:

```json
{
  "ai_decision": "RESTOCK",
  "risk_reason": "Stock will likely run out before supplier lead time.",
  "ai_reasoning": "Current inventory covers only about three days of demand while the supplier requires seven days to deliver new stock. Restocking soon will reduce the risk of stockout.",
  "confidence": 0.84
}
```

The AI layer focuses on interpretation and explanation, not on computing metrics.

## Interface Layer

The interface layer provides an interactive dashboard for users to explore product risk levels and restocking recommendations.

Implemented using Streamlit.

Location:
- app/

Dashboard components include:
- product priority table
- inventory risk indicators
- AI explanation panel
- recommended restocking quantities

The dashboard serves as a visual interface, while the decision logic remains inside the decision engine.

# 3. Repository Structure

```

retail-inventory-decision-engine/

ai/                # AI integration and prompt logic
app/               # Streamlit dashboard interface
engine/            # analytics and decision engine
utils/             # utilities and data loaders
data/              # datasets and database
prompts/           # LLM prompt templates
notebooks/         # exploratory analysis and validation
tests/             # unit tests

README.md
ARCHITECTURE.md

```
The repository structure is designed to be:
- modular
- easy to navigate
- recruiter-friendly
- aligned with real engineering projects.

# 4. Design Principles

The system follows several key principles:

## 4.1 Separation of Concerns

Each module handles a specific responsibility:
- data loading
- metrics computation
- scoring logic
- AI reasoning
- user interface

## 4.2 Analytics First, AI Second

The decision engine computes objective metrics and scores.
AI is used only to interpret and explain the results.

## 4.3 Simple but Powerful

The system focuses on solving a clear operational problem:

**Which products should be restocked first?**

Complex features are intentionally avoided to keep the project focused and maintainable.

---

# 5. System Goal

The goal of this project is to demonstrate how business analytics, decision modeling, and AI reasoning can be integrated into a single operational system.

The system acts as a Retail Operations Copilot, helping managers identify restocking priorities quickly and understand the reasoning behind each recommendation.
