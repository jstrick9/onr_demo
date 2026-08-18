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
        query = f"""
        SELECT
            'Bronze grants' as pipeline,
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
    except Exception:
        st.caption("Pipeline metrics appear after the first ingest.")


# -------------------------------
# QUALITY CHECK RESULTS
# -------------------------------
def render_quality_checks(cursor, catalog: str, schema: str):
    """DQ console: scoreboard, quarantine error log, published warnings, gate history."""
    from utils.demo_actions import load_hold_queue, load_quality_findings, grant_count, bronze_count
    from utils.ui import hold_tray, provenance_note

    st.markdown("### Data quality")
    st.caption(
        "Quarantine (empty / dup / amt) never enters bronze — it is written to `app.quarantine_log`. "
        "Warnings (missing abstract, unknown area, amount over $5M) still publish."
    )

    last = st.session_state.get("last_ingest") or {}
    holds = (load_hold_queue(cursor, catalog) if cursor else []) or last.get("holds") or []
    warns = (load_quality_findings(cursor, catalog) if cursor else []) or last.get("warnings") or []
    silver_n = grant_count(cursor, catalog) if cursor else last.get("after")
    bronze_n = None
    if cursor:
        try:
            bronze_n = bronze_count(cursor, catalog)
        except Exception:
            bronze_n = last.get("bronze")
    q_n = len(holds)
    w_n = len(warns)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Published (silver)", f"{silver_n:,}" if silver_n is not None else "—")
    c2.metric("Bronze", f"{bronze_n:,}" if bronze_n is not None else "—")
    c3.metric("Quarantined", f"{q_n:,}", delta=f"+{q_n}" if q_n else None)
    c4.metric("Warnings (published)", f"{w_n:,}", delta=f"+{w_n}" if w_n else None)
    provenance_note("app.quarantine_log", catalog)

    st.markdown("#### Quarantine — error log")
    if holds:
        hold_tray(holds)
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "grant_no": h.get("grant_no"),
                        "reason": h.get("code"),
                        "detail": h.get("detail"),
                        "amount": h.get("amount_usd"),
                        "title": h.get("title"),
                    }
                    for h in holds
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No quarantined rows.")

    st.markdown("#### Warnings — published with a finding")
    if warns:
        show = pd.DataFrame(warns)
        keep = [c for c in ("grant_no", "check_name", "detail", "program_area", "amount_usd", "severity", "published") if c in show.columns]
        st.dataframe(show[keep] if keep else show, use_container_width=True, hide_index=True)
    else:
        st.caption("No warning findings on published rows.")

    if not cursor:
        st.info("Warehouse is not connected — gate history is unavailable.")
        return
    st.markdown("#### Gate history")
    try:
        query = f"""
        SELECT
            check_name,
            check_status,
            records_checked,
            records_passed,
            records_failed,
            check_timestamp,
            pipeline_name
        FROM `{catalog}`.`app`.ingestion_quality_log
        ORDER BY check_timestamp DESC
        LIMIT 20
        """
        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            df = pd.DataFrame(results, columns=[
                "Check", "Status", "Checked", "Passed", "Failed", "Timestamp", "Pipeline"
            ])

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
            st.caption("No quality log rows yet. Ingest inbound grants and the quarantine sample.")
    except Exception as e:
        st.caption(f"Quality log not readable ({e}).")


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
    except Exception:
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


def _stream_bronze_count(cursor, catalog: str):
    if not cursor:
        return None
    try:
        cursor.execute(
            f"""
            SELECT COUNT(*) FROM `{catalog}`.`bronze`.grants
            WHERE coalesce(_batch_id, batch_id) = 'stream-demo-2026'
            """
        )
        return int(cursor.fetchone()[0])
    except Exception:
        return None


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
    from utils.demo_actions import grant_count
    from utils.ui import heartbeat_strip, provenance_note

    pulse = _bronze_pulse(cursor, catalog)
    last2 = pulse["last2"]
    n = pulse["n"]
    silver_n = grant_count(cursor, catalog) if cursor else None
    stream_n = _stream_bronze_count(cursor, catalog)
    streaming = bool(st.session_state.get("last_stream")) or bool(stream_n)
    try:
        streaming = streaming or (last2 not in {None, "—"} and int(last2) > 0)
    except (TypeError, ValueError):
        pass
    kicker = "Stream" if streaming else "Bronze"
    heartbeat_strip(
        f"{n:,}" if isinstance(n, int) else str(n),
        f"{last2}" if last2 != "—" else "—",
        pulse["ago"],
        kicker=kicker,
    )
    c1, c2, c3, c4 = st.columns(4)
    delta = None
    try:
        if last2 not in {None, "—"} and int(last2) > 0:
            delta = f"+{int(last2)}"
    except (TypeError, ValueError):
        delta = None
    c1.metric("Bronze", f"{n}")
    c2.metric("Silver", f"{silver_n:,}" if silver_n is not None else "—")
    if stream_n:
        c3.metric("Stream rows", f"{stream_n:,}", delta=f"+{stream_n}")
    elif isinstance(n, int) and silver_n is not None:
        held = n - int(silver_n)
        c3.metric("Quarantine gap", f"{held}", help="Bronze minus silver. Should be 0 — quarantine never lands in bronze.")
    else:
        c3.metric("Last 2 min", f"{last2}", delta=delta)
    c4.metric("Last file", pulse["ago"])
    provenance_note("bronze.grants", catalog, when=pulse["last"])
    if isinstance(n, int) and silver_n is not None and stream_n:
        st.caption(
            f"Bronze {n:,} includes {stream_n:,} stream-demo-2026 proof row(s). "
            f"Silver {silver_n:,} after grant_no dedupe."
        )
    elif isinstance(n, int) and silver_n is not None:
        st.caption(
            f"Bronze {n:,} and silver {silver_n:,} should match. "
            "Quarantine (empty / dup / amt) never enters bronze — see Quality / app.quarantine_log."
        )


def render_streaming_metrics(cursor=None, catalog: str = "onr_demo"):
    """Landing health from bronze. Stream kicker only after Start stream / recent files."""
    st.markdown("### Landing")
    st.caption("Bronze is the landing table. Silver is what leadership reads.")
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
    from utils.demo_actions import bronze_count, grant_count, load_hold_queue
    from utils.ui import hold_tray, provenance_note

    now = grant_count(cursor, catalog)
    bronze_n = None
    if cursor:
        try:
            bronze_n = bronze_count(cursor, catalog)
        except Exception:
            bronze_n = None
    stream = st.session_state.get("last_stream") or {}
    last = dict(st.session_state.get("last_ingest") or {})
    if last.get("before") is None and stream.get("before_silver") is not None:
        last["before"] = stream.get("before_silver")
        last["after"] = stream.get("after_silver")
    holds = last.get("holds") or load_hold_queue(cursor, catalog)
    held = last.get("held")
    if held is None:
        held = len(holds) if holds else None
    stream_n = _stream_bronze_count(cursor, catalog)
    if stream_n is None:
        stream_n = stream.get("stream_rows")
    c1, c2, c3 = st.columns(3)
    delta = None
    if now is not None and last.get("before") is not None:
        try:
            delta = f"{int(now) - int(last['before']):+d}"
        except (TypeError, ValueError):
            delta = None
    bronze_delta = None
    if bronze_n is not None and stream.get("before_bronze") is not None:
        try:
            bronze_delta = f"{int(bronze_n) - int(stream['before_bronze']):+d}"
        except (TypeError, ValueError):
            bronze_delta = None
    elif bronze_n is not None and last.get("bronze") is not None:
        try:
            bronze_delta = f"{int(bronze_n) - int(last['bronze']):+d}"
        except (TypeError, ValueError):
            bronze_delta = None
    c1.metric("Active grants", f"{now:,}" if now is not None else "—", delta=delta)
    c2.metric("Bronze", f"{bronze_n:,}" if bronze_n is not None else "—", delta=bronze_delta)
    if held:
        c3.metric("Quarantined", f"{int(held):,}", delta=f"+{int(held)}")
    else:
        c3.metric("Quarantined", "0")
    warns = last.get("warnings") or []
    if warns:
        st.caption(f"{len(warns)} warning(s) published with a finding — see Quality.")
    provenance_note("silver.grants", catalog)
    if last.get("before") is not None and last.get("after") is not None:
        st.caption(f"Active grants {last['before']} → {last['after']}")
    if stream_n:
        before_s = stream.get("before_silver")
        after_s = stream.get("after_silver") if stream.get("after_silver") is not None else now
        if before_s is not None and after_s is not None and int(after_s) == int(before_s):
            if bronze_n is not None:
                st.caption(
                    f"Stream published. Silver {after_s:,} unchanged (dedupe on grant_no). "
                    f"Bronze {bronze_n:,}."
                )
            else:
                st.caption(f"Stream published. Silver {after_s:,} unchanged (dedupe on grant_no).")
        elif after_s is not None and before_s is not None:
            st.caption(f"Stream published. Active grants {before_s} → {after_s}.")
        else:
            st.caption(f"Stream batch on bronze: {stream_n:,} row(s).")
    if holds:
        hold_tray(holds)


def _ingest_pulse_fragment():
    from utils.db_helpers import get_connection

    catalog = st.session_state.get("_onr_hb_catalog", "onr_demo")
    _conn, cur = get_connection()
    _show_ingest_pulse(cur, catalog)


def _apply_stream_snapshot(catalog: str, payload: dict) -> dict:
    """Write live silver/bronze counts onto last_stream and last_ingest."""
    from utils.db_helpers import get_connection
    from utils.demo_actions import bronze_count, grant_count

    _conn, cur = get_connection()
    after_s = grant_count(cur, catalog) if cur else None
    after_b = None
    stream_n = None
    if cur:
        try:
            after_b = bronze_count(cur, catalog)
        except Exception:
            after_b = None
        stream_n = _stream_bronze_count(cur, catalog)
    payload["after_silver"] = after_s
    payload["after_bronze"] = after_b
    payload["stream_rows"] = stream_n
    payload["_settled"] = True
    li = dict(st.session_state.get("last_ingest") or {})
    if li.get("before") is None:
        li["before"] = payload.get("before_silver")
    li["after"] = after_s
    if after_b is not None:
        li["bronze"] = after_b
    li.setdefault("holds", [])
    li.setdefault("held", 0)
    li.setdefault("warnings", [])
    if not li.get("via"):
        li["via"] = "stream"
    st.session_state["last_ingest"] = li
    return payload


def _stream_run_terminal(payload: dict) -> bool:
    from utils.workspace_ops import get_run_state

    if payload.get("_settled"):
        return True
    if payload.get("via") == "warehouse" or (
        payload.get("warehouse") and not (payload.get("run") or {}).get("run_id")
    ):
        return True
    run = payload.get("run") or {}
    run_id = run.get("run_id")
    if not run_id:
        return bool(payload.get("file"))
    live = get_run_state(run_id)
    result = (live.get("result") or "").upper()
    state = (live.get("state") or "").upper()
    payload["_run_state"] = state
    payload["_run_result"] = result
    if result in {
        "SUCCESS",
        "SUCCEEDED",
        "FAILED",
        "CANCELED",
        "CANCELLED",
        "TIMEDOUT",
        "TIMED_OUT",
        "EXCLUDED",
    }:
        return True
    if state in {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"} and result:
        return True
    return False


def _settle_stream_if_done(catalog: str) -> None:
    payload = st.session_state.get("last_stream") or {}
    if not payload or payload.get("_settled"):
        return
    if not _stream_run_terminal(payload):
        st.session_state["last_stream"] = payload
        return
    st.session_state["last_stream"] = _apply_stream_snapshot(catalog, payload)
    st.rerun()


def _stream_watch_fragment():
    catalog = st.session_state.get("_onr_stream_catalog") or st.session_state.get(
        "_onr_hb_catalog", "onr_demo"
    )
    _settle_stream_if_done(catalog)


if hasattr(st, "fragment"):
    try:
        from datetime import timedelta

        _streaming_heartbeat_fragment = st.fragment(run_every=timedelta(seconds=8))(
            _streaming_heartbeat_fragment
        )
        _ingest_pulse_fragment = st.fragment(run_every=timedelta(seconds=8))(
            _ingest_pulse_fragment
        )
        _stream_watch_fragment = st.fragment(run_every=timedelta(seconds=8))(
            _stream_watch_fragment
        )
    except Exception:
        pass


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
        "Drops a new file on the landing Volume. Prefers a serverless Auto Loader job "
        "(availableNow — ProcessingTime is not supported on Jobs serverless). "
        "If Jobs cannot start, the SQL warehouse appends the same file to bronze.grants. "
        "Warehouses cannot run spark.readStream / cloudFiles."
    )
    st.session_state["_onr_stream_catalog"] = catalog
    st.session_state["_onr_hb_catalog"] = catalog
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("Start stream", type="primary", key="start_stream"):
            try:
                from utils.db_helpers import get_connection
                from utils.demo_actions import bronze_count, grant_count

                _conn, cur = get_connection()
                before_s = grant_count(cur, catalog) if cur else None
                before_b = None
                if cur:
                    try:
                        before_b = bronze_count(cur, catalog)
                    except Exception:
                        before_b = None
                result = start_stream(catalog)
                result["before_silver"] = before_s
                result["before_bronze"] = before_b
                result["_settled"] = False
                if result.get("via") == "warehouse":
                    result = _apply_stream_snapshot(catalog, result)
                st.session_state["last_stream"] = result
                if result.get("error") and not result.get("file") and not result.get("warehouse"):
                    st.error(result["error"])
                elif result.get("via") == "warehouse":
                    ins = result.get("inserted")
                    bronze = result.get("after_bronze") or result.get("bronze")
                    st.success(
                        f"File landed and loaded on the SQL warehouse. "
                        f"Bronze {bronze} · +{ins}."
                    )
                    st.rerun()
                elif result.get("run"):
                    st.success("Stream file is on the Volume. Auto Loader job submitted.")
                    st.rerun()
                else:
                    st.success("Stream file is on the Volume.")
                    st.rerun()
            except Exception as e:
                st.error(f"Stream did not start: {e}")
    with c2:
        path = resolve_notebook(STREAM_NOTEBOOK)
        workspace_action_row("Open stream notebook", notebook_url(path))
    render_run_status("Stream", st.session_state.get("last_stream"))
    watched = False
    if hasattr(st, "fragment"):
        try:
            _stream_watch_fragment()
            watched = True
        except Exception:
            watched = False
    if not watched:
        _settle_stream_if_done(catalog)
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
    st.session_state["_onr_hb_catalog"] = catalog
    pulsed = False
    if hasattr(st, "fragment"):
        try:
            _ingest_pulse_fragment()
            pulsed = True
        except Exception:
            pulsed = False
    if not pulsed:
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
                        st.session_state.pop("last_stream", None)
                        st.success(
                            f"Baseline restored. Active grants {result['before_silver']} → {result['after_silver']}. "
                            f"Silver rebuilt. Quarantine log empty."
                        )
                        if result.get("warning"):
                            st.warning(result["warning"])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Restore failed: {e}")
        st.caption(
            "Removes inbound and stream batches (live-demo-2026, quality-fail-2026, "
            "stream-demo-2026), rebuilds silver and gold, and clears the quarantine "
            "error log plus quality findings."
        )


def render_ingestion_demo(catalog: str, schema: str):
    """Auto Loader contract — no operator runbook."""
    st.markdown("### Auto Loader")
    st.caption(
        "cloudFiles on the landing Volume. Schema evolution is addNewColumns. "
        "Jobs serverless uses availableNow (ProcessingTime is not supported on that cluster type). "
        "Classic clusters can still run processingTime 30-second micro-batches."
    )
    st.code(
        f'''
spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaLocation", "/Volumes/{catalog}/bronze/landing/_schemas/grants_stream_v3")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("header", "true")
    .load("/Volumes/{catalog}/bronze/landing/grants/")
    .writeStream.format("delta")
    .option("checkpointLocation", "/Volumes/{catalog}/bronze/checkpoints/grants_stream_v3")
    .trigger(availableNow=True)  # serverless / Start stream
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
