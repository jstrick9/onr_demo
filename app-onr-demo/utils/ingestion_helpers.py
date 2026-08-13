"""
Ingestion Helpers for ONR ITSS POC — Element 3
Automated Ingestion, Data Operations, and Streaming
"""

import streamlit as st
import pandas as pd


# -------------------------------
# INGESTION STATUS DISPLAY
# -------------------------------
def render_ingestion_status(cursor, catalog: str, schema: str):
    """Display current ingestion pipeline status."""
    st.markdown("### 📊 Pipeline Status")
    
    if not cursor:
        st.info("📊 Pipeline metrics will appear once the warehouse is connected.")
        return
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
    
    if not cursor:
        st.info("Quality check results will appear after pipeline execution.")
        return
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
            
            sty = df.style
            try:
                sty = sty.map(color_status, subset=["Status"])
            except Exception:
                sty = df.style.applymap(color_status, subset=["Status"])
            st.dataframe(sty, use_container_width=True)
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
    
    if not cursor:
        st.info("Schema evolution tracking requires Delta table history access.")
        return
    try:
        query = f"""
        DESCRIBE HISTORY `{catalog}`.`bronze`.grants
        """
        cursor.execute(query)
        history = cursor.fetchall()
        
        if history:
            # Show last 5 schema changes
            # DESCRIBE HISTORY: version, timestamp, userId, userName, operation, operationParameters, ...
            for entry in history[:5]:
                version = entry[0] if len(entry) > 0 else "?"
                ts = entry[1] if len(entry) > 1 else ""
                op = entry[4] if len(entry) > 4 else ""
                params = entry[5] if len(entry) > 5 else None
                with st.expander(f"Version {version} — {ts}"):
                    st.write(f"**Operation:** {op}")
                    st.write(f"**Timestamp:** {ts}")
                    if params:
                        st.json(params)
        else:
            st.info("No schema evolution history available.")
    except Exception as e:
        st.info("Schema evolution tracking requires Delta table history access.")


# -------------------------------
# STREAMING METRICS
# -------------------------------
def render_streaming_metrics(cursor=None, catalog: str = "onr_demo"):
    """File-based ingest health from bronze (Auto Loader availableNow)."""
    st.markdown("### 📡 Ingest health")
    files, last, n = "—", "—", "—"
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT COUNT(DISTINCT _source_file), MAX(_ingest_time), COUNT(*)
                FROM `{catalog}`.`bronze`.grants
                """
            )
            files, last, n = cursor.fetchone()
        except Exception:
            pass
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bronze grants", f"{n}")
    c2.metric("Source files", f"{files}")
    c3.metric("Last ingest", str(last)[:19] if last and last != "—" else "—")
    c4.metric("Trigger", "availableNow")
    st.caption("Notebooks 01–03 run on **onr demo cluster**. SQL in this app uses **onr demo warehouse**.")


def render_file_picker_and_reset(cursor, catalog: str):
    """Pick staged files to land, or reset tables back to the 400-grant seed."""
    from utils.demo_actions import (
        FILE_PACKS,
        grant_count,
        process_selected_files,
        reset_to_seed_sql,
        try_start_cluster_notebooks,
    )
    import pandas as pd

    st.markdown("### Process files / reset demo")
    now = grant_count(cursor, catalog)
    if now is not None:
        st.metric("silver.grants", f"{now:,}")

    packs = st.multiselect(
        "Staged files to process",
        options=list(FILE_PACKS.keys()),
        format_func=lambda k: FILE_PACKS[k]["label"],
        default=["live"],
        key="ingest_packs",
    )
    uploaded = st.file_uploader(
        "Or upload your own grants CSV (same columns as the fixture)",
        type=["csv"],
        key="ingest_multi_upload",
    )
    extra_rows = None
    extra_name = "upload.csv"
    if uploaded:
        extra_rows = pd.read_csv(uploaded).to_dict(orient="records")
        extra_name = uploaded.name
        st.caption(f"Upload loaded: {len(extra_rows)} rows")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Process selected files", type="primary", key="process_files"):
            if not cursor:
                st.error("Connect **onr demo warehouse** to write UC tables.")
            elif not packs and not extra_rows:
                st.warning("Pick at least one staged file or upload a CSV.")
            else:
                with st.spinner("Landing files → bronze → silver → gold…"):
                    try:
                        result = process_selected_files(
                            cursor, catalog, packs, extra_rows=extra_rows, extra_name=extra_name
                        )
                        st.success(
                            f"silver.grants: {result['before']} → {result['after']}"
                        )
                        st.dataframe(pd.DataFrame(result["files"]), use_container_width=True)
                        for fsum in result["files"]:
                            if fsum.get("reasons"):
                                with st.expander(f"Details: {fsum['file']}"):
                                    for r in fsum["reasons"]:
                                        st.write(f"- {r}")
                        st.info(try_start_cluster_notebooks())
                    except Exception as e:
                        st.error(f"Process failed: {e}")
                        st.exception(e)
    with c2:
        confirm = st.checkbox("I want to reset to the 400-grant seed", key="confirm_reset")
        if st.button("Reset demo to seed", key="reset_seed", disabled=not confirm):
            if not cursor:
                st.error("Connect **onr demo warehouse** to reset tables.")
            else:
                with st.spinner("Removing live batches, restoring seed, clearing checkpoints…"):
                    try:
                        result = reset_to_seed_sql(cursor, catalog)
                        st.success(
                            f"Reset complete. silver.grants {result['before_silver']} → {result['after_silver']} "
                            f"(bronze={result['bronze_grants']})"
                        )
                        if result.get("warning"):
                            st.warning(result["warning"])
                        st.caption(result["checkpoints"])
                    except Exception as e:
                        st.error(f"Reset failed: {e}")
                        st.exception(e)
        st.caption(
            "Reset deletes non-seed bronze rows, rebuilds silver/gold, and tries to clear "
            "`/Volumes/onr_demo/bronze/checkpoints` so Auto Loader can re-read the same files. "
            "Cluster equivalent: `notebooks/05_reset_demo.py` on **onr demo cluster**."
        )


def render_ingestion_demo(catalog: str, schema: str):
    """Auto Loader snippet — writes happen via Process selected files or notebook 01."""
    st.markdown("### Auto Loader (cluster notebook 01)")
    st.caption("Use **Process selected files** above to land CSVs through the warehouse. This cell is the cluster equivalent.")
    st.code(
        f'''
spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", "/Volumes/{catalog}/bronze/landing/_schemas/grants")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("header", "true")
    .load("/Volumes/{catalog}/bronze/landing/grants/")
        '''.strip(),
        language="python",
    )


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
