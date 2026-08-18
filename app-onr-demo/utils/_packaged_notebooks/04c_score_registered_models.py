# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** app Score uses **`onr demo ml`** (Dedicated to the app SP).
# MAGIC Night-before 04 / 04b stay on **`onr demo cluster`**.
# MAGIC
# MAGIC # 04c — Score from registered models (Element 5, camera beat)
# MAGIC
# MAGIC This notebook **does not train**. Night-before you ran `04` and `04b`.
# MAGIC On camera you **Run all** here to apply the Unity Catalog models to the
# MAGIC portfolio you just ingested (400 → 408).
# MAGIC
# MAGIC | Model | Registry | Writes |
# MAGIC |---|---|---|
# MAGIC | Random Forest large-award | `onr_demo.gold.grant_large_award` | `gold.grant_predictions` |
# MAGIC | IsolationForest anomalies | `onr_demo.gold.funding_anomaly_detector@champion` | `gold.grant_anomaly_scores` |
# MAGIC
# MAGIC Features are rebuilt from **current** `silver.grants` + `silver.financial`
# MAGIC so the eight live grants are scored. OLS forecast / `TREND-*` IDs stay
# MAGIC where Process / notebook 03 already wrote them.
# MAGIC
# MAGIC If a model is missing, this notebook **fails loudly** — do not improvise
# MAGIC a training run on camera. Stop and open Analytics on the night-before tables.
# MAGIC
# MAGIC Target runtime: **30–90 seconds** if sklearn + mlflow are already on **onr demo ml**.
# MAGIC Do **not** `%pip` here — MAGIC pip writes the Git folder over WSFS and the
# MAGIC app SP gets `RESOURCE_DOES_NOT_EXIST` on `/Users/<you>/onr_demo/notebooks`.
# MAGIC Install mlflow as a **cluster library** on `onr demo ml`.
#
# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")

# COMMAND ----------

# Cluster library first. Driver pip only if missing — never %pip (WSFS write).
import importlib.util
import subprocess
import sys


def _ensure_pkg(mod: str, spec: str) -> None:
    if importlib.util.find_spec(mod) is not None:
        print(f"{mod} present")
        return
    print(f"{mod} missing — driver pip {spec} (no %pip / no workspace write)")
    subprocess.check_call([sys.executable, "-m", "pip", "install", spec, "--quiet"])
    importlib.invalidate_caches()
    if importlib.util.find_spec(mod) is None:
        raise RuntimeError(
            f"Could not import {mod} after pip install {spec}. "
            "Off camera: Compute → onr demo ml → Libraries → install "
            "mlflow and scikit-learn, then restart the cluster and re-run 04c."
        )


_ensure_pkg("sklearn", "scikit-learn")
_ensure_pkg("pandas", "pandas")
_ensure_pkg("mlflow", "mlflow>=2.14,<3")
import mlflow  # noqa: F401
import pandas  # noqa: F401
import sklearn  # noqa: F401

print("sklearn + pandas + mlflow present — scoring only, no training")

# COMMAND ----------

catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Features from the *current* silver portfolio

# COMMAND ----------

from datetime import datetime as _dt, timezone as _tz

import numpy as np
import pandas as pd

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
print(f"funding_features = {n_feat:,}  (expect 408 after the live 8-grant drop)")
if n_feat < 8:
    raise ValueError("silver/gold features are empty — Process Live 8 or run 00_bootstrap first")

# COMMAND ----------

def _run_uris(experiment_paths, artifact="model"):
    """Night-before 04 / 04b log runs even when UC register creates no version."""
    import mlflow

    mlflow.set_registry_uri("databricks-uc")
    uris = []
    for path in experiment_paths:
        try:
            df = mlflow.search_runs(
                experiment_names=[path],
                order_by=["start_time DESC"],
                max_results=8,
            )
        except Exception as e:
            print("experiment search", path, e)
            continue
        if df is None or getattr(df, "empty", True):
            continue
        for run_id in df["run_id"].tolist():
            uris.append(f"runs:/{run_id}/{artifact}")
            print(f"Candidate {path} -> runs:/{run_id}/{artifact}")
    return uris


def _uc_model_uris(name: str):
    """Unity Catalog has no models:/name/latest. Aliases, then numeric versions."""
    uris = [f"models:/{name}@champion", f"models:/{name}@production"]
    versions = []
    try:
        from mlflow.tracking import MlflowClient

        client = MlflowClient(registry_uri="databricks-uc")
        found = list(client.search_model_versions(f"name='{name}'") or [])
        versions = sorted(
            {int(getattr(v, "version", 0) or 0) for v in found if getattr(v, "version", None)},
            reverse=True,
        )
        if versions:
            try:
                client.set_registered_model_alias(name=name, alias="champion", version=str(versions[0]))
                print(f"Set {name}@champion -> {versions[0]}")
            except Exception as e:
                print(f"Could not set {name}@champion ({e}); will load version {versions[0]}")
    except Exception as e:
        print("UC version lookup skipped:", e)
    for ver in versions:
        uris.append(f"models:/{name}/{ver}")
    return uris


def _load_sklearn(uri: str):
    import mlflow
    import mlflow.sklearn

    mlflow.set_registry_uri("databricks-uc")
    model = mlflow.sklearn.load_model(uri)
    print("Loaded", uri)
    return model


def _load_first(uris):
    errors = []
    seen = set()
    for uri in uris:
        if not uri or uri in seen:
            continue
        seen.add(uri)
        try:
            return _load_sklearn(uri), uri
        except Exception as e:
            errors.append(f"{uri}: {str(e).splitlines()[0]}")
    raise RuntimeError(
        "Could not load a registered model or a night-before MLflow run. "
        "Do not train on camera. Open Analytics on the existing gold tables.\n"
        + "\n".join(errors)
    )


def _maybe_register(name: str, uri: str) -> None:
    if not uri.startswith("runs:/"):
        return
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_registry_uri("databricks-uc")
        mv = mlflow.register_model(uri, name)
        MlflowClient(registry_uri="databricks-uc").set_registered_model_alias(
            name=name, alias="champion", version=str(mv.version)
        )
        print(f"Registered {name} v{mv.version} @champion from {uri}")
    except Exception as e:
        msg = str(e).splitlines()[0]
        if "CREATE MODEL" in msg or "PERMISSION_DENIED" in msg:
            print(
                "Register skipped — expected. The app scores; it does not "
                "CREATE MODEL on gold. Night-before 04 / 04b own the registry."
            )
        else:
            print("Register from run skipped:", msg)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Random Forest — `grant_large_award`

# COMMAND ----------

rf, rf_uri = _load_first(
    _uc_model_uris(f"{catalog}.gold.grant_large_award")
    + _run_uris(
        [
            "/Shared/onr-demo/grant-size",
            "/Workspace/Shared/onr-demo/grant-size",
            "/Shared/grant-size-onr-demo",
        ]
    )
)
_maybe_register(f"{catalog}.gold.grant_large_award", rf_uri)

pdf = spark.table(f"`{catalog}`.`silver`.grants").where("_is_active = true").toPandas()
pdf = pdf.dropna(subset=["amount_usd", "program_area", "fiscal_year"])
feat_cols = ["fiscal_year", "program_area", "org_unit"]
X_rf = pd.get_dummies(pdf[feat_cols], dummy_na=True)
feat_names = getattr(rf, "feature_names_in_", None)
if feat_names is not None:
    X_rf = X_rf.reindex(columns=list(feat_names), fill_value=0)

if hasattr(rf, "predict_proba"):
    proba = rf.predict_proba(X_rf)
    classes = list(getattr(rf, "classes_", [0, 1]))
    pos = classes.index(1) if 1 in classes else -1
    scores = proba[:, pos] if pos >= 0 else rf.predict(X_rf).astype(float)
else:
    scores = np.asarray(rf.predict(X_rf), dtype=float)

out_rf = pdf[["grant_no", "title", "program_area", "amount_usd", "awardee"]].copy()
out_rf["success_probability"] = pd.Series(scores).astype(float).round(4).to_numpy()
out_rf["risk_factors"] = out_rf["amount_usd"].map(
    lambda a: "Large award concentration" if a >= 2_000_000 else "Standard portfolio risk"
)
out_rf["recommendation"] = out_rf["success_probability"].map(
    lambda p: "Fund" if p >= 0.70 else ("Review" if p >= 0.45 else "Defer")
)
out_rf["model_name"] = "rf_large_award_v1"
out_rf["scored_at"] = _dt.now(_tz.utc).replace(tzinfo=None)
out_rf["amount_usd"] = out_rf["amount_usd"].astype(float)
out_rf["success_probability"] = out_rf["success_probability"].astype(float)

(
    spark.createDataFrame(out_rf)
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"`{catalog}`.`gold`.grant_predictions")
)

n_fund = int((out_rf["recommendation"] == "Fund").sum())
n_review = int((out_rf["recommendation"] == "Review").sum())
n_defer = int((out_rf["recommendation"] == "Defer").sum())
print(
    f"grant_predictions = {len(out_rf):,}  Fund={n_fund} Review={n_review} Defer={n_defer}"
)
print("RF source:", rf_uri)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. IsolationForest — `funding_anomaly_detector@champion`

# COMMAND ----------

ife, if_uri = _load_first(
    _uc_model_uris(f"{catalog}.gold.funding_anomaly_detector")
    + _run_uris(
        [
            "/Shared/onr-demo/funding-anomaly",
            "/Workspace/Shared/onr-demo/funding-anomaly",
            "/Shared/funding-anomaly-onr-demo",
        ]
    )
)
_maybe_register(f"{catalog}.gold.funding_anomaly_detector", if_uri)

df = spark.table(f"`{catalog}`.`gold`.funding_features").toPandas()
FEATURES_NUM = ["award_amount", "yoy_growth_ratio", "execution_rate", "amount_vs_area_median"]
FEATURES_CAT = ["program_area"]
X = df[FEATURES_NUM + FEATURES_CAT].copy()
X[FEATURES_NUM] = X[FEATURES_NUM].apply(pd.to_numeric, errors="coerce").fillna(0)

raw = np.asarray(ife.predict(X)).reshape(-1)
if hasattr(ife, "named_steps") and "clf" in ife.named_steps and "prep" in ife.named_steps:
    anom_score = -ife.named_steps["clf"].score_samples(ife.named_steps["prep"].transform(X))
elif hasattr(ife, "score_samples"):
    anom_score = -ife.score_samples(X)
else:
    anom_score = (raw == -1).astype(float)
smin, smax = float(np.min(anom_score)), float(np.max(anom_score))
scaled = (anom_score - smin) / (smax - smin + 1e-9)

out_if = df[
    [
        "grant_no", "title", "program_area", "fiscal_year", "award_amount",
        "awardee", "execution_rate", "yoy_growth_ratio", "amount_vs_area_median",
        "anomaly_type", "is_known_anomaly",
    ]
].copy()
out_if = out_if.rename(columns={"award_amount": "amount_usd"})
out_if["anomaly_score"] = [float(x) for x in scaled]
out_if["is_flagged"] = [bool(x) for x in (raw == -1)]

def _pred_type(row):
    if row["is_flagged"] and row["anomaly_type"] != "none":
        return row["anomaly_type"]
    if row["is_flagged"] and row["amount_usd"] >= 2_000_000:
        return "budget_spike"
    if row["is_flagged"]:
        return "execution_collapse"
    return "none"

out_if["predicted_type"] = out_if.apply(_pred_type, axis=1)
out_if["model_name"] = "iforest_funding_v1"
out_if["is_known_anomaly"] = out_if["is_known_anomaly"].fillna(0).astype(int)
out_if["scored_at"] = _dt.now(_tz.utc).replace(tzinfo=None)
for c in ("amount_usd", "execution_rate", "yoy_growth_ratio", "amount_vs_area_median", "anomaly_score"):
    out_if[c] = out_if[c].astype(float)
out_if["fiscal_year"] = out_if["fiscal_year"].astype(int)

(
    spark.createDataFrame(out_if)
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"`{catalog}`.`gold`.grant_anomaly_scores")
)

n_flag = int(out_if["is_flagged"].sum())
print(f"grant_anomaly_scores = {len(out_if):,}  flagged = {n_flag}")
print("IsolationForest source:", if_uri)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Camera readout
# MAGIC
# MAGIC Refresh Analytics. Predictions should read `rf_large_award_v1`.
# MAGIC Anomalies should read `iforest_funding_v1`. New live grants are in both tables.

# COMMAND ----------

print("=" * 56)
print("04c SCORE-FROM-REGISTRY")
print("=" * 56)
print(f"rows scored     : {len(out_rf):,}  (RF) / {len(out_if):,}  (IF)")
print(f"RF model        : {rf_uri}")
print(f"IF model        : {if_uri}")
print(f"Fund/Review/Def : {n_fund} / {n_review} / {n_defer}")
print(f"IF flagged      : {n_flag}")
print("Next: Analytics → Predictions + Anomalies. Do not run 04 / 04b.")
display(
    pd.DataFrame(
        {
            "item": ["rf_uri", "if_uri", "rows_rf", "rows_if", "flagged"],
            "value": [rf_uri, if_uri, len(out_rf), len(out_if), n_flag],
        }
    )
)
