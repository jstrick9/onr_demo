"""Ingestion."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.ingestion_helpers import (
    render_ingestion_status,
    render_quality_checks,
    render_schema_evolution,
    render_streaming_metrics,
    render_ingestion_demo,
    render_file_picker_and_reset,
    render_restore_baseline,
    render_time_travel_compare,
    render_stream_controls,
)
from utils.ui import page_header, render_architecture, live_chip
from utils.workspace_ops import render_page_links
from utils.mission_themes import render_mission_ribbon

set_page_config(page_title="Element 3 · Ingestion | ONR Portfolio")
setup_sidebar()

page_header(
    "Element 3 · Data operations",
    "Ingestion",
    "Ingest selected files → Hold → Start stream. Quality and schema are in the tabs.",
)
render_mission_ribbon("ingestion")

init_user_session_state()
get_runtime_env()

app_root = Path(__file__).resolve().parent.parent
try:
    configs = read_yaml(str(app_root / "config" / "onr-conf.yaml"))
    onr_catalog = configs["schema"]["catalog"]
    onr_schema = "silver"
except Exception as e:
    st.error(f"Configuration error: {str(e)}")
    st.stop()

render_page_links("ingestion", onr_catalog)

conn, cursor = get_connection()

if cursor:
    try:
        cursor.execute(
            f"""
            SELECT COUNT(*) FROM `{onr_catalog}`.`bronze`.grants
            WHERE _ingest_time >= CURRENT_TIMESTAMP() - INTERVAL 2 MINUTES
            """
        )
        if int(cursor.fetchone()[0] or 0) > 0:
            live_chip("Ingest active · last 2 minutes")
    except Exception:
        pass

render_file_picker_and_reset(cursor, onr_catalog)
render_stream_controls(onr_catalog)
render_streaming_metrics(cursor, onr_catalog)
render_time_travel_compare(cursor, onr_catalog)

tab1, tab2 = st.tabs(["Pipeline", "Quality"])

with tab1:
    render_ingestion_status(cursor, onr_catalog, onr_schema)

with tab2:
    render_quality_checks(cursor, onr_catalog, onr_schema)

with st.expander("Schema and Auto Loader"):
    render_schema_evolution(cursor, onr_catalog, onr_schema)
    render_ingestion_demo(onr_catalog, onr_schema)

render_architecture("ingestion")
render_restore_baseline(cursor, onr_catalog)
