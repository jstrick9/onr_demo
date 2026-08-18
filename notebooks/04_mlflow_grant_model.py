# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # 04 — MLflow large-award model (Element 5)
# MAGIC Trains a Random Forest on `silver.grants` to score whether an award is large (≥ $1M).
# MAGIC Writes **`gold.grant_predictions`** and **`gold.model_metrics`** so the Streamlit app
# MAGIC shows the same scores. Logs to MLflow experiment `/Shared/onr-demo/grant-size` and
# MAGIC registers the model to Unity Catalog as `{catalog}.gold.grant_large_award`.
# MAGIC
# MAGIC First cells install scikit-learn (standard DBR does not ship it).

# COMMAND ----------

dbutils.widgets.text("catalog", "onr_demo")

# COMMAND ----------

# MAGIC %pip install scikit-learn pandas --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

catalog = dbutils.widgets.get("catalog")

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
    import mlflow.sklearn

    mlflow.set_registry_uri("databricks-uc")
    experiment_path = "/Shared/onr-demo/grant-size"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        for folder in ("/Shared/onr-demo", "/Workspace/Shared/onr-demo"):
            try:
                w.workspace.mkdirs(folder)
            except Exception:
                pass
    except Exception:
        pass
    try:
        mlflow.set_experiment(experiment_path)
    except Exception:
        try:
            mlflow.create_experiment(experiment_path)
            mlflow.set_experiment(experiment_path)
        except Exception as e:
            print("MLflow experiment create failed:", e)
            experiment_path = "/Shared/grant-size-onr-demo"
            try:
                mlflow.set_experiment(experiment_path)
            except Exception:
                mlflow.create_experiment(experiment_path)
                mlflow.set_experiment(experiment_path)
            print("Fell back to", experiment_path)

    registered = f"{catalog}.gold.grant_large_award"
    with mlflow.start_run(run_name="rf-large-award"):
        mlflow.log_params({
            "n_estimators": 80,
            "max_depth": 8,
            "threshold_usd": 1_000_000,
        })
        mlflow.log_metrics({"accuracy": acc, "f1": f1})
        mlflow.sklearn.log_model(
            clf,
            artifact_path="model",
            registered_model_name=registered,
        )
    try:
        from mlflow.tracking import MlflowClient

        client = MlflowClient(registry_uri="databricks-uc")
        found = list(client.search_model_versions(f"name='{registered}'"))
        found.sort(key=lambda v: int(getattr(v, "version", 0) or 0), reverse=True)
        if found:
            client.set_registered_model_alias(
                name=registered, alias="champion", version=str(found[0].version)
            )
            print(f"alias champion -> {found[0].version}")
    except Exception as alias_e:
        print("Could not set champion alias:", alias_e)
    print(f"Logged to MLflow and registered {registered}")
except Exception as e:
    print("MLflow optional — skipped:", e)
    print("gold.grant_predictions / gold.model_metrics still written above.")

display(pd.DataFrame({"metric": ["accuracy", "f1", "rows"], "value": [acc, f1, len(pdf)]}))
