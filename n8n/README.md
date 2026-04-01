# n8n Workflow

The Daily Stock Risk Digest workflow is built in n8n (self-hosted).

## What it does
Runs daily at 07:00, downloads `executive_view_enriched.xlsx` from Google Drive, filters CRITICAL priority rows, and sends a formatted email digest via Gmail.

## How to use
1. Import the workflow JSON file into your n8n instance
2. Configure Google Drive and Gmail credentials (OAuth2)
3. Update the Google Drive file ID to point to your copy of `executive_view_enriched.xlsx`
4. Activate the workflow

## Architecture note
This workflow is optimized for medium-scale inventory datasets. For enterprise-scale deployments with millions of daily transactions, the architecture would separate concerns: n8n as orchestrator only, with heavy transformations handled by dbt/Spark on a cloud warehouse (BigQuery/Snowflake), and n8n triggering on aggregated summary outputs rather than raw data.
