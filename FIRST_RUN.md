# First-time Databricks setup (nothing installed yet)

Do these steps **in order**. This repo does **not** create compute (no second warehouse).

**Names must match exactly** (spaces, lowercase):

| Object | Exact name |
|--------|------------|
| SQL warehouse | `onr demo warehouse` |
| All-purpose cluster | `onr demo cluster` |
| Catalog | `onr_demo` |
| Databricks App | `onr-demo-poc` (from `app-onr-demo/`) |

Mock data only. No CUI / PII.

---

## 0. You need

- Workspace access to create a SQL warehouse and an all-purpose cluster.
- Databricks **Apps** enabled.
- A Unity Catalog **catalog** you can write. **Workspace Admin is not enough** for `CREATE CATALOG` — that privilege lives on the **metastore** (Metastore Admin or `CREATE CATALOG` on the metastore).

If you cannot create `onr_demo`, send this to a metastore / account admin (no extra S3 bucket):

```sql
CREATE CATALOG IF NOT EXISTS `onr_demo`
  COMMENT 'ONR ITSS POC — Technical Demonstration Catalog';

GRANT ALL PRIVILEGES ON CATALOG `onr_demo` TO `<YOUR_EMAIL>`;
```

Then you run `00_bootstrap.py` (it uses `CREATE CATALOG IF NOT EXISTS` and will skip create).

If they put the catalog in a different name, set the bootstrap `catalog` widget and `app-onr-demo/config/onr-conf.yaml` `schema.catalog` to that name.

---

## 1. Create compute (workspace UI)

**SQL warehouse**

1. SQL → SQL Warehouses → Create.
2. Name: `onr demo warehouse` (exact).
3. Type: **Serverless** if available; otherwise Pro.
4. Start it once so the first app connect does not sit in STARTING past the retry window.

**Cluster**

1. Compute → Create compute.
2. Name: `onr demo cluster` (exact).
3. Runtime: Databricks Runtime **14.3 LTS or newer** (standard is fine). Notebook `04` runs `%pip install scikit-learn pandas`.
4. Mode: single user or shared with your account.
5. Start it.

Do **not** create a second warehouse in a bundle.

---

## 2. Add this Git repo

Repos / Git folder → clone `https://github.com/jstrick9/onr_demo` onto `main`.

Note the folder path. Example: `/Workspace/Users/you@org/onr_demo`.

If Ingestion / Analytics notebook chips say the path is not resolved, set that path in `app-onr-demo/config/onr-conf.yaml` as `workspace.repo_root` and restart the app. Table chips do not need this — they use Catalog Explorer.

---

## 3. Bootstrap (creates UC + data)

1. Attach `notebooks/00_bootstrap.py` to **`onr demo cluster`**.
2. Leave the `repo_root` widget **blank** if the notebook lives under `…/notebooks/` (it infers the repo). Otherwise paste the Git folder path.
3. **Run all**.
4. Confirm the last cell prints roughly:

   - `silver.grants = 400`
   - `silver.financial = 1,200`

This creates catalog `onr_demo`, schemas `bronze` / `silver` / `gold` / `app`, volumes `landing` + `checkpoints`, loads the fixture, writes gold (including `grant_predictions`), and stages CSVs under `/Volumes/onr_demo/bronze/landing/_staged/`.

You do **not** need `sql/setup_uc_objects.sql` if bootstrap succeeded.

---

## 4. Create the Databricks App

1. New → App (or Compute → Apps).
2. Source: this repo’s `app-onr-demo/` folder (`app.yml` is already there).
3. Name: `onr-demo-poc`.
4. If the UI asks for a SQL warehouse resource, pick **`onr demo warehouse`**.
5. Deploy / start.

`app.yml` sets `DATABRICKS_WAREHOUSE_NAME=onr demo warehouse`.

---

## 5. Grant the app service principal (not yourself)

You can be workspace **Admin** and still skip this — **do not GRANT to your own user**.  
Notebooks and SQL you run are already yours.

The Streamlit app authenticates as a **different** service principal. Without grants to **that** identity, Home stays in fixture mode and Process/Reset fail.

1. Open the app → **Authorization** / service principal. Copy the name or application ID.
2. In a SQL editor attached to **`onr demo warehouse`**, open `sql/grant_app_principal.sql`.
3. Replace every `<APP_SERVICE_PRINCIPAL>` with that value (keep backticks).
4. Run the script.
5. Warehouse permissions (UI): SQL Warehouses → `onr demo warehouse` → Permissions → **CAN USE** for the same principal.

---

## 6. Smoke test (do this once)

| Step | Expected |
|------|----------|
| Open the app Home | Live counts 400 grants (not only “fixture”) if the warehouse is up |
| Ingestion → Process **Live 8 grants** | `silver.grants` 400 → 408 |
| Analytics → Predictions | Rows in `gold.grant_predictions` (`heuristic_v1`) |
| Analytics → Forecasting | `gold.funding_forecast` + `gold.program_trends` (OLS, trend IDs) after bootstrap / Process |
| Dashboard → Generate daily brief | Row in `app.daily_briefs` (ai_query or template) |
| Integration → Execute live Statement API | `statement_id` + JSON from `/api/2.0/sql/statements` |
| Optional: run `04` then `04b` on the cluster (night-before) | RF + IsolationForest registered |
| Ingestion → **Start stream** | Lands `batch_live_grants_stream.csv` and submits `01b` (or **Open stream notebook**) |
| Analytics → **Score registered models** | Scores UC models on the SQL warehouse (no cluster). Needs EXECUTE on the two models. |
| Ingestion → Restore baseline snapshot | Back to 400; silver rebuilt; `app.quarantine_log` empty |

---

## 7. Optional later

| Item | When |
|------|------|
| `01`–`03` on the cluster | availableNow Auto Loader on Volume files |
| `01b_streaming_autoloader.py` | Live `processingTime('30 seconds')` stream (auto-stops). Reset first so the stream checkpoint is empty. |
| `databricks bundle deploy -t poc` | After bootstrap. Deploys paused file-arrival job **and** SDP pipeline `onr-demo-grants-stream`. Does **not** create the warehouse/cluster. |
| [STRATEGIC_PROMPTS.md](STRATEGIC_PROMPTS.md) | Key-Personnel 60–90 s answers for 11.4 (a–e). Required for Completeness. |
| `sql/setup_uc_objects.sql` | Only if you want empty DDL without running Spark. Skip if bootstrap already ran. |

---

## If a step fails

| Symptom | Fix |
|---------|-----|
| `CREATE CATALOG` hangs (>1 min) | Cancel the cell. In a **SQL warehouse** editor run `SHOW CATALOGS` then `CREATE CATALOG IF NOT EXISTS onr_demo`. If that also hangs, the **metastore has no default storage** — an account admin must set the metastore root (or create the catalog). Workspace Admin ≠ Metastore storage. Then re-run bootstrap (it skips CREATE if `onr_demo` exists). |
| Bootstrap cannot open JSON | Set `repo_root` to the Git folder (must contain `resources/mock_data/grants_portfolio.json`) |
| App: fixture mode + warehouse error | Warehouse name mismatch, warehouse stopped too long, or app SP cannot **CAN USE** the warehouse |
| Process files fails with permission | Re-run `sql/grant_app_principal.sql` (needs **MANAGE** on silver/gold so the app can `CREATE OR REPLACE` tables you own) |
| Notebook 04: no sklearn | Re-run all cells; first cells `%pip install` then restart Python |
| MLflow “skipped” | Optional. UC tables still write. Notebook 04 creates `/Shared/onr-demo/grant-size` and registers `onr_demo.gold.grant_large_award` when MLflow is available |
| Governance page has no quality scores | Process a file (or Reset) — the app SQL path now writes `app.data_quality_scores`. Or run `02_silver_quality.py`. |
| Export date range ignored / no audit row | Pull latest `main`. Date filter is applied; exports land in `app.export_history`. |
