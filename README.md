# ONR ITSS POC — Databricks Streamlit demo (Elements 3–7)

Single-environment proof of concept for Office of Naval Research Code 08 ITSS.

**Mock data only** (Compass `grants_portfolio.json`, 400 grants). No CUI / PII / classified.

| Page | What you do |
|------|-------------|
| Ingestion | Land files, quality gates, reset |
| Catalog | Unity Catalog, scores, lineage |
| Analytics | RF scores, IsolationForest, OLS forecast + trend IDs |
| Portfolio | KPIs, search, daily brief, AT_RISK / anomaly flags |
| Export | CSV / JSON / Parquet, Statement Execution API |
| Infrastructure | DAB inventory, compute names, operator runbook |

**25-minute recording:** [DEMO_SCRIPT.md](DEMO_SCRIPT.md) is the word-for-word presenter script (Elements 3–7). Night-before train `04` + `04b`; on camera run `01b` + `04c`.

---

## Unity Catalog (medallion)

Catalog **`onr_demo`** — one POC, no prod.

| Schema | Tables / volumes |
|--------|------------------|
| `bronze` | `grants`, `financial` · volumes `landing`, `checkpoints` |
| `silver` | `grants`, `financial` |
| `gold` | `grants_summary`, `financial_summary`, `grants_by_awardee`, `budget_execution`, `grant_predictions`, `model_metrics`, `funding_forecast`, `program_trends`, `funding_features`, `grant_anomaly_scores` |
| `app` | `ingestion_quality_log`, `quarantine_log`, `quality_findings`, `data_quality_scores`, `lineage_tracking`, search/export history, `daily_briefs` |

Landing path: `/Volumes/onr_demo/bronze/landing/`

---

## New workspace — first run

Follow **[FIRST_RUN.md](FIRST_RUN.md)** in order. Short version:

1. Create compute with **exact** names: SQL warehouse `onr demo warehouse`, cluster `onr demo cluster`.
2. Add this Git repo to the workspace.
3. Run **`notebooks/00_bootstrap.py`** on that cluster (creates `onr_demo` + 400/1,200 rows).
4. Create Databricks App from `app-onr-demo/` (`onr-demo-poc`).
5. Run **`sql/grant_app_principal.sql`** (replace the app SP) and grant **CAN USE** on the warehouse.
6. Smoke test: Home shows 400 → Ingestion Process Live 8 → 408.

Do **not** `databricks bundle deploy` before bootstrap (volumes need schema `bronze`). The bundle does **not** create the warehouse or cluster. It *does* define a paused `trigger.file_arrival` job (`onr-demo-grants-file-arrival`) and a Lakeflow pipeline (`onr-demo-grants-stream`).

Optional empty DDL only: `sql/setup_uc_objects.sql` (skip if bootstrap already ran).

---

## Live second file (Element 3)

After bootstrap, extra files sit in:

`/Volumes/onr_demo/bronze/landing/_staged/`

| File | Purpose |
|------|---------|
| `batch_live_grants.csv` | 8 new grants (`live-demo-2026`) — copy into `landing/grants/` |
| `batch_quality_fail.csv` | 3 bad rows — show silver rejecting them |
| `sample_grants.csv` / `sample_financial.csv` | Full seed extracts |

**In the app (Ingestion page):**

- Multi-select staged files (**Live 8 grants**, **Quality-fail sample**) and/or upload a CSV → **Process selected files**
- **Restore baseline snapshot** (confirm checkbox) → back to 400 grants, silver rebuilt, quarantine / quality logs cleared

**On the cluster:** `05_reset_demo.py` on **onr demo cluster**, then `01`–`03` if you are showing Auto Loader on Volume files.

App count: **400 → 408** (live file) → **400** (reset).

---

## Repo layout

```
onr_demo/
├── FIRST_RUN.md                   # Greenfield workspace checklist
├── DEMO_SCRIPT.md                 # 50-minute talk track
├── STRATEGIC_PROMPTS.md           # 11.4 (a–e) Key-Personnel talking points
├── databricks.yml                 # Slim DAB: volumes + app + file-arrival job + SDP pipeline
├── pipelines/onr_grants_sdp.py    # Lakeflow streaming table (bronze.grants_stream)
├── app-onr-demo/                  # Streamlit app
│   ├── Home.py
│   ├── app.yml
│   ├── config/onr-conf.yaml
│   ├── data/grants_portfolio.json # App fixture fallback
│   ├── pages/                     # Ingestion, Catalog, Analytics, Portfolio, Export, Infrastructure
│   └── utils/
├── notebooks/
│   ├── 00_bootstrap.py            # RUN FIRST
│   ├── 01_bronze_ingestion.py     # Auto Loader (availableNow)
│   ├── 01b_streaming_autoloader.py # Auto Loader (availableNow on serverless)
│   ├── 02_silver_quality.py
│   ├── 03_gold_aggregation.py     # includes OLS forecast + trend IDs
│   ├── 04_mlflow_grant_model.py   # RF large-award classifier (night-before)
│   ├── 04b_funding_anomaly.py     # IsolationForest (night-before)
│   ├── 04c_score_registered_models.py # Camera: score 408 from UC models
│   └── 05_reset_demo.py           # Cluster reset to 400-grant seed
├── sql/
│   ├── setup_uc_objects.sql       # Optional empty DDL
│   ├── grant_app_principal.sql    # After the app exists
│   └── validation_queries.sql
└── resources/mock_data/
    ├── grants_portfolio.json      # Source of truth
    ├── batch_live_grants.csv
    ├── batch_quality_fail.csv
    └── generate_mock_data.py
```

---

## Data contract

`grant_no`, `title`, `abstract`, `program_area`, `fiscal_year`, `amount_usd`,
`awardee`, `org_unit`, `classification_band`, `batch_id`, `created_at`

ERP is derived (3 lines per grant, keyed by `grant_no`).
