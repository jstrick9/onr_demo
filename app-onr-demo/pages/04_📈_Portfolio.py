"""Portfolio."""

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
    render_routing,
)
from utils.brief_helpers import render_daily_brief
from utils.analytics_helpers import render_resource_action
from utils.ui import page_header, render_architecture
from utils.workspace_ops import render_page_links
from utils.mission_themes import render_mission_ribbon, theme_chip

set_page_config(page_title="Element 6 · Portfolio | ONR Portfolio")
setup_sidebar()

page_header(
    "Element 6 · Executive view",
    "Portfolio",
    "Officer view. Search first. Accept or Defer a flagged grant. Brief and AT_RISK stay on this page.",
)
render_mission_ribbon("portfolio")

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

render_page_links("portfolio", onr_catalog)

conn, cursor = get_connection()

render_executive_kpis(cursor, onr_catalog)
theme_chip("budget", "portfolio", "resource_action")
render_resource_action(cursor, onr_catalog)
render_search_extract(cursor, onr_catalog, onr_schema)
render_routing(cursor, onr_catalog)
filters = render_dashboard_filters()
render_grants_overview(cursor, onr_catalog, onr_schema, filters)

tab1, tab2, tab3 = st.tabs(["Budget", "Automation", "Activity"])

with tab1:
    render_budget_execution(cursor, onr_catalog)

with tab2:
    render_daily_brief(cursor, onr_catalog)
    render_process_automation(cursor, onr_catalog)

with tab3:
    render_activity_log(cursor, onr_catalog)

render_architecture("portfolio")
