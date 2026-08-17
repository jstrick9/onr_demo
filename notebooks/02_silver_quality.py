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

# Known areas — keep in sync with app-onr-demo/utils/quality_rules.py
KNOWN_AREAS = [
    "AI/ML", "Autonomy", "Biotech", "Cyber",
    "Directed Energy", "Materials", "Quantum", "Undersea",
]
LARGE_AMOUNT_USD = 5000000

bronze_grants = spark.table(f"`{catalog}`.`bronze`.grants")

# Quarantine never stays in bronze: log then delete.
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
""")
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
""")

q_empty = bronze_grants.filter(
    col("grant_no").isNull() | (trim(col("grant_no")) == "")
).withColumn("reason_code", lit("empty")).withColumn("reason_detail", lit("Empty grant_no"))
q_amt = bronze_grants.filter(
    col("amount_usd").isNull() | (col("amount_usd") <= 0)
).withColumn("reason_code", lit("amt")).withColumn("reason_detail", lit("Amount not positive"))
win = Window.partitionBy("grant_no").orderBy(col("_ingest_time").desc())
q_dup = (
    bronze_grants.filter(col("grant_no").isNotNull() & (trim(col("grant_no")) != ""))
    .withColumn("_rn", F.row_number().over(win))
    .filter(col("_rn") > 1)
    .drop("_rn")
    .withColumn("reason_code", lit("dup"))
    .withColumn("reason_detail", lit("Duplicate grant_no"))
)
q_all = q_empty.unionByName(q_amt, allowMissingColumns=True).unionByName(q_dup, allowMissingColumns=True)
q_n = q_all.count()
if q_n:
    from pyspark.sql.functions import monotonically_increasing_id
    logged = (
        q_all.select(
            "grant_no", "title", "abstract", "program_area", "fiscal_year", "amount_usd",
            "awardee", "org_unit", "classification_band", "batch_id",
            "reason_code", "reason_detail",
        )
        .withColumn("source_file", lit("02_silver_quality"))
        .withColumn("pipeline_name", lit("02_silver_quality"))
        .withColumn("quarantined_at", F.current_timestamp())
        .withColumn("event_id", F.concat(lit("q-02-"), monotonically_increasing_id().cast("string")))
    )
    logged.write.mode("append").saveAsTable(f"`{catalog}`.`app`.quarantine_log")
# Keep one good row per grant_no; drop empty / non-positive.
bronze_grants = (
    bronze_grants.filter(
        col("grant_no").isNotNull() & (trim(col("grant_no")) != "") & (col("amount_usd") > 0)
    )
    .withColumn("_rn", F.row_number().over(win))
    .filter(col("_rn") == 1)
    .drop("_rn")
)
bronze_grants.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`bronze`.grants"
)
bronze_grants = spark.table(f"`{catalog}`.`bronze`.grants")
print(f"Quarantined {q_n} row(s) to app.quarantine_log. Bronze now {bronze_grants.count():,} clean rows.")

# Warnings on rows that will publish
warn_rows = (
    bronze_grants
    .withColumn(
        "missing_abstract",
        (col("abstract").isNull()) | (trim(col("abstract")) == ""),
    )
    .withColumn(
        "unknown_area",
        ~col("program_area").isin(KNOWN_AREAS) | col("program_area").isNull(),
    )
    .withColumn("large_amount", col("amount_usd") > LARGE_AMOUNT_USD)
)
from pyspark.sql.functions import explode, array, struct
warn_long = (
    warn_rows.select(
        "grant_no", "title", "program_area", "amount_usd",
        F.when(col("missing_abstract"), lit("missing_abstract")).otherwise(lit(None)).alias("w1"),
        F.when(col("unknown_area"), lit("unknown_program_area")).otherwise(lit(None)).alias("w2"),
        F.when(col("large_amount"), lit("large_amount")).otherwise(lit(None)).alias("w3"),
    )
)
# Build findings via SQL for portability
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`app`.quality_findings AS
SELECT
  concat('w-02-', grant_no, '-', check_name) AS finding_id,
  grant_no, title, program_area, amount_usd,
  'WARN' AS severity,
  check_name,
  CASE check_name
    WHEN 'missing_abstract' THEN 'Missing abstract'
    WHEN 'unknown_program_area' THEN concat('Unknown program area: ', coalesce(program_area, ''))
    WHEN 'large_amount' THEN concat('Amount over $5M ($', cast(round(amount_usd,0) as string), ')')
  END AS detail,
  true AS published,
  '02_silver_quality' AS source_file,
  '02_silver_quality' AS pipeline_name,
  current_timestamp() AS found_at
FROM `{catalog}`.`bronze`.grants
LATERAL VIEW explode(filter(array(
  CASE WHEN abstract IS NULL OR trim(abstract) = '' THEN 'missing_abstract' END,
  CASE WHEN program_area IS NULL OR program_area NOT IN
    ('AI/ML','Autonomy','Biotech','Cyber','Directed Energy','Materials','Quantum','Undersea')
    THEN 'unknown_program_area' END,
  CASE WHEN amount_usd > 5000000 THEN 'large_amount' END
), x -> x IS NOT NULL)) t AS check_name
""")
print("Wrote app.quality_findings for published warnings.")


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

# Save quality scores. Cast every metric to DOUBLE — the warehouse CREATE OR
# REPLACE path types SQL 1.0 as DECIMAL, and overwrite without overwriteSchema
# then fails: DELTA_FAILED_TO_MERGE_FIELDS timeliness/timeliness.
from pyspark.sql.functions import current_timestamp
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

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
        ("gold.grants_summary", _f(gold_summary_score), _f(gold_summary[1] / _gst),
         _f(gold_summary[2] / _gst), 1.0, 1.0),
        ("gold.budget_execution", _f(gold_budget_score), _f(gold_budget[1] / _gbt),
         _f(gold_budget[2] / _gbt), 1.0, 1.0),
    ]
except Exception:
    gold_rows = []

score_schema = StructType([
    StructField("table_name", StringType(), False),
    StructField("quality_score", DoubleType(), True),
    StructField("completeness", DoubleType(), True),
    StructField("accuracy", DoubleType(), True),
    StructField("consistency", DoubleType(), True),
    StructField("timeliness", DoubleType(), True),
])
quality_scores = spark.createDataFrame(
    [
        ("silver.grants", _f(grants_score), _f(grants_completeness[1] / _gt),
         _f(grants_completeness[3] / _gt), _f(grants_completeness[2] / _gt), 1.0),
        ("silver.financial", _f(financial_score), _f(financial_completeness[1] / _ft),
         _f(financial_completeness[2] / _ft), _f(financial_completeness[3] / _ft), 1.0),
        *gold_rows,
    ],
    schema=score_schema,
)
quality_scores = quality_scores.withColumn("last_assessed", current_timestamp().cast("timestamp"))
quality_scores.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"`{catalog}`.`app`.data_quality_scores"
)

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
