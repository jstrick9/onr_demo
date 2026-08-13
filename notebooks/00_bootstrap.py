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

spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}` COMMENT 'ONR ITSS POC'")
for sch, cmt in [
    ("bronze", "Raw ingested files"),
    ("silver", "Cleansed validated"),
    ("gold", "Business aggregates"),
    ("app", "Quality, lineage, audit"),
]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{sch}` COMMENT '{cmt}'")

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

print("gold + app quality log written")
print("grants_summary", spark.table(f"`{catalog}`.`gold`.grants_summary").count())

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
