"""
Live demo actions: drop the staged 8-grant file through bronze → silver → gold.

SQL runs on the serverless warehouse named "onr demo warehouse".
Notebooks (01–04) are meant to run on the all-purpose cluster "onr demo cluster".
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Tuple

SEED_BATCH_ID = "seed-initial-2026"
LIVE_BATCH_ID = "live-demo-2026"
QUALITY_FAIL_BATCH_ID = "quality-fail-2026"

_APP_DATA = Path(__file__).resolve().parents[1] / "data"
_REPO_MOCK = Path(__file__).resolve().parents[2] / "resources" / "mock_data"

FILE_PACKS = {
    "live": {
        "label": "Live 8 grants (good file)",
        "batch_id": LIVE_BATCH_ID,
        "files": [
            _APP_DATA / "batch_live_grants.csv",
            _REPO_MOCK / "batch_live_grants.csv",
        ],
    },
    "quality_fail": {
        "label": "Quality-fail sample (3 bad rows)",
        "batch_id": QUALITY_FAIL_BATCH_ID,
        "files": [
            _APP_DATA / "batch_quality_fail.csv",
            _REPO_MOCK / "batch_quality_fail.csv",
        ],
    },
}

_CANDIDATES = FILE_PACKS["live"]["files"]


def _live_csv() -> Path:
    for p in _CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("batch_live_grants.csv not packaged with the app")


def load_live_rows() -> list[dict]:
    with _live_csv().open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grant_count(cursor, catalog: str) -> Optional[int]:
    if not cursor:
        return None
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM `{catalog}`.`silver`.grants WHERE _is_active = true"
        )
        return int(cursor.fetchone()[0])
    except Exception:
        return None


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    try:
        import math
        if isinstance(v, float) and math.isnan(v):
            return "NULL"
    except Exception:
        pass
    s = str(v)
    if s.lower() in {"nat", "nan", "none", "null", "n/a"}:
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def bronze_count(cursor, catalog: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants")
    return int(cursor.fetchone()[0])


def ingest_grant_rows(cursor, catalog: str, rows: list[dict], source_file: str, skip_existing: bool = True) -> dict:
    landed = skipped = rejected = 0
    reasons: list[str] = []
    for rec in rows:
        raw_gn = rec.get("grant_no")
        try:
            import math
            if raw_gn is None or (isinstance(raw_gn, float) and math.isnan(raw_gn)):
                raw_gn = ""
        except Exception:
            pass
        gn = str(raw_gn).strip()
        if not gn or gn.lower() in {"nan", "none", "null"}:
            rejected += 1
            reasons.append("empty grant_no (bronze NOT NULL)")
            continue
        try:
            amount = float(rec.get("amount_usd") or 0)
        except (TypeError, ValueError):
            rejected += 1
            reasons.append(f"{gn}: amount not numeric")
            continue
        if skip_existing:
            cursor.execute(
                f"SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants WHERE grant_no = {_sql_str(gn)}"
            )
            if int(cursor.fetchone()[0]) > 0:
                skipped += 1
                reasons.append(f"{gn}: duplicate")
                continue
        try:
            awardee = rec.get("awardee")
            cursor.execute(
                f"""
                INSERT INTO `{catalog}`.`bronze`.grants (
                    grant_no, title, abstract, program_area, fiscal_year, amount_usd,
                    awardee, org_unit, classification_band, batch_id, created_at,
                    _ingest_time, _source_file, _batch_id
                ) VALUES (
                    {_sql_str(gn)},
                    {_sql_str(rec.get("title"))},
                    {_sql_str(rec.get("abstract"))},
                    {_sql_str(rec.get("program_area"))},
                    {int(float(rec.get("fiscal_year") or 2026))},
                    {amount},
                    {_sql_str(awardee) if awardee else "NULL"},
                    {_sql_str(rec.get("org_unit"))},
                    {_sql_str(rec.get("classification_band"))},
                    {_sql_str(rec.get("batch_id") or LIVE_BATCH_ID)},
                    {_sql_str(rec.get("created_at"))},
                    CURRENT_TIMESTAMP(),
                    {_sql_str(source_file)},
                    {_sql_str(rec.get("batch_id") or LIVE_BATCH_ID)}
                )
                """
            )
            landed += 1
        except Exception as e:
            rejected += 1
            reasons.append(f"{gn}: {e}")
    return {"landed": landed, "skipped": skipped, "rejected": rejected, "reasons": reasons[:20], "input_rows": len(rows)}


def ingest_live_batch_sql(cursor, catalog: str) -> Tuple[int, str]:
    result = ingest_grant_rows(cursor, catalog, load_live_rows(), "batch_live_grants.csv", True)
    return result["landed"], LIVE_BATCH_ID


def process_selected_files(cursor, catalog: str, pack_keys: list[str], extra_rows=None, extra_name="upload.csv") -> dict:
    summaries = []
    before = grant_count(cursor, catalog)
    for key in pack_keys:
        matches = [p for p in FILE_PACKS[key]["files"] if p.exists()]
        if not matches:
            raise FileNotFoundError(f"Pack '{key}' CSV is not packaged with the app")
        path = matches[0]
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        summaries.append({"file": path.name, **ingest_grant_rows(cursor, catalog, rows, path.name, skip_existing=True)})
    if extra_rows:
        summaries.append({"file": extra_name, **ingest_grant_rows(cursor, catalog, extra_rows, extra_name, True)})
    refresh_silver_gold_sql(cursor, catalog)
    return {"before": before, "after": grant_count(cursor, catalog), "files": summaries}


def reset_to_seed_sql(cursor, catalog: str) -> dict:
    before = grant_count(cursor, catalog)
    cursor.execute(
        f"""DELETE FROM `{catalog}`.`bronze`.grants
            WHERE coalesce(batch_id, _batch_id, '{SEED_BATCH_ID}') <> '{SEED_BATCH_ID}'"""
    )
    cursor.execute(
        f"""DELETE FROM `{catalog}`.`bronze`.financial
            WHERE coalesce(batch_id, _batch_id, '{SEED_BATCH_ID}') <> '{SEED_BATCH_ID}'"""
    )
    bronze_n = bronze_count(cursor, catalog)
    reloaded = False
    if bronze_n != 400:
        # Do not INSERT 1,600 rows from the app (warehouse timeouts).
        # Point the operator at the cluster bootstrap instead.
        refresh_silver_gold_sql(cursor, catalog)
        return {
            "before_silver": before,
            "after_silver": grant_count(cursor, catalog),
            "bronze_grants": bronze_n,
            "reloaded_fixture": False,
            "checkpoints": clear_autoloader_checkpoints(),
            "warning": (
                f"bronze.grants is {bronze_n}, expected 400. "
                "Run notebooks/00_bootstrap.py on **onr demo cluster** to full-reload the fixture."
            ),
        }
    refresh_silver_gold_sql(cursor, catalog)
    return {
        "before_silver": before,
        "after_silver": grant_count(cursor, catalog),
        "bronze_grants": bronze_n,
        "reloaded_fixture": reloaded,
        "checkpoints": clear_autoloader_checkpoints(),
    }


def _reload_seed_tables(cursor, catalog: str) -> None:
    from utils.portfolio_data import grants_dataframe, financial_dataframe

    cursor.execute(f"TRUNCATE TABLE `{catalog}`.`bronze`.grants")
    cursor.execute(f"TRUNCATE TABLE `{catalog}`.`bronze`.financial")
    ingest_grant_rows(cursor, catalog, grants_dataframe().to_dict(orient="records"), "grants_portfolio.json", False)
    for rec in financial_dataframe().to_dict(orient="records"):
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`bronze`.financial (
                transaction_id, grant_no, cost_center, program_area, category,
                fiscal_year, quarter, budget_allocated, actual_expenditure,
                execution_rate, variance, status, batch_id,
                _ingest_time, _source_file, _batch_id
            ) VALUES (
                {_sql_str(rec.get("transaction_id"))},
                {_sql_str(rec.get("grant_no"))},
                {_sql_str(rec.get("cost_center"))},
                {_sql_str(rec.get("program_area"))},
                {_sql_str(rec.get("category"))},
                {int(rec.get("fiscal_year") or 2026)},
                {_sql_str(rec.get("quarter"))},
                {float(rec.get("budget_allocated") or 0)},
                {float(rec.get("actual_expenditure") or 0)},
                {float(rec.get("execution_rate") or 0)},
                {float(rec.get("variance") or 0)},
                {_sql_str(rec.get("status"))},
                {_sql_str(rec.get("batch_id") or SEED_BATCH_ID)},
                CURRENT_TIMESTAMP(),
                'derived_erp',
                {_sql_str(rec.get("batch_id") or SEED_BATCH_ID)}
            )
            """
        )


def clear_autoloader_checkpoints() -> str:
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        root = "/Volumes/onr_demo/bronze/checkpoints"
        deleted = 0
        try:
            for entry in w.files.list_directory_contents(root):
                path = getattr(entry, "path", None)
                if not path:
                    continue
                try:
                    w.files.delete_directory(path, recursive=True)
                    deleted += 1
                except Exception:
                    try:
                        w.files.delete(path)
                        deleted += 1
                    except Exception:
                        pass
        except Exception as e:
            return f"Could not list {root}: {e}"
        return f"Cleared {deleted} checkpoint path(s) under {root}"
    except Exception as e:
        return f"Checkpoint cleanup skipped ({e}). Use notebooks/05_reset_demo.py on the cluster."


def refresh_silver_gold_sql(cursor, catalog: str) -> None:
    """Rebuild silver + gold from bronze (same rules as notebooks 02/03)."""
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`silver`.grants AS
        SELECT grant_no, title, abstract, program_area, fiscal_year, amount_usd,
               awardee, org_unit, classification_band, batch_id,
               TRY_CAST(created_at AS TIMESTAMP) as created_at,
               _ingest_time, _source_file, true as _is_active,
               CASE WHEN amount_usd > 0 THEN 1.0 ELSE 0.5 END as _quality_score
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY grant_no ORDER BY _ingest_time DESC) rn
            FROM `{catalog}`.`bronze`.grants
        )
        WHERE rn = 1 AND grant_no IS NOT NULL AND trim(grant_no) <> ''
          AND amount_usd > 0 AND awardee IS NOT NULL
        """
    )
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`silver`.financial AS
        SELECT transaction_id, grant_no, cost_center, program_area, category,
               fiscal_year, quarter, budget_allocated, actual_expenditure,
               CASE WHEN budget_allocated > 0
                    THEN actual_expenditure / budget_allocated * 100 ELSE 0 END as execution_rate,
               budget_allocated - actual_expenditure as variance,
               status, _ingest_time, _source_file, true as _is_active, 1.0 as _quality_score
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY _ingest_time DESC) rn
            FROM `{catalog}`.`bronze`.financial
        )
        WHERE rn = 1 AND transaction_id IS NOT NULL AND budget_allocated > 0
        """
    )
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.grants_summary AS
        SELECT program_area, fiscal_year, COUNT(*) grant_count,
               SUM(amount_usd) total_funding, AVG(amount_usd) avg_award,
               MIN(amount_usd) min_award, MAX(amount_usd) max_award,
               SUM(CASE WHEN classification_band = 'CUI-Mock' THEN 1 ELSE 0 END) cui_mock_count,
               SUM(CASE WHEN classification_band = 'Public-Mock' THEN 1 ELSE 0 END) public_mock_count,
               CURRENT_TIMESTAMP() _updated_at
        FROM `{catalog}`.`silver`.grants WHERE _is_active
        GROUP BY program_area, fiscal_year
        """
    )
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.financial_summary AS
        SELECT cost_center, category, fiscal_year, quarter,
               SUM(budget_allocated) total_budget, SUM(actual_expenditure) total_actual,
               COUNT(*) transaction_count,
               ROUND(SUM(actual_expenditure)/NULLIF(SUM(budget_allocated),0)*100, 2) overall_execution_rate,
               SUM(budget_allocated)-SUM(actual_expenditure) variance_amount,
               CURRENT_TIMESTAMP() _updated_at
        FROM `{catalog}`.`silver`.financial WHERE _is_active
        GROUP BY cost_center, category, fiscal_year, quarter
        """
    )
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.budget_execution AS
        SELECT fiscal_year, quarter, category,
               SUM(budget_allocated) budget_plan, SUM(actual_expenditure) actual_spend,
               ROUND(SUM(actual_expenditure)/NULLIF(SUM(budget_allocated),0)*100, 2) execution_rate,
               SUM(budget_allocated)-SUM(actual_expenditure) variance,
               ROUND((SUM(budget_allocated)-SUM(actual_expenditure))/NULLIF(SUM(budget_allocated),0)*100, 2) variance_pct,
               CASE WHEN SUM(actual_expenditure)/NULLIF(SUM(budget_allocated),0)*100 >= 90 THEN 'ON_TARGET'
                    WHEN SUM(actual_expenditure)/NULLIF(SUM(budget_allocated),0)*100 >= 80 THEN 'WARNING'
                    ELSE 'AT_RISK' END status,
               CURRENT_TIMESTAMP() _updated_at
        FROM `{catalog}`.`silver`.financial WHERE _is_active
        GROUP BY fiscal_year, quarter, category
        """
    )
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.grants_by_awardee AS
        SELECT awardee, org_unit, COUNT(*) grant_count,
               SUM(amount_usd) total_funding,
               COLLECT_SET(program_area) program_areas,
               MAX(created_at) latest_grant_date,
               CURRENT_TIMESTAMP() _updated_at
        FROM `{catalog}`.`silver`.grants WHERE _is_active
        GROUP BY awardee, org_unit
        """
    )
    try:
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.ingestion_quality_log
            (check_id, check_name, check_status, records_checked, records_passed,
             records_failed, check_timestamp, pipeline_name)
            VALUES (
                concat('live-', date_format(current_timestamp(), 'yyyyMMddHHmmss')),
                'live_batch_drop', 'PASS',
                (SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants),
                (SELECT COUNT(*) FROM `{catalog}`.`silver`.grants),
                (SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants)
                  - (SELECT COUNT(*) FROM `{catalog}`.`silver`.grants),
                CURRENT_TIMESTAMP(), 'streamlit_live_drop'
            )
            """
        )
    except Exception:
        pass


def try_start_cluster_notebooks() -> str:
    """Best-effort: start 'onr demo cluster' so Key Personnel can run 01–04 live."""
    try:
        from databricks.sdk import WorkspaceClient
        from utils.workspace_names import ALL_PURPOSE_CLUSTER_NAME

        w = WorkspaceClient()
        for c in w.clusters.list():
            if (c.cluster_name or "").strip().lower() == ALL_PURPOSE_CLUSTER_NAME.lower():
                state = str(getattr(c, "state", "") or "")
                if "RUNNING" not in state.upper():
                    w.clusters.start(c.cluster_id)
                    return f"Starting cluster '{ALL_PURPOSE_CLUSTER_NAME}' ({c.cluster_id})."
                return f"Cluster '{ALL_PURPOSE_CLUSTER_NAME}' is already running."
        return f"Cluster '{ALL_PURPOSE_CLUSTER_NAME}' not found — run notebooks on it from the workspace UI."
    except Exception as e:
        return f"Could not reach cluster API ({e})."
