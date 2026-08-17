# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # 00 — Bootstrap (run this first on a new workspace)
# MAGIC
# MAGIC **What it does (one pass):**
# MAGIC 1. Creates catalog `onr_demo` and schemas `bronze` / `silver` / `gold` / `app`
# MAGIC 2. Creates Volumes `landing` and `checkpoints`
# MAGIC 3. Loads the Compass fixture (400 grants) + derived ERP (1,200 rows) into **bronze → silver → gold**
# MAGIC 4. Stages extra files for the live ingest demo
# MAGIC
# MAGIC **Set `repo_root`** to the folder where this Git repo lives in the workspace  
# MAGIC (example: `/Workspace/Users/you@navy.mil/onr_demo`).

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")
dbutils.widgets.text("repo_root", "")

catalog = dbutils.widgets.get("catalog")
repo_root = dbutils.widgets.get("repo_root").strip().rstrip("/")

def _infer_repo_root():
    try:
        p = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        if not p:
            return None
        if not p.startswith("/Workspace"):
            p = "/Workspace" + p
        if "/notebooks/" in p:
            return p.rsplit("/notebooks/", 1)[0]
    except Exception:
        return None
    return None

if (not repo_root) or ("REPLACE_ME" in repo_root):
    inferred = _infer_repo_root()
    if inferred:
        repo_root = inferred
        print("Inferred repo_root:", repo_root)
    else:
        raise ValueError(
            "Set the repo_root widget to the cloned onr_demo folder "
            "(example /Workspace/Users/you@org/onr_demo)."
        )

landing = f"/Volumes/{catalog}/bronze/landing"
staged = f"{landing}/_staged"

print(f"catalog={catalog}")
print(f"repo_root={repo_root}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create Unity Catalog objects

# COMMAND ----------

print("Checking catalogs…")
existing = {r[0] for r in spark.sql("SHOW CATALOGS").collect()}
if catalog in existing:
    print(f"Catalog `{catalog}` already exists — skip CREATE CATALOG")
else:
    print(f"Creating catalog `{catalog}` (uses metastore default location; no extra S3)…")
    print("If this cell sits more than ~60s, cancel it and run CREATE CATALOG in a SQL warehouse.")
    print("A hang usually means the metastore has no default managed storage (account admin).")
    spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}` COMMENT 'ONR ITSS POC'")
    print("CREATE CATALOG finished")

for sch, cmt in [
    ("bronze", "Raw ingested files"),
    ("silver", "Cleansed validated"),
    ("gold", "Business aggregates"),
    ("app", "Quality, lineage, audit"),
]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{sch}` COMMENT '{cmt}'")
    print("schema", sch)

spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`bronze`.landing")
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`bronze`.checkpoints")
print("UC objects ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Load fixture → bronze

# COMMAND ----------

import json
from datetime import datetime
from pyspark.sql import functions as F
from pyspark.sql.types import *

fixture_path = f"{repo_root}/resources/mock_data/grants_portfolio.json"
payload = None
candidates = [
    fixture_path,
    fixture_path.replace("/Workspace", "/Workspace"),
    "/Workspace" + fixture_path if not fixture_path.startswith("/Workspace") else fixture_path,
]
for p in candidates:
    try:
        with open(p, "r", encoding="utf-8") as f:
            payload = json.load(f)
            print(f"Loaded fixture from {p}")
            break
    except Exception:
        pass

if payload is None:
    raise FileNotFoundError(
        f"Could not open {fixture_path}. Set repo_root to the cloned onr_demo folder "
        "(example /Workspace/Users/you@org/onr_demo)."
    )

grants = payload["grants"]
print(f"Fixture grants: {len(grants)}  contract={payload.get('fixture_contract')}")

grants_schema = StructType([
    StructField("grant_no", StringType(), False),
    StructField("title", StringType(), True),
    StructField("abstract", StringType(), True),
    StructField("program_area", StringType(), True),
    StructField("fiscal_year", IntegerType(), True),
    StructField("amount_usd", DoubleType(), True),
    StructField("awardee", StringType(), True),
    StructField("org_unit", StringType(), True),
    StructField("classification_band", StringType(), True),
    StructField("batch_id", StringType(), True),
    StructField("created_at", StringType(), True),
])
# Normalize types so Spark does not fail schema inference
norm_grants = []
for rec in grants:
    row = dict(rec)
    row["fiscal_year"] = int(row["fiscal_year"]) if row.get("fiscal_year") is not None else None
    row["amount_usd"] = float(row["amount_usd"]) if row.get("amount_usd") is not None else None
    row["created_at"] = str(row["created_at"]) if row.get("created_at") is not None else None
    norm_grants.append(row)

grants_df = spark.createDataFrame(norm_grants, schema=grants_schema) \
    .withColumn("_ingest_time", F.current_timestamp()) \
    .withColumn("_source_file", F.lit("grants_portfolio.json")) \
    .withColumn("_batch_id", F.lit(payload.get("batch_id", "seed-initial-2026")))

grants_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`bronze`.grants")

# Derive ERP (same rules as generate_mock_data.py)
import random
FIN_CATS = ["Personnel", "Equipment", "Travel", "Contractors", "Supplies", "Training", "Facilities", "Other Direct Costs"]
rng = random.Random(20260810)
fin_rows = []
txn = 0
for rec in grants:
    amount = float(rec.get("amount_usd") or 0)
    if amount <= 0:
        continue
    weights = [rng.random() for _ in range(3)]
    tw = sum(weights) or 1
    remaining = amount
    for i, w in enumerate(weights):
        share = amount * (w / tw) if i < 2 else remaining
        remaining -= share if i < 2 else 0
        rate = rng.uniform(0.72, 1.08)
        budget = round(share, 2)
        actual = round(budget * rate, 2)
        fy = int(rec.get("fiscal_year") or 2025)
        txn += 1
        fin_rows.append({
            "transaction_id": f"FIN-{100000 + txn}",
            "grant_no": rec["grant_no"],
            "cost_center": rec.get("org_unit"),
            "program_area": rec.get("program_area"),
            "category": rng.choice(FIN_CATS),
            "fiscal_year": fy,
            "quarter": rng.choice(["Q1", "Q2", "Q3", "Q4"]),
            "budget_allocated": budget,
            "actual_expenditure": actual,
            "execution_rate": round(rate * 100, 1),
            "variance": round(budget - actual, 2),
            "status": "Closed" if fy < 2026 else "Open",
            "batch_id": rec.get("batch_id") or "seed-initial-2026",
        })

fin_schema = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("grant_no", StringType(), True),
    StructField("cost_center", StringType(), True),
    StructField("program_area", StringType(), True),
    StructField("category", StringType(), True),
    StructField("fiscal_year", IntegerType(), True),
    StructField("quarter", StringType(), True),
    StructField("budget_allocated", DoubleType(), True),
    StructField("actual_expenditure", DoubleType(), True),
    StructField("execution_rate", DoubleType(), True),
    StructField("variance", DoubleType(), True),
    StructField("status", StringType(), True),
    StructField("batch_id", StringType(), True),
])
fin_df = spark.createDataFrame(fin_rows, schema=fin_schema) \
    .withColumn("_ingest_time", F.current_timestamp()) \
    .withColumn("_source_file", F.lit("derived_erp")) \
    .withColumn("_batch_id", F.lit("seed-initial-2026"))
fin_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`bronze`.financial")

print(f"bronze.grants={grants_df.count():,}  bronze.financial={fin_df.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Bronze → silver (quality)

# COMMAND ----------

from pyspark.sql.window import Window

bg = spark.table(f"`{catalog}`.`bronze`.grants")
sg = (
    bg.withColumn("grant_no", F.trim("grant_no"))
      .withColumn("title", F.trim("title"))
      .withColumn("awardee", F.trim("awardee"))
      .withColumn("amount_usd", F.col("amount_usd").cast("double"))
      .withColumn("fiscal_year", F.col("fiscal_year").cast("int"))
      .withColumn("created_at", F.to_timestamp("created_at"))
      .withColumn("_is_active", F.lit(True))
      .withColumn("_quality_score", F.when(F.col("amount_usd") > 0, 1.0).otherwise(0.5))
      .withColumn("_rn", F.row_number().over(Window.partitionBy("grant_no").orderBy(F.col("_ingest_time").desc())))
      .filter("_rn = 1").drop("_rn")
      .filter(F.col("grant_no").isNotNull() & (F.trim(F.col("grant_no")) != "") & (F.col("amount_usd") > 0) & F.col("awardee").isNotNull())
)
sg.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`silver`.grants")

bf = spark.table(f"`{catalog}`.`bronze`.financial")
sf = (
    bf.withColumn("transaction_id", F.trim("transaction_id"))
      .withColumn("budget_allocated", F.col("budget_allocated").cast("double"))
      .withColumn("actual_expenditure", F.col("actual_expenditure").cast("double"))
      .withColumn("execution_rate", F.when(F.col("budget_allocated") > 0, F.col("actual_expenditure") / F.col("budget_allocated") * 100).otherwise(0))
      .withColumn("variance", F.col("budget_allocated") - F.col("actual_expenditure"))
      .withColumn("_is_active", F.lit(True))
      .withColumn("_quality_score", F.lit(1.0))
      .withColumn("_rn", F.row_number().over(Window.partitionBy("transaction_id").orderBy(F.col("_ingest_time").desc())))
      .filter("_rn = 1").drop("_rn")
      .filter(F.col("transaction_id").isNotNull() & (F.col("budget_allocated") > 0))
)
sf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`silver`.financial")
print(f"silver.grants={sg.count():,}  silver.financial={sf.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Silver → gold + quality log

# COMMAND ----------

g = spark.table(f"`{catalog}`.`silver`.grants").filter("_is_active")
f = spark.table(f"`{catalog}`.`silver`.financial").filter("_is_active")

g.groupBy("program_area", "fiscal_year").agg(
    F.count("*").alias("grant_count"),
    F.sum("amount_usd").alias("total_funding"),
    F.avg("amount_usd").alias("avg_award"),
    F.min("amount_usd").alias("min_award"),
    F.max("amount_usd").alias("max_award"),
    F.sum(F.when(F.col("classification_band") == "CUI-Mock", 1).otherwise(0)).alias("cui_mock_count"),
    F.sum(F.when(F.col("classification_band") == "Public-Mock", 1).otherwise(0)).alias("public_mock_count"),
).withColumn("_updated_at", F.current_timestamp()) \
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.grants_summary")

f.groupBy("cost_center", "category", "fiscal_year", "quarter").agg(
    F.sum("budget_allocated").alias("total_budget"),
    F.sum("actual_expenditure").alias("total_actual"),
    F.count("*").alias("transaction_count"),
).withColumn("overall_execution_rate", F.round(F.col("total_actual") / F.col("total_budget") * 100, 2)) \
 .withColumn("variance_amount", F.col("total_budget") - F.col("total_actual")) \
 .withColumn("_updated_at", F.current_timestamp()) \
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.financial_summary")

g.groupBy("awardee", "org_unit").agg(
    F.count("*").alias("grant_count"),
    F.sum("amount_usd").alias("total_funding"),
    F.collect_set("program_area").alias("program_areas"),
    F.max("created_at").alias("latest_grant_date"),
).withColumn("_updated_at", F.current_timestamp()) \
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.grants_by_awardee")

f.groupBy("fiscal_year", "quarter", "category").agg(
    F.sum("budget_allocated").alias("budget_plan"),
    F.sum("actual_expenditure").alias("actual_spend"),
).withColumn("execution_rate", F.round(F.col("actual_spend") / F.col("budget_plan") * 100, 2)) \
 .withColumn("variance", F.col("budget_plan") - F.col("actual_spend")) \
 .withColumn("variance_pct", F.round(F.col("variance") / F.col("budget_plan") * 100, 2)) \
 .withColumn("status", F.when(F.col("execution_rate") >= 90, "ON_TARGET").when(F.col("execution_rate") >= 80, "WARNING").otherwise("AT_RISK")) \
 .withColumn("_updated_at", F.current_timestamp()) \
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.budget_execution")

spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.grant_predictions AS
SELECT grant_no, title, program_area, amount_usd, awardee,
       ROUND(LEAST(0.95, GREATEST(0.35,
           0.42
           + CASE WHEN amount_usd >= 2000000 THEN 0.22
                  WHEN amount_usd >= 1000000 THEN 0.15
                  WHEN amount_usd >= 500000 THEN 0.08 ELSE 0.0 END
           + CASE WHEN program_area IN ('AI/ML','Quantum','Autonomy') THEN 0.12
                  WHEN program_area IN ('Cyber','Undersea') THEN 0.08 ELSE 0.04 END
           + CASE WHEN fiscal_year >= 2025 THEN 0.06 ELSE 0.0 END
       )), 4) AS success_probability,
       CASE WHEN amount_usd >= 2000000 THEN 'Large award concentration'
            WHEN classification_band = 'CUI-Mock' THEN 'CUI-Mock handling'
            ELSE 'Standard portfolio risk' END AS risk_factors,
       CASE WHEN amount_usd >= 1000000 THEN 'Fund'
            WHEN amount_usd >= 400000 THEN 'Review'
            ELSE 'Defer' END AS recommendation,
       'heuristic_v1' AS model_name,
       current_timestamp() AS scored_at
FROM `{catalog}`.`silver`.grants WHERE _is_active = true
""")
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.model_metrics AS
SELECT 'heuristic_v1' AS model_name, 'rows_scored' AS metric_name,
       CAST(COUNT(*) AS DOUBLE) AS metric_value, CAST(COUNT(*) AS INT) AS n_rows,
       current_timestamp() AS trained_at
FROM `{catalog}`.`gold`.grant_predictions
""")

qlog = spark.createDataFrame([{
    "check_id": "boot-001",
    "check_name": "bootstrap_load",
    "check_status": "PASS",
    "records_checked": sg.count() + sf.count(),
    "records_passed": sg.count() + sf.count(),
    "records_failed": 0,
    "check_timestamp": datetime.utcnow(),
    "pipeline_name": "00_bootstrap",
}])
qlog.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`app`.ingestion_quality_log")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.quarantine_log (
    event_id STRING NOT NULL,
    grant_no STRING,
    title STRING,
    abstract STRING,
    program_area STRING,
    fiscal_year INT,
    amount_usd DOUBLE,
    awardee STRING,
    org_unit STRING,
    classification_band STRING,
    batch_id STRING,
    reason_code STRING,
    reason_detail STRING,
    source_file STRING,
    pipeline_name STRING,
    quarantined_at TIMESTAMP
) USING DELTA
COMMENT 'Quarantined grants — never landed in bronze'
""")
spark.sql(f"DELETE FROM `{catalog}`.`app`.quarantine_log")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.quality_findings (
    finding_id STRING NOT NULL,
    grant_no STRING,
    title STRING,
    program_area STRING,
    amount_usd DOUBLE,
    severity STRING,
    check_name STRING,
    detail STRING,
    published BOOLEAN,
    source_file STRING,
    pipeline_name STRING,
    found_at TIMESTAMP
) USING DELTA
COMMENT 'WARN findings on rows that still published'
""")
spark.sql(f"DELETE FROM `{catalog}`.`app`.quality_findings")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.hold_queue (
    hold_id STRING NOT NULL,
    grant_no STRING,
    title STRING,
    amount_usd DOUBLE,
    reason_code STRING,
    detail STRING,
    source_file STRING,
    held_at TIMESTAMP
) USING DELTA
""")
spark.sql(f"DELETE FROM `{catalog}`.`app`.hold_queue")

# App audit / quality tables so Process / Export / Search work on a fresh workspace
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.export_history (
    export_id STRING NOT NULL,
    user_email STRING,
    dataset_name STRING,
    format STRING,
    record_count INT,
    file_size_bytes BIGINT,
    created_at TIMESTAMP
) USING DELTA
COMMENT 'Export audit trail'
""")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.search_history (
    search_id STRING NOT NULL,
    user_email STRING,
    search_type STRING,
    search_params STRING,
    results_count INT,
    execution_time_ms INT,
    created_at TIMESTAMP
) USING DELTA
COMMENT 'Search history for audit and replay'
""")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.lineage_tracking (
    lineage_id STRING NOT NULL,
    source_table STRING,
    target_table STRING,
    transformation_type STRING,
    records_processed INT,
    processing_time_ms INT,
    executed_at TIMESTAMP,
    executed_by STRING
) USING DELTA
COMMENT 'Lineage tracking records'
""")

# Same quality math as notebooks/02_silver_quality.py so Governance is populated
# without requiring a separate notebook 02 run.
_gt = max(sg.count(), 1)
_ft = max(sf.count(), 1)
_g_id = sg.filter("grant_no IS NOT NULL").count()
_g_aw = sg.filter("awardee IS NOT NULL").count()
_g_amt = sg.filter("amount_usd > 0").count()
_g_area = sg.filter("program_area IS NOT NULL").count()
_f_id = sf.filter("transaction_id IS NOT NULL").count()
_f_bud = sf.filter("budget_allocated > 0").count()
_f_act = sf.filter("actual_expenditure >= 0").count()
quality_scores = spark.createDataFrame([
    ("silver.grants",
     (_g_id / _gt) * 0.3 + (_g_aw / _gt) * 0.3 + (_g_amt / _gt) * 0.2 + (_g_area / _gt) * 0.2,
     _g_id / _gt, _g_amt / _gt, _g_aw / _gt, 1.0),
    ("silver.financial",
     (_f_id / _ft) * 0.4 + (_f_bud / _ft) * 0.3 + (_f_act / _ft) * 0.3,
     _f_id / _ft, _f_bud / _ft, _f_act / _ft, 1.0),
], ["table_name", "quality_score", "completeness", "accuracy", "consistency", "timeliness"])
quality_scores = quality_scores.withColumn("last_assessed", F.current_timestamp())
quality_scores.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`app`.data_quality_scores"
)

# OLS FY forecast + trend IDs (same SQL as notebook 03 / app refresh)
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_forecast AS
WITH hist AS (
    SELECT program_area, CAST(fiscal_year AS DOUBLE) AS fy,
           CAST(SUM(total_funding) AS DOUBLE) AS funding
    FROM `{catalog}`.`gold`.grants_summary GROUP BY program_area, fiscal_year
),
stats AS (
    SELECT program_area, COUNT(*) n, SUM(fy) sx, SUM(funding) sy,
           SUM(fy*funding) sxy, SUM(fy*fy) sx2, MAX(fy) last_fy
    FROM hist GROUP BY program_area
),
fit AS (
    SELECT program_area, n, last_fy, sx, sy,
           CASE WHEN (n*sx2 - sx*sx)=0 THEN 0.0 ELSE (n*sxy - sx*sy)/(n*sx2 - sx*sx) END slope
    FROM stats
),
fit2 AS (SELECT *, (sy - slope*sx)/NULLIF(n,0) intercept FROM fit),
resid AS (
    SELECT h.program_area, STDDEV_POP(h.funding - (f.intercept + f.slope*h.fy)) resid_sd
    FROM hist h JOIN fit2 f ON h.program_area=f.program_area GROUP BY h.program_area
),
actuals AS (
    SELECT h.program_area, CAST(h.fy AS INT) fiscal_year, 'actual' series,
           h.funding predicted_funding, h.funding lower_95, h.funding upper_95,
           f.slope slope_usd_per_year, f.intercept intercept_usd,
           COALESCE(r.resid_sd,0.0) resid_sd, 'ols_fy_v1' model_name
    FROM hist h JOIN fit2 f ON h.program_area=f.program_area
    LEFT JOIN resid r ON r.program_area=h.program_area
),
horizon AS (
    SELECT f.program_area, CAST(f.last_fy AS INT)+off fiscal_year,
           f.slope, f.intercept, COALESCE(r.resid_sd,0.0) resid_sd
    FROM fit2 f LEFT JOIN resid r ON r.program_area=f.program_area
    LATERAL VIEW EXPLODE(ARRAY(1,2)) t AS off
)
SELECT * FROM actuals
UNION ALL
SELECT program_area, fiscal_year, 'forecast',
       intercept+slope*fiscal_year, (intercept+slope*fiscal_year)-1.96*resid_sd,
       (intercept+slope*fiscal_year)+1.96*resid_sd, slope, intercept, resid_sd, 'ols_fy_v1'
FROM horizon
""")
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.program_trends AS
WITH last2 AS (
    SELECT program_area, fiscal_year, SUM(total_funding) funding,
           ROW_NUMBER() OVER (PARTITION BY program_area ORDER BY fiscal_year DESC) rn
    FROM `{catalog}`.`gold`.grants_summary GROUP BY program_area, fiscal_year
),
vel AS (
    SELECT a.program_area, a.funding last_actual, b.funding prior_actual,
           CASE WHEN b.funding IS NULL OR b.funding=0 THEN NULL
                ELSE (a.funding-b.funding)/b.funding END velocity_yoy
    FROM last2 a LEFT JOIN last2 b ON a.program_area=b.program_area AND b.rn=2
    WHERE a.rn=1
),
next_fy AS (
    SELECT program_area, predicted_funding, slope_usd_per_year, resid_sd, fiscal_year
    FROM `{catalog}`.`gold`.funding_forecast WHERE series='forecast'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY program_area ORDER BY fiscal_year)=1
)
SELECT n.program_area,
       CASE WHEN n.slope_usd_per_year/NULLIF(v.last_actual,0)>0.05 THEN 'TREND-ACCEL'
            WHEN n.slope_usd_per_year/NULLIF(v.last_actual,0)<-0.05 THEN 'TREND-DECLINE'
            ELSE 'TREND-STEADY' END trend_id,
       CASE WHEN n.slope_usd_per_year/NULLIF(v.last_actual,0)>0.05 THEN 'Accelerating'
            WHEN n.slope_usd_per_year/NULLIF(v.last_actual,0)<-0.05 THEN 'Declining'
            ELSE 'Steady' END trend_label,
       n.slope_usd_per_year, v.velocity_yoy, v.last_actual,
       n.predicted_funding forecast_next_fy, n.resid_sd,
       n.fiscal_year next_fiscal_year, 'ols_fy_v1' model_name, current_timestamp() computed_at
FROM next_fy n JOIN vel v ON n.program_area=v.program_area
""")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.daily_briefs (
    brief_id STRING NOT NULL, generated_at TIMESTAMP, generated_by STRING,
    source STRING, model_name STRING, brief_text STRING, prompt_chars INT
) USING DELTA
""")

spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_features AS
WITH fin AS (
    SELECT grant_no, SUM(actual_expenditure)/NULLIF(SUM(budget_allocated),0) execution_rate
    FROM `{catalog}`.`silver`.financial WHERE _is_active GROUP BY grant_no
),
area_stats AS (
    SELECT program_area, fiscal_year, approx_percentile(amount_usd, 0.5) median_amt, AVG(amount_usd) avg_amt
    FROM `{catalog}`.`silver`.grants WHERE _is_active GROUP BY program_area, fiscal_year
),
prior AS (SELECT program_area, fiscal_year+1 fiscal_year, avg_amt prior_avg FROM area_stats),
base AS (
    SELECT g.grant_no, g.title, g.program_area, g.fiscal_year, g.amount_usd award_amount,
           g.awardee, g.org_unit, g.classification_band,
           COALESCE(f.execution_rate, 0.90) execution_rate,
           g.amount_usd/NULLIF(COALESCE(p.prior_avg, a.avg_amt),0) yoy_growth_ratio,
           g.amount_usd/NULLIF(a.median_amt,0) amount_vs_area_median
    FROM `{catalog}`.`silver`.grants g
    LEFT JOIN fin f ON f.grant_no=g.grant_no
    LEFT JOIN area_stats a ON a.program_area=g.program_area AND a.fiscal_year=g.fiscal_year
    LEFT JOIN prior p ON p.program_area=g.program_area AND p.fiscal_year=g.fiscal_year
    WHERE g._is_active
)
SELECT *, CASE WHEN execution_rate<0.76 THEN 'execution_collapse'
              WHEN award_amount>=3000000 AND amount_vs_area_median>=1.8 THEN 'budget_spike'
              WHEN award_amount>=2500000 AND execution_rate<0.85 THEN 'low_return_concentration'
              ELSE 'none' END anomaly_type,
       CASE WHEN execution_rate<0.76 OR (award_amount>=3000000 AND amount_vs_area_median>=1.8)
              OR (award_amount>=2500000 AND execution_rate<0.85) THEN 1 ELSE 0 END is_known_anomaly,
       current_timestamp() _updated_at
FROM base
""")
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.grant_anomaly_scores AS
SELECT grant_no, title, program_area, fiscal_year, award_amount amount_usd, awardee,
       execution_rate, yoy_growth_ratio, amount_vs_area_median,
       CASE anomaly_type WHEN 'execution_collapse' THEN 0.92 WHEN 'budget_spike' THEN 0.88
            WHEN 'low_return_concentration' THEN 0.80 ELSE 0.12 END anomaly_score,
       CAST(is_known_anomaly AS BOOLEAN) is_flagged, anomaly_type predicted_type,
       anomaly_type, is_known_anomaly, 'heuristic_rules_v1' model_name, current_timestamp() scored_at
FROM `{catalog}`.`gold`.funding_features
""")

print("gold + app quality log + audit tables + quality scores + forecast + anomaly features written")
print("grants_summary", spark.table(f"`{catalog}`.`gold`.grants_summary").count())
print("funding_forecast", spark.table(f"`{catalog}`.`gold`.funding_forecast").count())
print("grant_anomaly_scores", spark.table(f"`{catalog}`.`gold`.grant_anomaly_scores").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Stage live-demo files (do **not** ingest yet)

# COMMAND ----------

for d in [f"{landing}/grants", f"{landing}/financial", staged]:
    dbutils.fs.mkdirs(d)

# Copy seed CSV + live batch + quality-fail batch into _staged
for name in ["sample_grants.csv", "sample_financial.csv", "batch_live_grants.csv", "batch_quality_fail.csv"]:
    src = f"{repo_root}/resources/mock_data/{name}"
    dst = f"{staged}/{name}"
    try:
        dbutils.fs.cp(f"file:{src}", dst, True)
        print("staged", dst)
    except Exception as e:
        # Workspace Git folders are often readable via open()
        try:
            dbutils.fs.put(dst, open(src, "r", encoding="utf-8").read(), overwrite=True)
            print("staged via put", dst)
        except Exception as e2:
            print("SKIP", name, e2)

print(
    f"""
DEMO READY
  silver.grants     = {spark.table(f'`{catalog}`.`silver`.grants').count():,}
  silver.financial  = {spark.table(f'`{catalog}`.`silver`.financial').count():,}

Live ingest (Element 3):
  1. Copy {staged}/batch_live_grants.csv  →  {landing}/grants/
  2. Run notebooks/01_bronze_ingestion.py  (Auto Loader, availableNow)
  3. Run 02_silver_quality.py then 03_gold_aggregation.py
  4. Refresh the Streamlit app — count goes 400 → 408
"""
)
