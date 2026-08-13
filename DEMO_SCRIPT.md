# ONR ITSS POC — 50-minute demo script

**Data:** 400 synthetic S&T grants (`grants_portfolio.json`) + 1,200 derived ERP lines. No CUI/PII.

**Story:** A new grants file lands → Auto Loader picks it up → quality gates → gold KPIs refresh → leadership searches, models, and exports.

---

## Before the room (once)

1. Clone this repo into the Databricks workspace (Repos / Git folder).
2. Open `notebooks/00_bootstrap.py`, set `repo_root` to that folder, **Run all**.
3. Confirm: `onr_demo.silver.grants` = **400**, `onr_demo.silver.financial` = **1,200**.
4. Create / open the Databricks App `onr-demo-poc` (`app-onr-demo/`, warehouse `onr-demo-warehouse`).

---

## Minute 0–5 — Home

- Catalog `onr_demo`, schemas **bronze · silver · gold · app**.
- Quick stats: 400 grants, ~$437M, 1,200 ERP rows.
- “Everything you will see is mock / synthetic.”

## Minute 5–15 — Element 3 Ingestion

**Talk:** Auto Loader watches `/Volumes/onr_demo/bronze/landing/grants/`.

**Do (live file drop):**

```
# In a notebook or the catalog UI, copy the staged file:
# /Volumes/onr_demo/bronze/landing/_staged/batch_live_grants.csv
#   → /Volumes/onr_demo/bronze/landing/grants/batch_live_grants.csv
```

Then **Run all** on:

1. `01_bronze_ingestion.py` — Auto Loader `availableNow` (streaming API, finite trigger)
2. `02_silver_quality.py` — dedupe + amount/awardee checks
3. `03_gold_aggregation.py` — refresh summaries

Optional: drop `batch_quality_fail.csv` to show 3 rows rejected (null id, negative amount, duplicate).

Refresh the Ingestion page — grants **400 → 408**, batch_id `live-demo-2026`.

## Minute 15–22 — Element 4 Governance

- Catalog registry: four schemas.
- Quality scores (silver.grants / silver.financial).
- Lineage: landing → bronze.grants → silver.grants → gold.grants_summary → dashboard.
- Tags: `data_source=mock`, `medallion=silver|gold`.

## Minute 22–32 — Element 5 Analytics

- Decision cards + program-area mix (real fixture numbers).
- Run `04_mlflow_grant_model.py` if you want a live MLflow run (large-award classifier).
- Show MLflow experiment `/Shared/onr-demo/grant-size`.

## Minute 32–42 — Element 6 Dashboard

- KPIs, filter FY + program area.
- Search `quantum` or `ONRD-2025`.
- Budget execution + “automation” (scheduled refresh / anomaly).

## Minute 42–48 — Element 7 Integration

- Export CSV / JSON / Parquet (fixture or warehouse).
- API + Advana / Cloud One talking point: open formats, no lock-in.
- Schema card matches `grant_no`, `program_area`, `amount_usd`, `awardee`.

## Minute 48–50 — Close

- Same pipeline tomorrow: drop another CSV, re-run 01–03.
- IL4/IL5 / Zero Trust is the hosting story; this POC is unclassified mock only.

---

## If something is down

| Symptom | Fallback |
|---|---|
| SQL Warehouse cold | App fixture mode still shows 400 grants |
| Auto Loader empty | Confirm file is under `landing/grants/` not `_staged/` |
| Bootstrap can’t find JSON | `repo_root` must be the cloned `onr_demo` folder |
