# Strategic Prompt Talking Points (11.4)

**Audience:** Key Personnel narration during the 50-minute recording.
**Rule:** All five prompts must be spoken. Business development may introduce; Key Personnel lead every technical answer.
**Budget:** ~60–90 seconds per prompt. Weave into the matching element (preferred) or close as a dedicated 6-minute block at minute 44–50.
**Data constraint:** Everything on screen is mock / synthetic. Say that once, then do not linger.

Full prompt text is quoted from Volume IV §11.4. Show a live artifact while you talk — never a slide.

| Prompt | Best moment | Live artifact to have on screen |
|--------|-------------|----------------------------------|
| (a) Legacy sustainment | Element 3 or 7 | Ingestion page + `landing/` volume, or Export tab |
| (b) Financial / budgetary | Element 5 + 6 | Analytics predictions + Dashboard budget gauge |
| (c) Zero Trust / IL5 | Element 4 or 7 | Catalog Explorer grants, or Integration Zero Trust panel |
| (d) DR / resilience | Element 3 reset, or close | Reset-to-seed + `databricks.yml` file-arrival job |
| (e) Vendor / lifecycle | Element 4 | Quality scores + UC tags (`data_source=mock`) |

---

## (a) Sustainment of the Legacy Footprint

> Detail your exact technical approach for sustaining and operating the current legacy D&A Portal application, reporting systems, databases, and existing ETL pipelines, ensuring zero service degradation or operational gaps during modernization phases.

**Show:** Ingestion page (warehouse SQL path) *and* `notebooks/01_bronze_ingestion.py` (Auto Loader). Optionally the Export tab (CSV/JSON/Parquet + JDBC).

**Say (~75 s):**

> We do not cut over the legacy D&A Portal, reporting stack, or existing ETL in a single weekend. The pattern is *strangler-fig coexistence*.
>
> New files land in a Unity Catalog Volume — `/Volumes/onr_demo/bronze/landing/grants/` — which is just cloud object storage with a governed path. Auto Loader (`cloudFiles`) incrementally picks up whatever arrives; schema evolution is `addNewColumns`, so a new column from the legacy extract does not break the pipeline. The same bronze table can be written by the legacy ETL *and* by the new Auto Loader job. Silver and gold are rebuilt from bronze, so consumers that are not ready stay on the old reports.
>
> Zero service degradation is a contract, not a slogan: the warehouse SQL path the app uses and the cluster Auto Loader path write the same Delta tables. Legacy reporting keeps reading gold through JDBC/ODBC — open standards, no proprietary extract. When a legacy report is ready to retire, we point it at the same gold table the Streamlit dashboard already uses. If we have to roll back, `05_reset_demo.py` (or the app Reset) deletes only the new batch — seed data never moves.
>
> Data leaves in CSV, JSON, or Parquet with a self-describing schema, so the portal, Advana, or a remaining on-prem store can consume the modernized feed until that system is retired.

**Do not say:** “We rewrite everything.” Evaluators will hear risk.

---

## (b) Financial & Budgetary Analytical Integration

> Describe how your platform's analytical modeling techniques (predictive, prescriptive) and your proposed team will support financial execution tracking, budget formulation, and cost optimization for various command resourcing priorities.

**Show:** Analytics → Forecasting tab (`gold.funding_forecast` + trend IDs); Dashboard → Budget gauge + **Generate daily brief**.

**Say (~80 s):**

> Financial execution is a first-class feed, not a side spreadsheet. The fixture derives 1,200 ERP lines from the 400-grant portfolio — budget, actual, execution rate, variance — and lands them in `bronze.financial` → `silver.financial` → `gold.budget_execution`.
>
> *Descriptive:* the executive dashboard is what a Code 08 resource officer would open — portfolio dollars, execution rate, and a status of `ON_TARGET` / `WARNING` / `AT_RISK` per FY-quarter-category. That is automated anomaly flagging, not a monthly Excel.
>
> *Predictive:* two models, both in gold. `ols_fy_v1` is an ordinary-least-squares fit of `total_funding ~ fiscal_year` per program area — two-year horizon, 95% residual band, written to `gold.funding_forecast`. Each area gets a **trend ID**: `TREND-ACCEL`, `TREND-STEADY`, or `TREND-DECLINE`, plus a YoY velocity, in `gold.program_trends`. Separately, notebook `04` trains a Random Forest on `silver.grants` (large-award ≥ $1M), writes `gold.grant_predictions` / `gold.model_metrics`, and registers `onr_demo.gold.grant_large_award`. Leadership sees Fund / Review / Defer with a probability, not a black-box score.
>
> *Prescriptive / budget formulation:* AT_RISK categories are the reallocation candidates. A resource officer filters to those rows, exports Parquet, and the same gold table is what a budget-formulation workbook or Advana cube would consume. Cost optimization is “move dollars off AT_RISK, protect ON_TARGET, review large-award concentration.”
>
> Team split on a live program: data engineer owns bronze/silver and the file-arrival job; data scientist owns the UC-registered model; analyst owns gold definitions and the dashboard. Same catalog, same identity, no copy-out.

**Honest boundary (only if asked):** `ols_fy_v1` is linear OLS, not Prophet / ARIMA. Eight fiscal years is enough to show a real fitted forecast with a confidence band and named trend IDs; it is not a deep time-series model.

---

## (c) Zero Trust & Cybersecurity Compliance (IL4/IL5 Baseline)

> Detail how the proposed application architecture implements micro-segmentation, continuous compliance, and least-privilege boundary configurations within a DoD Impact Level 5 (IL5) hosting environment.

**Show:** Integration page “Zero Trust / IL4/IL5” panel, *or* Catalog Explorer on `onr_demo` (grants + tags). Do **not** claim this POC *is* IL5 — it is unclassified mock on commercial AWS (FedRAMP Moderate). IL5 is the *target hosting pattern* (GovCloud + IL5 PA).

**Say (~80 s):**

> Three planes, same identity.
>
> *Micro-segmentation.* Compute, data, and the app are separate principals. The Streamlit app is a Databricks App with its own service principal. It does not share the human’s token. The warehouse (`onr demo warehouse`) and the cluster (`onr demo cluster`) are distinct. Unity Catalog is the data-plane firewall: catalogs, schemas, volumes, and (in production) row filters and column masks — the commented examples in `sql/setup_uc_objects.sql`. Network isolation at IL5 is VPC + PrivateLink + storage that never traverses the public internet; that is the Element 1 / hosting story, not this mock workspace.
>
> *Least privilege.* `sql/grant_app_principal.sql` is deliberately scoped to `onr_demo` and the two volumes. `MANAGE` on the four schemas is a POC concession so the app can `CREATE OR REPLACE` tables the bootstrap user owns. In production the job identity *owns* silver/gold and the app is `SELECT` + `MODIFY` only — we will say that out loud so it is not mistaken for the IL5 grant set. Analysts get `SELECT` on gold; they never see bronze.
>
> *Continuous compliance.* Every export is inserted into `app.export_history`. Every search into `app.search_history`. Ingestion quality lands in `app.ingestion_quality_log`. Unity Catalog audit (`system.access.audit`) is queried in `sql/validation_queries.sql`. Access is OAuth to the warehouse — short-lived tokens, not a static password. Tags (`data_source=mock`, `data_sensitivity`, `medallion`) travel with the table so a scanner can assert “no CUI in this catalog.”
>
> This recording uses sanitized mock data only. The IL5 production cell is GovCloud, encryption with customer-managed KMS, and the same Unity Catalog control plane.

---

## (d) Disaster Recovery, Resilience, and Failover

> Explain your approach to business continuity, specifically detailing: Target Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO); High-availability cloud configuration patterns; and your strategy for conducting non-disruptive annual disaster recovery exercises.

**Show:** App Reset (replayability) and, if open, `databricks.yml` file-arrival job (paused). Optionally mention serverless warehouse auto-stop/start.

**Say (~80 s):**

> Targets we will put on the contract, then prove annually.
>
> *RPO — 15 minutes for gold, ~0 for bronze landing.* Landing is a UC Volume on durable object storage, cross-region replicated at the storage layer. Auto Loader checkpoints live on a second volume. If the warehouse dies mid-query, files are still in `landing/grants/` and the file-arrival job (`onr-demo-grants-file-arrival` in the DAB) replays them. Delta time-travel on bronze/silver/gold is the row-level RPO — `DESCRIBE HISTORY` is on the Ingestion page.
>
> *RTO — 30 minutes to serving gold, 5 minutes to serving the app.* The SQL warehouse is serverless; it cold-starts in about a minute. The Streamlit app is already a Databricks App — if the warehouse is down the UI degrades to the packaged 400-grant fixture so leadership still has a picture, then reconnects. The all-purpose cluster is *not* on the serving path; it is for Auto Loader and model training.
>
> *HA pattern.* Multi-AZ by default on the warehouse and on managed storage. For IL5 we add a secondary region with catalog metastore follow and a warm volume replica. Failover is DNS + warehouse bind, not a rewrite.
>
> *Annual DR exercise, non-disruptive.* We do not take production down. We (1) pause the file-arrival trigger, (2) restore yesterday’s gold from time-travel into a `onr_demo_dr` catalog, (3) point a clone of the app at that catalog, (4) run `sql/validation_queries.sql` plus a filtered export, (5) tear the clone down. Production file-arrival is unpaused. The Reset button you just saw is the same muscle memory at demo scale: delete the live batch, rebuild silver/gold from seed, confirm 400.

---

## (e) Data Vendor and Lifecycle Management

> Explain your methodology and tooling for tracking commercial data subscriptions, monitoring data-usage licenses, validating data quality compliance, and managing renewals without causing data gaps in critical analytical dashboards.

**Show:** Governance quality scores + catalog tags; Ingestion quality-fail file (3 rejected rows).

**Say (~75 s):**

> Treat every external feed as a *licensed product* with an owner, a renewal date, and a quality SLO — not as an anonymous file drop.
>
> *Tracking.* Unity Catalog is the system of record. Tables carry tags: `data_source`, `domain`, `data_sensitivity`, `owner`, `refresh_frequency`. In production we add `vendor`, `license_id`, `renewal_date`, `feed_slo_hours`. Those tags are queryable from `system.information_schema` — the same registry the Governance page already reads.
>
> *License / usage.* Exports and searches are written to `app.export_history` and `app.search_history` with user, dataset, row count, and bytes. That is the usage meter a contracting officer needs before a renewal, and it is the same audit Zero Trust asked for.
>
> *Quality compliance.* Silver enforces `amount_usd > 0` and `awardee IS NOT NULL`; the quality-fail file shows three rows dying at the gate (empty grant_no, negative amount, duplicate). `app.data_quality_scores` is rewritten on every Process / Reset — completeness, accuracy, consistency, timeliness — so a lapsed feed shows up as a score drop, not a silent hole in the dashboard.
>
> *Renewals without gaps.* Ninety / sixty / thirty days before `renewal_date` a job flags the vendor in `ingestion_quality_log` and the Dashboard “Pipeline health” table. If the feed actually stops, Auto Loader simply has nothing new; gold stays at last-good and the freshness check in `validation_queries.sql` turns from Fresh → Aging → Stale. The dashboard does not go blank. We do not auto-delete last-good data when a subscription lapses.

---

## Timing cheat-sheet (if you close with a dedicated block)

| Clock | Prompt | On-screen |
|------:|--------|-----------|
| 0:00–0:80 | (a) Legacy | Ingestion + landing path |
| 1:20–2:40 | (b) Financial | Budget gauge + predictions |
| 2:40–4:00 | (c) Zero Trust | Integration IL4/IL5 panel |
| 4:00–5:20 | (d) DR | Reset confirmation / DAB job |
| 5:20–6:30 | (e) Vendor | Quality scores + tags |

If you are already over time, cut (d) and (e) to the first four sentences each — those two are the ones currently missing from the UI, so *some* spoken answer is required for Completeness.

---

## What not to invent

- Do not claim the POC warehouse is IL5 or FedRAMP High. Commercial AWS = Moderate; GovCloud + IL5 PA is the production cell.
- Do not claim the FY forecast is Prophet / a neural net. It is OLS (`ols_fy_v1`) with a 95% residual band and named trend IDs — say that.
- Do not claim native UC lineage is drawn inside Streamlit — open **Catalog Explorer → `onr_demo` → Lineage** for that beat.
- Do not let a non-Key-Personnel voice deliver any of these five answers.
