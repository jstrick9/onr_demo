# ONR ITSS POC — 25-minute presenter script (Elements 3–7)

**Persona:** one Key Personnel voice (platform / data lead). You click and you talk.  
**This tape:** Elements **3–7** + strategic prompts **(a)–(e)** woven at 20–30 seconds each.  
**Not this tape:** Element 1 (MFA / IdP) and Element 2 (Terraform / CI-CD). Infrastructure is a 10-second glance.

**How to read this page**

- Lines in **roman** are spoken. Read them. Do not paraphrase the Element labels or the five prompt answers.
- Lines in *italics* inside `[DO THIS]` are clicks. Do them, then keep reading.
- Clock marks are the latest you should still be on that beat. If you are late, jump to the next **[CATCH-UP]** line.

**On screen, product names only:** Ingestion · Catalog · Analytics · Portfolio · Export · Infrastructure.  
**Out loud, say “Element 3” through “Element 7.”** They are not labeled in the UI.

**Camera rule:** one take, live cloud + live repo, no slides, no overlays.

**Pace:** about 140 words per minute. The 01b and 04c waits are covered by talk. Do not stare at a spinner in silence.

---

## 25-minute clock

| Clock | Tab | Live action | Must say |
|------:|-----|-------------|----------|
| 0:00–1:00 | App · Home | Point at **400** | Mock data; catalog |
| 1:00–5:00 | App · Ingestion | Process **Live 8 + Quality-fail** | **Element 3**; 400→408; rejects; **(a)** |
| 5:00–10:00 | 01b + Volume + App | **Run all** 01b; copy `batch_live_grants_stream.csv` | `processingTime` 30s; **(d)** |
| 10:00–13:00 | Catalog + Catalog Explorer | Native **Lineage** | **Element 4**; **(e)** |
| 13:00–18:00 | 04c + App · Analytics | **Run all** 04c; Predictions / Anomalies / Forecast | **Element 5**; **(b)** |
| 18:00–21:00 | App · Portfolio | Search `quantum`; **Generate daily brief** | **Element 6** |
| 21:00–24:20 | App · Export | FY 2025–2026 export; **Execute live Statement API** | **Element 7**; **(c)** |
| 24:20–25:00 | App · Infrastructure | Inventory 10 s | Close; companion tape |

**Never cut:** Process 400→408, 01b tick, Catalog Explorer lineage, 04c, search, live Statement API, all five prompts.  
**Cut first if late:** MLflow tab, Trend Analysis, Schema Docs, Infrastructure, Quality Checks tab.

---

## Night before (not recorded)

1. Workspace Git folder: `git pull` `main` (recording pack **`38ac3c9`** or later). Redeploy / restart `onr-demo-poc`.
2. Start **`onr demo warehouse`** and **`onr demo cluster`**. Leave them running.
3. Home = live **400**, not “fixture.” If fixture: `sql/grant_app_principal.sql` + warehouse **CAN USE** for the **app service principal**.
4. If silver ≠ 400: `05_reset_demo.py` on the cluster.
5. **Run all** `04_mlflow_grant_model.py` → `onr_demo.gold.grant_large_award`.
6. **Run all** `04b_funding_anomaly.py` → `funding_anomaly_detector` @ `champion`. If MLflow says parent missing: create `/Shared/onr-demo`, re-run from the MLflow cell.
7. Analytics Predictions `model_name` = `rf_large_award_v1`. Anomalies scorer contains `iforest`.
8. Volume `_staged/batch_live_grants.csv` exists.
9. Attach `01b_streaming_autoloader.py` and `04c_score_registered_models.py`. **Do not Run all.**
10. Mute notifications. 1920×1080, zoom 110–125%, hide bookmarks.

### Seven tabs, already open

| Tab name | Parked on |
|----------|-----------|
| **App** | Home |
| **01b** | `notebooks/01b_streaming_autoloader.py` (attached, idle) |
| **Volume** | `/Volumes/onr_demo/bronze/landing/` |
| **Catalog Explorer** | `onr_demo.silver.grants` → **Lineage** |
| **04c** | `notebooks/04c_score_registered_models.py` (attached, idle) |
| **MLflow** | `/Shared/onr-demo` (do not start a run) |
| **Repo** | Workspace Git folder on `main` |

Do **not** open MFA, Terraform, or GitHub Actions.

---

## Word-for-word script

### 0:00–1:00 — Home

`[DO THIS]` App tab. Cursor on sidebar **Active grants = 400**. Do not scroll.

This is the ONR Code 08 portfolio on Databricks. Everything on this screen is mock, synthetic Compass data — four hundred S-and-T grants and twelve hundred derived ERP lines. No CUI, no PII, no classified.

You are looking at catalog `onr_demo`, medallion layers bronze, silver, gold, and app. SQL runs on the serverless warehouse named `onr demo warehouse`. Notebooks run on `onr demo cluster`. The product in front of you is the Databricks App `onr-demo-poc`.

This recording is the data-and-analytics path — Elements three through seven. Secure access and infrastructure-as-code are the companion tape. I will say the Element numbers; the UI uses product names.

`[DO THIS]` Click **Ingestion**.

---

### 1:00–5:00 — Element 3, part 1: ingest and quality

**Element three: automated ingestion, data operations, and streaming.**

A new grants file has arrived. I am not recoding a pipeline. The staged files are already on the Unity Catalog Volume. Live eight grants is the good file. Quality-fail sample is three bad rows — empty grant number, negative amount, and a duplicate.

`[DO THIS]` Confirm both **Live 8 grants** and **Quality-fail sample** are selected. Click **Process selected files**. Keep talking while it spins.

While that lands, here is how we sustain the legacy footprint — strategic prompt (a).

We do not cut over the D-and-A Portal, the reporting stack, or the existing ETL in a weekend. The pattern is strangler-fig coexistence. New files land in `/Volumes/onr_demo/bronze/landing/grants/` — governed object storage, not a DBFS mount. The warehouse path this button just used, and the Auto Loader path I will start next, write the **same** bronze Delta table. Legacy reports keep reading gold over JDBC. When a report is ready to retire, we point it at the table this app already uses. Rollback is delete-the-batch, not rewrite-the-estate.

`[DO THIS]` When the metrics appear, point at **Before 400 → After 408**. Open the file summary. Point at landed / rejected / skipped.

There it is. Silver grants: four hundred to four hundred and eight. Eight rows landed. Empty `grant_no` never entered bronze. Negative amount is called out and will not pass silver. The duplicate was skipped. Automated quality at the gate — no manual recode.

`[DO THIS]` Click the **Quality Checks** tab. Two seconds. Then go to tab **01b**. Do **not** Reset.

---

### 5:00–10:00 — Element 3, part 2: live stream

Same Element three. That button was the warehouse SQL path. This notebook is the near-real-time path.

`[DO THIS]` On **01b**, click **Run all**. Immediately switch to **Volume**.

This is Databricks Auto Loader — `cloudFiles` — with trigger `processingTime` thirty seconds, not a batch `availableNow`. Schema evolution is `addNewColumns`, so a new column from a legacy extract does not break the job. It auto-stops at ninety seconds so we cannot leave a stream running.

`[DO THIS]` Copy `_staged/batch_live_grants.csv` to `grants/batch_live_grants_stream.csv`. New filename. Switch back to **01b**. Point at `inputRows` / `bronze.grants` / last-two-min as they tick.

The stream detected the file. Bronze ticks. Silver will stay at four hundred and eight because silver dedupes on `grant_no`. That is the streaming proof: file arrival, not a scheduled batch. Kafka or Kinesis would be the equivalent bus on another estate; here the open equivalent is Auto Loader on a Volume.

Strategic prompt (d), resilience, while it finishes.

Contract targets: RPO fifteen minutes for gold, essentially zero for bronze landing — the file is still sitting in the Volume. Delta time-travel is the row-level RPO. RTO thirty minutes to serving gold, about five minutes to serving the app. The warehouse is serverless; the app is already deployed. The all-purpose cluster is **not** on the serving path. Annual DR is non-disruptive: pause file-arrival, restore yesterday’s gold into a `onr_demo_dr` catalog, point a clone of the app at it, validate, tear down. We are **not** resetting on camera.

`[DO THIS]` Optional two seconds: App → Ingestion → **Schema & Streaming** → **Last 2 min**. Then **Catalog Explorer** tab.

---

### 10:00–13:00 — Element 4: catalog, quality, lineage

**Element four: data governance, quality, and cataloging.**

`[DO THIS]` Catalog Explorer is already on `onr_demo.silver.grants`. Click **Lineage**. If the graph is empty, click `gold.grants_summary` instead.

This is Unity Catalog’s native lineage — landing Volume, to bronze, to silver, to gold, to the app. That graph is the Element four visual. The Streamlit page is the operator console, not the system of record.

`[DO THIS]` App tab → **Catalog** → **Catalog Registry**. Scroll just enough to show bronze, silver, gold, app.

Four schemas. The eight grants we just ingested are already registered. Metadata — source file, ingest time, tags — is on the table, not in a spreadsheet.

`[DO THIS]` **Quality Scores** tab. Open one expander if needed.

Health scores: completeness, accuracy, consistency, timeliness. Process rewrote `app.data_quality_scores`. A lapsed vendor feed shows up here as a timeliness drop, not a blank dashboard.

`[DO THIS]` **Policies & Tags**. Point at `data_source=mock`.

Strategic prompt (e). Every external feed is a licensed product: owner, renewal date, quality SLO. Today the tags are `data_source`, `domain`, `data_sensitivity`. In production we add `vendor`, `license_id`, `renewal_date`. Usage is metered in `app.export_history` and `app.search_history`. If a subscription stops, Auto Loader has nothing new; last-good gold stays. We do not auto-delete.

`[DO THIS]` Tab **04c**.

---

### 13:00–18:00 — Element 5: trigger and execute

**Element five: decision-support analytics and modeling.**

The models were trained last night and registered in Unity Catalog. I am **not** retraining on camera. I am triggering a live score against the portfolio we just ingested — including the eight new grants.

`[DO THIS]` **04c** → **Run all**. Switch to **Repo** for two seconds (live code on `main`), then back to **04c**. Keep talking.

Strategic prompt (b), financial and budgetary, while it scores.

Financial execution is a first-class feed: twelve hundred ERP lines, budget, actual, execution rate, into `gold.budget_execution`. Three complementary models, all on **this** ingested portfolio — not a second dataset.

Descriptive: the Portfolio page a Code 08 resource officer opens — dollars, execution, `ON_TARGET` / `WARNING` / `AT_RISK`.

Predictive: a Random Forest large-award classifier — Fund, Review, or Defer — registered as `onr_demo.gold.grant_large_award`. An IsolationForest for budget spike, execution collapse, and low-return concentration — `funding_anomaly_detector` at alias `champion`. And ordinary least squares, `ols_fy_v1`, two-year horizon, ninety-five percent band, trend IDs `TREND-ACCEL`, `TREND-STEADY`, `TREND-DECLINE`. That is OLS, not Prophet.

Prescriptive: protect `ON_TARGET`, move dollars off `AT_RISK` and `TREND-DECLINE`, review large-award concentration. Engineer owns bronze and silver. Scientist owns the registered models. Analyst owns gold and the daily brief. Same catalog.

`[DO THIS]` When 04c prints the readout, point at rows scored **408**, Fund / Review / Defer counts, IsolationForest flagged count. Then App → **Analytics**.

Predictions tab. `model_name` is `rf_large_award_v1`. Fund, Review, Defer. The live grants are in this table.

`[DO THIS]` **Anomalies**.

Review queue. Scorer `iforest_funding_v1`. These are the awards a comptroller should look at before the next execution review.

`[DO THIS]` **Forecasting**. Point at the orange horizon and one **TREND-DECLINE** row.

Two-year OLS forecast with a ninety-five percent band. That declining program is the reallocation candidate I will pair with `AT_RISK` on the next page.

`[DO THIS]` Optional: **MLflow** tab, fifteen seconds — existing runs only. Then **Portfolio**.

---

### 18:00–21:00 — Element 6: portfolio, search, automation

**Element six: unified dashboard, visualizations, and process automation.**

A non-technical leader does not need SQL. Sidebar still shows four hundred and eight.

`[DO THIS]` Change one filter — fiscal year or a program area — then clear it or leave it. Click **Search & Extract**. Type `quantum`. Press enter / search.

Search is live against gold. It is also written to `app.search_history`. That is the audit Zero Trust asked for, and it is the usage meter for prompt (e).

`[DO THIS]` **Process Automation** → **Generate daily brief**. Wait for the text.

Automated summary. If Foundation Model serving is on, this is `ai_query`. If not, it is the structured template. Either way a row lands in `app.daily_briefs`. That is process automation — not a staffer writing the morning book.

`[DO THIS]` **Budget Execution**. Point at one **AT_RISK** row.

Same gold the forecast used. `AT_RISK` plus `TREND-DECLINE` is the reallocation set. Extract is on the next page.

`[DO THIS]` **Export**.

---

### 21:00–24:20 — Element 7: export and open API

**Element seven: interoperability, data portability, and secure export.**

`[DO THIS]` **Data Export**. Date range is already **2025 to 2026**. Leave **CSV** and **Parquet** on. Dataset **Grants Summary**. Click **Execute Export**. Click **Download Parquet** or **Download CSV** once.

Filtered bulk extract — not `SELECT *`. Open formats: CSV, JSON, Parquet. Schema travels with the file: `grant_no`, `program_area`, `amount_usd`, `awardee`.

`[DO THIS]` **Export History**. Point at the new row.

`app.export_history` — who, what, filter, row count. Continuous authorization, not a static password file.

`[DO THIS]` **API** tab. Click **Execute live Statement API call**. Point at `statement_id` and the JSON.

This is the live, documented Databricks Statement Execution REST API — `POST /api/2.0/sql/statements` — OAuth, short-lived token, same warehouse the dashboard uses. That is what Advana or Cloud One would call. It is not a Databricks-only extract and it is not a fictional host.

Strategic prompt (c). Three planes, same identity. The app has its **own** service principal; it does not borrow mine. The warehouse and the cluster are separate. Unity Catalog is the data-plane firewall. Least privilege: analysts `SELECT` gold, they never see bronze. This cell is unclassified mock on commercial AWS — FedRAMP Moderate. The IL5 production cell is GovCloud, PrivateLink, customer-managed KMS. We are not claiming this POC is IL5.

`[DO THIS]` **Infrastructure**.

---

### 24:20–25:00 — Close

Ten seconds. Warehouse `onr demo warehouse`, cluster `onr demo cluster`, app `onr-demo-poc`, paused file-arrival job, SDP pipeline — all named in `databricks.yml`. Full IaC and CI-CD are the companion tape.

Tomorrow another CSV lands on the same Volume. Same gold. Same registered models — we rescore with notebook `04c`. Mock data only.

`[DO THIS]` Stop talking. Leave Infrastructure or Home on screen.

---

## [CATCH-UP] if you are late

| If the clock says | Skip and go to |
|-------------------|----------------|
| 4:30 and Process is still spinning | Keep talking (a); do not open Quality Checks |
| 9:30 and 01b has not ticked | Say “waiting one thirty-second micro-batch”; if still nothing, say “file must sit under `landing/grants/`, not `_staged`,” and go to Catalog Explorer |
| 12:30 still on Catalog | Skip tags table; say (e) in two sentences; go to 04c |
| 16:30 and 04c still running | Stay on 04c; skip MLflow; go Analytics Predictions only, then Portfolio |
| 20:00 still on Analytics | Skip Anomalies **or** Forecast (keep one); go Portfolio search |
| 22:30 still on Portfolio | Skip Budget Execution; export now |
| 24:00 and no API yet | Skip download; **Execute live Statement API** immediately; say (c) in four sentences |

---

## If something is down (one sentence, then move)

| Symptom | Say, then do |
|---|---|
| Home says fixture | “Warehouse or app service-principal grant is cold.” Do **not** fake Process. Portfolio fixture only if you must. |
| Process errors | “I will not debug IAM on camera.” Open rehearsal gold if you have it; otherwise skip to Catalog Explorer. |
| 01b no `inputRows` | “Confirm the copy is `landing/grants/batch_live_grants_stream.csv`.” Wait one micro-batch. Then leave. |
| 04c cannot load champion | “Registry miss — I will not train on camera. These are last night’s gold tables.” Open Analytics. |
| Brief is the template | “Foundation Models are off; the structured brief still writes `app.daily_briefs`.” |
| Statement API SDK fails | “Same SQL on the warehouse cursor — still live. The curl is the Advana contract.” |
| Streamlit rerun clears a widget | Re-select. **Do not Reset.** |

---

## What you will not say

- This POC is IL5 or FedRAMP High.
- The forecast is Prophet or a neural net. It is OLS.
- 01b is Amazon Kinesis. It is Auto Loader `processingTime`.
- Lineage is drawn inside Streamlit. Native lineage is Catalog Explorer.
- “We trained the models just now.” You ran **04c**. Training was last night.
- “We rewrite the legacy estate.” Strangler-fig only.
- Any Element 1 or Element 2 deep-dive. Companion tape.

Longer prompt text, if a reviewer asks after the recording: [STRATEGIC_PROMPTS.md](STRATEGIC_PROMPTS.md). Do not read those 75-second versions on this 25-minute take.
