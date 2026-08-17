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
    st.markdown("### Pipeline")
    
    if not cursor:
        st.caption("Pipeline metrics appear when the warehouse is connected.")
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
        st.caption("Pipeline metrics appear after the first ingest.")


# -------------------------------
# QUALITY CHECK RESULTS
# -------------------------------
def render_quality_checks(cursor, catalog: str, schema: str):
    """Display data quality check results from ingestion."""
    st.markdown("### Quality checks")
    
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
            st.caption("No quality results yet.")
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
            colnames = [str(d[0]).lower() for d in (cursor.description or [])]

            def _col(entry, *names, fallback_idx=None):
                for name in names:
                    if name in colnames:
                        return entry[colnames.index(name)]
                if fallback_idx is not None and len(entry) > fallback_idx:
                    return entry[fallback_idx]
                return None

            for entry in history[:5]:
                version = _col(entry, "version", fallback_idx=0) or "?"
                ts = _col(entry, "timestamp", fallback_idx=1) or ""
                op = _col(entry, "operation", fallback_idx=4) or ""
                params = _col(entry, "operationparameters", "operation_parameters", fallback_idx=5)
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
    st.markdown("### Stream health")
    files, last, n, last2 = "—", "—", "—", "—"
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
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM `{catalog}`.`bronze`.grants
                WHERE _ingest_time >= CURRENT_TIMESTAMP() - INTERVAL 2 MINUTES
                """
            )
            last2 = cursor.fetchone()[0]
        except Exception:
            last2 = "—"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bronze grants", f"{n}")
    c2.metric("Source files", f"{files}")
    c3.metric("Last 2 min", f"{last2}")
    c4.metric("Last ingest", str(last)[:19] if last and last != "—" else "—")


def render_file_picker_and_reset(cursor, catalog: str):
    """Inbound files and baseline restore."""
    from utils.demo_actions import (
        FILE_PACKS,
        grant_count,
        process_selected_files,
        reset_to_seed_sql,
    )
    import pandas as pd

    st.markdown("### Inbound files")
    now = grant_count(cursor, catalog)
    if now is not None:
        st.metric("Active grants", f"{now:,}")

    packs = st.multiselect(
        "Queued files",
        options=list(FILE_PACKS.keys()),
        format_func=lambda k: FILE_PACKS[k]["label"],
        default=["live", "quality_fail"],
        key="ingest_packs",
    )
    uploaded = st.file_uploader(
        "Or upload a grants CSV",
        type=["csv"],
        key="ingest_multi_upload",
    )
    extra_rows = None
    extra_name = "upload.csv"
    if uploaded:
        extra_rows = pd.read_csv(uploaded).to_dict(orient="records")
        extra_name = uploaded.name
        st.caption(f"{len(extra_rows)} rows loaded")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ingest selected files", type="primary", key="process_files"):
            if not cursor:
                st.error("Warehouse is not connected.")
            elif not packs and not extra_rows:
                st.warning("Select a queued file or upload a CSV.")
            else:
                with st.spinner("Landing files…"):
                    try:
                        result = process_selected_files(
                            cursor, catalog, packs, extra_rows=extra_rows, extra_name=extra_name
                        )
                        before_n = result.get("before")
                        after_n = result.get("after")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Before", f"{before_n:,}" if before_n is not None else "—")
                        m2.metric(
                            "After",
                            f"{after_n:,}" if after_n is not None else "—",
                            delta=(
                                f"{after_n - before_n:+d}"
                                if before_n is not None and after_n is not None
                                else None
                            ),
                        )
                        landed = sum(int(f.get("landed") or 0) for f in result["files"])
                        rejected = sum(
                            int(f.get("rejected") or 0) + int(f.get("skipped") or 0)
                            for f in result["files"]
                        )
                        m3.metric("Held / skipped", f"{rejected:,}")
                        st.success(f"Active grants {before_n} → {after_n} · landed {landed}")
                        st.dataframe(pd.DataFrame(result["files"]), use_container_width=True)
                        for fsum in result["files"]:
                            if fsum.get("reasons"):
                                with st.expander(fsum["file"]):
                                    for r in fsum["reasons"]:
                                        st.write(f"- {r}")
                    except Exception as e:
                        st.error(f"Ingest failed: {e}")
    with c2:
        confirm = st.checkbox("Confirm restore of the baseline snapshot", key="confirm_reset")
        if st.button("Restore baseline snapshot", key="reset_seed", disabled=not confirm):
            if not cursor:
                st.error("Warehouse is not connected.")
            else:
                with st.spinner("Restoring baseline…"):
                    try:
                        result = reset_to_seed_sql(cursor, catalog)
                        st.success(
                            f"Baseline restored. Active grants {result['before_silver']} → {result['after_silver']}"
                        )
                        if result.get("warning"):
                            st.warning(result["warning"])
                    except Exception as e:
                        st.error(f"Restore failed: {e}")
        st.caption("Removes inbound batches and rebuilds silver and gold from the official snapshot.")


def render_ingestion_demo(catalog: str, schema: str):
    """Auto Loader contract — no operator runbook."""
    st.markdown("### Auto Loader")
    st.caption(
        "cloudFiles on the landing Volume. Schema evolution is addNewColumns. "
        "Micro-batches use processingTime 30 seconds; file-arrival jobs use availableNow."
    )
    st.code(
        f'''
spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", "/Volumes/{catalog}/bronze/landing/_schemas/grants")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("header", "true")
    .load("/Volumes/{catalog}/bronze/landing/grants/")
    .writeStream.format("delta")
    .option("checkpointLocation", "/Volumes/{catalog}/bronze/checkpoints/grants_stream")
    .trigger(processingTime="30 seconds")
    .toTable("`{catalog}`.`bronze`.grants")
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
