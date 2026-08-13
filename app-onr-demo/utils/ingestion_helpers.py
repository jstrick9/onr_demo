"""
Ingestion Helpers for ONR ITSS POC — Element 3
Automated Ingestion, Data Operations, and Streaming
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json


# -------------------------------
# INGESTION STATUS DISPLAY
# -------------------------------
def render_ingestion_status(cursor, catalog: str, schema: str):
    """Display current ingestion pipeline status."""
    st.markdown("### 📊 Pipeline Status")
    
    try:
        # Get ingestion metrics
        query = f"""
        SELECT 
            'Grants' as pipeline,
            COUNT(*) as total_records,
            SUM(CASE WHEN _ingest_time >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR THEN 1 ELSE 0 END) as last_hour,
            MAX(_ingest_time) as last_ingest,
            COUNT(DISTINCT _source_file) as source_files
        FROM `{catalog}`.`bronze`.grants
        UNION ALL
        SELECT 
            'Financial' as pipeline,
            COUNT(*) as total_records,
            SUM(CASE WHEN _ingest_time >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR THEN 1 ELSE 0 END) as last_hour,
            MAX(_ingest_time) as last_ingest,
            COUNT(DISTINCT _source_file) as source_files
        FROM `{catalog}`.`bronze`.financial
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        cols = st.columns(len(results))
        for idx, (pipeline, total, last_hour, last_ingest, files) in enumerate(results):
            with cols[idx]:
                st.metric(
                    label=f"📦 {pipeline}",
                    value=f"{total:,} records",
                    delta=f"+{last_hour} in last hour"
                )
                st.caption(f"Last ingest: {last_ingest}")
                st.caption(f"Source files: {files}")
    except Exception as e:
        st.info("📊 Pipeline metrics will appear once data is ingested.")


# -------------------------------
# QUALITY CHECK RESULTS
# -------------------------------
def render_quality_checks(cursor, catalog: str, schema: str):
    """Display data quality check results from ingestion."""
    st.markdown("### ✅ Quality Checks")
    
    try:
        query = f"""
        SELECT 
            check_name,
            check_status,
            records_checked,
            records_passed,
            records_failed,
            check_timestamp
        FROM `{catalog}`.`app`.ingestion_quality_log
        ORDER BY check_timestamp DESC
        LIMIT 10
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        if results:
            df = pd.DataFrame(results, columns=[
                "Check Name", "Status", "Checked", "Passed", "Failed", "Timestamp"
            ])
            
            # Color code status
            def color_status(val):
                if val == "PASS":
                    return "background-color: #d4edda"
                elif val == "FAIL":
                    return "background-color: #f8d7da"
                return ""
            
            st.dataframe(
                df.style.applymap(color_status, subset=["Status"]),
                use_container_width=True
            )
        else:
            st.info("No quality check results available yet.")
    except Exception as e:
        st.info("Quality check results will appear after pipeline execution.")


# -------------------------------
# SCHEMA EVOLUTION DISPLAY
# -------------------------------
def render_schema_evolution(cursor, catalog: str, schema: str):
    """Display schema evolution history."""
    st.markdown("### 🔄 Schema Evolution")
    
    try:
        query = f"""
        DESCRIBE HISTORY `{catalog}`.`bronze`.grants
        """
        cursor.execute(query)
        history = cursor.fetchall()
        
        if history:
            # Show last 5 schema changes
            for entry in history[:5]:
                with st.expander(f"Version {entry[0]} — {entry[1]}"):
                    st.write(f"**Operation:** {entry[3]}")
                    st.write(f"**Timestamp:** {entry[1]}")
                    if entry[7]:  # operationParameters
                        st.json(entry[7])
        else:
            st.info("No schema evolution history available.")
    except Exception as e:
        st.info("Schema evolution tracking requires Delta table history access.")


# -------------------------------
# STREAMING METRICS
# -------------------------------
def render_streaming_metrics():
    """Display streaming architecture metrics (simulated for demo)."""
    st.markdown("### 📡 Streaming Architecture")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Throughput",
            value="1,250 events/sec",
            delta="+5.2%"
        )
    with col2:
        st.metric(
            label="Latency (p99)",
            value="45ms",
            delta="-3ms",
            delta_color="inverse"
        )
    with col3:
        st.metric(
            label="Uptime",
            value="99.97%",
            delta="Last 30 days"
        )
    with col4:
        st.metric(
            label="Backlog",
            value="< 100",
            delta="Healthy"
        )


# -------------------------------
# INGESTION DEMO CONTROLS
# -------------------------------
def render_ingestion_demo(catalog: str, schema: str):
    """Render interactive ingestion demo controls."""
    st.markdown("### 🎮 Live Ingestion Demo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Upload Sample File")
        uploaded_file = st.file_uploader(
            "Upload a CSV or JSON file to simulate ingestion",
            type=["csv", "json"],
            key="ingestion_uploader"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_json(uploaded_file)
                
                st.success(f"✅ File loaded: {len(df)} records")
                st.dataframe(df.head(10))
                
                if st.button("🚀 Trigger Ingestion", type="primary"):
                    with st.spinner("Processing..."):
                        # Simulate ingestion steps
                        progress = st.progress(0)
                        status = st.empty()
                        
                        status.text("1️⃣ Detecting file schema...")
                        progress.progress(20)
                        
                        status.text("2️⃣ Running quality checks...")
                        progress.progress(40)
                        
                        status.text("3️⃣ Writing to Bronze layer...")
                        progress.progress(60)
                        
                        status.text("4️⃣ Updating catalog metadata...")
                        progress.progress(80)
                        
                        status.text("5️⃣ Ingestion complete!")
                        progress.progress(100)
                        
                        st.success("🎉 Ingestion completed successfully!")
                        
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    with col2:
        st.markdown("#### Auto Loader Configuration")
        st.code("""
# cloudFiles configuration for Auto Loader
spark.readStream \\
    .format("cloudFiles") \\
    .option("cloudFiles.format", "csv") \\
    .option("cloudFiles.inferColumnTypes", "true") \\
    .option("cloudFiles.schemaLocation", 
            f"/Volumes/{catalog}/bronze/landing/_schemas") \\
    .option("cloudFiles.schemaEvolutionMode", 
            "addNewColumns") \\
    .load(f"/Volumes/{catalog}/bronze/landing/")
        """, language="python")
        
        st.markdown("#### Key Features")
        st.markdown("""
        - ✅ **Incremental processing** — only new files
        - ✅ **Schema evolution** — handles new columns
        - ✅ **Quality gates** — validates on ingestion
        - ✅ **Error handling** — quarantines bad records
        - ✅ **Idempotent** — safe to re-run
        """)


# -------------------------------
# MOCK DATA GENERATION
# -------------------------------
def generate_mock_grants_data(num_records: int = 100) -> pd.DataFrame:
    """Return Compass fixture grants (exact schema)."""
    from utils.portfolio_data import grants_dataframe

    df = grants_dataframe()
    return df.head(num_records) if num_records else df


def generate_mock_financial_data(num_records: int = 200) -> pd.DataFrame:
    """Return ERP rows derived from the Compass grants fixture."""
    from utils.portfolio_data import financial_dataframe

    df = financial_dataframe()
    return df.head(num_records) if num_records else df
