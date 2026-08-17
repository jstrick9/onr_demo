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
def _human_ago(ts) -> str:
    if ts is None or ts == "—":
        return "—"
    try:
        import datetime as dt

        parsed = pd.to_datetime(ts, utc=True)
        if parsed is None or pd.isna(parsed):
            return "—"
        now = dt.datetime.now(dt.timezone.utc)
        if getattr(parsed, "tzinfo", None) is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        sec = int((now - parsed.to_pydatetime()).total_seconds())
        if sec < 0:
            sec = 0
        if sec < 60:
            return f"{sec}s ago"
        if sec < 3600:
            return f"{sec // 60}m ago"
        return f"{sec // 3600}h ago"
    except Exception:
        return str(ts)[:19]


def _bronze_pulse(cursor, catalog: str) -> dict:
    files, last, n, last2 = "—", None, "—", "—"
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
    return {"files": files, "last": last, "n": n, "last2": last2, "ago": _human_ago(last)}


def _heartbeat_body(cursor, catalog: str) -> None:
    from utils.ui import heartbeat_strip, provenance_note

    pulse = _bronze_pulse(cursor, catalog)
    last2 = pulse["last2"]
    n = pulse["n"]
    heartbeat_strip(
        f"{n:,}" if isinstance(n, int) else str(n),
        f"{last2}" if last2 != "—" else "—",
        pulse["ago"],
    )
    c1, c2, c3, c4 = st.columns(4)
    delta = None
    try:
        if last2 not in {None, "—"} and int(last2) > 0:
            delta = f"+{int(last2)}"
    except (TypeError, ValueError):
        delta = None
    c1.metric("Bronze grants", f"{n}", delta=delta)
    c2.metric("Source files", f"{pulse['files']}")
    c3.metric("Last 2 min", f"{last2}", delta=delta)
    c4.metric("Last file", pulse["ago"])
    provenance_note("bronze.grants", catalog, when=pulse["last"])


def render_streaming_metrics(cursor=None, catalog: str = "onr_demo"):
    """File-based ingest health from bronze (Auto Loader processingTime)."""
    st.markdown("### Stream health")
    st.session_state["_onr_hb_catalog"] = catalog
    rendered = False
    if hasattr(st, "fragment"):
        try:
            _streaming_heartbeat_fragment()
            rendered = True
        except Exception:
            rendered = False
    if not rendered:
        _heartbeat_body(cursor, catalog)


def _streaming_heartbeat_fragment():
    from utils.db_helpers import get_connection

    catalog = st.session_state.get("_onr_hb_catalog", "onr_demo")
    _conn, cur = get_connection()
    _heartbeat_body(cur, catalog)


if hasattr(st, "fragment"):
    try:
        from datetime import timedelta

        _streaming_heartbeat_fragment = st.fragment(run_every=timedelta(seconds=8))(
            _streaming_heartbeat_fragment
        )
    except Exception:
        pass


def render_time_travel_compare(cursor=None, catalog: str = "onr_demo"):
    """Gold/silver as of the previous Delta version vs now. No reset."""
    from utils.ui import time_travel_strip

    if not cursor:
        return
    try:
        cursor.execute(f"DESCRIBE HISTORY `{catalog}`.`silver`.grants")
        hist = cursor.fetchall()
        colnames = [str(d[0]).lower() for d in (cursor.description or [])]
    except Exception:
        return
    if not hist:
        return

    def _col(entry, *names, idx=0):
        for name in names:
            if name in colnames:
                return entry[colnames.index(name)]
        return entry[idx] if entry and len(entry) > idx else None

    versions = []
    for entry in hist[:8]:
        versions.append(
            {
                "version": _col(entry, "version", idx=0),
                "ts": _col(entry, "timestamp", idx=1),
            }
        )
    if not versions:
        return
    current = versions[0]
    baseline = versions[1] if len(versions) > 1 else versions[0]

    def _count_at(version) -> int | None:
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM `{catalog}`.`silver`.grants
                VERSION AS OF {int(version)}
                WHERE _is_active = true
                """
            )
            return int(cursor.fetchone()[0])
        except Exception:
            return None

    now_n = _count_at(current["version"])
    base_n = _count_at(baseline["version"]) if baseline["version"] != current["version"] else now_n
    if now_n is None:
        return
    time_travel_strip(
        {
            "label": "Baseline snapshot",
            "value": f"{base_n:,}" if base_n is not None else "—",
            "detail": f"silver.grants · version {baseline['version']} · {str(baseline['ts'])[:19]}",
        },
        {
            "label": "Now",
            "value": f"{now_n:,}",
            "detail": f"silver.grants · version {current['version']} · {str(current['ts'])[:19]}",
        },
        "RPO is the previous Delta version, not a backup truck.",
    )


def _show_ingest_pulse(cursor, catalog: str) -> None:
    from utils.demo_actions import grant_count, load_hold_queue
    from utils.ui import hold_tray, provenance_note

    now = grant_count(cursor, catalog)
    last = st.session_state.get("last_ingest") or {}
    holds = last.get("holds") or load_hold_queue(cursor, catalog)
    held = last.get("held")
    if held is None:
        held = len(holds) if holds else None
    c1, c2 = st.columns(2)
    delta = None
    if now is not None and last.get("before") is not None:
        try:
            delta = f"{int(now) - int(last['before']):+d}"
        except (TypeError, ValueError):
            delta = None
    with c1:
        c1.metric("Active grants", f"{now:,}" if now is not None else "—", delta=delta)
    with c2:
        if held:
            c2.metric("Held / skipped", f"{int(held):,}", delta=f"+{int(held)}")
        else:
            c2.metric("Held / skipped", "0")
    provenance_note("silver.grants", catalog)
    if last.get("before") is not None and last.get("after") is not None:
        st.caption(f"Active grants {last['before']} → {last['after']}")
    if holds:
        hold_tray(holds)


def render_stream_controls(catalog: str = "onr_demo") -> None:
    """Start the Auto Loader stream and land a new file — stay on this page."""
    from utils.ui import provenance_note
    from utils.workspace_ops import (
        STREAM_NOTEBOOK,
        notebook_url,
        render_run_status,
        resolve_notebook,
        start_stream,
        workspace_action_row,
    )

    st.markdown("### Stream")
    st.caption(
        "Same bronze table as Ingest selected files. Auto Loader on the landing Volume, "
        "thirty-second micro-batches, auto-stops after ninety seconds."
    )
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("Start stream", type="primary", key="start_stream"):
            try:
                result = start_stream(catalog)
                st.session_state["last_stream"] = result
                if result.get("error") and not result.get("file"):
                    st.error(result["error"])
                else:
                    st.success("Stream file is on the Volume.")
            except Exception as e:
                st.error(f"Stream did not start: {e}")
    with c2:
        path = resolve_notebook(STREAM_NOTEBOOK)
        workspace_action_row("Open stream notebook", notebook_url(path))
    render_run_status("Stream", st.session_state.get("last_stream"))
    provenance_note("bronze.grants", catalog)


def render_file_picker_and_reset(cursor, catalog: str):
    """Inbound files and baseline restore."""
    from utils.demo_actions import (
        FILE_PACKS,
        process_selected_files,
        reset_to_seed_sql,
    )
    import pandas as pd

    st.markdown("### Inbound files")
    _show_ingest_pulse(cursor, catalog)

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
                        st.session_state["last_ingest"] = result
                        before_n = result.get("before")
                        after_n = result.get("after")
                        landed = sum(int(f.get("landed") or 0) for f in result["files"])
                        st.success(f"Active grants {before_n} → {after_n} · landed {landed}")
                        st.rerun()
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
                        st.session_state.pop("last_ingest", None)
                        st.success(
                            f"Baseline restored. Active grants {result['before_silver']} → {result['after_silver']}"
                        )
                        if result.get("warning"):
                            st.warning(result["warning"])
                        st.rerun()
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
