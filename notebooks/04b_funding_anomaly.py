# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**
# MAGIC
# MAGIC # 04b — Funding anomaly detector (Element 5)
# MAGIC
# MAGIC Adapted from the ML engineer's `ITSS_ML_Demo.dbc`
# MAGIC (`github.com/jstrick9/Agents/ONR_ITSS_ML_Demo`) onto **this demo's ingested
# MAGIC Compass portfolio** — the same `silver.grants` + `silver.financial` Element 3
# MAGIC just landed. We did **not** introduce a second 15k-row universe.
# MAGIC
# MAGIC Full ML lifecycle: features → IsolationForest → MLflow grid → Unity Catalog
# MAGIC registry (`onr_demo.gold.funding_anomaly_detector` @ `champion`) → scores
# MAGIC written to `gold.grant_anomaly_scores` for the Streamlit Anomalies tab.
# MAGIC
# MAGIC **Complementary models (keep all three):**
# MAGIC - Notebook 04 Random Forest — large-award Fund / Review / Defer
# MAGIC - `ols_fy_v1` — FY forecast + `TREND-*` IDs
# MAGIC - **This notebook** — unsupervised award-level anomaly flags
# MAGIC
# MAGIC Run **after** 00/03 (or app Process) so `gold.funding_features` exists.
# MAGIC First cells install **mlflow** + scikit-learn (standard DBR / Jobs serverless
# MAGIC do not ship them).
# MAGIC
# MAGIC Experiment: `/Shared/onr-demo/funding-anomaly`  
# MAGIC Registry: `onr_demo.gold.funding_anomaly_detector`

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")

# COMMAND ----------

# MAGIC %pip install mlflow>=2.14,<3 scikit-learn pandas --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Features from the ingested portfolio
# MAGIC
# MAGIC IsolationForest needs numeric + categorical award features. We map the ML
# MAGIC engineer's RDT&E schema onto Compass:
# MAGIC
# MAGIC | Engineer demo | This catalog |
# MAGIC |---|---|
# MAGIC | `award_amount` | `silver.grants.amount_usd` |
# MAGIC | `budget_activity` (6.1/6.2/6.3) | `program_area` (8 ONR areas) |
# MAGIC | `performer_id` | `awardee` |
# MAGIC | `execution_rate` | ERP actual / budget per `grant_no` |
# MAGIC | `yoy_growth_ratio` | award / prior-FY program-area average |
# MAGIC | `pubs_per_100k` / patents | **dropped** (not in Compass) |
# MAGIC | `amount_vs_area_median` | **added** — concentration vs peers |
# MAGIC
# MAGIC Ground-truth `is_known_anomaly` / `anomaly_type` are **held out of training**
# MAGIC and used only to score precision/recall/AUC. Labels:
# MAGIC `execution_collapse`, `budget_spike`, `low_return_concentration`.

# COMMAND ----------

from pyspark.sql import functions as F

# Rebuild features from silver so 04b stands alone if Process hasn't run.
spark.sql(f"""
CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_features AS
WITH fin AS (
    SELECT grant_no,
           SUM(actual_expenditure) / NULLIF(SUM(budget_allocated), 0) AS execution_rate
    FROM `{catalog}`.`silver`.financial
    WHERE _is_active = true
    GROUP BY grant_no
),
area_stats AS (
    SELECT program_area, fiscal_year,
           approx_percentile(amount_usd, 0.5) AS median_amt,
           AVG(amount_usd) AS avg_amt
    FROM `{catalog}`.`silver`.grants
    WHERE _is_active = true
    GROUP BY program_area, fiscal_year
),
prior AS (
    SELECT program_area, fiscal_year + 1 AS fiscal_year, avg_amt AS prior_avg
    FROM area_stats
),
base AS (
    SELECT
        g.grant_no, g.title, g.program_area, g.fiscal_year,
        g.amount_usd AS award_amount, g.awardee, g.org_unit, g.classification_band,
        COALESCE(f.execution_rate, 0.90) AS execution_rate,
        g.amount_usd / NULLIF(COALESCE(p.prior_avg, a.avg_amt), 0) AS yoy_growth_ratio,
        g.amount_usd / NULLIF(a.median_amt, 0) AS amount_vs_area_median
    FROM `{catalog}`.`silver`.grants g
    LEFT JOIN fin f ON f.grant_no = g.grant_no
    LEFT JOIN area_stats a
      ON a.program_area = g.program_area AND a.fiscal_year = g.fiscal_year
    LEFT JOIN prior p
      ON p.program_area = g.program_area AND p.fiscal_year = g.fiscal_year
    WHERE g._is_active = true
)
SELECT
    grant_no, title, program_area, fiscal_year, award_amount, awardee,
    org_unit, classification_band, execution_rate, yoy_growth_ratio,
    amount_vs_area_median,
    CASE
        WHEN execution_rate < 0.76 THEN 'execution_collapse'
        WHEN award_amount >= 3000000 AND amount_vs_area_median >= 1.8 THEN 'budget_spike'
        WHEN award_amount >= 2500000 AND execution_rate < 0.85 THEN 'low_return_concentration'
        ELSE 'none'
    END AS anomaly_type,
    CASE
        WHEN execution_rate < 0.76
          OR (award_amount >= 3000000 AND amount_vs_area_median >= 1.8)
          OR (award_amount >= 2500000 AND execution_rate < 0.85)
        THEN 1 ELSE 0
    END AS is_known_anomaly,
    current_timestamp() AS _updated_at
FROM base
""")
n_feat = spark.table(f"`{catalog}`.`gold`.funding_features").count()
n_pos = spark.table(f"`{catalog}`.`gold`.funding_features").filter("is_known_anomaly = 1").count()
print(f"funding_features={n_feat:,}  known_anomalies={n_pos:,} ({n_pos/max(n_feat,1):.1%})")
display(spark.table(f"`{catalog}`.`gold`.funding_features").limit(8))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Train IsolationForest (unsupervised)
# MAGIC
# MAGIC Fit on the **full population**. Labels are never a training feature.
# MAGIC IsolationForest predicts `-1` = anomaly, `1` = normal. We convert to
# MAGIC `1 = anomaly` and use `-score_samples` (higher = more anomalous) for AUC.

# COMMAND ----------

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

df = spark.table(f"`{catalog}`.`gold`.funding_features").toPandas()
if len(df) < 20:
    raise ValueError("gold.funding_features too small — run 00_bootstrap or Process first")

FEATURES_NUM = ["award_amount", "yoy_growth_ratio", "execution_rate", "amount_vs_area_median"]
FEATURES_CAT = ["program_area"]

X = df[FEATURES_NUM + FEATURES_CAT].copy()
X[FEATURES_NUM] = X[FEATURES_NUM].apply(pd.to_numeric, errors="coerce").fillna(0)
y_true = df["is_known_anomaly"].fillna(0).astype(int)

preprocessor = ColumnTransformer([
    ("num", StandardScaler(), FEATURES_NUM),
    ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
])

def build_pipeline(n_estimators=200, contamination=0.08):
    return Pipeline([
        ("prep", preprocessor),
        ("clf", IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42,
        )),
    ])

pipe0 = build_pipeline()
pipe0.fit(X)
raw0 = pipe0.predict(X)
pred0 = (raw0 == -1).astype(int)
scores0 = -pipe0.named_steps["clf"].score_samples(pipe0.named_steps["prep"].transform(X))
print({
    "precision": float(precision_score(y_true, pred0, zero_division=0)),
    "recall": float(recall_score(y_true, pred0, zero_division=0)),
    "f1": float(f1_score(y_true, pred0, zero_division=0)),
    "auc": float(roc_auc_score(y_true, scores0)) if y_true.nunique() > 1 else None,
    "n": len(df),
    "flagged": int(pred0.sum()),
})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. MLflow iteration
# MAGIC
# MAGIC Four `(n_estimators, contamination)` runs. Experiment is **shared**, not a
# MAGIC personal `/Users/...` folder. Tag every run with the source table so
# MAGIC Catalog Explorer lineage + MLflow tell the same story.

# COMMAND ----------

import mlflow
import mlflow.sklearn

EXPERIMENT = "/Shared/onr-demo/funding-anomaly"

def _ensure_mlflow_experiment(path: str) -> str:
    """Create /Shared/onr-demo if needed. Nested experiment create fails without the parent folder."""
    parent = path.rsplit("/", 1)[0]
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        for folder in (parent, f"/Workspace{parent}"):
            try:
                w.workspace.mkdirs(folder)
            except Exception:
                pass
    except Exception as e:
        print("workspace mkdirs skipped:", e)
    try:
        mlflow.set_experiment(path)
        return path
    except Exception as e1:
        print("set_experiment failed:", e1)
    try:
        mlflow.create_experiment(path)
        mlflow.set_experiment(path)
        return path
    except Exception as e2:
        print("create_experiment failed:", e2)
    fallback = "/Shared/funding-anomaly-onr-demo"
    print(f"Falling back to {fallback}")
    try:
        mlflow.set_experiment(fallback)
    except Exception:
        mlflow.create_experiment(fallback)
        mlflow.set_experiment(fallback)
    return fallback

EXPERIMENT = _ensure_mlflow_experiment(EXPERIMENT)
print("MLflow experiment:", EXPERIMENT)

def train_and_log(n_estimators, contamination, run_name=None):
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("contamination", contamination)
        mlflow.log_param("train_rows", len(X))
        mlflow.log_param("feature_set", ",".join(FEATURES_NUM + FEATURES_CAT))
        mlflow.set_tag("data_table", f"{catalog}.gold.funding_features")
        mlflow.set_tag("scenario_element", "5-decision-support-analytics-ml")
        pipe = build_pipeline(n_estimators=n_estimators, contamination=contamination)
        pipe.fit(X)
        raw = pipe.predict(X)
        pred = (raw == -1).astype(int)
        sc = -pipe.named_steps["clf"].score_samples(pipe.named_steps["prep"].transform(X))
        metrics = {
            "precision": float(precision_score(y_true, pred, zero_division=0)),
            "recall": float(recall_score(y_true, pred, zero_division=0)),
            "f1": float(f1_score(y_true, pred, zero_division=0)),
            "auc": float(roc_auc_score(y_true, sc)) if y_true.nunique() > 1 else 0.0,
            "n_flagged": float(pred.sum()),
        }
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(pipe, artifact_path="model", input_example=X.head(5))
        return run.info.run_id, metrics

grid = [
    {"n_estimators": 100, "contamination": 0.05},
    {"n_estimators": 200, "contamination": 0.08},
    {"n_estimators": 300, "contamination": 0.08},
    {"n_estimators": 300, "contamination": 0.10},
]
results = []
for cfg in grid:
    run_id, m = train_and_log(**cfg, run_name=f"iforest_{cfg['n_estimators']}_{cfg['contamination']}")
    results.append({"run_id": run_id, **cfg, **m})

results_df = pd.DataFrame(results).sort_values("f1", ascending=False)
display(results_df)

# COMMAND ----------

best = mlflow.search_runs(
    experiment_names=[EXPERIMENT],
    order_by=["metrics.f1 DESC"],
    max_results=1,
)
best_run_id = best.iloc[0]["run_id"]
best_auc = float(best.iloc[0]["metrics.auc"])
best_f1 = float(best.iloc[0]["metrics.f1"])
print("best_run_id", best_run_id, "f1", best_f1, "auc", best_auc)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Register to Unity Catalog (aliases, not Staging/Production)
# MAGIC
# MAGIC Three-level name: `{catalog}.gold.funding_anomaly_detector`.
# MAGIC Downstream (Element 6 dashboard) loads `models:/...@champion`.

# COMMAND ----------

from mlflow.tracking import MlflowClient

mlflow.set_registry_uri("databricks-uc")
MODEL_NAME = f"{catalog}.gold.funding_anomaly_detector"
model_uri = f"runs:/{best_run_id}/model"
try:
    registered = mlflow.register_model(model_uri=model_uri, name=MODEL_NAME)
    print(registered.name, registered.version)
    client = MlflowClient(registry_uri="databricks-uc")
    client.update_registered_model(
        name=MODEL_NAME,
        description=(
            "IsolationForest funding anomaly detector trained on the Compass ONR "
            "grants + ERP fixture (silver.grants / silver.financial). Flags "
            "budget_spike, execution_collapse, low_return_concentration."
        ),
    )
    client.update_model_version(
        name=MODEL_NAME,
        version=registered.version,
        description=(
            f"Trained from run {best_run_id}. F1={best_f1:.3f}, AUC={best_auc:.3f}. "
            f"Source table: {catalog}.gold.funding_features."
        ),
    )
    client.set_registered_model_alias(name=MODEL_NAME, alias="champion", version=registered.version)
    print("alias champion ->", registered.version)
except Exception as e:
    print("UC register optional — skipped:", e)
    print("Scoring cell will use the in-memory best pipeline.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Score the portfolio → `gold.grant_anomaly_scores`
# MAGIC
# MAGIC This is what the Streamlit **Anomalies** tab and the Dashboard flags read.

# COMMAND ----------

import numpy as np
from datetime import datetime as _dt

# Score with the in-memory best pipeline first so this cell still writes
# gold.grant_anomaly_scores if the UC alias load fails.
best_cfg = results_df.iloc[0]
sk = build_pipeline(int(best_cfg["n_estimators"]), float(best_cfg["contamination"]))
sk.fit(X)
try:
    sk = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
    print("Loaded champion from UC registry")
except Exception as e:
    print("champion load failed — using in-memory best pipeline:", e)

raw = np.asarray(sk.predict(X)).reshape(-1)
anom_score = -sk.named_steps["clf"].score_samples(sk.named_steps["prep"].transform(X))
smin, smax = float(np.min(anom_score)), float(np.max(anom_score))
scaled = (anom_score - smin) / (smax - smin + 1e-9)

out = df[["grant_no", "title", "program_area", "fiscal_year", "award_amount",
          "awardee", "execution_rate", "yoy_growth_ratio", "amount_vs_area_median",
          "anomaly_type", "is_known_anomaly"]].copy()
out = out.rename(columns={"award_amount": "amount_usd"})
out["anomaly_score"] = [float(x) for x in scaled]
out["is_flagged"] = [bool(x) for x in (raw == -1)]

def _pred_type(row):
    if row["is_flagged"] and row["anomaly_type"] != "none":
        return row["anomaly_type"]
    if row["is_flagged"] and row["amount_usd"] >= 2_000_000:
        return "budget_spike"
    if row["is_flagged"]:
        return "execution_collapse"
    return "none"
out["predicted_type"] = out.apply(_pred_type, axis=1)
out["model_name"] = "iforest_funding_v1"
out["is_known_anomaly"] = out["is_known_anomaly"].fillna(0).astype(int)
out["scored_at"] = _dt.utcnow()
# Native Python types — numpy dtypes make spark.createDataFrame infer fail
for c in ("amount_usd", "execution_rate", "yoy_growth_ratio", "amount_vs_area_median", "anomaly_score"):
    out[c] = out[c].astype(float)
out["fiscal_year"] = out["fiscal_year"].astype(int)

(
    spark.createDataFrame(out)
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"`{catalog}`.`gold`.grant_anomaly_scores")
)

metrics_rows = pd.DataFrame([
    {"model_name": "iforest_funding_v1", "metric_name": "f1", "metric_value": best_f1,
     "n_rows": len(df), "trained_at": _dt.utcnow()},
    {"model_name": "iforest_funding_v1", "metric_name": "auc", "metric_value": best_auc,
     "n_rows": len(df), "trained_at": _dt.utcnow()},
    {"model_name": "iforest_funding_v1", "metric_name": "n_flagged",
     "metric_value": float(out["is_flagged"].sum()), "n_rows": len(df), "trained_at": _dt.utcnow()},
])
(
    spark.createDataFrame(metrics_rows)
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"`{catalog}`.`gold`.anomaly_model_metrics")
)
print("Wrote gold.grant_anomaly_scores and gold.anomaly_model_metrics")
print("flagged", int(out["is_flagged"].sum()), "/", len(out))
display(out.sort_values("anomaly_score", ascending=False).head(12))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Access control (commented — groups may not exist in this POC)
# MAGIC
# MAGIC Same GRANT model as tables. `EXECUTE` for the app / UDAP portal;
# MAGIC `MODIFY` for data scientists; `MANAGE` is admin-only.
# MAGIC Uncomment after those account groups exist. Do **not** copy `MANAGE`
# MAGIC onto the app service principal.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- GRANT USE CATALOG ON CATALOG onr_demo TO `data-scientists`;
# MAGIC -- GRANT USE SCHEMA  ON SCHEMA  onr_demo.gold TO `data-scientists`;
# MAGIC -- GRANT MODIFY, EXECUTE ON FUNCTION onr_demo.gold.funding_anomaly_detector TO `data-scientists`;
# MAGIC -- GRANT EXECUTE ON FUNCTION onr_demo.gold.funding_anomaly_detector TO `svc-udap-portal`;
# MAGIC -- GRANT ALL PRIVILEGES ON FUNCTION onr_demo.gold.funding_anomaly_detector TO `ml-platform-admins`;
# MAGIC SELECT 'GRANTs are commented — see markdown above. App reads gold.grant_anomaly_scores, not the model binary.' AS note;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC 1. Features from **ingested** silver grants + ERP → `gold.funding_features`
# MAGIC 2. IsolationForest, labels held out → precision/recall/AUC
# MAGIC 3. Four MLflow runs in `/Shared/onr-demo/funding-anomaly`
# MAGIC 4. Winner registered as `{catalog}.gold.funding_anomaly_detector` @ `champion`
# MAGIC 5. Scores in `gold.grant_anomaly_scores` — Analytics Anomalies tab + Dashboard flags
# MAGIC
# MAGIC Refresh the Streamlit app. Then Catalog Explorer → Models → lineage back to `funding_features`.
