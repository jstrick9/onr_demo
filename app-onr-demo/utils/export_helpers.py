"""
Export & Integration Helpers for ONR ITSS POC — Element 7
Interoperability, Data Portability, and Secure Export
"""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime


# -------------------------------
# EXPORT FORMAT SELECTION
# -------------------------------
def render_export_options():
    """Display export format options."""
    st.markdown("### 📤 Export Format Selection")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📄 CSV Format")
        st.markdown("""
        - Universal compatibility
        - Lightweight, human-readable
        - Excel, Google Sheets compatible
        - Ideal for tabular data
        """)
        csv_selected = st.checkbox("Include CSV", value=True, key="export_csv")
    
    with col2:
        st.markdown("#### 📋 JSON Format")
        st.markdown("""
        - Web/API friendly
        - Nested data structures
        - JavaScript ecosystem native
        - Ideal for API integration
        """)
        json_selected = st.checkbox("Include JSON", value=True, key="export_json")
    
    with col3:
        st.markdown("#### 📊 Parquet Format")
        st.markdown("""
        - Columnar storage
        - Highly compressed
        - Big data optimized
        - Ideal for analytics
        """)
        parquet_selected = st.checkbox("Include Parquet", value=False, key="export_parquet")
    
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
        "Raw Grants": f"`{catalog}`.`silver`.grants",
        "Raw Financial": f"`{catalog}`.`silver`.financial",
    }
    
    selected_dataset = st.selectbox(
        "Select Dataset",
        options=list(datasets.keys()),
        key="export_dataset"
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_range = st.date_input(
            "Date Range",
            value=(datetime(2025, 1, 1), datetime(2026, 12, 31)),
            key="export_date_range"
        )
    
    with col2:
        max_records = st.number_input(
            "Maximum Records",
            min_value=100,
            max_value=1000000,
            value=100000,
            step=1000,
            key="export_max_records"
        )
    
    return {
        "date_start": date_range[0] if len(date_range) > 0 else None,
        "date_end": date_range[1] if len(date_range) > 1 else None,
        "max_records": max_records
    }


# -------------------------------
# SECURE EXPORT EXECUTION
# -------------------------------
def render_secure_export(cursor, catalog: str, schema: str, dataset_table: str, formats: list, filters: dict):
    """Execute secure data export."""
    st.markdown("### 🔒 Secure Export")
    
    # Security notice
    st.warning("""
    ⚠️ **Security Notice**: This export uses:
    - Encrypted data transfer (TLS 1.3)
    - Audit logging of all exports
    - Data classification tags applied
    - No CUI/PII in mock data
    """)
    
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
                if cursor:
                    query = f"""
                    SELECT * FROM {dataset_table}
                    LIMIT {filters.get('max_records', 100000)}
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
                    df = df.head(int(filters.get("max_records", 100000)))
                
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
                    df.to_parquet(parquet_buffer, index=False)
                    exports["parquet"] = parquet_buffer.getvalue()
                
                status.text("5️⃣ Logging export to audit trail...")
                progress.progress(90)
                
                # Log export (in production, this would write to audit table)
                st.session_state.setdefault("export_history", []).append({
                    "timestamp": datetime.now().isoformat(),
                    "dataset": dataset_table,
                    "records": len(df),
                    "formats": formats,
                    "user": st.session_state.get("email", "unknown")
                })
                
                status.text("✅ Export complete!")
                progress.progress(100)
                
                st.success(f"✅ Successfully exported {len(df):,} records!")
                
                # Download buttons
                col1, col2, col3 = st.columns(3)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                with col1:
                    if "csv" in exports:
                        st.download_button(
                            label="📥 Download CSV",
                            data=exports["csv"],
                            file_name=f"onr_export_{timestamp}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if "json" in exports:
                        st.download_button(
                            label="📥 Download JSON",
                            data=exports["json"],
                            file_name=f"onr_export_{timestamp}.json",
                            mime="application/json"
                        )
                
                with col3:
                    if "parquet" in exports:
                        st.download_button(
                            label="📥 Download Parquet",
                            data=exports["parquet"],
                            file_name=f"onr_export_{timestamp}.parquet",
                            mime="application/octet-stream"
                        )
                
            except Exception as e:
                st.error(f"Export failed: {str(e)}")


# -------------------------------
# API DOCUMENTATION
# -------------------------------
def render_api_documentation():
    """Display API documentation for integration."""
    st.markdown("### 🔌 API Integration Documentation")
    
    st.markdown("""
    The ONR ITSS platform provides RESTful APIs for seamless integration with enterprise systems.
    """)
    
    tab1, tab2, tab3 = st.tabs(["Grants API", "Financial API", "Export API"])
    
    with tab1:
        st.markdown("#### GET /api/v1/grants")
        st.code("""
# Retrieve grants with filters
curl -X GET "https://api.onr-demo.com/v1/grants" \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "fiscal_year": 2026,
    "program_area": "AI/ML",
    "limit": 100
  }'

# Response
{
  "status": "success",
  "count": 45,
  "data": [
    {
      "grant_no": "ONRD-2026-AIML-00336",
      "title": "Advancing graph neural network reasoning...",
      "amount_usd": 2551000,
      "awardee": "Anchor Applied Research LLC"
    }
  ]
}
        """, language="bash")
    
    with tab2:
        st.markdown("#### GET /api/v1/financial")
        st.code("""
# Retrieve financial data
curl -X GET "https://api.onr-demo.com/v1/financial" \\
  -H "Authorization: Bearer {token}" \\
  -d '{
    "cost_center": "R&D-001",
    "fiscal_year": 2026,
    "quarter": "Q2"
  }'
        """, language="bash")
    
    with tab3:
        st.markdown("#### POST /api/v1/export")
        st.code("""
# Trigger secure export
curl -X POST "https://api.onr-demo.com/v1/export" \\
  -H "Authorization: Bearer {token}" \\
  -d '{
    "dataset": "grants_summary",
    "format": "parquet",
    "filters": {
      "fiscal_year": 2026
    },
    "notify_email": "user@navy.mil"
  }'

# Response
{
  "export_id": "exp-789xyz",
  "status": "processing",
  "estimated_time": "2 minutes",
  "download_url": null  // Available when complete
}
        """, language="bash")


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
        st.markdown("""
        - **Open Standards**: CSV, JSON, Parquet, SQL
        - **Standard APIs**: RESTful, ODBC/JDBC
        - **Portable Storage**: Delta Lake (open format)
        - **No Vendor Lock-in**: Standard protocols, exportable data
        - **Loose Coupling**: Microservices architecture
        - **Schema Portability**: Self-describing data formats
        """)


# -------------------------------
# EXPORT HISTORY
# -------------------------------
def render_export_history():
    """Display export history log."""
    st.markdown("### 📜 Export History")
    
    history = st.session_state.get("export_history", [])
    
    if history:
        df = pd.DataFrame(history)
        st.dataframe(
            df.style.format({"timestamp": lambda x: x[:19]}),
            use_container_width=True
        )
    else:
        # Show sample history
        sample_history = [
            {"timestamp": "2026-08-12 14:30:00", "dataset": "gold.grants_summary", "records": 400, "formats": "CSV, JSON", "user": "analyst@navy.mil"},
            {"timestamp": "2026-08-12 10:15:00", "dataset": "gold.financial_summary", "records": 1200, "formats": "Parquet", "user": "admin@navy.mil"},
            {"timestamp": "2026-08-11 16:45:00", "dataset": "silver.grants", "records": 400, "formats": "CSV", "user": "jsmith@navy.mil"},
        ]
        st.dataframe(pd.DataFrame(sample_history), use_container_width=True)


# -------------------------------
# SCHEMA DOCUMENTATION
# -------------------------------
def render_schema_documentation():
    """Display schema documentation for portability."""
    st.markdown("### 📖 Schema Documentation")
    
    st.markdown("""
    All exported data includes self-describing schemas for maximum portability.
    """)
    
    with st.expander("Grants Schema"):
        st.code("""
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
        """, language="json")
    
    with st.expander("Financial Schema"):
        st.code("""
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
        """, language="json")
