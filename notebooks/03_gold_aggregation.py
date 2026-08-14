# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # Gold Layer Aggregation
# MAGIC **Purpose:** Create business-ready aggregates from silver data  
# MAGIC **Catalog:** onr_demo.bronze / silver / gold / app | **Compute:** Serverless  
# MAGIC **Input:** onr_demo.silver.grants, onr_demo.silver.financial  
# MAGIC **Output:** onr_demo.gold.grants_summary, financial_summary, grants_by_awardee, budget_execution  
# MAGIC **QA:** Count validation + freshness check

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
    col, current_timestamp, count, sum as spark_sum, avg, min, max,
    when, collect_set, round as spark_round
)
import time

_timing = {}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Grants Summary

# COMMAND ----------

# Read silver grants
silver_grants = spark.table(f"`{catalog}`.`silver`.grants")

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
_t = time.perf_counter()
gold_grants_summary.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`gold`.grants_summary"
)
_timing["grants_summary"] = int((time.perf_counter() - _t) * 1000)

summary_count = gold_grants_summary.count()
print(f"✅ Gold Grants Summary: {summary_count:,} records ({_timing['grants_summary']} ms)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Financial Summary

# COMMAND ----------

# Read silver financial
silver_financial = spark.table(f"`{catalog}`.`silver`.financial")

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
_t = time.perf_counter()
gold_financial_summary.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`gold`.financial_summary"
)
_timing["financial_summary"] = int((time.perf_counter() - _t) * 1000)

fin_count = gold_financial_summary.count()
print(f"✅ Gold Financial Summary: {fin_count:,} records ({_timing['financial_summary']} ms)")

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

_t = time.perf_counter()
gold_grants_by_awardee.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`gold`.grants_by_awardee"
)
_timing["grants_by_awardee"] = int((time.perf_counter() - _t) * 1000)

pi_count = gold_grants_by_awardee.count()
print(f"✅ Gold Grants by Awardee: {pi_count:,} records ({_timing['grants_by_awardee']} ms)")

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
_t = time.perf_counter()
gold_budget_execution.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`gold`.budget_execution"
)
_timing["budget_execution"] = int((time.perf_counter() - _t) * 1000)

budget_count = gold_budget_execution.count()
print(f"✅ Gold Budget Execution: {budget_count:,} records ({_timing['budget_execution']} ms)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: grant predictions (heuristic; notebook 04 overwrites with RF)

# COMMAND ----------

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
print("grant_predictions", spark.table(f"`{catalog}`.`gold`.grant_predictions").count())
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.model_metrics AS
SELECT 'heuristic_v1' AS model_name, 'rows_scored' AS metric_name,
       CAST(COUNT(*) AS DOUBLE) AS metric_value, CAST(COUNT(*) AS INT) AS n_rows,
       current_timestamp() AS trained_at
FROM `{catalog}`.`gold`.grant_predictions
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: OLS FY forecast + trend IDs (Element 5)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_forecast AS
WITH hist AS (
    SELECT program_area,
           CAST(fiscal_year AS DOUBLE) AS fy,
           CAST(SUM(total_funding) AS DOUBLE) AS funding
    FROM `{catalog}`.`gold`.grants_summary
    GROUP BY program_area, fiscal_year
),
stats AS (
    SELECT program_area, COUNT(*) AS n, SUM(fy) AS sx, SUM(funding) AS sy,
           SUM(fy * funding) AS sxy, SUM(fy * fy) AS sx2, MAX(fy) AS last_fy
    FROM hist GROUP BY program_area
),
fit AS (
    SELECT program_area, n, last_fy, sx, sy,
           CASE WHEN (n * sx2 - sx * sx) = 0 THEN 0.0
                ELSE (n * sxy - sx * sy) / (n * sx2 - sx * sx) END AS slope
    FROM stats
),
fit2 AS (
    SELECT *, (sy - slope * sx) / NULLIF(n, 0) AS intercept FROM fit
),
resid AS (
    SELECT h.program_area,
           STDDEV_POP(h.funding - (f.intercept + f.slope * h.fy)) AS resid_sd
    FROM hist h JOIN fit2 f ON h.program_area = f.program_area
    GROUP BY h.program_area
),
actuals AS (
    SELECT h.program_area, CAST(h.fy AS INT) AS fiscal_year, 'actual' AS series,
           h.funding AS predicted_funding, h.funding AS lower_95, h.funding AS upper_95,
           f.slope AS slope_usd_per_year, f.intercept AS intercept_usd,
           COALESCE(r.resid_sd, 0.0) AS resid_sd, 'ols_fy_v1' AS model_name
    FROM hist h JOIN fit2 f ON h.program_area = f.program_area
    LEFT JOIN resid r ON r.program_area = h.program_area
),
horizon AS (
    SELECT f.program_area, CAST(f.last_fy AS INT) + off AS fiscal_year,
           f.slope, f.intercept, COALESCE(r.resid_sd, 0.0) AS resid_sd
    FROM fit2 f LEFT JOIN resid r ON r.program_area = f.program_area
    LATERAL VIEW EXPLODE(ARRAY(1, 2)) t AS off
),
forecasts AS (
    SELECT program_area, fiscal_year, 'forecast' AS series,
           intercept + slope * fiscal_year AS predicted_funding,
           (intercept + slope * fiscal_year) - 1.96 * resid_sd AS lower_95,
           (intercept + slope * fiscal_year) + 1.96 * resid_sd AS upper_95,
           slope AS slope_usd_per_year, intercept AS intercept_usd, resid_sd,
           'ols_fy_v1' AS model_name
    FROM horizon
)
SELECT * FROM actuals UNION ALL SELECT * FROM forecasts
""")
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.program_trends AS
WITH last2 AS (
    SELECT program_area, fiscal_year, SUM(total_funding) AS funding,
           ROW_NUMBER() OVER (PARTITION BY program_area ORDER BY fiscal_year DESC) AS rn
    FROM `{catalog}`.`gold`.grants_summary
    GROUP BY program_area, fiscal_year
),
vel AS (
    SELECT a.program_area, a.funding AS last_actual, b.funding AS prior_actual,
           CASE WHEN b.funding IS NULL OR b.funding = 0 THEN NULL
                ELSE (a.funding - b.funding) / b.funding END AS velocity_yoy
    FROM last2 a
    LEFT JOIN last2 b ON a.program_area = b.program_area AND b.rn = 2
    WHERE a.rn = 1
),
next_fy AS (
    SELECT program_area, predicted_funding, slope_usd_per_year, resid_sd, fiscal_year
    FROM `{catalog}`.`gold`.funding_forecast
    WHERE series = 'forecast'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY program_area ORDER BY fiscal_year) = 1
)
SELECT n.program_area,
       CASE WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) > 0.05 THEN 'TREND-ACCEL'
            WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) < -0.05 THEN 'TREND-DECLINE'
            ELSE 'TREND-STEADY' END AS trend_id,
       CASE WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) > 0.05 THEN 'Accelerating'
            WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) < -0.05 THEN 'Declining'
            ELSE 'Steady' END AS trend_label,
       n.slope_usd_per_year, v.velocity_yoy, v.last_actual,
       n.predicted_funding AS forecast_next_fy, n.resid_sd,
       n.fiscal_year AS next_fiscal_year, 'ols_fy_v1' AS model_name,
       current_timestamp() AS computed_at
FROM next_fy n JOIN vel v ON n.program_area = v.program_area
""")
print("funding_forecast", spark.table(f"`{catalog}`.`gold`.funding_forecast").count())
print("program_trends", spark.table(f"`{catalog}`.`gold`.program_trends").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Lineage Tracking

# COMMAND ----------

import uuid as _uuid
_ms_summary = int(_timing.get("grants_summary") or 0)
_ms_fin = int(_timing.get("financial_summary") or 0)
# bronze→silver is owned by notebook 02; this notebook only measures gold writes.
lineage_records = spark.createDataFrame([
    (f"lin_{_uuid.uuid4()}",
     "bronze.grants", "silver.grants", "quality_transform",
     spark.table(f"`{catalog}`.`bronze`.grants").count(),
     0, "system"),
    (f"lin_{_uuid.uuid4()}",
     "bronze.financial", "silver.financial", "quality_transform",
     spark.table(f"`{catalog}`.`bronze`.financial").count(),
     0, "system"),
    (f"lin_{_uuid.uuid4()}",
     "silver.grants", "gold.grants_summary", "aggregation",
     spark.table(f"`{catalog}`.`silver`.grants").count(),
     _ms_summary, "system"),
    (f"lin_{_uuid.uuid4()}",
     "silver.financial", "gold.financial_summary", "aggregation",
     spark.table(f"`{catalog}`.`silver`.financial").count(),
     _ms_fin, "system"),
], ["lineage_id", "source_table", "target_table", "transformation_type",
    "records_processed", "processing_time_ms", "executed_by"])

lineage_records = lineage_records.withColumn("executed_at", current_timestamp())
try:
    lineage_records.write.mode("append").saveAsTable(f"`{catalog}`.`app`.lineage_tracking")
    print("✅ Lineage tracking recorded")
except Exception as e:
    print("Lineage log skipped:", e)

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
    "grants_summary", "financial_summary",
    "grants_by_awardee", "budget_execution", "grant_predictions", "model_metrics"
]

all_passed = True
for table in tables:
    cnt = spark.table(f"`{catalog}`.`gold`.{table}").count()
    status = "✅" if cnt > 0 else "❌"
    print(f"{status} {table}: {cnt:,} records")
    if cnt == 0:
        all_passed = False

# Freshness check
freshness = spark.sql(f"""
    SELECT MAX(_updated_at) as latest_update 
    FROM `{catalog}`.`gold`.grants_summary
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
# MAGIC 1. Refresh the Streamlit app — gold KPIs update automatically
# MAGIC 2. Run validation queries: `sql/validation_queries.sql`
