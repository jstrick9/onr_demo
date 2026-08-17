"""Ingestion — land files, quality gates, stream heartbeat."""

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
)

set_page_config(page_title="Ingestion | ONR Portfolio")
setup_sidebar()

st.title("Ingestion")
st.caption(
    "Land a grants file, apply quality gates, and rebuild silver / gold. "
    "Process uses the SQL warehouse. Auto Loader notebooks run on the cluster."
)

sso_user = init_user_session_state()
dbx_env = get_runtime_env()

app_root = Path(__file__).resolve().parent.parent
config_file = app_root / "config" / "onr-conf.yaml"

try:
    configs = read_yaml(str(config_file))
    onr_catalog = configs["schema"]["catalog"]
    onr_schema = "silver"
except Exception as e:
    st.error(f"Configuration error: {str(e)}")
    st.stop()

conn, cursor = get_connection()

st.markdown("---")
render_file_picker_and_reset(cursor, onr_catalog)

tab1, tab2, tab3, tab4 = st.tabs([
    "Pipeline Status",
    "Quality Checks",
    "Schema & Streaming",
    "Auto Loader (cluster)",
])

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

with tab4:
    render_ingestion_demo(onr_catalog, onr_schema)

st.markdown("---")
with st.expander("How it works"):
    st.code(
        """
landing Volume          Auto Loader                 bronze.grants
CSV / JSON         ->   cloudFiles addNewColumns -> Raw Delta + _ingest_time
/landing/grants                                     + _source_file
                                                          |
                                                          v
                                                   Quality gates
                                                   grant_no NOT NULL
                                                   amount_usd > 0
                                                          |
                     PASS -> silver then gold             REJECT / skip
                                                          empty / dup / amt <= 0

Triggers (same bronze table unless noted)
  App Process button : warehouse SQL INSERT
  Notebook 01 / job  : availableNow (batch, file-arrival)
  Notebook 01b       : processingTime 30s (live stream)
  SDP pipeline       : sibling bronze.grants_stream
        """.strip(),
        language="text",
    )
