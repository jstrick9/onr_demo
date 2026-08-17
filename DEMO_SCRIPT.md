# ONR ITSS POC — 50-minute recording shot list

**This tape:** Elements **3–7** + strategic prompts **(a)–(e)**.  
**Not this tape:** Element 1 (MFA / IdP) and Element 2 (Terraform / CI-CD). Glance Infrastructure for 15 seconds only.

**Data:** 400 synthetic S&T grants + 1,200 ERP lines. Say *“mock / synthetic only”* once on Home, then move on.

**UI names on screen:** Ingestion · Catalog · Analytics · Portfolio · Export · Infrastructure.  
**Say “Element 3–7” out loud.** It is not labeled in the product.

**Camera rule:** one take, live cloud + live repo, no slides, no post-production overlays.

---

## Recording cut (what is live vs already done)

| Beat | On camera | Already done (night before) |
|------|-----------|-----------------------------|
| Ingest + quality | Process **Live 8 + Quality-fail** → **400 → 408** + rejected-row table | Seed is 400 |
| Streaming | `01b` Run all, drop a **new filename** into `landing/grants/` | Cluster warm |
| Lineage | Catalog Explorer native graph | — |
| Models | `04c` **Score from registered models** (30–90 s) | `04` then `04b` trained + registered |
| Dashboard | Search `quantum`, Generate daily brief | — |
| Export | FY **2025–2026**, CSV + Parquet, then live Statement API | — |
| Do **not** | Reset, Start SDP, unpause file-arrival, retrain 04/04b, bundle deploy | — |

**Why Process then 01b without Reset:** Process writes bronze/silver through the warehouse (does **not** land a file in `landing/grants/`). The stream still has a new file to detect. Copy as `batch_live_grants_stream.csv` so Auto Loader sees a new path. Silver stays 408 (dedupe). Bronze may tick above 408 — that is the stream proof.

---

## Night before (not recorded)

Follow [FIRST_RUN.md](FIRST_RUN.md) if the workspace is new. Then:

1. `git pull` on `main` in the workspace Git folder. Redeploy / restart app `onr-demo-poc`.
2. Start **`onr demo warehouse`** and **`onr demo cluster`**. Leave them running.
3. Confirm Home shows live **400** (not “fixture”). If fixture: `sql/grant_app_principal.sql` + warehouse **CAN USE** for the **app SP**.
4. If silver is not 400: run `05_reset_demo.py` on the cluster (off camera).
5. Run **`04_mlflow_grant_model.py`** (Run all) → `onr_demo.gold.grant_large_award`.
6. Run **`04b_funding_anomaly.py`** (Run all) → `funding_anomaly_detector` @ `champion`. If MLflow says parent folder missing: `WorkspaceClient().workspace.mkdirs("/Shared/onr-demo")` and re-run from the MLflow cell.
7. Confirm Analytics Predictions `model_name` is `rf_large_award_v1` and Anomalies scorer contains `iforest`.
8. Confirm `/Volumes/onr_demo/bronze/landing/_staged/batch_live_grants.csv` exists.
9. Attach `01b_streaming_autoloader.py` and `04c_score_registered_models.py` to the cluster. **Do not Run all yet.**
10. Mute notifications. Browser **1920×1080**, zoom **110–125%**, hide bookmarks. Dark or light — pick one and stay.

### Tabs to pre-open (name them)

| # | Tab | Parked on |
|---|-----|-----------|
| 1 | **App** | Home |
| 2 | **01b** | `notebooks/01b_streaming_autoloader.py` (attached, not running) |
| 3 | **Volume** | `/Volumes/onr_demo/bronze/landing/` (so you can copy `_staged` → `grants/`) |
| 4 | **Catalog Explorer** | `onr_demo.silver.grants` → **Lineage** |
| 5 | **04c** | `notebooks/04c_score_registered_models.py` (attached, not running) |
| 6 | **MLflow** | Experiments `/Shared/onr-demo/grant-size` and `/Shared/onr-demo/funding-anomaly` |
| 7 | **Repo** | Workspace Git folder on `main` (live code — required) |

Do **not** open account-console MFA, Terraform, or GitHub Actions on this tape.

---

## Timed shot list

Spoken Element labels are in **bold**. Weave prompts while the UI is doing work — do not save all five for the last four minutes.

### 0:00–2:00 — Home (open)

**Show:** App tab, live counts **400** / **1,200**, catalog `onr_demo`, warehouse `onr demo warehouse`.

**Say:** Mock / synthetic Compass grants. Medallion bronze → silver → gold. This recording is the data-and-analytics path (ingestion through export). Identity and IaC are the companion tape.

**Do not** scroll the “What you can do” table for long. Sidebar **Active grants** is the sticky 400.

---

### 2:00–14:00 — **Element 3** Ingestion + stream  
*Prompts (a) legacy ETL and (d) RPO while files land.*

**2:00–6:30 Process (warehouse SQL path)**

1. Ingestion. Confirm sidebar / metric **400**.
2. Staged files: **Live 8 grants** and **Quality-fail sample** (both selected).
3. **Process selected files**.
4. Point at the big **400 → 408**. Open the file summary: 8 landed, empty `grant_no` rejected, negative amount called out, duplicate skipped.
5. Quality Checks tab — `ingestion_quality_log`.
6. Expand **How it works** only if you need the picture; otherwise keep talking.

**Say (a):** Legacy ETL keeps writing the same Volume path. We do not cut over the D&A Portal in a weekend. Warehouse SQL and Auto Loader write the same bronze table. Rollback is delete-the-batch, not rewrite-the-estate.

**6:30–13:30 Stream (`processingTime`, not a batch trigger)**

1. Switch to **01b**. **Run all**.
2. Switch to **Volume**. Copy  
   `_staged/batch_live_grants.csv`  
   → `grants/batch_live_grants_stream.csv`  
   (new name).
3. Back to 01b: watch `bronze.grants` / `last_2_min` / `inputRows` tick. App Ingestion → Schema & Streaming → **Last 2 min**.
4. Open the Auto Loader snippet (Ingestion last tab) and say `addNewColumns` + `processingTime('30 seconds')` vs notebook 01 `availableNow`.

**Say:** This is Auto Loader `cloudFiles` on a UC Volume — Kafka/Kinesis-class file arrival, not a scheduled batch. 01b auto-stops at 90 seconds.

**Say (d), 20 s:** Landing is durable object storage. RPO for bronze is the file still sitting in `landing/grants/` plus Delta time-travel. RTO for gold is rebuild from bronze (~minutes). We are **not** resetting on camera.

**Do not** Reset. **Do not** Start `onr-demo-grants-stream`. **Do not** unpause file-arrival.

---

### 14:00–21:00 — **Element 4** Catalog  
*Prompt (e) vendor / quality tags.*

1. Catalog → **Catalog Registry** — four schemas, tables that just moved.
2. **Quality Scores** — `app.data_quality_scores` rewritten by Process.
3. **Lineage** tab — read the operator cue, then switch to the **Catalog Explorer** tab. Click **Lineage** on `silver.grants` (or `gold.grants_summary`). That native graph is the Element 4 visual, not the mermaid sketch.
4. **Policies & Tags** — `data_source=mock`, `data_sensitivity`, `medallion`.

**Say (e):** Tags are the subscription registry. In production we add `vendor`, `license_id`, `renewal_date`. A lapsed feed shows up as a timeliness drop, not a blank dashboard. Last-good gold stays.

**Do not** linger on the DDL expanders.

---

### 21:00–32:00 — **Element 5** Analytics  
*Prompt (b) financial predictive / prescriptive.*

**21:00–24:00 Trigger (required action verb)**

1. Repo tab (2 s): “training already registered last night.”
2. **04c** tab → **Run all**.
3. Point at the printed line: scored **408** from `grant_large_award` and `funding_anomaly_detector@champion`.
4. MLflow tab (15 s): four IsolationForest runs + RF run. Do not start a new run.

**24:00–32:00 Read the outputs**

1. Analytics → **Predictions** — `rf_large_award_v1`, Fund / Review / Defer. The eight new grants are in the table.
2. **Anomalies** — flagged review queue, scorer `iforest_funding_v1`.
3. **Forecasting** — `ols_fy_v1`, 2-year horizon, 95% band. Point at one **TREND-DECLINE** as the reallocation candidate.
4. **Trend Analysis** only if you have spare 20 s.

**Say (b):** Same ingested portfolio — not a second dataset. Descriptive = budget gauge you will open next. Predictive = RF + IsolationForest + OLS. Prescriptive = Fund/Review/Defer + AT_RISK + TREND-DECLINE. Team split: engineer owns bronze/silver, scientist owns the UC models, analyst owns gold and the brief.

**Honest if asked:** OLS, not Prophet. IsolationForest, not a neural net.

---

### 32:00–40:00 — **Element 6** Portfolio

1. Portfolio KPIs. Filter FY or program area once.
2. **Search & Extract** — type `quantum`. Point at `app.search_history` (Activity Log).
3. **Process Automation** — **Generate daily brief**. Row lands in `app.daily_briefs` (`ai_query` or template — say which).
4. **Budget Execution** — one **AT_RISK** row. Tie to the declining program from Element 5.

**Say:** A Code 08 resource officer does this without SQL.

---

### 40:00–46:00 — **Element 7** Export  
*Prompt (c) Zero Trust / IL5 — hosting target, not this cell.*

1. Export → Data Export. Date range is already **2025–2026**. Leave CSV + Parquet on.
2. Dataset **Grants Summary** or **Raw Grants**. **Execute Export**. Download one file.
3. **Export History** — `app.export_history` row (user, filter, count).
4. **API Documentation** — **Execute live Statement API call**. Show `statement_id` + JSON. Say: `/api/2.0/sql/statements`, OAuth, same warehouse. Advana / Cloud One call this, not a Databricks-only extract.
5. Schema Docs expander — `grant_no`, `program_area`, `amount_usd`, `awardee`.

**Say (c):** Three planes, same identity. App has its own service principal. Unity Catalog is the data-plane firewall. Exports are audited. Tokens are short-lived. This cell is unclassified mock on commercial AWS (FedRAMP Moderate). IL5 is GovCloud + PrivateLink + customer-managed KMS — the other tape.

**Do not** read the fictional `api.onr-demo.com` curls. They are behind an expander.

---

### 46:00–50:00 — Close + leftover prompts

1. **Infrastructure** (15 s) — Inventory tab: warehouse, cluster, app, paused file-arrival job, SDP pipeline. “Version-controlled in `databricks.yml`; full IaC/CI is the companion tape.”
2. Finish any prompt not yet spoken. Prefer (d) RTO/RPO numbers and (a) strangler-fig if you skipped them.
3. Close on: drop another CSV tomorrow; same Volume, same gold, same registered models (`04c` to rescore). Mock data only.

Full prompt text: [STRATEGIC_PROMPTS.md](STRATEGIC_PROMPTS.md). 60–90 s each if you did not weave them.

---

## Clock

| Clock | On screen | Must say |
|------:|-----------|----------|
| 0:00–2:00 | Home 400 | Mock data; catalog |
| 2:00–6:30 | Ingestion Process | **Element 3**; 400→408; rejects; (a) |
| 6:30–13:30 | 01b + Volume copy | `processingTime` 30s; (d) RPO |
| 14:00–21:00 | Catalog + Explorer lineage | **Element 4**; (e) tags |
| 21:00–32:00 | 04c + Analytics | **Element 5**; (b) |
| 32:00–40:00 | Portfolio search + brief | **Element 6** |
| 40:00–46:00 | Export + Statement API | **Element 7**; (c) |
| 46:00–50:00 | Infrastructure 15 s + leftovers | Any remaining (a)–(e) |

If you are over: cut Trend Analysis, Schema Docs, and Infrastructure. **Never** cut 01b, Catalog Explorer lineage, 04c, search, or the live Statement API.

---

## If something is down (keep rolling)

| Symptom | On-camera fallback |
|---|---|
| Warehouse cold / Home says fixture | Wait one retry; if still fixture, say SP grants and proceed on fixture **only** for Portfolio visuals — do **not** fake Process |
| Process fails | Open `01_bronze_ingestion.py` + `02` + `03` already run from rehearsal; do not debug IAM live |
| 01b no tick | Confirm copy is under `landing/grants/` not `_staged/`; wait one 30 s micro-batch |
| 04c cannot load champion | Say “registry miss — scoring with the night-before tables” and open Analytics; do **not** Run all on 04/04b |
| `ai_query` off | Brief template still writes `app.daily_briefs` |
| Statement API SDK fails | Page falls back to the same SQL on the warehouse — still a live result; curl is the contract |
| Streamlit rerun wipes a widget | Re-select and continue; do not Reset |

---

## What not to invent

- This POC is **not** IL5 or FedRAMP High.
- Forecast is **OLS** (`ols_fy_v1`), not Prophet.
- 01b is Auto Loader `processingTime`, not Amazon Kinesis.
- Native UC lineage lives in **Catalog Explorer**, not the in-app mermaid.
- Do not claim you trained the models on camera if you ran **04c**.
- Key Personnel narrate every technical beat.
