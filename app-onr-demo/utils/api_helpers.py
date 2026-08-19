"""
Live Databricks Statement Execution REST proof — Element 7.
The open integration surface Advana / Cloud One / any JDBC client would call.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st


DEMO_STATEMENT = (
    "SELECT program_area, "
    "ROUND(SUM(total_funding)/1e6, 2) AS funding_m, "
    "SUM(grant_count) AS grants "
    "FROM {catalog}.gold.grants_summary "
    "GROUP BY program_area "
    "ORDER BY funding_m DESC "
    "LIMIT 8"
)


def _as_plain(v):
    """SDK enums expose .value; Apps sometimes hands us a bare str."""
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    if hasattr(v, "value"):
        try:
            return v.value
        except Exception:
            pass
    return str(v)


def _execute_statement_rest(w, host: str, warehouse_id: str, statement: str, catalog: str) -> dict:
    """POST /api/2.0/sql/statements with a single OAuth header. No SDK enums."""
    import json
    import urllib.error
    import urllib.request

    headers = dict(w.config.authenticate() or {})
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    body = json.dumps(
        {
            "warehouse_id": warehouse_id,
            "catalog": catalog,
            "schema": "gold",
            "statement": statement,
            "wait_timeout": "30s",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
        }
    ).encode("utf-8")
    url = f"https://{host}/api/2.0/sql/statements"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {e.code} {detail}") from e


def _resolve_warehouse():
    from utils.db_helpers import workspace_client
    from utils.workspace_names import SQL_WAREHOUSE_NAME
    import os

    w = workspace_client()
    want = (os.getenv("DATABRICKS_WAREHOUSE_NAME") or SQL_WAREHOUSE_NAME).strip().lower()
    matches = [wh for wh in w.warehouses.list() if (wh.name or "").strip().lower() == want]
    if not matches:
        raise ValueError(f"No SQL warehouse named '{want}'")
    wh = matches[0]
    host = (w.config.host or "").replace("https://", "").replace("http://", "").rstrip("/")
    return w, host, wh.id, wh.name


def render_live_statement_api(cursor=None, catalog: str = "onr_demo"):
    """Show a real Statement Execution REST call + live response."""
    st.markdown("### Statement Execution API")
    st.caption(
        "POST /api/2.0/sql/statements — OAuth, same warehouse as this console. Token redacted."
    )

    statement = DEMO_STATEMENT.format(catalog=catalog)
    host = "<workspace>"
    warehouse_id = "<warehouse_id>"
    try:
        _w, host, warehouse_id, wname = _resolve_warehouse()
        st.caption(f"Resolved warehouse **{wname}** (`{warehouse_id}`) on `{host}`.")
    except Exception as e:
        st.caption(f"Warehouse lookup deferred — curl still shows the contract. ({e})")

    payload = {
        "warehouse_id": warehouse_id,
        "catalog": catalog,
        "schema": "gold",
        "statement": statement,
        "wait_timeout": "30s",
        "disposition": "INLINE",
    }
    st.markdown("#### curl (token redacted)")
    st.code(
        f"""curl -sS -X POST 'https://{host}/api/2.0/sql/statements' \\
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(payload, indent=2)}'""",
        language="bash",
    )

    if st.button("Execute live Statement API call", type="primary", key="live_stmt_api"):
        try:
            import time
            from utils.ui import receipt_card
            from utils.workspace_names import SQL_WAREHOUSE_NAME

            w, host, warehouse_id, wname = _resolve_warehouse()
            t0 = time.perf_counter()
            dumped = None
            rest_error = None
            try:
                dumped = _execute_statement_rest(w, host, warehouse_id, statement, catalog)
            except Exception as rest_e:
                rest_error = rest_e
            if dumped is None:
                try:
                    from databricks.sdk.service.sql import Disposition, Format

                    resp = w.statement_execution.execute_statement(
                        warehouse_id=warehouse_id,
                        statement=statement,
                        catalog=catalog,
                        schema="gold",
                        wait_timeout="30s",
                        disposition=Disposition.INLINE,
                        format=Format.JSON_ARRAY,
                    )
                except TypeError:
                    resp = w.statement_execution.execute_statement(
                        warehouse_id=warehouse_id,
                        statement=statement,
                        catalog=catalog,
                        schema="gold",
                        wait_timeout="30s",
                    )
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                dumped = resp.as_dict() if hasattr(resp, "as_dict") else None
                if dumped is None:
                    dumped = {
                        "statement_id": getattr(resp, "statement_id", None),
                        "status": str(getattr(resp, "status", None)),
                        "manifest": str(getattr(resp, "manifest", None))[:500],
                    }
                if rest_error:
                    dumped["_rest_note"] = f"REST first attempt: {rest_error}"
            else:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
            # Never render secrets if the SDK echoed auth
            dumped.pop("access_token", None)
            sid = dumped.get("statement_id") or "?"
            status = dumped.get("status") or {}
            if isinstance(status, dict):
                state = _as_plain(status.get("state") or status.get("status")) or "SUCCEEDED"
            else:
                state = _as_plain(status) or "SUCCEEDED"
            manifest = dumped.get("manifest") or {}
            row_count = None
            if isinstance(manifest, dict):
                row_count = manifest.get("total_row_count")
                if row_count is None:
                    row_count = (manifest.get("schema") or {}).get("total_row_count")
            result = dumped.get("result") or {}
            if row_count is None and isinstance(result, dict) and result.get("data_array") is not None:
                row_count = len(result.get("data_array") or [])
            receipt_card(
                {
                    "statement_id": sid,
                    "status": state,
                    "row_count": row_count if row_count is not None else "—",
                    "warehouse": wname or SQL_WAREHOUSE_NAME,
                    "elapsed": f"{elapsed_ms} ms",
                }
            )
            st.session_state["last_statement_receipt"] = {
                "statement_id": sid,
                "status": state,
                "row_count": row_count,
                "warehouse": wname or SQL_WAREHOUSE_NAME,
                "elapsed": f"{elapsed_ms} ms",
            }
            st.success(f"statement_id = `{sid}`")
            with st.expander("Full response"):
                st.json(dumped)

            # Tabular view of data_array when present
            result = dumped.get("result") or {}
            data = result.get("data_array")
            manifest = dumped.get("manifest") or {}
            cols = []
            schema = (manifest.get("schema") or {}) if isinstance(manifest, dict) else {}
            for c in schema.get("columns") or []:
                cols.append(c.get("name") or "col")
            if data:
                st.dataframe(pd.DataFrame(data, columns=cols or None), use_container_width=True)
        except Exception as e:
            # Fallback: same SQL via the existing warehouse cursor so the page
            # still shows a live result even if the REST client path fails.
            st.warning(f"SDK REST call failed ({e}). Running the same SQL on the warehouse cursor.")
            if not cursor:
                st.error("No warehouse cursor either — start **onr demo warehouse**.")
                return
            try:
                import time
                from utils.ui import receipt_card
                from utils.workspace_names import SQL_WAREHOUSE_NAME

                t0 = time.perf_counter()
                cursor.execute(statement)
                cols = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                rcpt = {
                    "statement_id": "cursor-fallback",
                    "status": "SUCCEEDED",
                    "row_count": len(rows),
                    "warehouse": SQL_WAREHOUSE_NAME,
                    "elapsed": f"{elapsed_ms} ms",
                }
                st.session_state["last_statement_receipt"] = rcpt
                receipt_card(rcpt)
                st.dataframe(pd.DataFrame(rows, columns=cols), use_container_width=True)
                st.caption(
                    "Result came from the SQL warehouse (same compute the REST API would use). "
                    "The curl above is the integration contract for Advana / Cloud One."
                )
            except Exception as e2:
                st.error(f"Cursor fallback failed: {e2}")
    elif st.session_state.get("last_statement_receipt"):
        from utils.ui import receipt_card

        receipt_card(st.session_state["last_statement_receipt"])
