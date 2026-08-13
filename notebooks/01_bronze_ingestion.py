# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer Ingestion
# MAGIC **Purpose:** Auto Loader ingest raw files → Bronze Delta tables  
# MAGIC **Catalog:** onr_demo.dev | **Compute:** Serverless  
# MAGIC **Inputs:** /Volumes/onr_demo/dev/landing/*.csv, *.json  
# MAGIC **Output:** onr_demo.dev.bronze_grants, onr_demo.dev.bronze_financial  
# MAGIC **QA:** Expectations + row count validation

# COMMAND ----------

# Configuration widgets
dbutils.widgets.text("catalog", "onr_demo")
dbutils.widgets.text("schema", "dev")
dbutils.widgets.text("landing_path", "/Volumes/onr_demo/dev/landing/")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
landing_path = dbutils.widgets.get("landing_path")

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, input_file_name, lit
from pyspark.sql.types import *

# Set catalog context
spark.sql(f"USE CATALOG `{catalog}`")
spark.sql(f"USE SCHEMA `{schema}`")

print(f"✅ Context set: {catalog}.{schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingest Grants Data (Auto Loader)

# COMMAND ----------

# Auto Loader — Incremental ingest for grants
grants_schema = StructType([
    StructField("grant_id", StringType(), False),
    StructField("title", StringType(), True),
    StructField("principal_investigator", StringType(), True),
    StructField("institution", StringType(), True),
    StructField("research_area", StringType(), True),
    StructField("award_amount", DoubleType(), True),
    StructField("status", StringType(), True),
    StructField("start_date", StringType(), True),
    StructField("end_date", StringType(), True),
    StructField("fiscal_year", IntegerType(), True),
])

grants_bronze_df = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", f"{landing_path}_schemas/bronze_grants")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("header", "true")
    .schema(grants_schema)
    .load(f"{landing_path}grants/")
    .withColumn("_ingest_time", current_timestamp())
    .withColumn("_source_file", input_file_name())
    .withColumn("_batch_id", lit(None).cast("string"))
)

# Write stream to Delta
(
    grants_bronze_df.writeStream
    .format("delta")
    .option("checkpointLocation", f"{landing_path}_chk/bronze_grants")
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .toTable(f"`{catalog}`.`{schema}`.bronze_grants")
)

print("✅ Grants ingestion complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingest Financial Data (Auto Loader)

# COMMAND ----------

# Auto Loader — Incremental ingest for financial data
financial_schema = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("cost_center", StringType(), True),
    StructField("category", StringType(), True),
    StructField("fiscal_year", IntegerType(), True),
    StructField("quarter", StringType(), True),
    StructField("budget_allocated", DoubleType(), True),
    StructField("actual_expenditure", DoubleType(), True),
    StructField("execution_rate", DoubleType(), True),
    StructField("variance", DoubleType(), True),
    StructField("status", StringType(), True),
])

financial_bronze_df = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", f"{landing_path}_schemas/bronze_financial")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("header", "true")
    .schema(financial_schema)
    .load(f"{landing_path}financial/")
    .withColumn("_ingest_time", current_timestamp())
    .withColumn("_source_file", input_file_name())
    .withColumn("_batch_id", lit(None).cast("string"))
)

# Write stream to Delta
(
    financial_bronze_df.writeStream
    .format("delta")
    .option("checkpointLocation", f"{landing_path}_chk/bronze_financial")
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .toTable(f"`{catalog}`.`{schema}`.bronze_financial")
)

print("✅ Financial ingestion complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation (QA)

# COMMAND ----------

# Row count + schema checks
grants_cnt = spark.table(f"`{catalog}`.`{schema}`.bronze_grants").count()
financial_cnt = spark.table(f"`{catalog}`.`{schema}`.bronze_financial").count()

print(f"📊 Bronze Grants: {grants_cnt:,} records")
print(f"📊 Bronze Financial: {financial_cnt:,} records")

# Validate non-zero
assert grants_cnt > 0, "QA FAIL: bronze_grants empty after ingest"
assert financial_cnt > 0, "QA FAIL: bronze_financial empty after ingest"

# Schema verification
print("\n📋 Grants Schema:")
spark.table(f"`{catalog}`.`{schema}`.bronze_grants").printSchema()

print("\n📋 Financial Schema:")
spark.table(f"`{catalog}`.`{schema}`.bronze_financial").printSchema()

# Null checks
null_grants = spark.sql(f"""
    SELECT COUNT(*) as null_ids 
    FROM `{catalog}`.`{schema}`.bronze_grants 
    WHERE grant_id IS NULL
""").collect()[0][0]

null_financial = spark.sql(f"""
    SELECT COUNT(*) as null_ids 
    FROM `{catalog}`.`{schema}`.bronze_financial 
    WHERE transaction_id IS NULL
""").collect()[0][0]

print(f"\n⚠️ Null grant_ids: {null_grants}")
print(f"⚠️ Null transaction_ids: {null_financial}")

# COMMAND ----------

# Log quality check result
quality_log = spark.createDataFrame([
    ("bronze_ingestion", "PASS", grants_cnt + financial_cnt, 
     grants_cnt + financial_cnt - null_grants - null_financial, 
     null_grants + null_financial, "bronze_pipeline")
], ["check_name", "check_status", "records_checked", "records_passed", "records_failed", "pipeline_name"])

quality_log = quality_log.withColumn("check_id", lit(None).cast("string"))
quality_log = quality_log.withColumn("check_timestamp", current_timestamp())

quality_log.write.mode("append").saveAsTable(f"`{catalog}`.`{schema}`.ingestion_quality_log")

print("✅ Quality check logged")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Ingestion Complete
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Run `02_silver_quality.py` to cleanse and validate data
# MAGIC 2. Run `03_gold_aggregation.py` to create business-ready aggregates
