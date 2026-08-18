# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** Jobs **serverless** (app Start stream) or **`onr demo cluster`**
# MAGIC
# MAGIC # 01b — Live Auto Loader stream (Element 3)
# MAGIC
# MAGIC Same `cloudFiles` path as `01_bronze_ingestion.py`. Trigger depends on
# MAGIC compute:
# MAGIC
# MAGIC - **Jobs serverless / Spark Connect** — `availableNow` only.
# MAGIC   `processingTime` raises `INFINITE_STREAMING_TRIGGER_NOT_SUPPORTED`.
# MAGIC - **Classic `onr demo cluster`** — `processingTime` 30-second micro-batches,
# MAGIC   auto-stop after `run_for_seconds` (default 90).
# MAGIC
# MAGIC The app lands a **new** `batch_live_grants_stream_*.csv` **before** it
# MAGIC submits this notebook, so `availableNow` always sees a fresh Auto Loader
# MAGIC path (checkpoints key by file path). That is the Start stream path.
# MAGIC
# MAGIC **Recording beat (do not Reset on camera):**
# MAGIC 1. App Process already landed Live 8 + quality-fail (silver **408**).
# MAGIC 2. App **Start stream** (preferred) or **Run all** here.
# MAGIC 3. File on Volume:
# MAGIC    `/Volumes/onr_demo/bronze/landing/grants/batch_live_grants_stream_*.csv`
# MAGIC 4. Watch bronze tick. Silver stays 408 (dedupe). Extra bronze rows are
# MAGIC    the stream proof.
# MAGIC
# MAGIC Checkpoint is **`.../checkpoints/grants_stream_v3`** so it does not collide
# MAGIC with the availableNow job in notebook 01.
# MAGIC
# MAGIC After the query stops, this notebook **publishes silver + gold** (dedupe on
# MAGIC `grant_no`). It does **not** run 02's bronze quarantine cleanup — that would
# MAGIC delete the extra stream rows. Restore baseline deletes `_batch_id` /
# MAGIC `batch_id = stream-demo-2026`.

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")
dbutils.widgets.text("processing_seconds", "30")
dbutils.widgets.text("run_for_seconds", "90")
dbutils.widgets.dropdown("trigger_mode", "availableNow", ["availableNow", "processingTime"])

catalog = dbutils.widgets.get("catalog")
processing_seconds = dbutils.widgets.get("processing_seconds").strip() or "30"
run_for_seconds = int(dbutils.widgets.get("run_for_seconds") or "90")
trigger_mode = dbutils.widgets.get("trigger_mode")

landing = f"/Volumes/{catalog}/bronze/landing/"
# v3: no .schema() and no schemaHints — this DBR treats either as "schema specified"
# and rejects addNewColumns. Infer types; mergeSchema on write.
ckpt = f"/Volumes/{catalog}/bronze/checkpoints/grants_stream_v3"
schema_loc = f"{landing}_schemas/grants_stream_v3"

for p in (f"{landing}grants", schema_loc, ckpt):
    try:
        dbutils.fs.mkdirs(p)
    except Exception:
        pass

spark.sql(f"USE CATALOG `{catalog}`")
print(f"catalog={catalog}  trigger={trigger_mode}  interval={processing_seconds}s  run_for={run_for_seconds}s")

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, lit
import time


def _spark_is_connect() -> bool:
    """Serverless Jobs and Spark Connect reject ProcessingTime triggers."""
    try:
        if "pyspark.sql.connect" in (type(spark).__module__ or ""):
            return True
    except Exception:
        pass
    for key in (
        "spark.databricks.service.client.enabled",
        "spark.databricks.remote.enabled",
    ):
        try:
            if str(spark.conf.get(key, "false")).lower() == "true":
                return True
        except Exception:
            pass
    return False


requested = (trigger_mode or "availableNow").strip()
connect = _spark_is_connect()
if requested == "processingTime" and connect:
    print("01b: ProcessingTime not supported on serverless/Spark Connect — using availableNow")
    trigger_mode = "availableNow"
else:
    trigger_mode = requested if requested in {"availableNow", "processingTime"} else "availableNow"

QUERY_NAME = f"onr_grants_{trigger_mode}"
print("01b cloudFiles: inferColumnTypes + addNewColumns; no .schema(); no schemaHints; ckpt=v3")
print(f"01b trigger={trigger_mode} connect={connect}")

# Stop any leftover demo query so a prior failed run cannot keep streaming.
for active in spark.streams.active:
    try:
        if (active.name or "") == QUERY_NAME:
            active.stop()
            print("Stopped leftover query", QUERY_NAME)
    except Exception as e:
        print("Could not stop leftover query:", e)

src = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("header", "true")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", schema_loc)
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .load(f"{landing}grants/")
    .withColumn("_ingest_time", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
    .withColumn("_batch_id", lit("stream-demo-2026"))
    .withColumn("batch_id", lit("stream-demo-2026"))
)

writer = (
    src.writeStream
    .format("delta")
    .option("checkpointLocation", ckpt)
    .option("mergeSchema", "true")
    .outputMode("append")
    .queryName(QUERY_NAME)
)

q = None
last_n = None
used_available_now = trigger_mode == "availableNow"
try:
    if not used_available_now:
        try:
            q = writer.trigger(processingTime=f"{processing_seconds} seconds").toTable(
                f"`{catalog}`.`bronze`.grants"
            )
        except Exception as e:
            err = str(e)
            if (
                "INFINITE_STREAMING_TRIGGER_NOT_SUPPORTED" in err
                or "AvailableNow" in err
                or "Once" in err
            ):
                print("01b: ProcessingTime rejected — falling back to availableNow:", e)
                used_available_now = True
                q = None
            else:
                raise
    if used_available_now:
        q = writer.trigger(availableNow=True).toTable(f"`{catalog}`.`bronze`.grants")
        q.awaitTermination()
        print("availableNow stream finished")
        try:
            last_n = spark.table(f"`{catalog}`.`bronze`.grants").count()
        except Exception:
            last_n = "?"
    else:
        print(
            f"Stream '{q.name}' started. Drop a CSV into {landing}grants/ now. "
            f"This query is bounded — it stops itself in {run_for_seconds}s. "
            "To stop early: Cancel the job run, or run spark.streams.active stop."
        )
        t0 = time.time()
        while q.isActive and (time.time() - t0) < run_for_seconds:
            time.sleep(5)
            try:
                n = spark.table(f"`{catalog}`.`bronze`.grants").count()
            except Exception:
                n = "?"
            progress = q.lastProgress or {}
            batch_id = progress.get("batchId")
            inputs = (progress.get("sources") or [{}])[0].get("numInputRows")
            print(f"  t={int(time.time()-t0):3d}s  bronze.grants={n}  batch={batch_id}  inputRows={inputs}")
            last_n = n
finally:
    if q is not None:
        try:
            if q.isActive:
                q.stop()
                print(f"Stopped '{QUERY_NAME}' after {run_for_seconds}s (demo safety).")
            else:
                print("Stream already stopped.")
        except Exception as e:
            print("Stop:", e)
    print("Final bronze.grants =", last_n)

# COMMAND ----------

n = spark.table(f"`{catalog}`.`bronze`.grants").count()
recent = spark.sql(
    f"""
    SELECT COUNT(*) AS last_2_min
    FROM `{catalog}`.`bronze`.grants
    WHERE _ingest_time >= current_timestamp() - INTERVAL 2 MINUTES
    """
).collect()[0][0]
print(f"bronze.grants = {n:,}   ingested in last 2 min = {recent:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Publish stream batch — bronze → silver → gold
# MAGIC
# MAGIC Silver dedupes on `grant_no` (keeps latest `_ingest_time`). Bronze keeps
# MAGIC the extra stream rows as the file-arrival proof. Do **not** run 02's
# MAGIC bronze quarantine here — that would delete those rows.
# MAGIC
# MAGIC Restore baseline / `05_reset_demo` deletes `stream-demo-2026`.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

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

f.groupBy("fiscal_year", "quarter", "category").agg(
    F.sum("budget_allocated").alias("budget_plan"), F.sum("actual_expenditure").alias("actual_spend"),
).withColumn("execution_rate", F.round(F.col("actual_spend") / F.col("budget_plan") * 100, 2)).withColumn("variance", F.col("budget_plan") - F.col("actual_spend")).withColumn("variance_pct", F.round(F.col("variance") / F.col("budget_plan") * 100, 2)).withColumn("status", F.when(F.col("execution_rate") >= 90, "ON_TARGET").when(F.col("execution_rate") >= 80, "WARNING").otherwise("AT_RISK")).withColumn("_updated_at", F.current_timestamp()).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalog}`.`gold`.budget_execution")

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

stream_n = spark.table(f"`{catalog}`.`bronze`.grants").filter("_batch_id = 'stream-demo-2026'").count()
silver_n = spark.table(f"`{catalog}`.`silver`.grants").filter("_is_active").count()
print(f"Published medallion. stream bronze rows={stream_n:,}  silver.grants={silver_n:,}")
print("Restore baseline deletes stream-demo-2026 from bronze then rebuilds silver/gold.")
