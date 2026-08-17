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
    render_time_travel_compare,
)
from utils.ui import page_header, render_architecture, live_chip

set_page_config(page_title="Ingestion | ONR Portfolio")
setup_sidebar()

page_header(
    "Data operations",
    "Ingestion",
    "Land grants files, apply quality gates, and refresh the serving layer.",
)

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

tab1, tab2, tab3, tab4 = st.tabs(
    ["Pipeline", "Quality", "Schema & stream", "Auto Loader"]
)

with tab1:
    render_ingestion_status(cursor, onr_catalog, onr_schema)

with tab2:
    render_quality_checks(cursor, onr_catalog, onr_schema)

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        render_schema_evolution(cursor, onr_catalog, onr_schema)
    with col2:
        render_streaming_metrics(cursor, onr_catalog)
        render_time_travel_compare(cursor, onr_catalog)

with tab4:
    render_ingestion_demo(onr_catalog, onr_schema)

render_architecture("ingestion")
