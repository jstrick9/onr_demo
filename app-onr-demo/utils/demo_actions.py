"""
Live demo actions: drop the staged 8-grant file through bronze → silver → gold.

SQL runs on the serverless warehouse named "onr demo warehouse".
Notebooks (01–04) are meant to run on the all-purpose cluster "onr demo cluster".
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

SEED_BATCH_ID = "seed-initial-2026"
LIVE_BATCH_ID = "live-demo-2026"
QUALITY_FAIL_BATCH_ID = "quality-fail-2026"

_APP_DATA = Path(__file__).resolve().parents[1] / "data"
_REPO_MOCK = Path(__file__).resolve().parents[2] / "resources" / "mock_data"

FILE_PACKS = {
    "live": {
        "label": "Inbound grants",
        "batch_id": LIVE_BATCH_ID,
        "files": [
            _APP_DATA / "batch_live_grants.csv",
            _REPO_MOCK / "batch_live_grants.csv",
        ],
    },
    "quality_fail": {
        "label": "Quarantine sample",
        "batch_id": QUALITY_FAIL_BATCH_ID,
        "files": [
            _APP_DATA / "batch_quality_fail.csv",
            _REPO_MOCK / "batch_quality_fail.csv",
        ],
    },
}

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


def _hold_row(code: str, rec: dict, gn: str, amount=None, detail: str = "") -> dict:
    return {
        "code": code,
        "grant_no": gn or "—",
        "title": rec.get("title") or detail or "",
        "amount_usd": amount if amount is not None else rec.get("amount_usd"),
        "detail": detail,
    }


def ingest_grant_rows(cursor, catalog: str, rows: list[dict], source_file: str, skip_existing: bool = True) -> dict:
    from utils.quality_rules import quarantine_reason, warn_findings

    landed = skipped = rejected = held = 0
    reasons: list[str] = []
    holds: list[dict] = []
    warnings: list[dict] = []
    for rec in rows:
        gn_raw = rec.get("grant_no")
        exists = False
        gn = "" if gn_raw is None else str(gn_raw).strip()
        if skip_existing and gn and gn.lower() not in {"nan", "none", "null"}:
            cursor.execute(
                f"SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants WHERE grant_no = {_sql_str(gn)}"
            )
            exists = int(cursor.fetchone()[0]) > 0
        q = quarantine_reason(rec, exists)
        if q:
            code, detail = q
            held += 1
            if code == "dup":
                skipped += 1
            else:
                rejected += 1
            reasons.append(f"{gn or '—'}: {detail}")
            holds.append({**_hold_row(code, rec, gn or "—", rec.get("amount_usd"), detail), "source_file": source_file, "record": rec})
            continue
        try:
            amount = float(rec.get("amount_usd") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        for check_name, detail in warn_findings(rec):
            warnings.append(
                {
                    "grant_no": gn,
                    "check_name": check_name,
                    "detail": detail,
                    "source_file": source_file,
                    "title": rec.get("title"),
                    "amount_usd": rec.get("amount_usd"),
                    "program_area": rec.get("program_area"),
                }
            )
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
            held += 1
            reasons.append(f"{gn}: {e}")
            holds.append({**_hold_row("empty", rec, gn, amount, str(e)), "source_file": source_file, "record": rec})
    return {
        "landed": landed,
        "skipped": skipped,
        "rejected": rejected,
        "held": held,
        "reasons": reasons[:20],
        "holds": holds,
        "warnings": warnings,
        "input_rows": len(rows),
    }


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
    holds = [h for s in summaries for h in (s.get("holds") or [])]
    warnings = [w for s in summaries for w in (s.get("warnings") or [])]
    held = sum(int(s.get("held") or 0) for s in summaries)
    try:
        _write_quarantine_log(cursor, catalog, holds)
    except Exception:
        pass
    try:
        _write_hold_queue(cursor, catalog, holds)
    except Exception:
        pass
    try:
        _write_quality_findings(cursor, catalog, warnings)
    except Exception:
        pass
    after = grant_count(cursor, catalog)
    try:
        bronze_n = bronze_count(cursor, catalog)
    except Exception:
        bronze_n = None
    try:
        _write_ingest_quality_log(
            cursor,
            catalog,
            summaries=summaries,
            holds=holds,
            before=before,
            after=after,
            bronze_n=bronze_n,
            warn_n=len(warnings),
        )
    except Exception:
        pass
    return {
        "before": before,
        "after": after,
        "bronze": bronze_n,
        "files": summaries,
        "holds": holds,
        "held": held,
        "warnings": warnings,
    }


def _write_ingest_quality_log(
    cursor,
    catalog: str,
    summaries: list[dict],
    holds: list[dict],
    before,
    after,
    bronze_n,
    warn_n: int = 0,
) -> None:
    """One row per quality gate so the Quality tab matches the Hold tray."""
    if not cursor:
        return
    _ensure_app_tables(cursor, catalog)
    by_code = {"empty": 0, "dup": 0, "amt": 0}
    for rec in holds or []:
        code = str(rec.get("code") or "").lower()
        if code in by_code:
            by_code[code] += 1
    landed = sum(int(s.get("landed") or 0) for s in summaries or [])
    checked = sum(int(s.get("input_rows") or 0) for s in summaries or [])
    held_n = sum(by_code.values())
    rows = [
        ("grant_no_present", by_code["empty"] == 0, checked, checked - by_code["empty"], by_code["empty"]),
        ("amount_positive", by_code["amt"] == 0, checked, checked - by_code["amt"], by_code["amt"]),
        ("grant_no_unique", by_code["dup"] == 0, checked, checked - by_code["dup"], by_code["dup"]),
        (
            "silver_publish",
            True,
            bronze_n if bronze_n is not None else checked,
            after if after is not None else 0,
            held_n,
        ),
        ("warn_published", True, checked, landed, int(warn_n or 0)),
    ]
    stamp = "date_format(current_timestamp(), 'yyyyMMddHHmmss')"
    for name, ok, n_checked, n_pass, n_fail in rows:
        status = "PASS" if ok else "FAIL"
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.ingestion_quality_log
            (check_id, check_name, check_status, records_checked, records_passed,
             records_failed, check_timestamp, pipeline_name)
            VALUES (
                concat('ingest-', {stamp}, '-', '{name}'),
                '{name}',
                '{status}',
                {int(n_checked or 0)},
                {int(n_pass or 0)},
                {int(n_fail or 0)},
                CURRENT_TIMESTAMP(),
                'ingest_selected_files'
            )
            """
        )


def _write_quarantine_log(cursor, catalog: str, holds: list[dict]) -> None:
    if not cursor:
        return
    _ensure_app_tables(cursor, catalog)
    cursor.execute(f"DELETE FROM `{catalog}`.`app`.quarantine_log")
    for i, rec in enumerate(holds or []):
        src = rec.get("record") or {}
        try:
            amt = rec.get("amount_usd", src.get("amount_usd"))
            amt_sql = "NULL"
            if amt is not None and str(amt) not in {"", "nan", "None"}:
                amt_sql = str(float(amt))
        except (TypeError, ValueError):
            amt_sql = "NULL"
        fy = src.get("fiscal_year")
        try:
            fy_sql = str(int(float(fy))) if fy not in (None, "") else "NULL"
        except (TypeError, ValueError):
            fy_sql = "NULL"
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.quarantine_log
            (event_id, grant_no, title, abstract, program_area, fiscal_year, amount_usd,
             awardee, org_unit, classification_band, batch_id, reason_code, reason_detail,
             source_file, pipeline_name, quarantined_at)
            VALUES (
                concat('q-', date_format(current_timestamp(), 'yyyyMMddHHmmss'), '-{i}'),
                {_sql_str(rec.get("grant_no"))},
                {_sql_str(rec.get("title") or src.get("title"))},
                {_sql_str(src.get("abstract"))},
                {_sql_str(src.get("program_area"))},
                {fy_sql},
                {amt_sql},
                {_sql_str(src.get("awardee"))},
                {_sql_str(src.get("org_unit"))},
                {_sql_str(src.get("classification_band"))},
                {_sql_str(src.get("batch_id"))},
                {_sql_str(rec.get("code"))},
                {_sql_str(rec.get("detail"))},
                {_sql_str(rec.get("source_file") or "ingest")},
                'ingest_selected_files',
                CURRENT_TIMESTAMP()
            )
            """
        )


def _write_quality_findings(cursor, catalog: str, warnings: list[dict]) -> None:
    if not cursor:
        return
    _ensure_app_tables(cursor, catalog)
    cursor.execute(f"DELETE FROM `{catalog}`.`app`.quality_findings")
    for i, rec in enumerate(warnings or []):
        try:
            amt = rec.get("amount_usd")
            amt_sql = "NULL"
            if amt is not None and str(amt) not in {"", "nan", "None"}:
                amt_sql = str(float(amt))
        except (TypeError, ValueError):
            amt_sql = "NULL"
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.quality_findings
            (finding_id, grant_no, title, program_area, amount_usd, severity,
             check_name, detail, published, source_file, pipeline_name, found_at)
            VALUES (
                concat('w-', date_format(current_timestamp(), 'yyyyMMddHHmmss'), '-{i}'),
                {_sql_str(rec.get("grant_no"))},
                {_sql_str(rec.get("title"))},
                {_sql_str(rec.get("program_area"))},
                {amt_sql},
                'WARN',
                {_sql_str(rec.get("check_name"))},
                {_sql_str(rec.get("detail"))},
                true,
                {_sql_str(rec.get("source_file") or "ingest")},
                'ingest_selected_files',
                CURRENT_TIMESTAMP()
            )
            """
        )


def load_quarantine_log(cursor, catalog: str) -> list[dict]:
    if not cursor:
        return []
    try:
        cursor.execute(
            f"""
            SELECT grant_no, title, amount_usd, reason_code, reason_detail, source_file, quarantined_at
            FROM `{catalog}`.`app`.quarantine_log
            ORDER BY quarantined_at DESC
            """
        )
        cols = [str(d[0]).lower() for d in cursor.description]
        out = []
        for row in cursor.fetchall():
            rec = dict(zip(cols, row))
            out.append(
                {
                    "grant_no": rec.get("grant_no"),
                    "title": rec.get("title"),
                    "amount_usd": rec.get("amount_usd"),
                    "code": rec.get("reason_code"),
                    "detail": rec.get("reason_detail"),
                    "source_file": rec.get("source_file"),
                }
            )
        return out
    except Exception:
        return []


def load_quality_findings(cursor, catalog: str) -> list[dict]:
    if not cursor:
        return []
    try:
        cursor.execute(
            f"""
            SELECT grant_no, title, program_area, amount_usd, severity, check_name,
                   detail, published, source_file, found_at
            FROM `{catalog}`.`app`.quality_findings
            ORDER BY found_at DESC
            """
        )
        cols = [str(d[0]).lower() for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception:
        return []


def _write_hold_queue(cursor, catalog: str, holds: list[dict]) -> None:
    if not cursor:
        return
    _ensure_app_tables(cursor, catalog)
    cursor.execute(f"DELETE FROM `{catalog}`.`app`.hold_queue")
    for i, rec in enumerate(holds or []):
        try:
            amt = rec.get("amount_usd")
            amt_sql = "NULL"
            if amt is not None and str(amt) not in {"", "nan", "None"}:
                amt_sql = str(float(amt))
        except (TypeError, ValueError):
            amt_sql = "NULL"
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.hold_queue
            (hold_id, grant_no, title, amount_usd, reason_code, detail, source_file, held_at)
            VALUES (
                concat('hold-', date_format(current_timestamp(), 'yyyyMMddHHmmss'), '-{i}'),
                {_sql_str(rec.get("grant_no"))},
                {_sql_str(rec.get("title"))},
                {amt_sql},
                {_sql_str(rec.get("code"))},
                {_sql_str(rec.get("detail"))},
                {_sql_str(rec.get("source_file") or "ingest")},
                CURRENT_TIMESTAMP()
            )
            """
        )


def load_hold_queue(cursor, catalog: str) -> list[dict]:
    q = load_quarantine_log(cursor, catalog)
    if q:
        return q
    if not cursor:
        return []
    try:
        cursor.execute(
            f"""
            SELECT grant_no, title, amount_usd, reason_code, detail
            FROM `{catalog}`.`app`.hold_queue
            ORDER BY held_at DESC
            """
        )
        cols = [str(d[0]).lower() for d in cursor.description]
        out = []
        for row in cursor.fetchall():
            rec = dict(zip(cols, row))
            out.append(
                {  "title": rec.get("title"),
                    "amount_usd": rec.get("amount_usd"),
                    "code": rec.get("reason_code"),
                    "detail": rec.get("detail"),
                }
            )
        return out
    except Exception:
        return []


QUALITY_LOG_TABLES = (
    "hold_queue",
    "quarantine_log",
    "quality_findings",
    "ingestion_quality_log",
)


def _clear_quality_logs(cursor, catalog: str) -> list[str]:
    """Empty quarantine / findings / gate history so restore matches the seed."""
    cleared: list[str] = []
    _ensure_app_tables(cursor, catalog)
    for table in QUALITY_LOG_TABLES:
        try:
            cursor.execute(f"DELETE FROM `{catalog}`.`app`.{table}")
            cleared.append(table)
        except Exception:
            pass
    return cleared


def _write_baseline_quality_log(cursor, catalog: str, silver_n: int, bronze_n: int) -> None:
    """Seed-state gate history: silver published, quarantine empty."""
    if not cursor:
        return
    _ensure_app_tables(cursor, catalog)
    checked = int(bronze_n or 0)
    passed = int(silver_n or 0)
    rows = [
        ("grant_no_present", True, checked, passed, 0),
        ("amount_positive", True, checked, passed, 0),
        ("grant_no_unique", True, checked, passed, 0),
        ("silver_publish", True, checked, passed, 0),
        ("quarantine_log", True, 0, 0, 0),
        ("warn_published", True, checked, passed, 0),
    ]
    stamp = "date_format(current_timestamp(), 'yyyyMMddHHmmss')"
    for name, ok, n_checked, n_pass, n_fail in rows:
        status = "PASS" if ok else "FAIL"
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.ingestion_quality_log
            (check_id, check_name, check_status, records_checked, records_passed,
             records_failed, check_timestamp, pipeline_name)
            VALUES (
                concat('reset-', {stamp}, '-', '{name}'),
                '{name}',
                '{status}',
                {int(n_checked or 0)},
                {int(n_pass or 0)},
                {int(n_fail or 0)},
                CURRENT_TIMESTAMP(),
                'restore_baseline'
            )
            """
        )


def reset_to_seed_sql(cursor, catalog: str) -> dict:
    before = grant_count(cursor, catalog)
    _ensure_app_tables(cursor, catalog)
    cursor.execute(
        f"""DELETE FROM `{catalog}`.`bronze`.grants
            WHERE coalesce(batch_id, _batch_id, '{SEED_BATCH_ID}') <> '{SEED_BATCH_ID}'"""
    )
    cursor.execute(
        f"""DELETE FROM `{catalog}`.`bronze`.financial
            WHERE coalesce(batch_id, _batch_id, '{SEED_BATCH_ID}') <> '{SEED_BATCH_ID}'"""
    )
    # Safety: leftover quarantine-class rows must not sit in bronze after restore.
    try:
        cursor.execute(
            f"""DELETE FROM `{catalog}`.`bronze`.grants
                WHERE grant_no IS NULL OR trim(grant_no) = ''
                   OR amount_usd IS NULL OR amount_usd <= 0"""
        )
    except Exception:
        pass
    cleared = _clear_quality_logs(cursor, catalog)
    bronze_n = bronze_count(cursor, catalog)
    reloaded = False
    if bronze_n != 400:
        # Do not INSERT 1,600 rows from the app (warehouse timeouts).
        # Point the operator at the cluster bootstrap instead.
        refresh_silver_gold_sql(cursor, catalog, quality_pipeline=None)
        after = grant_count(cursor, catalog)
        try:
            _write_baseline_quality_log(cursor, catalog, after or 0, bronze_n)
        except Exception:
            pass
        return {
            "before_silver": before,
            "after_silver": after,
            "bronze_grants": bronze_n,
            "quarantine_log": 0,
            "quality_logs_cleared": cleared,
            "reloaded_fixture": False,
            "checkpoints": clear_autoloader_checkpoints(),
            "warning": (
                f"bronze.grants is {bronze_n}, expected 400. Restore from the official snapshot on the cluster."
            ),
        }
    refresh_silver_gold_sql(cursor, catalog, quality_pipeline=None)
    after = grant_count(cursor, catalog)
    try:
        _write_baseline_quality_log(cursor, catalog, after or 0, bronze_n)
    except Exception:
        pass
    return {
        "before_silver": before,
        "after_silver": after,
        "bronze_grants": bronze_n,
        "quarantine_log": 0,
        "quality_logs_cleared": cleared,
        "reloaded_fixture": reloaded,
        "checkpoints": clear_autoloader_checkpoints(),
    }


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
                    deleter = getattr(w.files, "delete_directory", None)
                    if deleter:
                        deleter(path, recursive=True)
                    else:
                        w.files.delete(path)
                    deleted += 1
                except Exception:
                    try:
                        w.files.delete(path)
                        deleted += 1
                    except Exception:
                        pass
        except Exception as e:
            return (
            f"Could not list {root}: {e}. "
            "WorkspaceClient.files does not operate on UC Volumes — "
            "run notebooks/05_reset_demo.py on **onr demo cluster** to clear checkpoints."
        )
        return f"Cleared {deleted} checkpoint path(s) under {root}"
    except Exception as e:
        return (
            f"Checkpoint cleanup skipped ({e}). "
            "App reset does not clear Auto Loader checkpoints; "
            "use notebooks/05_reset_demo.py on **onr demo cluster**."
        )


def _ensure_app_tables(cursor, catalog: str) -> None:
    """Create app audit / quality tables if bootstrap has not yet."""
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.data_quality_scores (
            table_name STRING,
            quality_score DOUBLE,
            completeness DOUBLE,
            accuracy DOUBLE,
            consistency DOUBLE,
            timeliness DOUBLE,
            last_assessed TIMESTAMP
        ) USING DELTA
        COMMENT 'Data quality health scores'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.lineage_tracking (
            lineage_id STRING NOT NULL,
            source_table STRING,
            target_table STRING,
            transformation_type STRING,
            records_processed INT,
            processing_time_ms INT,
            executed_at TIMESTAMP,
            executed_by STRING
        ) USING DELTA
        COMMENT 'Lineage tracking records'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.export_history (
            export_id STRING NOT NULL,
            user_email STRING,
            dataset_name STRING,
            format STRING,
            record_count INT,
            file_size_bytes BIGINT,
            created_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Export audit trail'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.search_history (
            search_id STRING NOT NULL,
            user_email STRING,
            search_type STRING,
            search_params STRING,
            results_count INT,
            execution_time_ms INT,
            created_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Search history for audit and replay'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.ingestion_quality_log (
            check_id STRING NOT NULL,
            check_name STRING,
            check_status STRING,
            records_checked INT,
            records_passed INT,
            records_failed INT,
            check_timestamp TIMESTAMP,
            pipeline_name STRING
        ) USING DELTA
        COMMENT 'Ingestion quality check results'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.daily_briefs (
            brief_id STRING NOT NULL,
            generated_at TIMESTAMP,
            generated_by STRING,
            source STRING,
            model_name STRING,
            brief_text STRING,
            prompt_chars INT
        ) USING DELTA
        COMMENT 'Automated daily portfolio briefs (ai_query or template)'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.hold_queue (
            hold_id STRING NOT NULL,
            grant_no STRING,
            title STRING,
            amount_usd DOUBLE,
            reason_code STRING,
            detail STRING,
            source_file STRING,
            held_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Quality-gate Hold inbox (empty / dup / amt)'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.quarantine_log (
            event_id STRING NOT NULL,
            grant_no STRING,
            title STRING,
            abstract STRING,
            program_area STRING,
            fiscal_year INT,
            amount_usd DOUBLE,
            awardee STRING,
            org_unit STRING,
            classification_band STRING,
            batch_id STRING,
            reason_code STRING,
            reason_detail STRING,
            source_file STRING,
            pipeline_name STRING,
            quarantined_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Quarantined grants — never landed in bronze'
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.quality_findings (
            finding_id STRING NOT NULL,
            grant_no STRING,
            title STRING,
            program_area STRING,
            amount_usd DOUBLE,
            severity STRING,
            check_name STRING,
            detail STRING,
            published BOOLEAN,
            source_file STRING,
            pipeline_name STRING,
            found_at TIMESTAMP
        ) USING DELTA
        COMMENT 'WARN findings on rows that still published'
        """
    )


def _write_data_quality_scores(cursor, catalog: str) -> None:
    """Same completeness/accuracy/consistency math as notebooks/02_silver_quality.py."""
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`app`.data_quality_scores AS
        WITH g AS (
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN grant_no IS NOT NULL THEN 1 END) AS valid_id,
                COUNT(CASE WHEN awardee IS NOT NULL THEN 1 END) AS valid_awardee,
                COUNT(CASE WHEN amount_usd > 0 THEN 1 END) AS valid_amount,
                COUNT(CASE WHEN program_area IS NOT NULL THEN 1 END) AS valid_area
            FROM `{catalog}`.`silver`.grants
        ),
        f AS (
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN transaction_id IS NOT NULL THEN 1 END) AS valid_id,
                COUNT(CASE WHEN budget_allocated > 0 THEN 1 END) AS valid_budget,
                COUNT(CASE WHEN actual_expenditure >= 0 THEN 1 END) AS valid_actual
            FROM `{catalog}`.`silver`.financial
        ),
        gs AS (
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN program_area IS NOT NULL THEN 1 END) AS valid_area,
                COUNT(CASE WHEN total_funding > 0 THEN 1 END) AS valid_funding
            FROM `{catalog}`.`gold`.grants_summary
        ),
        be AS (
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN status IS NOT NULL THEN 1 END) AS valid_status,
                COUNT(CASE WHEN execution_rate IS NOT NULL THEN 1 END) AS valid_rate
            FROM `{catalog}`.`gold`.budget_execution
        )
        SELECT 'silver.grants' AS table_name,
               (g.valid_id / NULLIF(g.total, 0)) * 0.3
             + (g.valid_awardee / NULLIF(g.total, 0)) * 0.3
             + (g.valid_amount / NULLIF(g.total, 0)) * 0.2
             + (g.valid_area / NULLIF(g.total, 0)) * 0.2 AS quality_score,
               g.valid_id / NULLIF(g.total, 0) AS completeness,
               g.valid_amount / NULLIF(g.total, 0) AS accuracy,
               g.valid_awardee / NULLIF(g.total, 0) AS consistency,
               1.0 AS timeliness,
               CURRENT_TIMESTAMP() AS last_assessed
        FROM g
        UNION ALL
        SELECT 'silver.financial',
               (f.valid_id / NULLIF(f.total, 0)) * 0.4
             + (f.valid_budget / NULLIF(f.total, 0)) * 0.3
             + (f.valid_actual / NULLIF(f.total, 0)) * 0.3,
               f.valid_id / NULLIF(f.total, 0),
               f.valid_budget / NULLIF(f.total, 0),
               f.valid_actual / NULLIF(f.total, 0),
               1.0,
               CURRENT_TIMESTAMP()
        FROM f
        UNION ALL
        SELECT 'gold.grants_summary',
               (gs.valid_area / NULLIF(gs.total, 0)) * 0.5
             + (gs.valid_funding / NULLIF(gs.total, 0)) * 0.5,
               gs.valid_area / NULLIF(gs.total, 0),
               gs.valid_funding / NULLIF(gs.total, 0),
               1.0,
               1.0,
               CURRENT_TIMESTAMP()
        FROM gs
        UNION ALL
        SELECT 'gold.budget_execution',
               (be.valid_status / NULLIF(be.total, 0)) * 0.5
             + (be.valid_rate / NULLIF(be.total, 0)) * 0.5,
               be.valid_status / NULLIF(be.total, 0),
               be.valid_rate / NULLIF(be.total, 0),
               1.0,
               1.0,
               CURRENT_TIMESTAMP()
        FROM be
        """
    )


def _write_lineage(cursor, catalog: str, timings: dict) -> None:
    """Append measured bronze→silver→gold hops into app.lineage_tracking."""
    hops = [
        ("bronze.grants", "silver.grants", "quality_transform", "bronze_grants", "silver_ms"),
        ("bronze.financial", "silver.financial", "quality_transform", "bronze_financial", "silver_ms"),
        ("silver.grants", "gold.grants_summary", "aggregation", "silver_grants", "gold_ms"),
        ("silver.financial", "gold.financial_summary", "aggregation", "silver_financial", "gold_ms"),
    ]
    for src, tgt, kind, n_key, ms_key in hops:
        n = int(timings.get(n_key) or 0)
        ms = int(timings.get(ms_key) or 0)
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.lineage_tracking
            (lineage_id, source_table, target_table, transformation_type,
             records_processed, processing_time_ms, executed_at, executed_by)
            VALUES (
                concat('lin-', date_format(current_timestamp(), 'yyyyMMddHHmmss'), '-', '{tgt}'),
                '{src}', '{tgt}', '{kind}',
                {n}, {ms}, CURRENT_TIMESTAMP(), 'streamlit_live_drop'
            )
            """
        )


def refresh_silver_gold_sql(cursor, catalog: str, quality_pipeline: str | None = "streamlit_live_drop") -> None:
    """Rebuild silver + gold from bronze (same rules as notebooks 02/03)."""
    import time

    _ensure_app_tables(cursor, catalog)
    t_silver = time.perf_counter()
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
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.grant_predictions AS
        SELECT grant_no, title, program_area, amount_usd, awardee,
               ROUND(LEAST(0.95, GREATEST(0.35,
                   0.42
                   + CASE WHEN amount_usd >= 2000000 THEN 0.22
                          WHEN amount_usd >= 1000000 THEN 0.15
                          WHEN amount_usd >= 500000 THEN 0.08 ELSE 0.0 END
                   + CASE WHEN program_area IN ('AI/ML','Quantum','Autonomy') THEN 0.12
                          WHEN program_area IN ('Cyber','Undersea') THEN 0.08 ELSE 0.04 END
                   + CASE WHEN fiscal_year >= 2025 THEN 0.06 ELSE 0.0 END
               )), 4) AS success_probability,
               CASE WHEN amount_usd >= 2000000 THEN 'Large award concentration'
                    WHEN classification_band = 'CUI-Mock' THEN 'CUI-Mock handling'
                    ELSE 'Standard portfolio risk' END AS risk_factors,
               CASE WHEN amount_usd >= 1000000 THEN 'Fund'
                    WHEN amount_usd >= 400000 THEN 'Review'
                    ELSE 'Defer' END AS recommendation,
               'heuristic_v1' AS model_name,
               CURRENT_TIMESTAMP() AS scored_at
        FROM `{catalog}`.`silver`.grants
        WHERE _is_active = true
        """
    )
    try:
        cursor.execute(
            f"""
            CREATE OR REPLACE TABLE `{catalog}`.`gold`.model_metrics AS
            SELECT 'heuristic_v1' AS model_name,
                   'rows_scored' AS metric_name,
                   CAST(COUNT(*) AS DOUBLE) AS metric_value,
                   CAST(COUNT(*) AS INT) AS n_rows,
                   CURRENT_TIMESTAMP() AS trained_at
            FROM `{catalog}`.`gold`.grant_predictions
            """
        )
    except Exception:
        pass
    silver_ms = int((time.perf_counter() - t_silver) * 1000)
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants")
        bronze_g = int(cursor.fetchone()[0])
        cursor.execute(f"SELECT COUNT(*) FROM `{catalog}`.`bronze`.financial")
        bronze_f = int(cursor.fetchone()[0])
        cursor.execute(f"SELECT COUNT(*) FROM `{catalog}`.`silver`.grants")
        silver_g = int(cursor.fetchone()[0])
        cursor.execute(f"SELECT COUNT(*) FROM `{catalog}`.`silver`.financial")
        silver_f = int(cursor.fetchone()[0])
    except Exception:
        bronze_g = bronze_f = silver_g = silver_f = 0
    try:
        from utils.forecast_sql import forecast_sql, trends_sql
        cursor.execute(forecast_sql(catalog))
        cursor.execute(trends_sql(catalog))
    except Exception:
        pass
    try:
        from utils.anomaly_sql import funding_features_sql, heuristic_anomaly_scores_sql
        cursor.execute(funding_features_sql(catalog))
        # Do not clobber IsolationForest scores written by notebook 04b.
        keep_iforest = False
        try:
            cursor.execute(
                f"SELECT MAX(model_name) FROM `{catalog}`.`gold`.grant_anomaly_scores"
            )
            mn = cursor.fetchone()[0]
            keep_iforest = bool(mn) and "iforest" in str(mn).lower()
        except Exception:
            keep_iforest = False
        if not keep_iforest:
            cursor.execute(heuristic_anomaly_scores_sql(catalog))
    except Exception:
        pass
    try:
        _write_data_quality_scores(cursor, catalog)
    except Exception:
        pass
    try:
        _write_lineage(
            cursor,
            catalog,
            {
                "bronze_grants": bronze_g,
                "bronze_financial": bronze_f,
                "silver_grants": silver_g,
                "silver_financial": silver_f,
                "silver_ms": silver_ms,
                "gold_ms": silver_ms,
            },
        )
    except Exception:
        pass
    if quality_pipeline:
        try:
            pipe = str(quality_pipeline).replace("'", "")
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
                    CURRENT_TIMESTAMP(), '{pipe}'
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
