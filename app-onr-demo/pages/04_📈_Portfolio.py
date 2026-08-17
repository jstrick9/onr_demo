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
)
from utils.brief_helpers import render_daily_brief
from utils.ui import page_header, render_how_it_works

set_page_config(page_title="Portfolio | ONR Portfolio")
setup_sidebar()

page_header(
    "Executive view",
    "Portfolio",
    "Search, filter, and extract without SQL. Daily brief, AT_RISK rows, and the anomaly queue.",
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

render_executive_kpis(cursor, onr_catalog)
filters = render_dashboard_filters()
render_grants_overview(cursor, onr_catalog, onr_schema, filters)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Budget", "Automation", "Search", "Activity"]
)

with tab1:
    render_budget_execution(cursor, onr_catalog)

with tab2:
    render_daily_brief(cursor, onr_catalog)
    render_process_automation(cursor, onr_catalog)

with tab3:
    render_search_extract(cursor, onr_catalog, onr_schema)

with tab4:
    render_activity_log(cursor, onr_catalog)

render_how_it_works(
    "How leadership uses the portfolio",
    [
        {"name": "See", "detail": "KPIs and program mix from gold, no warehouse login required."},
        {"name": "Filter", "detail": "Fiscal year, program area, classification, award size."},
        {"name": "Search", "detail": "Find an award; the lookup is written to the audit log."},
        {"name": "Act", "detail": "Daily brief, AT_RISK rows, and the anomaly queue."},
    ],
)
