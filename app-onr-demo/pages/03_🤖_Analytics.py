"""Analytics."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.analytics_helpers import (
    render_model_execution,
    render_forecast_visualization,
    render_grant_predictions,
    render_trend_analysis,
    render_decision_support,
    render_model_metrics,
    render_anomaly_detection,
    render_score_controls,
    render_score_strip,
    render_drift,
)
from utils.ui import page_header, render_architecture
from utils.workspace_ops import render_page_links
from utils.mission_themes import render_mission_ribbon

set_page_config(page_title="Element 5 · Analytics | ONR Portfolio")
setup_sidebar()

page_header(
    "Element 5 · Decision support",
    "Analytics",
    "Scientist view. Scores sit on this page after Score registered models — Fund / Review / Defer and flags, then tabs.",
)
render_mission_ribbon("analytics")

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

render_page_links("analytics", onr_catalog)

conn, cursor = get_connection()

render_score_controls(onr_catalog)
render_score_strip(cursor, onr_catalog)
render_decision_support(cursor, onr_catalog)
render_drift(cursor, onr_catalog)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Predictions", "Anomalies", "Forecasting", "Trends", "Metrics"]
)

with tab1:
    render_grant_predictions(cursor, onr_catalog, onr_schema)
    render_model_execution(cursor, onr_catalog)

with tab2:
    render_anomaly_detection(cursor, onr_catalog)

with tab3:
    render_forecast_visualization(cursor, onr_catalog)

with tab4:
    render_trend_analysis(cursor, onr_catalog)

with tab5:
    render_model_metrics(cursor, onr_catalog)

render_architecture("analytics")
