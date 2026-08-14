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


def _resolve_warehouse():
    from databricks.sdk import WorkspaceClient
    from utils.workspace_names import SQL_WAREHOUSE_NAME
    import os

    w = WorkspaceClient()
    want = (os.getenv("DATABRICKS_WAREHOUSE_NAME") or SQL_WAREHOUSE_NAME).strip().lower()
    matches = [wh for wh in w.warehouses.list() if (wh.name or "").strip().lower() == want]
    if not matches:
        raise ValueError(f"No SQL warehouse named '{want}'")
    wh = matches[0]
    host = (w.config.host or "").replace("https://", "").replace("http://", "").rstrip("/")
    return w, host, wh.id, wh.name


def render_live_statement_api(cursor=None, catalog: str = "onr_demo"):
    """Show a real Statement Execution REST call + live response."""
    st.markdown("### Live API — Databricks Statement Execution REST")
    st.markdown(
        """
        This is the **real, open, documented API** — not a fictional `api.onr-demo.com`.
        Advana, Cloud One, or any enterprise client authenticates with OAuth and POSTs SQL
        at `/api/2.0/sql/statements`. Same warehouse the dashboard already uses.
        The token below is **redacted**; the live call uses the app service principal.
        """
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
            w, host, warehouse_id, _name = _resolve_warehouse()
            resp = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                catalog=catalog,
                schema="gold",
                wait_timeout="30s",
                disposition="INLINE",
            )
            # SDK object → json-friendly dict
            dumped = resp.as_dict() if hasattr(resp, "as_dict") else None
            if dumped is None:
                dumped = {
                    "statement_id": getattr(resp, "statement_id", None),
                    "status": str(getattr(resp, "status", None)),
                    "manifest": str(getattr(resp, "manifest", None))[:500],
                }
            # Never render secrets if the SDK echoed auth
            dumped.pop("access_token", None)
            st.success(
                f"statement_id = `{dumped.get('statement_id') or getattr(resp, 'statement_id', '?')}`"
            )
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
                cursor.execute(statement)
                cols = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                st.dataframe(pd.DataFrame(rows, columns=cols), use_container_width=True)
                st.caption(
                    "Result came from the SQL warehouse (same compute the REST API would use). "
                    "The curl above is the integration contract for Advana / Cloud One."
                )
            except Exception as e2:
                st.error(f"Cursor fallback failed: {e2}")
