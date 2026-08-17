# ONR ITSS POC — 25-minute presenter script (Elements 3–7)

**Persona:** one Key Personnel voice (platform / data lead). You click and you talk.  
**This tape:** Elements **3–7** + strategic prompts **(a)–(e)** woven at 20–30 seconds each.  
**Not this tape:** Element 1 (MFA / IdP) and Element 2 (Terraform / CI-CD). Infrastructure is a 10-second glance.

**How to read this page**

- Lines in **roman** are spoken. Read them. Do not paraphrase the Element labels or the five prompt answers.
- Lines in *italics* inside `[DO THIS]` are clicks. Do them, then keep reading.
- Clock marks are the latest you should still be on that beat. If you are late, jump to the next **[CATCH-UP]** line.

**On screen:** gold kicker is the Element number (`Element 3 · Data operations`); the title stays the product name (`Ingestion`). Sidebar nav stays product names.  
**Out loud, still say “Element 3” through “Element 7.”**

**Camera rule:** one take, live cloud + live repo, no slides, no overlays.

**Path rule:** one app window. Forward only — Home → Ingestion → Catalog → Analytics → Portfolio → Export → Infrastructure. Do not go back. Do not pre-open notebooks, Volume, Repo, or MLflow. If a workspace object is required, click the button or link **on that page**.

**Pace:** about 140 words per minute. Stream and score waits are covered by talk. Do not stare at a spinner in silence.

---

## 25-minute clock

| Clock | Page | Live action | Must say |
|------:|------|-------------|----------|
| 0:00–1:00 | Home | Point at **400** | Mock data; catalog |
| 1:00–8:30 | Ingestion | **Ingest selected files** then **Start stream** | **Element 3**; 400→408; Hold; **(a)**; **(d)** |
| 8:30–12:00 | Catalog | **Open lineage** | **Element 4**; **(e)** |
| 12:00–18:00 | Analytics | **Score registered models**; point at **Drift** | **Element 5**; **(b)**; Resource action |
| 18:00–21:00 | Portfolio | Search `quantum`; **Generate daily brief** | **Element 6** |
| 21:00–24:20 | Export | FY 2025–2026 export; **Execute live Statement API** | **Element 7**; **(c)** |
| 24:20–25:00 | Infrastructure | Inventory 10 s | Close; companion tape |

**Never cut:** 400→408, Hold tray, stream heartbeat, Catalog Explorer lineage, score, search, live Statement API, all five prompts.  
**Cut first if late:** Quality tab, Policies tab, Trends tab, Schema Docs, Infrastructure.

---

## Night before (not recorded)

1. Workspace Git folder: `git pull` `main`. Redeploy / restart `onr-demo-poc`.
2. Start **`onr demo warehouse`** and **`onr demo cluster`**. Leave them running.
3. Home = live **400**, not “fixture.” If fixture: `sql/grant_app_principal.sql` + warehouse **CAN USE** for the **app service principal**.
4. If silver ≠ 400: `05_reset_demo.py` on the cluster.
5. **Run all** `04_mlflow_grant_model.py` → `onr_demo.gold.grant_large_award`.
6. **Run all** `04b_funding_anomaly.py` → `funding_anomaly_detector` @ `champion`. If MLflow says parent missing: create `/Shared/onr-demo`, re-run from the MLflow cell.
7. Confirm `01b_streaming_autoloader` and `04c_score_registered_models` exist in the Git folder (the app resolves them). Optional: give the app SP **CAN ATTACH TO** / **CAN RESTART** on `onr demo cluster` so **Start stream** and **Score registered models** submit the run. If not, the on-page **Open … notebook** link is the backup.
8. Volume `_staged/batch_live_grants.csv` exists (bootstrap). The app can also land the packaged CSV.
9. Mute notifications. 1920×1080, zoom 110–125%, hide bookmarks.

### What is open

| Window | Parked on |
|--------|-----------|
| **App** | Home |

That is the only window you need. Do **not** open MFA, Terraform, GitHub Actions, Volume, MLflow, or a notebook ahead of time.

---

## Word-for-word script

### 0:00–1:00 — Home

`[DO THIS]` App on **Home**. Cursor on **Active grants = 400**. Do not scroll.

This is the ONR Code 08 portfolio on Databricks. Everything on this screen is mock, synthetic Compass data — four hundred S-and-T grants and twelve hundred derived ERP lines. No CUI, no PII, no classified.

You are looking at catalog `onr_demo`, medallion layers bronze, silver, gold, and app. SQL runs on the serverless warehouse named `onr demo warehouse`. Jobs run on `onr demo cluster`. The product in front of you is the Databricks App `onr-demo-poc`.

This recording is the data-and-analytics path — Elements three through seven. Secure access and infrastructure-as-code are the companion tape. Each page kicker is the Element number. The Workspace strip on every page opens the live notebook or Unity Catalog table for that Element.

`[DO THIS]` Click **Ingestion**.

---

### 1:00–8:30 — Element 3: ingest, quality, stream

**Element three: automated ingestion, data operations, and streaming.**

A new grants file has arrived. I am not recoding a pipeline. The staged files are already on the Unity Catalog Volume. Inbound grants is the good file. Quarantine sample is three bad rows — empty grant number, negative amount, and a duplicate.

`[DO THIS]` Confirm both **Inbound grants** and **Quarantine sample** are selected. Click **Ingest selected files**. Keep talking while it spins.

While that lands, here is how we sustain the legacy footprint — strategic prompt (a).

We do not cut over the D-and-A Portal, the reporting stack, or the existing ETL in a weekend. The pattern is strangler-fig coexistence. New files land in `/Volumes/onr_demo/bronze/landing/grants/` — governed object storage, not a DBFS mount. The warehouse path this button just used, and the Auto Loader path I will start next, write the **same** bronze Delta table. Legacy reports keep reading gold over JDBC. When a report is ready to retire, we point it at the table this app already uses. Rollback is delete-the-batch, not rewrite-the-estate.

`[DO THIS]` Point at **Active grants 400 → 408** and **Held / skipped +3**. Point at the **Hold** tray — chips **empty**, **dup**, **amt**.

There it is. Silver and bronze: four hundred to four hundred and eight. Eight rows published. The three quarantine rows never entered bronze — they are in `app.quarantine_log` (empty, dup, amt). One live grant published with a warning (missing abstract) in `app.quality_findings`. Open **Quality** to see the scoreboard, error log, and warnings.

Same Element three. That button was the warehouse SQL path. Next is the near-real-time path. I am not leaving this console.

`[DO THIS]` Click **Start stream**. Do **not** restore the baseline. If the run does not submit, use the Workspace strip — **01b stream** — Run all there, then come straight back to this page.

This is Databricks Auto Loader — `cloudFiles` — with trigger `processingTime` thirty seconds, not a batch `availableNow`. The console just wrote `batch_live_grants_stream.csv` onto the landing Volume. Schema evolution is `addNewColumns`, so a new column from a legacy extract does not break the job. The stream auto-stops at ninety seconds so we cannot leave it running.

`[DO THIS]` Point at the bronze count, **last 2 min**, and **last file … ago**. Then at **Delta time travel**.

The stream detected the file. Bronze ticks. Silver stays at four hundred and eight because silver dedupes on `grant_no`. That is the streaming proof: file arrival, not a scheduled batch. Kafka or Kinesis would be the equivalent bus on another estate; here the open equivalent is Auto Loader on a Volume.

Strategic prompt (d), resilience, while it finishes.

Contract targets: RPO fifteen minutes for gold, essentially zero for bronze landing — the file is still sitting in the Volume. Delta time-travel is the row-level RPO — baseline snapshot versus now, no restore. RTO thirty minutes to serving gold, about five minutes to serving the app. The warehouse is serverless; the app is already deployed. The all-purpose cluster is **not** on the serving path. Annual DR is non-disruptive: pause file-arrival, restore yesterday’s gold into a `onr_demo_dr` catalog, point a clone of the app at it, validate, tear down. We are **not** resetting on camera.

`[DO THIS]` Click **Catalog**. Do not return to Ingestion.

---

### 8:30–12:00 — Element 4: catalog, quality, lineage

**Element four: data governance, quality, and cataloging.**

`[DO THIS]` Click **Open lineage**. That is the only workspace jump. If the graph is empty, open `gold.grants_summary` from the same explorer.

This is Unity Catalog’s native lineage — landing Volume, to bronze, to silver, to gold, to the app. That graph is the Element four visual. This console is the operator surface, not the system of record.

`[DO THIS]` Back on the Catalog page — **Registry**. Scroll just enough to show bronze, silver, gold, app.

Four schemas. The eight grants we just ingested are already registered. Metadata — source file, ingest time, tags — is on the table, not in a spreadsheet.

`[DO THIS]` **Quality** tab. Open one expander if needed.

Health scores: completeness, accuracy, consistency, timeliness. Ingest rewrote `app.data_quality_scores`. A lapsed vendor feed shows up here as a timeliness drop, not a blank dashboard.

`[DO THIS]` **Policies & tags**. Point at `data_source=mock`.

Strategic prompt (e). Every external feed is a licensed product: owner, renewal date, quality SLO. Today the tags are `data_source`, `domain`, `data_sensitivity`. In production we add `vendor`, `license_id`, `renewal_date`. Usage is metered in `app.export_history` and `app.search_history`. If a subscription stops, Auto Loader has nothing new; last-good gold stays. We do not auto-delete.

`[DO THIS]` Click **Analytics**. Do not return to Catalog.

---

### 12:00–18:00 — Element 5: score and decide

**Element five: decision-support analytics and modeling.**

The models were trained last night and registered in Unity Catalog. I am **not** retraining on camera. I am triggering a live score against the portfolio we just ingested — including the eight new grants. Still this page.

`[DO THIS]` Click **Score registered models**. If the run does not submit, Workspace strip **04c score** — Run all, then come straight back here. Keep talking.

Strategic prompt (b), financial and budgetary, while it scores.

Financial execution is a first-class feed: twelve hundred ERP lines, budget, actual, execution rate, into `gold.budget_execution`. Three complementary models, all on **this** ingested portfolio — not a second dataset.

Descriptive: the Portfolio page a Code 08 resource officer opens — dollars, execution, `ON_TARGET` / `WARNING` / `AT_RISK`.

Predictive: a Random Forest large-award classifier — Fund, Review, or Defer — registered as `onr_demo.gold.grant_large_award`. An IsolationForest for budget spike, execution collapse, and low-return concentration — `funding_anomaly_detector` at alias `champion`. And ordinary least squares, `ols_fy_v1`, two-year horizon, ninety-five percent band, trend IDs `TREND-ACCEL`, `TREND-STEADY`, `TREND-DECLINE`. That is OLS, not Prophet.

Prescriptive: protect `ON_TARGET`, move dollars off `AT_RISK` and `TREND-DECLINE`, review large-award concentration. Engineer owns bronze and silver. Scientist owns the registered models. Analyst owns gold and the daily brief. Same catalog.

`[DO THIS]` Point at **Resource action**. Then **Drift** — program-mix PSI, award-size PSI, Fund share, baseline versus now.

That is feature and score drift on the portfolio we just ingested, not a fake accuracy drop. The live grants moved the mix. Workspace strip **grant_predictions** is the scored table.

`[DO THIS]` **Predictions**. `model_name` is `rf_large_award_v1`. Fund, Review, Defer. The live grants are in this table.

That Resource action sentence is the close a resource officer would sign — Defer dollars off one area onto AT_RISK plus TREND-DECLINE.

`[DO THIS]` **Anomalies**.

Review queue. Scorer `iforest_funding_v1`. These are the awards a comptroller should look at before the next execution review.

`[DO THIS]` **Forecasting**. Point at the orange horizon and one **TREND-DECLINE** row.

Two-year OLS forecast with a ninety-five percent band. That declining program is the reallocation candidate I will pair with `AT_RISK` on the next page.

`[DO THIS]` Click **Portfolio**. Do not return to Analytics.

---

### 18:00–21:00 — Element 6: portfolio, search, automation

**Element six: unified dashboard, visualizations, and process automation.**

A non-technical leader does not need SQL. Active grants is still four hundred and eight.

`[DO THIS]` Change one filter — fiscal year or a program area — then clear it or leave it. Click **Search**. Type `quantum`. Press enter / search.

Search is live against gold. It is also written to `app.search_history`. That is the audit Zero Trust asked for, and it is the usage meter for prompt (e).

`[DO THIS]` **Automation** → **Generate daily brief**. Wait for the letterhead.

Automated summary. Classification banner, three bullets, one recommended action. If Foundation Model serving is on, this is `ai_query`. If not, it is the structured template. Either way a row lands in `app.daily_briefs`. That is process automation — not a staffer writing the morning book.

`[DO THIS]` **Budget**. Point at one **AT_RISK** row.

Same gold the forecast used. `AT_RISK` plus `TREND-DECLINE` is the reallocation set. Extract is on the next page.

`[DO THIS]` Click **Export**.

---

### 21:00–24:20 — Element 7: export and open API

**Element seven: interoperability, data portability, and secure export.**

`[DO THIS]` Date range is already **2025 to 2026**. Leave **CSV** and **Parquet** on. Dataset **Grants Summary**. Click **Execute export**. Download Parquet or CSV once.

Filtered bulk extract — not `SELECT *`. Open formats: CSV, JSON, Parquet. Schema travels with the file: `grant_no`, `program_area`, `amount_usd`, `awardee`.

`[DO THIS]` **History**. Point at the new row.

`app.export_history` — who, what, filter, row count. Continuous authorization, not a static password file.

`[DO THIS]` **API**. Click **Execute live Statement API call**. Point at the statement receipt — `statement_id`, `SUCCEEDED`, `row_count`, warehouse, elapsed.

This is the live, documented Databricks Statement Execution REST API — `POST /api/2.0/sql/statements` — OAuth, short-lived token, same warehouse the dashboard uses. That is what Advana or Cloud One would call. It is not a Databricks-only extract and it is not a fictional host.

Strategic prompt (c). Three planes, same identity. The app has its **own** service principal; it does not borrow mine. The warehouse and the cluster are separate. Unity Catalog is the data-plane firewall. Least privilege: analysts `SELECT` gold, they never see bronze. This cell is unclassified mock on commercial AWS — FedRAMP Moderate. The IL5 production cell is GovCloud, PrivateLink, customer-managed KMS. We are not claiming this POC is IL5.

`[DO THIS]` Click **Infrastructure**.

---

### 24:20–25:00 — Close

Ten seconds. Warehouse `onr demo warehouse`, cluster `onr demo cluster`, app `onr-demo-poc`, paused file-arrival job, SDP pipeline — all named in `databricks.yml`. Full IaC and CI-CD are the companion tape.

Tomorrow another CSV lands on the same Volume. Same gold. Same registered models — we rescore from this console. Mock data only.

`[DO THIS]` Stop talking. Leave Infrastructure on screen.

---

## [CATCH-UP] if you are late

| If the clock says | Skip and go to |
|-------------------|----------------|
| 4:30 and Ingest is still spinning | Keep talking (a); do not open Quality |
| 7:30 and bronze has not ticked | Say “waiting one thirty-second micro-batch.” If still nothing, click **Open stream notebook**, then come back. At 8:30 go to **Catalog** anyway |
| 11:30 still on Catalog | Skip Policies; say (e) in two sentences; go to **Analytics** |
| 16:30 and score is still running | Stay on Analytics; skip Trends; go **Portfolio** at 18:00 |
| 20:00 still on Analytics | Skip Anomalies **or** Forecast (keep one); go **Portfolio** search |
| 22:30 still on Portfolio | Skip Budget; go **Export** |
| 24:00 and no API yet | Skip download; **Execute live Statement API** immediately; say (c) in four sentences |

---

## If something is down (one sentence, then move)

| Symptom | Say, then do |
|---|---|
| Home says fixture | “Warehouse or app service-principal grant is cold.” Do **not** fake Ingest. Portfolio fixture only if you must. |
| Ingest errors | “I will not debug IAM on camera.” Skip to Catalog **Open lineage**. |
| Start stream fails | Click **Open stream notebook**. “Same Auto Loader job — the file is already on the Volume.” Come back. |
| Bronze does not tick | “File must sit under `landing/grants/`, not `_staged`.” Wait one micro-batch. Then **Catalog**. |
| Open lineage is empty | “Same graph lives on `gold.grants_summary`.” Do not rebuild it in the app. |
| Score fails | Click **Open scoring notebook**. If champion is missing: “I will not train on camera. These are last night’s gold tables.” Stay on Analytics. |
| Brief is the template | “Foundation Models are off; the structured brief still writes `app.daily_briefs`.” |
| Statement API SDK fails | “Same SQL on the warehouse cursor — still live. The curl is the Advana contract.” |
| Streamlit rerun clears a widget | Re-select. **Do not Restore baseline.** |

---

## What you will not say

- This POC is IL5 or FedRAMP High.
- The forecast is Prophet or a neural net. It is OLS.
- The stream is Amazon Kinesis. It is Auto Loader `processingTime`.
- Lineage is drawn inside Streamlit. Native lineage is Catalog Explorer.
- “We trained the models just now.” You scored from the registry. Training was last night.
- Drift is accuracy decay. It is feature and score mix versus the baseline snapshot.
- “We rewrite the legacy estate.” Strangler-fig only.
- Any Element 1 or Element 2 deep-dive. Companion tape.

Longer prompt text, if a reviewer asks after the recording: [STRATEGIC_PROMPTS.md](STRATEGIC_PROMPTS.md). Do not read those 75-second versions on this 25-minute take.
