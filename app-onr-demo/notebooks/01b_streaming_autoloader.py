# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**
# MAGIC
# MAGIC # 01b — Live Auto Loader stream (Element 3)
# MAGIC
# MAGIC Same `cloudFiles` path as `01_bronze_ingestion.py`, but the trigger is
# MAGIC **`processingTime`** (near-real-time), not `availableNow` (batch).
# MAGIC
# MAGIC **Recording beat (do not Reset on camera):**
# MAGIC 1. App Process already landed Live 8 + quality-fail (silver **408**).
# MAGIC 2. **Run all** here. 30-second micro-batches; **auto-stops** after
# MAGIC    `run_for_seconds` (default 90).
# MAGIC 3. While it is running, copy
# MAGIC    `/Volumes/onr_demo/bronze/landing/_staged/batch_live_grants.csv`
# MAGIC    → `/Volumes/onr_demo/bronze/landing/grants/batch_live_grants_stream.csv`
# MAGIC    (new filename so Auto Loader sees a new path).
# MAGIC 4. Watch `last_2_min` / `inputRows` tick. Silver stays 408 (dedupe). Bronze
# MAGIC    may grow — that is the stream proof.
# MAGIC
# MAGIC Checkpoint is **`.../checkpoints/grants_stream`** so it does not collide with
# MAGIC the availableNow job in notebook 01.
# MAGIC
# MAGIC Then run `02` + `03` (or Process/Reset in the app) to refresh silver/gold.

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")
dbutils.widgets.text("processing_seconds", "30")
dbutils.widgets.text("run_for_seconds", "90")
dbutils.widgets.dropdown("trigger_mode", "processingTime", ["processingTime", "availableNow"])

catalog = dbutils.widgets.get("catalog")
processing_seconds = dbutils.widgets.get("processing_seconds").strip() or "30"
run_for_seconds = int(dbutils.widgets.get("run_for_seconds") or "90")
trigger_mode = dbutils.widgets.get("trigger_mode")

landing = f"/Volumes/{catalog}/bronze/landing/"
ckpt = f"/Volumes/{catalog}/bronze/checkpoints/grants_stream"
schema_loc = f"{landing}_schemas/grants_stream"

for p in (f"{landing}grants", schema_loc, ckpt):
    try:
        dbutils.fs.mkdirs(p)
    except Exception:
        pass

spark.sql(f"USE CATALOG `{catalog}`")
print(f"catalog={catalog}  trigger={trigger_mode}  interval={processing_seconds}s  run_for={run_for_seconds}s")

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, input_file_name, lit
from pyspark.sql.types import *
import time

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

src = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", schema_loc)
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("header", "true")
    .schema(grants_schema)
    .load(f"{landing}grants/")
    .withColumn("_ingest_time", current_timestamp())
    .withColumn("_source_file", input_file_name())
    .withColumn("_batch_id", lit("stream-demo-2026"))
)

writer = (
    src.writeStream
    .format("delta")
    .option("checkpointLocation", ckpt)
    .option("mergeSchema", "true")
    .outputMode("append")
    .queryName("onr_grants_processingTime")
)

if trigger_mode == "availableNow":
    q = writer.trigger(availableNow=True).toTable(f"`{catalog}`.`bronze`.grants")
    q.awaitTermination()
    print("availableNow stream finished")
else:
    q = writer.trigger(processingTime=f"{processing_seconds} seconds").toTable(
        f"`{catalog}`.`bronze`.grants"
    )
    print(
        f"Stream '{q.name}' started. Drop a CSV into {landing}grants/ now. "
        f"Auto-stop in {run_for_seconds}s."
    )
    t0 = time.time()
    last_n = None
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
    if q.isActive:
        q.stop()
        print("Stopped after run_for_seconds (demo safety).")
    else:
        print("Stream already stopped.")
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
print("Next: run 02_silver_quality.py then 03_gold_aggregation.py, or Process in the app.")
