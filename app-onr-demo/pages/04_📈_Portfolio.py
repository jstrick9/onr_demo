"""
ONR ITSS POC — Element 6: Dashboard Page
Unified Dashboard, Visualizations, and Process Automation
"""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.dashboard_helpers import (
    render_executive_kpis,
    render_dashboard_filters,
    render_grants_overview,
    render_budget_execution,
    render_process_automation,
    render_search_extract,
    render_activity_log,
)
from utils.brief_helpers import render_daily_brief

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Portfolio | ONR Portfolio")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("Portfolio")
st.caption(
    "Search, filter, and extract without SQL. Generate a daily brief. "
    "Review budget AT_RISK rows and the anomaly queue."
)

# -------------------------------
# SESSION STATE
# -------------------------------
sso_user = init_user_session_state()
dbx_env = get_runtime_env()

# Load configuration
app_root = Path(__file__).resolve().parent.parent
config_file = app_root / "config" / "onr-conf.yaml"

try:
    configs = read_yaml(str(config_file))
    onr_catalog = configs["schema"]["catalog"]
    onr_schema = "silver"  # medallion layer used by helpers that still accept schema arg
except Exception as e:
    st.error(f"Configuration error: {str(e)}")
    st.stop()

conn, cursor = get_connection()


# -------------------------------
# EXECUTIVE KPIs
# -------------------------------
render_executive_kpis(cursor, onr_catalog)

# -------------------------------
# FILTERS
# -------------------------------
st.markdown("---")
filters = render_dashboard_filters()

# -------------------------------
# GRANTS OVERVIEW
# -------------------------------
st.markdown("---")
render_grants_overview(cursor, onr_catalog, onr_schema, filters)

# -------------------------------
# TABS
# -------------------------------
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "💰 Budget Execution",
    "🤖 Process Automation",
    "🔍 Search & Extract",
    "📜 Activity Log"
])

with tab1:
    render_budget_execution(cursor, onr_catalog)

with tab2:
    render_daily_brief(cursor, onr_catalog)
    st.markdown("---")
    render_process_automation(cursor, onr_catalog)

with tab3:
    render_search_extract(cursor, onr_catalog, onr_schema)

with tab4:
    render_activity_log(cursor, onr_catalog)

# -------------------------------
# DASHBOARD ARCHITECTURE
# -------------------------------
st.markdown("---")
with st.expander("How it works"):
    st.caption(
        "Non-technical leader: search, filter FY/area, extract, daily brief. "
        "Automation writes `app.daily_briefs`, budget AT_RISK, anomaly queue, "
        "and `app.search_history` / `app.export_history` from gold tables."
    )

