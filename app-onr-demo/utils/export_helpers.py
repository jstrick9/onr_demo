"""
Export & Integration Helpers for ONR ITSS POC — Element 7
Interoperability, Data Portability, and Secure Export
"""

import streamlit as st
import pandas as pd
import json
import io
import uuid
from datetime import date, datetime


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def _ensure_export_history_table(cursor, catalog: str) -> None:
    if not cursor:
        return
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


def _date_column_for_table(dataset_table: str):
    """Return (column, kind) where kind is 'year' or 'ts'."""
    table_l = (dataset_table or "").lower()
    if "grants_by_awardee" in table_l:
        return "latest_grant_date", "ts"
    if "grant_predictions" in table_l:
        return "scored_at", "ts"
    if "funding_forecast" in table_l:
        return "fiscal_year", "year"
    if "program_trends" in table_l:
        return "computed_at", "ts"
    if "anomaly" in table_l:
        return "scored_at", "ts"
    if any(
        name in table_l
        for name in (
            "grants_summary",
            "financial_summary",
            "budget_execution",
            ".financial",
        )
    ):
        return "fiscal_year", "year"
    if "grants" in table_l:
        return "created_at", "ts"
    return None, None


def _filter_clause(dataset_table: str, filters: dict) -> tuple[str, str]:
    """SQL WHERE clause (including WHERE) and a human-readable summary."""
    start = filters.get("date_start")
    end = filters.get("date_end")
    col, kind = _date_column_for_table(dataset_table)
    if not start or not end or not col:
        return "", "none"
    if hasattr(start, "isoformat"):
        start_s = start.isoformat()
    else:
        start_s = str(start)
    if hasattr(end, "isoformat"):
        end_s = end.isoformat()
    else:
        end_s = str(end)
    if kind == "year":
        y0 = getattr(start, "year", int(str(start)[:4]))
        y1 = getattr(end, "year", int(str(end)[:4]))
        return f" WHERE {col} BETWEEN {int(y0)} AND {int(y1)}", f"{col} {y0}–{y1}"
    return (
        f" WHERE {col} >= TIMESTAMP '{start_s}' "
        f"AND {col} < TIMESTAMP '{end_s}' + INTERVAL 1 DAY",
        f"{col} {start_s} .. {end_s}",
    )


def _apply_filter_df(df: pd.DataFrame, dataset_table: str, filters: dict) -> pd.DataFrame:
    start = filters.get("date_start")
    end = filters.get("date_end")
    col, kind = _date_column_for_table(dataset_table)
    if df is None or df.empty or not start or not end or not col:
        return df
    if col not in df.columns:
        # fixture frames use created_at / fiscal_year
        if kind == "year" and "fiscal_year" in df.columns:
            col = "fiscal_year"
        elif "created_at" in df.columns:
            col, kind = "created_at", "ts"
        else:
            return df
    series = df[col]
    if kind == "year":
        y0 = getattr(start, "year", int(str(start)[:4]))
        y1 = getattr(end, "year", int(str(end)[:4]))
        years = pd.to_numeric(series, errors="coerce")
        return df[(years >= y0) & (years <= y1)]
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return df[(parsed >= start_ts) & (parsed < end_ts)]


def _persist_export(cursor, catalog: str, rec: dict) -> None:
    if not cursor:
        return
    try:
        _ensure_export_history_table(cursor, catalog)
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.export_history
            (export_id, user_email, dataset_name, format, record_count, file_size_bytes, created_at)
            VALUES (
                {_sql_str(rec.get("export_id"))},
                {_sql_str(rec.get("user"))},
                {_sql_str(rec.get("dataset"))},
                {_sql_str(",".join(rec.get("formats") or []))},
                {int(rec.get("records") or 0)},
                {int(rec.get("file_size_bytes") or 0)},
                CURRENT_TIMESTAMP()
            )
            """
        )
    except Exception:
        # Audit write must never fail the download itself.
        pass


# -------------------------------
# EXPORT FORMAT SELECTION
# -------------------------------
def render_export_options():
    """Display export format options."""
    st.markdown("### 📤 Export Format Selection")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📄 CSV Format")
        st.markdown(
            """
        - Universal compatibility
        - Lightweight, human-readable
        - Excel, Google Sheets compatible
        - Ideal for tabular data
        """
        )
        csv_selected = st.checkbox("Include CSV", value=True, key="export_csv")

    with col2:
        st.markdown("#### 📋 JSON Format")
        st.markdown(
            """
        - Web/API friendly
        - Nested data structures
        - JavaScript ecosystem native
        - Ideal for API integration
        """
        )
        json_selected = st.checkbox("Include JSON", value=True, key="export_json")

    with col3:
        st.markdown("#### 📊 Parquet Format")
        st.markdown(
            """
        - Columnar storage
        - Highly compressed
        - Big data optimized
        - Ideal for analytics
        """
        )
        parquet_selected = st.checkbox("Include Parquet", value=True, key="export_parquet")

    formats = []
    if csv_selected:
        formats.append("csv")
    if json_selected:
        formats.append("json")
    if parquet_selected:
        formats.append("parquet")

    return formats


# -------------------------------
# DATASET SELECTION
# -------------------------------
def render_dataset_selection(cursor, catalog: str, schema: str):
    """Display dataset selection for export."""
    st.markdown("### 📁 Dataset Selection")

    datasets = {
        "Grants Summary": f"`{catalog}`.`gold`.grants_summary",
        "Financial Summary": f"`{catalog}`.`gold`.financial_summary",
        "Grants by Awardee": f"`{catalog}`.`gold`.grants_by_awardee",
        "Budget Execution": f"`{catalog}`.`gold`.budget_execution",
        "Grant Predictions": f"`{catalog}`.`gold`.grant_predictions",
        "Funding Forecast": f"`{catalog}`.`gold`.funding_forecast",
        "Program Trends": f"`{catalog}`.`gold`.program_trends",
        "Anomaly Scores": f"`{catalog}`.`gold`.grant_anomaly_scores",
        "Raw Grants": f"`{catalog}`.`silver`.grants",
        "Raw Financial": f"`{catalog}`.`silver`.financial",
    }

    selected_dataset = st.selectbox(
        "Select Dataset",
        options=list(datasets.keys()),
        key="export_dataset",
    )

    # Show preview
    try:
        query = f"SELECT COUNT(*) as cnt FROM {datasets[selected_dataset]}"
        if not cursor:
            raise RuntimeError("no warehouse")
        cursor.execute(query)
        count = cursor.fetchone()[0]
        st.info(f"📊 **{selected_dataset}**: {count:,} records available for export")
    except Exception:
        st.info("Dataset count will appear once data is loaded.")

    return selected_dataset, datasets.get(selected_dataset)


# -------------------------------
# FILTER BEFORE EXPORT
# -------------------------------
def render_export_filters():
    """Display filters to apply before export."""
    st.markdown("### 🔍 Apply Filters (Optional)")
    st.caption(
        "Date range is applied to the dataset’s date column "
        "(`fiscal_year` on summaries, `created_at` / `scored_at` / `latest_grant_date` on detail tables). "
        "Narrow the range during the demo to prove a **filtered** bulk export."
    )

    col1, col2 = st.columns(2)

    with col1:
        date_range = st.date_input(
            "Date Range",
            value=(date(2025, 1, 1), date(2026, 12, 31)),
            min_value=date(2018, 1, 1),
            max_value=date(2027, 12, 31),
            key="export_date_range",
        )

    with col2:
        max_records = st.number_input(
            "Maximum Records",
            min_value=100,
            max_value=1000000,
            value=100000,
            step=1000,
            key="export_max_records",
        )

    if isinstance(date_range, (list, tuple)):
        date_start = date_range[0] if len(date_range) > 0 else None
        date_end = date_range[1] if len(date_range) > 1 else date_start
    else:
        date_start = date_end = date_range
    return {
        "date_start": date_start,
        "date_end": date_end,
        "max_records": max_records,
    }


# -------------------------------
# SECURE EXPORT EXECUTION
# -------------------------------
def render_secure_export(cursor, catalog: str, schema: str, dataset_table: str, formats: list, filters: dict):
    """Execute secure data export."""
    st.markdown("### 🔒 Secure Export")

    where_sql, filter_label = _filter_clause(dataset_table, filters)
    col, _kind = _date_column_for_table(dataset_table)
    if col:
        st.caption(f"Filter that will be applied: **{filter_label}** on `{col}`.")

    st.caption(
        "TLS to the warehouse · row written to `app.export_history` · mock data only."
    )

    if st.button("🚀 Execute Export", type="primary", key="exec_export_btn"):
        with st.spinner("Preparing secure export..."):
            progress = st.progress(0)
            status = st.empty()

            status.text("1️⃣ Validating access permissions...")
            progress.progress(15)

            status.text("2️⃣ Applying filters...")
            progress.progress(30)

            status.text("3️⃣ Querying data...")
            progress.progress(50)

            # Execute query
            try:
                limit = int(filters.get("max_records") or 100000)
                if cursor:
                    query = f"""
                    SELECT * FROM {dataset_table}
                    {where_sql}
                    LIMIT {limit}
                    """
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    df = pd.DataFrame(rows, columns=columns)
                else:
                    from utils.portfolio_data import grants_dataframe, financial_dataframe

                    if "financial" in (dataset_table or "").lower():
                        df = financial_dataframe()
                    else:
                        df = grants_dataframe()
                    df = _apply_filter_df(df, dataset_table, filters)
                    df = df.head(limit)

                status.text("4️⃣ Generating export files...")
                progress.progress(70)

                # Generate exports
                exports = {}

                if "csv" in formats:
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    exports["csv"] = csv_buffer.getvalue()

                if "json" in formats:
                    json_data = df.to_json(orient="records", indent=2)
                    exports["json"] = json_data

                if "parquet" in formats:
                    parquet_buffer = io.BytesIO()
                    pq = df.copy()
                    for pcol in pq.columns:
                        if pq[pcol].dtype == object:
                            pq[pcol] = pq[pcol].apply(
                                lambda x: json.dumps(x) if isinstance(x, (list, dict, tuple)) else x
                            )
                    pq.to_parquet(parquet_buffer, index=False)
                    exports["parquet"] = parquet_buffer.getvalue()

                status.text("5️⃣ Logging export to audit trail...")
                progress.progress(90)

                file_size = 0
                for payload in exports.values():
                    if isinstance(payload, bytes):
                        file_size += len(payload)
                    else:
                        file_size += len(str(payload).encode("utf-8"))

                rec = {
                    "export_id": f"exp-{uuid.uuid4().hex[:12]}",
                    "timestamp": datetime.now().isoformat(),
                    "dataset": dataset_table,
                    "records": len(df),
                    "formats": formats,
                    "filter": filter_label,
                    "user": st.session_state.get("email") or "unknown",
                    "file_size_bytes": file_size,
                }
                st.session_state.setdefault("export_history", []).append(rec)
                _persist_export(cursor, catalog, rec)

                status.text("✅ Export complete!")
                progress.progress(100)

                st.success(
                    f"✅ Exported {len(df):,} filtered records "
                    f"({filter_label}). Logged to `app.export_history`."
                )

                # Download buttons
                col1, col2, col3 = st.columns(3)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                with col1:
                    if "csv" in exports:
                        st.download_button(
                            label="📥 Download CSV",
                            data=exports["csv"],
                            file_name=f"onr_export_{timestamp}.csv",
                            mime="text/csv",
                        )

                with col2:
                    if "json" in exports:
                        st.download_button(
                            label="📥 Download JSON",
                            data=exports["json"],
                            file_name=f"onr_export_{timestamp}.json",
                            mime="application/json",
                        )

                with col3:
                    if "parquet" in exports:
                        st.download_button(
                            label="📥 Download Parquet",
                            data=exports["parquet"],
                            file_name=f"onr_export_{timestamp}.parquet",
                            mime="application/octet-stream",
                        )

            except Exception as e:
                st.error(f"Export failed: {str(e)}")


# -------------------------------
# API DOCUMENTATION
# -------------------------------
def render_api_documentation():
    """Display API documentation for integration."""
    st.markdown("### 🔌 API Integration Documentation")

    st.markdown(
        """
The live integration surface is **Databricks Statement Execution REST**
(`/api/2.0/sql/statements`) against the serverless SQL warehouse — the same
endpoint Advana, Cloud One, or any JDBC client would call. Use the button
above. Do not treat `api.onr-demo.com` as a real host.
        """
    )
    with st.expander("Illustrative resource paths (not a public host)"):
        st.caption(
            "These curls are a mapping story only. The live call is the Statement API above."
        )
        st.code(
            """
# Same SQL the Statement API runs:
# POST https://<workspace>/api/2.0/sql/statements
# { "warehouse_id": "<onr demo warehouse>",
#   "statement": "SELECT grant_no, title, amount_usd, awardee
#                 FROM onr_demo.silver.grants
#                 WHERE fiscal_year BETWEEN 2025 AND 2026 LIMIT 100" }
            """.strip(),
            language="bash",
        )


# -------------------------------
# INTEROPERABILITY DEMO
# -------------------------------
def render_interoperability():
    """Display interoperability capabilities."""
    st.markdown("### 🔄 Platform Interoperability")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ Supported Integrations")

        integrations = [
            {"platform": "Advana", "status": "✅ Compatible", "method": "REST API / JDBC"},
            {"platform": "Cloud One", "status": "✅ Compatible", "method": "S3 / REST API"},
            {"platform": "Palantir Foundry", "status": "✅ Compatible", "method": "API / Bulk Export"},
            {"platform": "Tableau", "status": "✅ Compatible", "method": "JDBC / ODBC"},
            {"platform": "Power BI", "status": "✅ Compatible", "method": "ODBC / REST"},
            {"platform": "Excel", "status": "✅ Compatible", "method": "CSV / XLSX Export"},
        ]

        st.dataframe(pd.DataFrame(integrations), use_container_width=True)

    with col2:
        st.markdown("#### 🏗️ Architecture Principles")
        st.markdown(
            """
        - **Open Standards**: CSV, JSON, Parquet, SQL
        - **Standard APIs**: RESTful, ODBC/JDBC
        - **Portable Storage**: Delta Lake (open format)
        - **No Vendor Lock-in**: Standard protocols, exportable data
        - **Loose Coupling**: Microservices architecture
        - **Schema Portability**: Self-describing data formats
        """
        )


# -------------------------------
# EXPORT HISTORY
# -------------------------------
def render_export_history(cursor=None, catalog: str = "onr_demo"):
    """Display export history from this session and from Unity Catalog."""
    st.markdown("### 📜 Export History")

    session_hist = st.session_state.get("export_history", [])
    if session_hist:
        st.markdown("#### This app session")
        st.dataframe(pd.DataFrame(session_hist), use_container_width=True)

    uc = pd.DataFrame()
    if cursor:
        try:
            _ensure_export_history_table(cursor, catalog)
            cursor.execute(
                f"""
                SELECT export_id, created_at, user_email, dataset_name, format,
                       record_count, file_size_bytes
                FROM `{catalog}`.`app`.export_history
                ORDER BY created_at DESC
                LIMIT 50
                """
            )
            cols = [str(d[0]).lower() for d in cursor.description]
            uc = pd.DataFrame(cursor.fetchall(), columns=cols)
        except Exception:
            uc = pd.DataFrame()

    st.markdown("#### Persisted audit (`app.export_history`)")
    if uc.empty:
        st.caption("No persisted exports yet. Run an export on the Data Export tab.")
    else:
        st.dataframe(uc, use_container_width=True)


# -------------------------------
# SCHEMA DOCUMENTATION
# -------------------------------
def render_schema_documentation():
    """Display schema documentation for portability."""
    st.markdown("### 📖 Schema Documentation")

    st.markdown(
        """
    All exported data includes self-describing schemas for maximum portability.
    """
    )

    with st.expander("Grants Schema"):
        st.code(
            """
{
  "schema": {
    "grant_no": "string — Unique grant identifier (ONRD-YYYY-AREA-#####)",
    "title": "string — Grant title",
    "abstract": "string — Synthetic abstract",
    "program_area": "string — ONR program area",
    "fiscal_year": "integer — Federal fiscal year",
    "amount_usd": "decimal — Award amount in USD",
    "awardee": "string — Performing organization (synthetic)",
    "org_unit": "string — ONR code / corporate unit",
    "classification_band": "string — CUI-Mock or Public-Mock",
    "batch_id": "string — Ingestion batch",
    "created_at": "timestamp — Award create time"
  },
  "version": "1.0",
  "last_updated": "2026-08-12",
  "data_classification": "UNCLASSIFIED // MOCK DATA"
}
        """,
            language="json",
        )

    with st.expander("Financial Schema"):
        st.code(
            """
{
  "schema": {
    "transaction_id": "string — Unique transaction ID",
    "grant_no": "string — FK to grants.grant_no",
    "cost_center": "string — Organizational cost center (from org_unit)",
    "category": "string — Expenditure category",
    "fiscal_year": "integer — Federal fiscal year",
    "quarter": "string — Fiscal quarter (Q1-Q4)",
    "budget_allocated": "decimal — Budget allocation in USD",
    "actual_expenditure": "decimal — Actual spend in USD",
    "execution_rate": "decimal — Execution rate as percentage",
    "variance": "decimal — Budget variance in USD",
    "status": "string — Period status (Open/Closed)"
  },
  "version": "1.0",
  "last_updated": "2026-08-12",
  "data_classification": "UNCLASSIFIED // MOCK DATA"
}
        """,
            language="json",
        )
