# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # 04 — MLflow large-award model (Element 5)
# MAGIC Trains a Random Forest on `silver.grants` to score whether an award is large (≥ $1M).
# MAGIC Writes **`gold.grant_predictions`** and **`gold.model_metrics`** so the Streamlit app
# MAGIC shows the same scores. Logs to MLflow when the experiment is available.

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

pdf = spark.table(f"`{catalog}`.`silver`.grants").toPandas()
pdf = pdf.dropna(subset=["amount_usd", "program_area", "fiscal_year"])
if len(pdf) < 8:
    raise ValueError("silver.grants has too few rows — run 00_bootstrap.py first")

pdf["large_award"] = (pdf["amount_usd"] >= 1_000_000).astype(int)
feat_cols = ["fiscal_year", "program_area", "org_unit"]
X = pd.get_dummies(pdf[feat_cols], dummy_na=True)
y = pdf["large_award"]
split_kw = {"test_size": 0.25, "random_state": 42}
if y.nunique() > 1 and y.value_counts().min() >= 2:
    split_kw["stratify"] = y
X_train, X_test, y_train, y_test = train_test_split(X, y, **split_kw)

clf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42)
clf.fit(X_train, y_train)
pred = clf.predict(X_test)
acc = float(accuracy_score(y_test, pred))
f1 = float(f1_score(y_test, pred, zero_division=0))
print(f"accuracy={acc:.3f}  f1={f1:.3f}  n={len(pdf)}")

# Score every silver row so the app can display UC-backed predictions
X_all = pd.get_dummies(pdf[feat_cols], dummy_na=True).reindex(columns=X.columns, fill_value=0)
if hasattr(clf, "predict_proba"):
    proba = clf.predict_proba(X_all)
    pos = list(clf.classes_).index(1) if 1 in list(clf.classes_) else -1
    scores = proba[:, pos] if pos >= 0 else pred.astype(float)
else:
    scores = clf.predict(X_all).astype(float)

out = pdf[["grant_no", "title", "program_area", "amount_usd", "awardee"]].copy()
out["success_probability"] = scores.round(4)
out["risk_factors"] = out["amount_usd"].map(
    lambda a: "Large award concentration" if a >= 2_000_000 else "Standard portfolio risk"
)
out["recommendation"] = out["success_probability"].map(
    lambda p: "Fund" if p >= 0.70 else ("Review" if p >= 0.45 else "Defer")
)
out["model_name"] = "rf_large_award_v1"
from datetime import datetime as _dt
out["scored_at"] = _dt.utcnow()

(
    spark.createDataFrame(out)
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"`{catalog}`.`gold`.grant_predictions")
)

metrics = pd.DataFrame([
    {"model_name": "rf_large_award_v1", "metric_name": "accuracy", "metric_value": acc, "n_rows": len(pdf), "trained_at": _dt.utcnow()},
    {"model_name": "rf_large_award_v1", "metric_name": "f1", "metric_value": f1, "n_rows": len(pdf), "trained_at": _dt.utcnow()},
    {"model_name": "rf_large_award_v1", "metric_name": "rows_scored", "metric_value": float(len(out)), "n_rows": len(pdf), "trained_at": _dt.utcnow()},
])
(
    spark.createDataFrame(metrics)
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"`{catalog}`.`gold`.model_metrics")
)
print("Wrote gold.grant_predictions and gold.model_metrics")

try:
    import mlflow
    mlflow.set_experiment("/Shared/onr-demo/grant-size")
    with mlflow.start_run(run_name="rf-large-award"):
        mlflow.log_params({"n_estimators": 80, "max_depth": 8})
        mlflow.log_metrics({"accuracy": acc, "f1": f1})
        mlflow.sklearn.log_model(clf, "model")
    print("Logged to MLflow")
except Exception as e:
    print("MLflow optional — skipped:", e)

display(pd.DataFrame({"metric": ["accuracy", "f1", "rows"], "value": [acc, f1, len(pdf)]}))
