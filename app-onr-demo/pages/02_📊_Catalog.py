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
)
from utils.ui import page_header, render_how_it_works

set_page_config(page_title="Catalog | ONR Portfolio")
setup_sidebar()

page_header(
    "Governance",
    "Catalog",
    "Unity Catalog is the system of record for tables, tags, health, and lineage.",
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Registry", "Quality", "Lineage", "Policies & tags", "Tracking"]
)

with tab1:
    render_catalog_registry(cursor, onr_catalog, onr_schema)

with tab2:
    render_quality_scores(cursor, onr_catalog, onr_schema)

with tab3:
    render_lineage_visualization()

with tab4:
    render_governance_policies(cursor, onr_catalog, onr_schema)

with tab5:
    render_lineage_tracking(cursor, onr_catalog, onr_schema)

render_how_it_works(
    "How the catalog governs the portfolio",
    [
        {"name": "Register", "detail": "Ingested tables appear in bronze, silver, gold, and app."},
        {"name": "Score", "detail": "Completeness, accuracy, consistency, and timeliness."},
        {"name": "Lineage", "detail": "Landing to gold is mapped in Unity Catalog."},
        {"name": "Policy", "detail": "Tags and grants travel with the table, not a side spreadsheet."},
    ],
)
