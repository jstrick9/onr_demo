"""Score Unity Catalog models in the app using the SQL warehouse.

A serverless warehouse cannot run notebook 04c (sklearn + MLflow). The app
already has sklearn; it loads the night-before registered models and writes
gold.grant_predictions / gold.grant_anomaly_scores the same way 04c does.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    try:
        import math

        if isinstance(v, float) and math.isnan(v):
            return "NULL"
    except Exception:
        pass
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float, np.integer, np.floating)):
        try:
            if pd.isna(v):
                return "NULL"
        except Exception:
            pass
        return str(float(v) if isinstance(v, (float, np.floating)) else int(v))
    s = str(v)
    if s.lower() in {"nat", "nan", "none", "null", "n/a"}:
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def _query_df(cursor, sql: str) -> pd.DataFrame:
    cursor.execute(sql)
    cols = [str(d[0]).lower() for d in (cursor.description or [])]
    rows = cursor.fetchall() or []
    return pd.DataFrame(rows, columns=cols)


def _configure_mlflow():
    import mlflow

    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    host = (w.config.host or "").strip()
    if host and not host.startswith("http"):
        host = "https://" + host
    if host:
        os.environ["DATABRICKS_HOST"] = host
    try:
        headers = w.config.authenticate() or {}
        token = headers.get("Authorization", "").split(" ", 1)[-1]
        if token:
            os.environ["DATABRICKS_TOKEN"] = token
    except Exception:
        pass
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")
    return mlflow


def _uc_versions(name: str) -> list[int]:
    """Best-effort list of UC model versions. App SP often cannot search."""
    found: set[int] = set()
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        lister = None
        if hasattr(w, "model_versions") and hasattr(w.model_versions, "list"):
            lister = lambda: w.model_versions.list(full_name=name)
        elif hasattr(w, "registered_models") and hasattr(w.registered_models, "list_versions"):
            lister = lambda: w.registered_models.list_versions(full_name=name)
        if lister:
            for rec in lister() or []:
                ver = getattr(rec, "version", None)
                if ver is not None:
                    found.add(int(ver))
    except Exception:
        pass
    try:
        from mlflow.tracking import MlflowClient

        client = MlflowClient(registry_uri="databricks-uc")
        for filt in (f"name='{name}'", f"name = '{name}'"):
            try:
                for rec in client.search_model_versions(filt) or []:
                    ver = getattr(rec, "version", None)
                    if ver is not None:
                        found.add(int(ver))
            except Exception:
                continue
    except Exception:
        pass
    return sorted(found, reverse=True)


def _uc_model_uris(name: str) -> list[str]:
    """Unity Catalog has no models:/name/latest. Aliases, then numeric versions."""
    uris = [f"models:/{name}@champion", f"models:/{name}@production"]
    versions = _uc_versions(name)
    if versions:
        try:
            from mlflow.tracking import MlflowClient

            MlflowClient(registry_uri="databricks-uc").set_registered_model_alias(
                name=name, alias="champion", version=str(versions[0])
            )
        except Exception:
            pass
    else:
        versions = list(range(1, 9))
    for ver in versions:
        uris.append(f"models:/{name}/{ver}")
    return uris


def _load_sklearn(uris: list[str]):
    _configure_mlflow()
    import mlflow.sklearn

    errors: list[str] = []
    seen: set[str] = set()
    for uri in uris:
        if not uri or uri in seen:
            continue
        seen.add(uri)
        try:
            model = mlflow.sklearn.load_model(uri)
            return model, uri
        except Exception as e:
            try:
                import mlflow.pyfunc

                wrapped = mlflow.pyfunc.load_model(uri)
                inner = getattr(wrapped, "_model_impl", None)
                model = getattr(inner, "sklearn_model", None) or getattr(inner, "_model_impl", None) or wrapped
                return model, uri
            except Exception:
                errors.append(f"{uri}: {str(e).splitlines()[0]}")
    raise RuntimeError(
        "Could not load a registered Unity Catalog model. "
        "Night-before 04 / 04b must have registered the models, and the app "
        "principal needs GRANT EXECUTE ON FUNCTION for them (sql/grant_app_principal.sql). "
        + " | ".join(errors)
    )


def _insert_rows(cursor, catalog: str, schema: str, table: str, columns: list[str], rows: list[tuple]) -> None:
    if not rows:
        return
    col_sql = ", ".join(columns)
    batch = 40
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        values = []
        for rec in chunk:
            values.append("(" + ", ".join(_sql_str(v) for v in rec) + ")")
        cursor.execute(
            f"INSERT INTO `{catalog}`.`{schema}`.{table} ({col_sql}) VALUES " + ", ".join(values)
        )


def score_registered_models(cursor, catalog: str) -> dict:
    """Apply UC champion models to current silver. Does not train."""
    if not cursor:
        raise RuntimeError("SQL warehouse is not connected")

    from utils.anomaly_sql import funding_features_sql

    cursor.execute(funding_features_sql(catalog))
    grants = _query_df(
        cursor,
        f"""
        SELECT grant_no, title, program_area, fiscal_year, amount_usd, awardee, org_unit
        FROM `{catalog}`.`silver`.grants
        WHERE _is_active = true
        """,
    )
    feats = _query_df(
        cursor,
        f"""
        SELECT grant_no, title, program_area, fiscal_year, award_amount, awardee,
               execution_rate, yoy_growth_ratio, amount_vs_area_median,
               anomaly_type, is_known_anomaly
        FROM `{catalog}`.`gold`.funding_features
        """,
    )
    if grants.empty or len(grants) < 8:
        raise RuntimeError("silver.grants is empty — ingest the portfolio first")

    rf, rf_uri = _load_sklearn(_uc_model_uris(f"{catalog}.gold.grant_large_award"))
    ife, if_uri = _load_sklearn(_uc_model_uris(f"{catalog}.gold.funding_anomaly_detector"))

    pdf = grants.dropna(subset=["amount_usd", "program_area", "fiscal_year"]).copy()
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

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out_rf = pdf[["grant_no", "title", "program_area", "amount_usd", "awardee"]].copy()
    out_rf["success_probability"] = pd.Series(scores).astype(float).round(4).to_numpy()
    out_rf["risk_factors"] = out_rf["amount_usd"].map(
        lambda a: "Large award concentration" if float(a or 0) >= 2_000_000 else "Standard portfolio risk"
    )
    out_rf["recommendation"] = out_rf["success_probability"].map(
        lambda p: "Fund" if p >= 0.70 else ("Review" if p >= 0.45 else "Defer")
    )
    out_rf["model_name"] = "rf_large_award_v1"

    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.grant_predictions (
            grant_no STRING,
            title STRING,
            program_area STRING,
            amount_usd DOUBLE,
            awardee STRING,
            success_probability DOUBLE,
            risk_factors STRING,
            recommendation STRING,
            model_name STRING,
            scored_at TIMESTAMP
        ) USING DELTA
        """
    )
    rf_rows = []
    for rec in out_rf.to_dict(orient="records"):
        rf_rows.append(
            (
                rec.get("grant_no"),
                rec.get("title"),
                rec.get("program_area"),
                float(rec.get("amount_usd") or 0),
                rec.get("awardee"),
                float(rec.get("success_probability") or 0),
                rec.get("risk_factors"),
                rec.get("recommendation"),
                rec.get("model_name"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    _insert_rows(
        cursor,
        catalog,
        "gold",
        "grant_predictions",
        [
            "grant_no",
            "title",
            "program_area",
            "amount_usd",
            "awardee",
            "success_probability",
            "risk_factors",
            "recommendation",
            "model_name",
            "scored_at",
        ],
        rf_rows,
    )

    if feats.empty:
        raise RuntimeError("gold.funding_features is empty after rebuild")
    FEATURES_NUM = ["award_amount", "yoy_growth_ratio", "execution_rate", "amount_vs_area_median"]
    FEATURES_CAT = ["program_area"]
    X = feats[FEATURES_NUM + FEATURES_CAT].copy()
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

    out_if = feats.copy()
    out_if["amount_usd"] = pd.to_numeric(out_if["award_amount"], errors="coerce")
    out_if["anomaly_score"] = [float(x) for x in scaled]
    out_if["is_flagged"] = [bool(x) for x in (raw == -1)]

    def _pred_type(row):
        if row["is_flagged"] and str(row.get("anomaly_type") or "") != "none":
            return row["anomaly_type"]
        if row["is_flagged"] and float(row.get("amount_usd") or 0) >= 2_000_000:
            return "budget_spike"
        if row["is_flagged"]:
            return "execution_collapse"
        return "none"

    out_if["predicted_type"] = out_if.apply(_pred_type, axis=1)
    out_if["model_name"] = "iforest_funding_v1"

    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.grant_anomaly_scores (
            grant_no STRING,
            title STRING,
            program_area STRING,
            fiscal_year INT,
            amount_usd DOUBLE,
            awardee STRING,
            execution_rate DOUBLE,
            yoy_growth_ratio DOUBLE,
            amount_vs_area_median DOUBLE,
            anomaly_score DOUBLE,
            is_flagged BOOLEAN,
            predicted_type STRING,
            anomaly_type STRING,
            is_known_anomaly INT,
            model_name STRING,
            scored_at TIMESTAMP
        ) USING DELTA
        """
    )
    if_rows = []
    for rec in out_if.to_dict(orient="records"):
        try:
            fy = int(float(rec.get("fiscal_year") or 0))
        except (TypeError, ValueError):
            fy = 0
        try:
            known = int(float(rec.get("is_known_anomaly") or 0))
        except (TypeError, ValueError):
            known = 0
        if_rows.append(
            (
                rec.get("grant_no"),
                rec.get("title"),
                rec.get("program_area"),
                fy,
                float(rec.get("amount_usd") or 0),
                rec.get("awardee"),
                float(rec.get("execution_rate") or 0),
                float(rec.get("yoy_growth_ratio") or 0),
                float(rec.get("amount_vs_area_median") or 0),
                float(rec.get("anomaly_score") or 0),
                bool(rec.get("is_flagged")),
                rec.get("predicted_type"),
                rec.get("anomaly_type"),
                known,
                rec.get("model_name"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    _insert_rows(
        cursor,
        catalog,
        "gold",
        "grant_anomaly_scores",
        [
            "grant_no",
            "title",
            "program_area",
            "fiscal_year",
            "amount_usd",
            "awardee",
            "execution_rate",
            "yoy_growth_ratio",
            "amount_vs_area_median",
            "anomaly_score",
            "is_flagged",
            "predicted_type",
            "anomaly_type",
            "is_known_anomaly",
            "model_name",
            "scored_at",
        ],
        if_rows,
    )

    n_fund = int((out_rf["recommendation"] == "Fund").sum())
    n_review = int((out_rf["recommendation"] == "Review").sum())
    n_defer = int((out_rf["recommendation"] == "Defer").sum())
    n_flag = int(out_if["is_flagged"].sum())
    return {
        "n_rf": int(len(out_rf)),
        "n_if": int(len(out_if)),
        "n_fund": n_fund,
        "n_review": n_review,
        "n_defer": n_defer,
        "n_flag": n_flag,
        "rf_uri": rf_uri,
        "if_uri": if_uri,
        "via": "warehouse",
    }
