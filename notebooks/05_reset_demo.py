# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**
# MAGIC
# MAGIC # 05 — Reset demo to seed
# MAGIC
# MAGIC Deletes live / quality-fail / **stream** bronze rows (`live-demo-2026`,
# MAGIC `quality-fail-2026`, `stream-demo-2026` on either `batch_id` or `_batch_id`),
# MAGIC rebuilds silver + gold with Spark SQL (no `notebook.run` dependency),
# MAGIC clears `app.quarantine_log` / `app.quality_findings` / `app.ingestion_quality_log`,
# MAGIC writes a baseline silver quality log, and clears Auto Loader checkpoints.

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")
catalog = dbutils.widgets.get("catalog")
SEED = "seed-initial-2026"

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

DEMO_BATCHES = (
    "live-demo-2026",
    "quality-fail-2026",
    "stream-demo-2026",
    "sdp-stream-2026",
)
demo_sql = ", ".join(f"'{b}'" for b in DEMO_BATCHES)
for table in ("grants", "financial"):
    spark.sql(f"""
    DELETE FROM `{catalog}`.`bronze`.{table}
    WHERE coalesce(batch_id, '{SEED}') <> '{SEED}'
       OR coalesce(_batch_id, '{SEED}') <> '{SEED}'
       OR batch_id IN ({demo_sql})
       OR _batch_id IN ({demo_sql})
    """)
try:
    dbutils.fs.rm(f"/Volumes/{catalog}/bronze/landing/grants/batch_live_grants_stream.csv", True)
    print("Removed stream landing file")
except Exception as e:
    print("Stream file rm:", e)
spark.sql(f"""
DELETE FROM `{catalog}`.`bronze`.grants
WHERE grant_no IS NULL OR trim(grant_no) = ''
   OR amount_usd IS NULL OR amount_usd <= 0
""")
bronze_n = spark.table(f"`{catalog}`.`bronze`.grants").count()
print("bronze.grants", bronze_n)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver / quarantine logs — empty at baseline

# COMMAND ----------

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
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.ingestion_quality_log (
    check_id STRING NOT NULL,
    check_name STRING,
    check_status STRING,
    records_checked INT,
    records_passed INT,
    records_failed INT,
    check_timestamp TIMESTAMP,
    pipeline_name STRING
) USING DELTA
""")
for table in ("hold_queue", "quarantine_log", "quality_findings", "ingestion_quality_log"):
    spark.sql(f"DELETE FROM `{catalog}`.`app`.{table}")
    print("cleared app." + table)

# COMMAND ----------

bg = spark.table(f"`{catalog}`.`bronze`.grants")
sg = (
    bg.withColumn("grant_no", F.trim("grant_no"))
      .withColumn("amount_usd", F.col("amount_usd").cast("double"))
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
      .withColumn("_is_active", F.lit(True))
      .withColumn("_rn", F.row_number().over(Window.partitionBy("transaction_id").orderBy(F.col("_ingest_time").desc())))
      .filter("_rn = 1").drop("_rn")
      .filter(F.col("transaction_id").isNotNull() & (F.col("budget_allocated") > 0))
)
sf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`silver`.financial")
print("silver.grants", sg.count(), "silver.financial", sf.count())

# COMMAND ----------

g = spark.table(f"`{catalog}`.`silver`.grants").filter("_is_active")
f = spark.table(f"`{catalog}`.`silver`.financial").filter("_is_active")
g.groupBy("program_area", "fiscal_year").agg(
    F.count("*").alias("grant_count"), F.sum("amount_usd").alias("total_funding"),
    F.avg("amount_usd").alias("avg_award"), F.min("amount_usd").alias("min_award"),
    F.max("amount_usd").alias("max_award"),
    F.sum(F.when(F.col("classification_band") == "CUI-Mock", 1).otherwise(0)).alias("cui_mock_count"),
    F.sum(F.when(F.col("classification_band") == "Public-Mock", 1).otherwise(0)).alias("public_mock_count"),
).withColumn("_updated_at", F.current_timestamp()).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.grants_summary")

f.groupBy("cost_center", "category", "fiscal_year", "quarter").agg(
    F.sum("budget_allocated").alias("total_budget"),
    F.sum("actual_expenditure").alias("total_actual"),
    F.count("*").alias("transaction_count"),
).withColumn("overall_execution_rate", F.round(F.col("total_actual") / F.col("total_budget") * 100, 2)).withColumn("variance_amount", F.col("total_budget") - F.col("total_actual")).withColumn("_updated_at", F.current_timestamp()).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.financial_summary")

g.groupBy("awardee", "org_unit").agg(
    F.count("*").alias("grant_count"), F.sum("amount_usd").alias("total_funding"),
    F.collect_set("program_area").alias("program_areas"), F.max("created_at").alias("latest_grant_date"),
).withColumn("_updated_at", F.current_timestamp()).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.grants_by_awardee")

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

f.groupBy("fiscal_year", "quarter", "category").agg(
    F.sum("budget_allocated").alias("budget_plan"), F.sum("actual_expenditure").alias("actual_spend"),
).withColumn("execution_rate", F.round(F.col("actual_spend") / F.col("budget_plan") * 100, 2)).withColumn("variance", F.col("budget_plan") - F.col("actual_spend")).withColumn("variance_pct", F.round(F.col("variance") / F.col("budget_plan") * 100, 2)).withColumn("status", F.when(F.col("execution_rate") >= 90, "ON_TARGET").when(F.col("execution_rate") >= 80, "WARNING").otherwise("AT_RISK")).withColumn("_updated_at", F.current_timestamp()).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.budget_execution")

spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_forecast AS
WITH hist AS (
    SELECT program_area, CAST(fiscal_year AS DOUBLE) fy, CAST(SUM(total_funding) AS DOUBLE) funding
    FROM `{catalog}`.`gold`.grants_summary GROUP BY program_area, fiscal_year
),
stats AS (
    SELECT program_area, COUNT(*) n, SUM(fy) sx, SUM(funding) sy,
           SUM(fy*funding) sxy, SUM(fy*fy) sx2, MAX(fy) last_fy FROM hist GROUP BY program_area
),
fit AS (
    SELECT program_area, n, last_fy, sx, sy,
           CASE WHEN (n*sx2-sx*sx)=0 THEN 0.0 ELSE (n*sxy-sx*sy)/(n*sx2-sx*sx) END slope FROM stats
),
fit2 AS (SELECT *, (sy-slope*sx)/NULLIF(n,0) intercept FROM fit),
resid AS (
    SELECT h.program_area, STDDEV_POP(h.funding-(f.intercept+f.slope*h.fy)) resid_sd
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
SELECT program_area, fiscal_year, 'forecast', intercept+slope*fiscal_year,
       (intercept+slope*fiscal_year)-1.96*resid_sd, (intercept+slope*fiscal_year)+1.96*resid_sd,
       slope, intercept, resid_sd, 'ols_fy_v1' FROM horizon
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
    FROM last2 a LEFT JOIN last2 b ON a.program_area=b.program_area AND b.rn=2 WHERE a.rn=1
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

# COMMAND ----------

ckpt = f"/Volumes/{catalog}/bronze/checkpoints"
try:
    dbutils.fs.rm(ckpt, True)
    dbutils.fs.mkdirs(ckpt)
    print("Cleared", ckpt)
except Exception as e:
    print("Checkpoint rm:", e)

n = spark.table(f"`{catalog}`.`silver`.grants").count()
bronze_n = spark.table(f"`{catalog}`.`bronze`.grants").count()
q_n = spark.table(f"`{catalog}`.`app`.quarantine_log").count()
w_n = spark.table(f"`{catalog}`.`app`.quality_findings").count()

from datetime import datetime
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

now = datetime.utcnow()
baseline_rows = [
    ("reset-grant_no_present", "grant_no_present", "PASS", int(bronze_n), int(n), 0, now, "restore_baseline"),
    ("reset-amount_positive", "amount_positive", "PASS", int(bronze_n), int(n), 0, now, "restore_baseline"),
    ("reset-grant_no_unique", "grant_no_unique", "PASS", int(bronze_n), int(n), 0, now, "restore_baseline"),
    ("reset-silver_publish", "silver_publish", "PASS", int(bronze_n), int(n), 0, now, "restore_baseline"),
    ("reset-quarantine_log", "quarantine_log", "PASS", 0, 0, 0, now, "restore_baseline"),
    ("reset-warn_published", "warn_published", "PASS", int(bronze_n), int(n), 0, now, "restore_baseline"),
]
qlog_schema = StructType([
    StructField("check_id", StringType(), False),
    StructField("check_name", StringType(), True),
    StructField("check_status", StringType(), True),
    StructField("records_checked", IntegerType(), True),
    StructField("records_passed", IntegerType(), True),
    StructField("records_failed", IntegerType(), True),
    StructField("check_timestamp", TimestampType(), True),
    StructField("pipeline_name", StringType(), True),
])
spark.createDataFrame(baseline_rows, schema=qlog_schema).write.mode("append").saveAsTable(
    f"`{catalog}`.`app`.ingestion_quality_log"
)

print("RESET COMPLETE — silver.grants =", n)
print("bronze.grants =", bronze_n, "quarantine_log =", q_n, "quality_findings =", w_n)
if n != 400:
    print("WARNING: expected 400. Run 00_bootstrap.py to full-reload the fixture.")
if q_n != 0:
    print("WARNING: quarantine_log should be empty after restore.")
