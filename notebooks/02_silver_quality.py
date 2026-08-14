# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # Silver Layer Quality Transforms
# MAGIC **Purpose:** Cleanse, deduplicate, and validate bronze data → Silver Delta tables  
# MAGIC **Catalog:** onr_demo.bronze / silver / gold / app | **Compute:** Serverless  
# MAGIC **Input:** onr_demo.bronze.grants, onr_demo.bronze.financial  
# MAGIC **Output:** onr_demo.silver.grants, onr_demo.silver.financial  
# MAGIC **QA:** Quality constraints + row count validation

# COMMAND ----------

# Configuration widgets
dbutils.widgets.text("catalog", "onr_demo")

catalog = dbutils.widgets.get("catalog")

# Set catalog context
spark.sql(f"USE CATALOG `{catalog}`")
spark.sql("USE SCHEMA `bronze`")

print(f"✅ Context set: {catalog}.{{bronze,silver,gold,app}}")

# COMMAND ----------

from pyspark.sql.functions import (
    col, current_timestamp, to_date, when, lit, 
    trim, upper, lower, coalesce, count, sum as spark_sum
)
from pyspark.sql.window import Window
import pyspark.sql.functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## Grants: Bronze → Silver

# COMMAND ----------

# Read bronze grants
bronze_grants = spark.table(f"`{catalog}`.`bronze`.grants")

# Cleanse and transform
silver_grants = (
    bronze_grants
    # Trim whitespace
    .withColumn("grant_no", trim(col("grant_no")))
    .withColumn("title", trim(col("title")))
    .withColumn("abstract", trim(col("abstract")))
    .withColumn("program_area", trim(col("program_area")))
    .withColumn("awardee", trim(col("awardee")))
    .withColumn("org_unit", trim(col("org_unit")))
    .withColumn("classification_band", trim(col("classification_band")))
    
    # Type casting
    .withColumn("amount_usd", col("amount_usd").cast("double"))
    .withColumn("fiscal_year", col("fiscal_year").cast("int"))
    .withColumn("created_at", F.to_timestamp(col("created_at")))
    
    # Add metadata
    .withColumn("_is_active", lit(True))
    .withColumn("_quality_score", 
        when(col("amount_usd").isNotNull() & (col("amount_usd") > 0), 1.0)
        .otherwise(0.5)
    )
    
    # Remove duplicates (keep latest by ingest time)
    .withColumn("_row_num", 
        F.row_number().over(
            Window.partitionBy("grant_no").orderBy(col("_ingest_time").desc())
        )
    )
    .filter(col("_row_num") == 1)
    .drop("_row_num")
    
    # Apply quality filters
    .filter(col("grant_no").isNotNull())
    .filter(trim(col("grant_no")) != "")
    .filter(col("amount_usd") > 0)
    .filter(col("awardee").isNotNull())
)

# Overwrite silver table
silver_grants.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`silver`.grants"
)

grants_count = silver_grants.count()
print(f"✅ Silver Grants: {grants_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Financial: Bronze → Silver

# COMMAND ----------

# Read bronze financial
bronze_financial = spark.table(f"`{catalog}`.`bronze`.financial")

# Cleanse and transform
silver_financial = (
    bronze_financial
    # Trim whitespace
    .withColumn("transaction_id", trim(col("transaction_id")))
    .withColumn("cost_center", trim(col("cost_center")))
    .withColumn("category", trim(col("category")))
    .withColumn("quarter", upper(trim(col("quarter"))))
    .withColumn("status", upper(trim(col("status"))))
    
    # Type casting
    .withColumn("budget_allocated", col("budget_allocated").cast("double"))
    .withColumn("actual_expenditure", col("actual_expenditure").cast("double"))
    .withColumn("execution_rate", col("execution_rate").cast("double"))
    .withColumn("variance", col("variance").cast("double"))
    .withColumn("fiscal_year", col("fiscal_year").cast("int"))
    
    # Calculate derived fields
    .withColumn("execution_rate", 
        when(col("budget_allocated") > 0, 
             (col("actual_expenditure") / col("budget_allocated")) * 100)
        .otherwise(0)
    )
    .withColumn("variance", col("budget_allocated") - col("actual_expenditure"))
    
    # Add metadata
    .withColumn("_is_active", lit(True))
    .withColumn("_quality_score", 
        when(col("budget_allocated").isNotNull() & (col("budget_allocated") > 0), 1.0)
        .otherwise(0.5)
    )
    
    # Remove duplicates
    .withColumn("_row_num", 
        F.row_number().over(
            Window.partitionBy("transaction_id").orderBy(col("_ingest_time").desc())
        )
    )
    .filter(col("_row_num") == 1)
    .drop("_row_num")
    
    # Apply quality filters
    .filter(col("transaction_id").isNotNull())
    .filter(col("budget_allocated") > 0)
)

# Overwrite silver table
silver_financial.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`silver`.financial"
)

financial_count = silver_financial.count()
print(f"✅ Silver Financial: {financial_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Scoring

# COMMAND ----------

# Calculate quality scores
grants_completeness = spark.sql(f"""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN grant_no IS NOT NULL THEN 1 END) as valid_id,
        COUNT(CASE WHEN awardee IS NOT NULL THEN 1 END) as valid_awardee,
        COUNT(CASE WHEN amount_usd > 0 THEN 1 END) as valid_amount,
        COUNT(CASE WHEN program_area IS NOT NULL THEN 1 END) as valid_area
    FROM `{catalog}`.`silver`.grants
""").collect()[0]

_gt = grants_completeness[0] or 1
grants_score = (
    (grants_completeness[1] / _gt) * 0.3 +
    (grants_completeness[2] / _gt) * 0.3 +
    (grants_completeness[3] / _gt) * 0.2 +
    (grants_completeness[4] / _gt) * 0.2
)

financial_completeness = spark.sql(f"""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN transaction_id IS NOT NULL THEN 1 END) as valid_id,
        COUNT(CASE WHEN budget_allocated > 0 THEN 1 END) as valid_budget,
        COUNT(CASE WHEN actual_expenditure >= 0 THEN 1 END) as valid_actual
    FROM `{catalog}`.`silver`.financial
""").collect()[0]

_ft = financial_completeness[0] or 1
financial_score = (
    (financial_completeness[1] / _ft) * 0.4 +
    (financial_completeness[2] / _ft) * 0.3 +
    (financial_completeness[3] / _ft) * 0.3
)

# Save quality scores
from pyspark.sql.functions import current_timestamp

# Gold-layer scores (same shape as the app SQL path) — skip if gold not built yet
try:
    gold_summary = spark.sql(f"""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN program_area IS NOT NULL THEN 1 END) as valid_area,
               COUNT(CASE WHEN total_funding > 0 THEN 1 END) as valid_funding
        FROM `{catalog}`.`gold`.grants_summary
    """).collect()[0]
    _gst = gold_summary[0] or 1
    gold_summary_score = (gold_summary[1] / _gst) * 0.5 + (gold_summary[2] / _gst) * 0.5
    gold_budget = spark.sql(f"""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN status IS NOT NULL THEN 1 END) as valid_status,
               COUNT(CASE WHEN execution_rate IS NOT NULL THEN 1 END) as valid_rate
        FROM `{catalog}`.`gold`.budget_execution
    """).collect()[0]
    _gbt = gold_budget[0] or 1
    gold_budget_score = (gold_budget[1] / _gbt) * 0.5 + (gold_budget[2] / _gbt) * 0.5
    gold_rows = [
        ("gold.grants_summary", gold_summary_score, gold_summary[1]/_gst,
         gold_summary[2]/_gst, 1.0, 1.0),
        ("gold.budget_execution", gold_budget_score, gold_budget[1]/_gbt,
         gold_budget[2]/_gbt, 1.0, 1.0),
    ]
except Exception:
    gold_rows = []

quality_scores = spark.createDataFrame([
    ("silver.grants", grants_score, grants_completeness[1]/_gt,
     grants_completeness[3]/_gt, grants_completeness[2]/_gt, 1.0),
    ("silver.financial", financial_score, financial_completeness[1]/_ft,
     financial_completeness[2]/_ft, financial_completeness[3]/_ft, 1.0),
    *gold_rows,
], ["table_name", "quality_score", "completeness", "accuracy", "consistency", "timeliness"])

quality_scores = quality_scores.withColumn("last_assessed", current_timestamp())

quality_scores.write.mode("overwrite").saveAsTable(f"`{catalog}`.`app`.data_quality_scores")

print(f"📊 Grants Quality Score: {grants_score:.2%}")
print(f"📊 Financial Quality Score: {financial_score:.2%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation (QA)

# COMMAND ----------

# Final validation
print("=" * 50)
print("SILVER LAYER VALIDATION")
print("=" * 50)

# Count checks
grants_final = spark.table(f"`{catalog}`.`silver`.grants").count()
financial_final = spark.table(f"`{catalog}`.`silver`.financial").count()

print(f"\n📊 Silver Grants: {grants_final:,} records")
print(f"📊 Silver Financial: {financial_final:,} records")

# Null checks
null_awardee = spark.sql(f"""
    SELECT COUNT(*) FROM `{catalog}`.`silver`.grants 
    WHERE awardee IS NULL
""").collect()[0][0]

print(f"⚠️ Null awardees: {null_awardee}")

dup_grants = spark.sql(f"""
    SELECT COUNT(*) FROM (
        SELECT grant_no, COUNT(*) as cnt 
        FROM `{catalog}`.`silver`.grants 
        GROUP BY grant_no HAVING cnt > 1
    )
""").collect()[0][0]

print(f"⚠️ Duplicate grant_no: {dup_grants}")

assert grants_final > 0, "FAIL: silver.grants empty"
assert financial_final > 0, "FAIL: silver.financial empty"
assert null_awardee == 0, "FAIL: null awardee found"

print("\n✅ All silver layer validations passed!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer Complete
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Run `03_gold_aggregation.py` to create business-ready aggregates
# MAGIC 2. Run `validation_queries.sql` for comprehensive validation
