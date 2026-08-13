# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**
# MAGIC
# MAGIC # 05 — Reset demo to seed
# MAGIC
# MAGIC 1. Deletes non-seed bronze rows (`live-demo-2026`, `quality-fail-2026`, uploads)
# MAGIC 2. Rebuilds silver + gold
# MAGIC 3. Deletes Auto Loader checkpoints so the same files can be ingested again
# MAGIC
# MAGIC If bronze is empty or not 400, run **`00_bootstrap.py`** after this.

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")
catalog = dbutils.widgets.get("catalog")
SEED = "seed-initial-2026"

# COMMAND ----------

spark.sql(f"""
DELETE FROM `{catalog}`.`bronze`.grants
WHERE coalesce(batch_id, '{SEED}') <> '{SEED}'
   OR coalesce(_batch_id, '{SEED}') <> '{SEED}'
""")
spark.sql(f"""
DELETE FROM `{catalog}`.`bronze`.financial
WHERE coalesce(batch_id, '{SEED}') <> '{SEED}'
   OR coalesce(_batch_id, '{SEED}') <> '{SEED}'
""")
print("bronze.grants", spark.table(f"`{catalog}`.`bronze`.grants").count())

# COMMAND ----------

# Rebuild silver / gold (same rules as 02 / 03)
dbutils.notebook.run("02_silver_quality", 0, {"catalog": catalog})

# COMMAND ----------

dbutils.notebook.run("03_gold_aggregation", 0, {"catalog": catalog})

# COMMAND ----------

ckpt = f"/Volumes/{catalog}/bronze/checkpoints"
try:
    dbutils.fs.rm(ckpt, True)
    dbutils.fs.mkdirs(ckpt)
    print("Cleared checkpoints", ckpt)
except Exception as e:
    print("Checkpoint rm:", e)

n = spark.table(f"`{catalog}`.`silver`.grants").count()
print("RESET COMPLETE — silver.grants =", n)
if n != 400:
    print("WARNING: expected 400. Run 00_bootstrap.py to full-reload the fixture.")
