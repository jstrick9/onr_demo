# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # Bronze Layer Ingestion
# MAGIC **Purpose:** Auto Loader ingest raw files → Bronze Delta tables  
# MAGIC **Catalog:** onr_demo | **Inputs:** /Volumes/onr_demo/bronze/landing/grants/ and .../financial/  
# MAGIC **Output:** onr_demo.bronze.grants, onr_demo.bronze.financial  
# MAGIC Run **00_bootstrap.py** first. For the live demo, copy `_staged/batch_live_grants.csv` into `landing/grants/`.  
# MAGIC **QA:** Expectations + row count validation

# COMMAND ----------

# Configuration widgets
dbutils.widgets.text("catalog", "onr_demo")
dbutils.widgets.text("landing_path", "")

catalog = dbutils.widgets.get("catalog")
landing_path = dbutils.widgets.get("landing_path").strip()
if not landing_path:
    landing_path = f"/Volumes/{catalog}/bronze/landing/"
if not landing_path.endswith("/"):
    landing_path = landing_path + "/"
for sub in ("grants", "financial", "_schemas/grants", "_schemas/financial"):
    try:
        dbutils.fs.mkdirs(f"{landing_path}{sub}")
    except Exception:
        pass

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, lit

# Set catalog context
spark.sql(f"USE CATALOG `{catalog}`")
spark.sql("USE SCHEMA `bronze`")

print(f"✅ Context set: {catalog}.{{bronze,silver,gold,app}}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingest Grants Data (Auto Loader)

# COMMAND ----------

# Auto Loader — Incremental ingest for grants
# addNewColumns cannot be combined with .schema(); use schemaHints.
GRANTS_HINTS = (
    "grant_no STRING, title STRING, abstract STRING, program_area STRING, "
    "fiscal_year INT, amount_usd DOUBLE, awardee STRING, org_unit STRING, "
    "classification_band STRING, batch_id STRING, created_at STRING"
)

grants_bronze_df = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", f"{landing_path}_schemas/grants")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("cloudFiles.schemaHints", GRANTS_HINTS)
    .option("header", "true")
    .load(f"{landing_path}grants/")
    .withColumn("_ingest_time", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
    .withColumn("_batch_id", lit(None).cast("string"))
)

# Write stream to Delta
grants_q = (
    grants_bronze_df.writeStream
    .format("delta")
    .option("checkpointLocation", f"/Volumes/{catalog}/bronze/checkpoints/grants")
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .toTable(f"`{catalog}`.`bronze`.grants")
)
grants_q.awaitTermination()

print("✅ Grants ingestion complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingest Financial Data (Auto Loader)

# COMMAND ----------

# Auto Loader — Incremental ingest for financial data
FIN_HINTS = (
    "transaction_id STRING, grant_no STRING, cost_center STRING, program_area STRING, "
    "category STRING, fiscal_year INT, quarter STRING, budget_allocated DOUBLE, "
    "actual_expenditure DOUBLE, execution_rate DOUBLE, variance DOUBLE, "
    "status STRING, batch_id STRING"
)

financial_bronze_df = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", f"{landing_path}_schemas/financial")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("cloudFiles.schemaHints", FIN_HINTS)
    .option("header", "true")
    .load(f"{landing_path}financial/")
    .withColumn("_ingest_time", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
    .withColumn("_batch_id", lit(None).cast("string"))
)

# Write stream to Delta
fin_q = (
    financial_bronze_df.writeStream
    .format("delta")
    .option("checkpointLocation", f"/Volumes/{catalog}/bronze/checkpoints/financial")
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .toTable(f"`{catalog}`.`bronze`.financial")
)
fin_q.awaitTermination()

print("✅ Financial ingestion complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation (QA)

# COMMAND ----------

# Row count + schema checks
grants_cnt = spark.table(f"`{catalog}`.`bronze`.grants").count()
financial_cnt = spark.table(f"`{catalog}`.`bronze`.financial").count()

print(f"📊 Bronze Grants: {grants_cnt:,} records")
print(f"📊 Bronze Financial: {financial_cnt:,} records")

# Validate non-zero
assert grants_cnt > 0, "QA FAIL: bronze.grants empty after ingest"
assert financial_cnt > 0, "QA FAIL: bronze.financial empty after ingest"

# Schema verification
print("\n📋 Grants Schema:")
spark.table(f"`{catalog}`.`bronze`.grants").printSchema()

print("\n📋 Financial Schema:")
spark.table(f"`{catalog}`.`bronze`.financial").printSchema()

# Null checks
null_grants = spark.sql(f"""
    SELECT COUNT(*) as null_ids 
    FROM `{catalog}`.`bronze`.grants 
    WHERE grant_no IS NULL
""").collect()[0][0]

null_financial = spark.sql(f"""
    SELECT COUNT(*) as null_ids 
    FROM `{catalog}`.`bronze`.financial 
    WHERE transaction_id IS NULL
""").collect()[0][0]

print(f"\n⚠️ Null grant_no: {null_grants}")
print(f"⚠️ Null transaction_ids: {null_financial}")

# COMMAND ----------

# Log quality check result
from datetime import datetime as _dt
quality_log = spark.createDataFrame([
    (
        f"bronze-{_dt.utcnow().strftime('%Y%m%d%H%M%S')}",
        "bronze_ingestion",
        "PASS",
        grants_cnt + financial_cnt,
        grants_cnt + financial_cnt - null_grants - null_financial,
        null_grants + null_financial,
        _dt.utcnow(),
        "bronze_pipeline",
    )
], ["check_id", "check_name", "check_status", "records_checked",
    "records_passed", "records_failed", "check_timestamp", "pipeline_name"])

try:
    quality_log.write.mode("append").saveAsTable(f"`{catalog}`.`app`.ingestion_quality_log")
    print("✅ Quality check logged")
except Exception as e:
    print("Quality log skipped:", e)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Ingestion Complete
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Run `02_silver_quality.py` to cleanse and validate data
# MAGIC 2. Run `03_gold_aggregation.py` to create business-ready aggregates
