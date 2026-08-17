# Lakeflow Declarative Pipeline (SDP) — Element 3 streaming table
#
# Deployed by databricks.yml as pipeline `onr-demo-grants-stream` (triggered,
# not continuous). This is the IaC twin of notebook 01b:
#   cloudFiles → bronze.grants_stream with DLT/SDP expectations.
#
# It writes a *sibling* streaming table so it never fights the batch
# bronze.grants used by the app and the availableNow job.
#
# Run from Workflows → Pipelines → onr-demo-grants-stream → Start,
# then drop a CSV into /Volumes/onr_demo/bronze/landing/grants/.

from pyspark import pipelines as dp
from pyspark.sql.functions import col, current_timestamp, lit


LANDING = "/Volumes/onr_demo/bronze/landing/grants/"
SCHEMA_LOC = "/Volumes/onr_demo/bronze/landing/_schemas/sdp_grants"


@dp.table(
    name="grants_stream",
    comment="Element 3 — Auto Loader streaming table (SDP). Sibling of bronze.grants.",
)
@dp.expect_or_drop("valid_grant_no", "grant_no IS NOT NULL AND length(trim(grant_no)) > 0")
@dp.expect("non_negative_amount", "amount_usd IS NULL OR amount_usd > 0")
def grants_stream():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaLocation", SCHEMA_LOC)
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .load(LANDING)
        .withColumn("_ingest_time", current_timestamp())
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("_batch_id", lit("sdp-stream-2026"))
    )
