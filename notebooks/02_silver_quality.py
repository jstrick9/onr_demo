# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer Quality Transforms
# MAGIC **Purpose:** Cleanse, deduplicate, and validate bronze data → Silver Delta tables  
# MAGIC **Catalog:** onr_demo.dev | **Compute:** Serverless  
# MAGIC **Input:** onr_demo.dev.bronze_grants, onr_demo.dev.bronze_financial  
# MAGIC **Output:** onr_demo.dev.silver_grants, onr_demo.dev.silver_financial  
# MAGIC **QA:** Quality constraints + row count validation

# COMMAND ----------

# Configuration widgets
dbutils.widgets.text("catalog", "onr_demo")
dbutils.widgets.text("schema", "dev")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# Set catalog context
spark.sql(f"USE CATALOG `{catalog}`")
spark.sql(f"USE SCHEMA `{schema}`")

print(f"✅ Context set: {catalog}.{schema}")

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
bronze_grants = spark.table(f"`{catalog}`.`{schema}`.bronze_grants")

# Cleanse and transform
silver_grants = (
    bronze_grants
    # Trim whitespace
    .withColumn("grant_id", trim(col("grant_id")))
    .withColumn("title", trim(col("title")))
    .withColumn("principal_investigator", trim(col("principal_investigator")))
    .withColumn("institution", trim(col("institution")))
    .withColumn("research_area", trim(col("research_area")))
    .withColumn("status", upper(trim(col("status"))))
    
    # Type casting
    .withColumn("award_amount", col("award_amount").cast("double"))
    .withColumn("start_date", to_date(col("start_date"), "yyyy-MM-dd"))
    .withColumn("end_date", to_date(col("end_date"), "yyyy-MM-dd"))
    .withColumn("fiscal_year", col("fiscal_year").cast("int"))
    
    # Add metadata
    .withColumn("_is_active", lit(True))
    .withColumn("_quality_score", 
        when(col("award_amount").isNotNull() & (col("award_amount") > 0), 1.0)
        .otherwise(0.5)
    )
    
    # Remove duplicates (keep latest by ingest time)
    .withColumn("_row_num", 
        F.row_number().over(
            Window.partitionBy("grant_id").orderBy(col("_ingest_time").desc())
        )
    )
    .filter(col("_row_num") == 1)
    .drop("_row_num")
    
    # Apply quality filters
    .filter(col("grant_id").isNotNull())
    .filter(col("award_amount") > 0)
    .filter(col("end_date") > col("start_date"))
)

# Overwrite silver table
silver_grants.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`{schema}`.silver_grants"
)

grants_count = silver_grants.count()
print(f"✅ Silver Grants: {grants_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Financial: Bronze → Silver

# COMMAND ----------

# Read bronze financial
bronze_financial = spark.table(f"`{catalog}`.`{schema}`.bronze_financial")

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
    f"`{catalog}`.`{schema}`.silver_financial"
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
        COUNT(CASE WHEN grant_id IS NOT NULL THEN 1 END) as valid_id,
        COUNT(CASE WHEN principal_investigator IS NOT NULL THEN 1 END) as valid_pi,
        COUNT(CASE WHEN award_amount > 0 THEN 1 END) as valid_amount,
        COUNT(CASE WHEN start_date IS NOT NULL AND end_date IS NOT NULL THEN 1 END) as valid_dates
    FROM `{catalog}`.`{schema}`.silver_grants
""").collect()[0]

grants_score = (
    (grants_completeness[1] / grants_completeness[0]) * 0.3 +
    (grants_completeness[2] / grants_completeness[0]) * 0.3 +
    (grants_completeness[3] / grants_completeness[0]) * 0.2 +
    (grants_completeness[4] / grants_completeness[0]) * 0.2
)

financial_completeness = spark.sql(f"""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN transaction_id IS NOT NULL THEN 1 END) as valid_id,
        COUNT(CASE WHEN budget_allocated > 0 THEN 1 END) as valid_budget,
        COUNT(CASE WHEN actual_expenditure >= 0 THEN 1 END) as valid_actual
    FROM `{catalog}`.`{schema}`.silver_financial
""").collect()[0]

financial_score = (
    (financial_completeness[1] / financial_completeness[0]) * 0.4 +
    (financial_completeness[2] / financial_completeness[0]) * 0.3 +
    (financial_completeness[3] / financial_completeness[0]) * 0.3
)

# Save quality scores
from pyspark.sql.functions import current_timestamp

quality_scores = spark.createDataFrame([
    ("silver_grants", grants_score, grants_completeness[1]/grants_completeness[0],
     grants_completeness[3]/grants_completeness[0], grants_completeness[2]/grants_completeness[0], 1.0),
    ("silver_financial", financial_score, financial_completeness[1]/financial_completeness[0],
     financial_completeness[2]/financial_completeness[0], financial_completeness[3]/financial_completeness[0], 1.0),
], ["table_name", "quality_score", "completeness", "accuracy", "consistency", "timeliness"])

quality_scores = quality_scores.withColumn("last_assessed", current_timestamp())

quality_scores.write.mode("overwrite").saveAsTable(f"`{catalog}`.`{schema}`.onr_data_quality_scores")

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
grants_final = spark.table(f"`{catalog}`.`{schema}`.silver_grants").count()
financial_final = spark.table(f"`{catalog}`.`{schema}`.silver_financial").count()

print(f"\n📊 Silver Grants: {grants_final:,} records")
print(f"📊 Silver Financial: {financial_final:,} records")

# Null checks
null_pi = spark.sql(f"""
    SELECT COUNT(*) FROM `{catalog}`.`{schema}`.silver_grants 
    WHERE principal_investigator IS NULL
""").collect()[0][0]

print(f"⚠️ Null PIs: {null_pi}")

# Duplicate check
dup_grants = spark.sql(f"""
    SELECT COUNT(*) FROM (
        SELECT grant_id, COUNT(*) as cnt 
        FROM `{catalog}``.`{schema}`.silver_grants 
        GROUP BY grant_id HAVING cnt > 1
    )
""").collect()[0][0]

print(f"⚠️ Duplicate grant_ids: {dup_grants}")

# Assert success
assert grants_final > 0, "FAIL: silver_grants empty"
assert financial_final > 0, "FAIL: silver_financial empty"
assert null_pi == 0, "FAIL: null principal_investigator found"

print("\n✅ All silver layer validations passed!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer Complete
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Run `03_gold_aggregation.py` to create business-ready aggregates
# MAGIC 2. Run `validation_queries.sql` for comprehensive validation
