# Databricks notebook source
# MAGIC %md
# MAGIC **Compute:** all-purpose cluster **`onr demo cluster`**  
# MAGIC **SQL / App:** serverless warehouse **`onr demo warehouse`**  
# MAGIC # 04 — Tiny MLflow demo (Element 5)
# MAGIC Trains a simple model on `onr_demo.silver.grants` to predict whether an award
# MAGIC is "large" (>$1M). Logs to MLflow if available. Safe to skip if MLflow is off.

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
X = pd.get_dummies(pdf[["fiscal_year", "program_area", "org_unit"]], dummy_na=True)
y = pdf["large_award"]
split_kw = {"test_size": 0.25, "random_state": 42}
if y.nunique() > 1 and y.value_counts().min() >= 2:
    split_kw["stratify"] = y
X_train, X_test, y_train, y_test = train_test_split(X, y, **split_kw)

clf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42)
clf.fit(X_train, y_train)
pred = clf.predict(X_test)
acc = accuracy_score(y_test, pred)
f1 = f1_score(y_test, pred, zero_division=0)
print(f"accuracy={acc:.3f}  f1={f1:.3f}  n={len(pdf)}")

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
