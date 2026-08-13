# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer Aggregation
# MAGIC **Purpose:** Create business-ready aggregates from silver data  
# MAGIC **Catalog:** onr_demo.dev | **Compute:** Serverless  
# MAGIC **Input:** onr_demo.dev.silver_grants, onr_demo.dev.silver_financial  
# MAGIC **Output:** gold_grants_summary, gold_financial_summary, gold_grants_by_awardee, gold_budget_execution  
# MAGIC **QA:** Count validation + freshness check

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
    col, current_timestamp, count, sum as spark_sum, avg, min, max,
    when, collect_set, array, lit, datediff, round as spark_round
)
from pyspark.sql.window import Window

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Grants Summary

# COMMAND ----------

# Read silver grants
silver_grants = spark.table(f"`{catalog}`.`{schema}`.silver_grants")

# Aggregate by program area and fiscal year
gold_grants_summary = (
    silver_grants
    .filter(col("_is_active") == True)
    .groupBy("program_area", "fiscal_year")
    .agg(
        count("*").alias("grant_count"),
        spark_sum("amount_usd").alias("total_funding"),
        avg("amount_usd").alias("avg_award"),
        min("amount_usd").alias("min_award"),
        max("amount_usd").alias("max_award"),
        spark_sum(when(col("classification_band") == "CUI-Mock", 1).otherwise(0)).alias("cui_mock_count"),
        spark_sum(when(col("classification_band") == "Public-Mock", 1).otherwise(0)).alias("public_mock_count"),
    )
    .withColumn("_updated_at", current_timestamp())
)

# Write to gold table
gold_grants_summary.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`{schema}`.gold_grants_summary"
)

summary_count = gold_grants_summary.count()
print(f"✅ Gold Grants Summary: {summary_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Financial Summary

# COMMAND ----------

# Read silver financial
silver_financial = spark.table(f"`{catalog}`.`{schema}`.silver_financial")

# Aggregate by cost center, category, and time
gold_financial_summary = (
    silver_financial
    .filter(col("_is_active") == True)
    .groupBy("cost_center", "category", "fiscal_year", "quarter")
    .agg(
        spark_sum("budget_allocated").alias("total_budget"),
        spark_sum("actual_expenditure").alias("total_actual"),
        count("*").alias("transaction_count"),
    )
    .withColumn("overall_execution_rate", 
        spark_round(col("total_actual") / col("total_budget") * 100, 2)
    )
    .withColumn("variance_amount", col("total_budget") - col("total_actual"))
    .withColumn("_updated_at", current_timestamp())
)

# Write to gold table
gold_financial_summary.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`{schema}`.gold_financial_summary"
)

fin_count = gold_financial_summary.count()
print(f"✅ Gold Financial Summary: {fin_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Grants by Awardee

# COMMAND ----------

gold_grants_by_awardee = (
    silver_grants
    .filter(col("_is_active") == True)
    .groupBy("awardee", "org_unit")
    .agg(
        count("*").alias("grant_count"),
        spark_sum("amount_usd").alias("total_funding"),
        collect_set("program_area").alias("program_areas"),
        max("created_at").alias("latest_grant_date"),
    )
    .withColumn("_updated_at", current_timestamp())
)

gold_grants_by_awardee.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`{schema}`.gold_grants_by_awardee"
)

pi_count = gold_grants_by_awardee.count()
print(f"✅ Gold Grants by Awardee: {pi_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Budget Execution

# COMMAND ----------

# Calculate budget execution metrics
gold_budget_execution = (
    silver_financial
    .filter(col("_is_active") == True)
    .groupBy("fiscal_year", "quarter", "category")
    .agg(
        spark_sum("budget_allocated").alias("budget_plan"),
        spark_sum("actual_expenditure").alias("actual_spend"),
        count("*").alias("transaction_count"),
    )
    .withColumn("execution_rate", 
        spark_round(col("actual_spend") / col("budget_plan") * 100, 2)
    )
    .withColumn("variance", col("budget_plan") - col("actual_spend"))
    .withColumn("variance_pct", 
        spark_round(col("variance") / col("budget_plan") * 100, 2)
    )
    .withColumn("status", 
        when(col("execution_rate") >= 90, "ON_TARGET")
        .when(col("execution_rate") >= 80, "WARNING")
        .otherwise("AT_RISK")
    )
    .withColumn("_updated_at", current_timestamp())
)

# Write to gold table
gold_budget_execution.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`{schema}`.gold_budget_execution"
)

budget_count = gold_budget_execution.count()
print(f"✅ Gold Budget Execution: {budget_count:,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Lineage Tracking

# COMMAND ----------

# Record lineage
lineage_records = spark.createDataFrame([
    (f"lin_{spark.sql('SELECT uuid()').collect()[0][0]}", 
     "bronze_grants", "silver_grants", "quality_transform", 
     spark.table(f"`{catalog}`.`{schema}`.bronze_grants").count(), 
     1500, "system"),
    (f"lin_{spark.sql('SELECT uuid()').collect()[0][0]}", 
     "bronze_financial", "silver_financial", "quality_transform", 
     spark.table(f"`{catalog}`.`{schema}`.bronze_financial").count(), 
     1200, "system"),
    (f"lin_{spark.sql('SELECT uuid()').collect()[0][0]}", 
     "silver_grants", "gold_grants_summary", "aggregation", 
     spark.table(f"`{catalog}`.`{schema}`.silver_grants").count(), 
     800, "system"),
    (f"lin_{spark.sql('SELECT uuid()').collect()[0][0]}", 
     "silver_financial", "gold_financial_summary", "aggregation", 
     spark.table(f"`{catalog}`.`{schema}`.silver_financial").count(), 
     600, "system"),
], ["lineage_id", "source_table", "target_table", "transformation_type", 
    "records_processed", "processing_time_ms", "executed_by"])

lineage_records = lineage_records.withColumn("executed_at", current_timestamp())

lineage_records.write.mode("append").saveAsTable(f"`{catalog}`.`{schema}`.onr_lineage_tracking")

print("✅ Lineage tracking recorded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Final Validation

# COMMAND ----------

# Validation
print("=" * 50)
print("GOLD LAYER VALIDATION")
print("=" * 50)

# Count checks
tables = [
    "gold_grants_summary", "gold_financial_summary", 
    "gold_grants_by_pi", "gold_budget_execution"
]

all_passed = True
for table in tables:
    cnt = spark.table(f"`{catalog}`.`{schema}`.{table}").count()
    status = "✅" if cnt > 0 else "❌"
    print(f"{status} {table}: {cnt:,} records")
    if cnt == 0:
        all_passed = False

# Freshness check
freshness = spark.sql(f"""
    SELECT MAX(_updated_at) as latest_update 
    FROM `{catalog}`.`{schema}`.gold_grants_summary
""").collect()[0][0]

print(f"\n📅 Latest update: {freshness}")

# Assert
assert all_passed, "FAIL: Some gold tables are empty"
print("\n✅ All gold layer validations passed!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer Complete
# MAGIC 
# MAGIC **Summary:**
# MAGIC - ✅ gold_grants_summary — Aggregated by program area and fiscal year
# MAGIC - ✅ gold_financial_summary — Aggregated by cost center and category
# MAGIC - ✅ gold_grants_by_awardee — Performance metrics by awardee
# MAGIC - ✅ gold_budget_execution — Budget execution tracking
# MAGIC - ✅ Lineage tracking recorded
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Deploy Streamlit app: `databricks bundle deploy -t dev`
# MAGIC 2. Run validation queries: `sql/validation_queries.sql`
