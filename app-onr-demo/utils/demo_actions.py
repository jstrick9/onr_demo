"""
Live demo actions: drop the staged 8-grant file through bronze → silver → gold.

SQL runs on the serverless warehouse named "onr demo warehouse".
Notebooks (01–04) are meant to run on the all-purpose cluster "onr demo cluster".
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Tuple

LIVE_BATCH_ID = "live-demo-2026"

_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "data" / "batch_live_grants.csv",
    Path(__file__).resolve().parents[2] / "resources" / "mock_data" / "batch_live_grants.csv",
]


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
    return "'" + str(v).replace("'", "''") + "'"


def ingest_live_batch_sql(cursor, catalog: str) -> Tuple[int, str]:
    """Append live-demo grants to bronze (skips grant_no already present)."""
    rows = load_live_rows()
    inserted = 0
    for rec in rows:
        gn = rec.get("grant_no")
        cursor.execute(
            f"SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants WHERE grant_no = {_sql_str(gn)}"
        )
        if int(cursor.fetchone()[0]) > 0:
            continue
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`bronze`.grants VALUES (
                {_sql_str(gn)},
                {_sql_str(rec.get("title"))},
                {_sql_str(rec.get("abstract"))},
                {_sql_str(rec.get("program_area"))},
                {int(rec.get("fiscal_year") or 2026)},
                {float(rec.get("amount_usd") or 0)},
                {_sql_str(rec.get("awardee"))},
                {_sql_str(rec.get("org_unit"))},
                {_sql_str(rec.get("classification_band"))},
                {_sql_str(rec.get("batch_id") or LIVE_BATCH_ID)},
                {_sql_str(rec.get("created_at"))},
                CURRENT_TIMESTAMP(),
                'batch_live_grants.csv',
                {_sql_str(rec.get("batch_id") or LIVE_BATCH_ID)}
            )
            """
        )
        inserted += 1
    return inserted, LIVE_BATCH_ID


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
        WHERE rn = 1 AND grant_no IS NOT NULL AND amount_usd > 0 AND awardee IS NOT NULL
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
    cursor.execute(
        f"""
        INSERT INTO `{catalog}`.`app`.ingestion_quality_log
        VALUES (
            'live-' || CAST(UNIX_TIMESTAMP() AS STRING), 'live_batch_drop', 'PASS',
            (SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants),
            (SELECT COUNT(*) FROM `{catalog}`.`silver`.grants),
            (SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants)
              - (SELECT COUNT(*) FROM `{catalog}`.`silver`.grants),
            CURRENT_TIMESTAMP(), 'streamlit_live_drop'
        )
        """
    )


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
