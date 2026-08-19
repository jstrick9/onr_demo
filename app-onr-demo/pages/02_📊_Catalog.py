"""Catalog."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.governance_helpers import (
    render_catalog_registry,
    render_quality_scores,
    render_lineage_visualization,
    render_governance_policies,
    render_lineage_tracking,
    render_lineage_launch,
)
from utils.ui import page_header, render_architecture
from utils.workspace_ops import render_page_links

set_page_config(page_title="Element 4 · Catalog | ONR Portfolio")
setup_sidebar()

page_header(
    "Element 4 · Governance",
    "Catalog",
    "Governance view. Click Open lineage after ingest so the native graph is populated.",
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

render_page_links("catalog", onr_catalog)

conn, cursor = get_connection()

render_lineage_launch(onr_catalog)

tab1, tab2, tab3 = st.tabs(["Registry", "Quality", "Policies & tags"])

with tab1:
    render_catalog_registry(cursor, onr_catalog, onr_schema)

with tab2:
    render_quality_scores(cursor, onr_catalog, onr_schema)

with tab3:
    render_governance_policies(cursor, onr_catalog, onr_schema)

with st.expander("Lineage sketch and tracking log"):
    render_lineage_visualization()
    render_lineage_tracking(cursor, onr_catalog, onr_schema)

render_architecture("catalog")
