# ONR ITSS POC — Databricks Streamlit demo (Elements 3–7)

Single-environment proof of concept for Office of Naval Research Code 08 ITSS.

**Mock data only** (Compass `grants_portfolio.json`, 400 grants). No CUI / PII / classified.

| Page | Element | What you show |
|------|---------|----------------|
| Ingestion | 3 | Auto Loader, quality gates, a second file drop |
| Governance | 4 | Unity Catalog, scores, lineage |
| Analytics | 5 | Forecasts + a small MLflow model |
| Dashboard | 6 | KPIs, search, extract |
| Integration | 7 | CSV / JSON / Parquet export, open APIs |

---

## Unity Catalog (medallion)

Catalog **`onr_demo`** — one POC, no prod.

| Schema | Tables / volumes |
|--------|------------------|
| `bronze` | `grants`, `financial` · volumes `landing`, `checkpoints` |
| `silver` | `grants`, `financial` |
| `gold` | `grants_summary`, `financial_summary`, `grants_by_awardee`, `budget_execution` |
| `app` | `ingestion_quality_log`, `data_quality_scores`, `lineage_tracking`, search/export history |

Landing path: `/Volumes/onr_demo/bronze/landing/`

---

## New workspace — four steps

1. **Add the Git repo** to the Databricks workspace (Repos / Git folder).
2. Open **`notebooks/00_bootstrap.py`**, set `repo_root` to that folder, **Run all**.  
   This creates UC objects and loads 400 grants + 1,200 ERP rows.
3. Use existing compute only:
   - SQL: **`onr demo warehouse`**
   - Notebooks: **`onr demo cluster`**
4. Create a **Databricks App** from `app-onr-demo/` (binds to `onr demo warehouse` in `app.yml`).
5. Follow **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** (50 minutes). Live moment = Ingestion → **Process selected files** (Live 8).

Optional SQL-only create: `sql/setup_uc_objects.sql` (no extra S3 bucket).

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
- **Reset demo to seed** (confirm checkbox) → back to 400 grants, checkpoints cleared

**On the cluster:** `05_reset_demo.py` on **onr demo cluster**, then `01`–`03` if you are showing Auto Loader on Volume files.

App count: **400 → 408** (live file) → **400** (reset).

---

## Repo layout

```
onr_demo/
├── DEMO_SCRIPT.md                 # 50-minute talk track
├── databricks.yml                 # Slim DAB: volumes + app (does not create compute)
├── app-onr-demo/                  # Streamlit app
│   ├── Home.py
│   ├── app.yml
│   ├── config/onr-conf.yaml
│   ├── data/grants_portfolio.json # App fixture fallback
│   ├── pages/                     # Elements 3–7
│   └── utils/
├── notebooks/
│   ├── 00_bootstrap.py            # RUN FIRST
│   ├── 01_bronze_ingestion.py     # Auto Loader
│   ├── 02_silver_quality.py
│   ├── 03_gold_aggregation.py
│   ├── 04_mlflow_grant_model.py
│   └── 05_reset_demo.py           # Cluster reset to 400-grant seed
├── sql/
│   ├── setup_uc_objects.sql
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
