# ONR ITSS POC — 50-minute demo script

**Data:** 400 synthetic S&T grants (`grants_portfolio.json`) + 1,200 derived ERP lines. No CUI/PII.

**Story:** A new grants file lands → Auto Loader picks it up → quality gates → gold KPIs refresh → leadership searches, models, and exports.

---

## Before the room (once)

Follow **[FIRST_RUN.md](FIRST_RUN.md)** if this workspace is new.

1. Warehouse **`onr demo warehouse`** and cluster **`onr demo cluster`** exist and are started.
2. Git folder cloned; `notebooks/00_bootstrap.py` **Run all** → 400 / 1,200.
3. App `onr-demo-poc` running; `sql/grant_app_principal.sql` applied; warehouse **CAN USE** for the app SP.
4. Home shows live **400** grants (not fixture-only).

---

## Minute 0–5 — Home

- Catalog `onr_demo`, schemas **bronze · silver · gold · app**.
- Quick stats: 400 grants, ~$437M, 1,200 ERP rows.
- “Everything you will see is mock / synthetic.”

## Minute 5–15 — Element 3 Ingestion

**Talk:** New file, no recode. SQL path uses **onr demo warehouse**. Auto Loader notebooks run on **onr demo cluster**.

**Do:** On Ingestion, leave **Live 8 grants** selected → **Process selected files**.  
Say the count: **400 → 408**.

To show quality: add **Quality-fail sample** and process again (empty `grant_no` rejected, negative amount never reaches silver, duplicate skipped).

**Reset:** check *I want to reset* → **Reset demo to seed** (back to 400). Or run `05_reset_demo.py` on **onr demo cluster**.

Then open `01_bronze_ingestion.py` **attached to `onr demo cluster`** and scroll the Auto Loader `cloudFiles` cell (do not need to re-run if the button already landed the rows).

Optional: drop `batch_quality_fail.csv` via the cluster notebooks to show 3 rows rejected.

## Minute 15–22 — Element 4 Governance

- Catalog registry: four schemas.
- Quality scores (`app.data_quality_scores`) — written by Process/Reset *and* by notebook 02. After the live 8-grant drop they should already be there.
- Lineage: landing → bronze.grants → silver.grants → gold.grants_summary → dashboard. `processing_time_ms` is measured on gold writes.
- **Also open Catalog Explorer → `onr_demo` → Lineage** — that is the native UC graph (open architecture beat).
- Tags: `data_source=mock`, `medallion=silver|gold`.

## Minute 22–32 — Element 5 Analytics

- Decision cards + program-area mix (real fixture numbers).
- Predictions tab reads `gold.grant_predictions` (heuristic after ingest).
- Run `04_mlflow_grant_model.py` on **onr demo cluster** — refresh the app; scores and `gold.model_metrics` update. Model registers to Unity Catalog as `onr_demo.gold.grant_large_award` (experiment `/Shared/onr-demo/grant-size`).

## Minute 32–42 — Element 6 Dashboard

- KPIs, filter FY + program area.
- Search `quantum` or `ONRD-2025` — the search is written to `app.search_history`.
- Budget execution from `gold.budget_execution`. Pipeline health from `app.ingestion_quality_log`.

## Minute 42–46 — Element 7 Integration

- Narrow the **Date Range** (e.g. 2025–2026) so the evaluator sees a **filtered** export, not `SELECT *`.
- Export CSV / JSON / Parquet. Open the **Export History** tab — the row is in `app.export_history`.
- API + Advana / Cloud One talking point: open formats, JDBC/ODBC, Statement Execution REST. No lock-in.
- Schema card matches `grant_no`, `program_area`, `amount_usd`, `awardee`.

## Minute 46–50 — Close + Strategic Prompts (11.4)

All five prompts **must** be spoken. Use **[STRATEGIC_PROMPTS.md](STRATEGIC_PROMPTS.md)** (60–90 s each). If you already wove (b) and (c) into Elements 5/7, spend this block on (a), (d), (e).

- Same pipeline tomorrow: drop another CSV; or unpause the DAB job `onr-demo-grants-file-arrival` (`databricks.yml`) and let file-arrival run 01→02→03.
- IL4/IL5 / Zero Trust is the *hosting* story; this POC is unclassified mock only.

---

## If something is down

| Symptom | Fallback |
|---|---|
| SQL Warehouse cold | App fixture mode still shows 400 grants |
| Auto Loader empty | Confirm file is under `landing/grants/` not `_staged/` |
| Bootstrap can’t find JSON | `repo_root` must be the cloned `onr_demo` folder |
