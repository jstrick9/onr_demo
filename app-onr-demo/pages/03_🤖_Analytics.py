"""
ONR ITSS POC — Element 5: Analytics Page
Decision-Support Analytics and Modeling
"""

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
)

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Analytics | ONR Portfolio")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("Analytics")
st.caption(
    "Fund / Review / Defer (RF), award-level anomalies (IsolationForest), "
    "and FY forecast + TREND-* IDs (OLS) on the ingested portfolio."
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
# EXECUTIVE DECISION SUPPORT
# -------------------------------
render_decision_support(cursor, onr_catalog)

# -------------------------------
# TABS
# -------------------------------
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Predictions",
    "🚨 Anomalies",
    "📈 Forecasting",
    "📊 Trend Analysis",
    "📏 Model Metrics"
])

with tab1:
    render_grant_predictions(cursor, onr_catalog, onr_schema)
    st.markdown("---")
    render_model_execution(cursor, onr_catalog)

with tab2:
    render_anomaly_detection(cursor, onr_catalog)

with tab3:
    render_forecast_visualization(cursor, onr_catalog)

with tab4:
    render_trend_analysis(cursor, onr_catalog)

with tab5:
    render_model_metrics(cursor, onr_catalog)

# -------------------------------
# ANALYTICS ARCHITECTURE
# -------------------------------
st.markdown("---")
with st.expander("How it works"):
    st.code(
        """
gold (grants + ERP + funding_features)
        |                    |                    |
        v                    v                    v
RF (04 train / 04c score)  IsolationForest     OLS ols_fy_v1
Fund / Review / Defer      @champion           TREND-* IDs
        |                    |                    |
grant_predictions    grant_anomaly_scores   funding_forecast
grant_large_award    funding_anomaly_       program_trends
                     detector

MLflow /Shared/onr-demo/{grant-size, funding-anomaly}
App reads Unity Catalog tables -- not screenshots.
        """.strip(),
        language="text",
    )

st.markdown("### MLflow")
st.markdown(
    "Night-before training: `04_mlflow_grant_model.py` (RF) and "
    "`04b_funding_anomaly.py` (IsolationForest) on **onr demo cluster**. "
    "On camera: `04c_score_registered_models.py` applies those UC models to the "
    "current portfolio. This page reads `{catalog}.gold.grant_predictions` and "
    "`{catalog}.gold.grant_anomaly_scores`.".format(catalog=onr_catalog)
)

