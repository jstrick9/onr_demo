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
from utils.eval_prompt import render_eval_prompt
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
set_page_config(page_title="Analytics | ONR ITSS POC")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("🤖 Element 5: Decision-Support Analytics and Modeling")
st.markdown(
    """
    This element demonstrates **analytical routines and ML models** against the ingested dataset, 
    showing how model outputs serve as **strategic decision-making aids for leadership**.
    """
)
render_eval_prompt(
    "Element 5",
    "How do analytics and models help leadership decide where to put the next dollar?",
    "Anomalies tab = IsolationForest flags. Forecast = OLS + TREND-* IDs. Predictions = RF Fund/Review/Defer.",
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
# ELEMENT OVERVIEW
# -------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745;">
        <strong>📌 Key Focus Areas:</strong>
        <ul>
            <li>ML model execution against ingested data</li>
            <li>Predictive forecasting and trend analysis</li>
            <li>Executive decision support with actionable insights</li>
            <li>Structured analytical outputs for leadership</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)

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
st.markdown("### 🏗️ Analytics Architecture")

st.markdown("""
```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                Decision-Support Analytics                                │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  gold (ingested portfolio: grants + ERP + funding_features)                              │
│              |                          |                          |                     │
│              v                          v                          v                     │
│  +-----------------------+  +-----------------------+  +-----------------------+         │
│  | RF classifier         |  | IsolationForest       |  | OLS FY forecast       |         │
│  | notebook 04           |  | notebook 04b          |  | ols_fy_v1 (SQL)       |         │
│  | large award >= $1M    |  | spike / collapse      |  | 2-yr + 95% band       |         │
│  | Fund / Review / Defer |  | low-return conc.      |  | TREND-* IDs           |         │
│  +-----------+-----------+  +-----------+-----------+  +-----------+-----------+         │
│              |                          |                          |                     │
│              v                          v                          v                     │
│  grant_predictions           grant_anomaly_scores        funding_forecast                │
│  grant_large_award           funding_anomaly_            program_trends                  │
│  (UC model registry)         detector @ champion         TREND-ACCEL / STEADY / DECLINE  │
│                                                                                          │
│  MLflow  /Shared/onr-demo/{grant-size, funding-anomaly}                                  │
│  App reads Unity Catalog tables -- not screenshots.                                      │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# MLFLOW EXAMPLE
# -------------------------------
st.markdown("---")
st.markdown("### MLflow")
st.markdown(
    "Training lives in `notebooks/04_mlflow_grant_model.py` (RF) and "
    "`notebooks/04b_funding_anomaly.py` (IsolationForest) on **onr demo cluster**. "
    "Scores land in `{catalog}.gold.grant_predictions` and `{catalog}.gold.grant_anomaly_scores` "
    "so this page is reading Unity Catalog, not a canned screenshot.".format(catalog=onr_catalog)
)

# -------------------------------
# EVALUATION ALIGNMENT
# -------------------------------
st.markdown("---")
st.markdown("### 📝 Evaluation Alignment")

st.markdown(
    """
    | Criterion | How Element 5 Demonstrates It |
    |-----------|-------------------------------|
    | **Technical Competence** | Key Personnel execute models live, explain algorithms and workflows |
    | **Strategic Alignment** | Analytics serve as decision-making aids for leadership, not just technical outputs |
    | **Completeness** | Model execution seamless within 50-minute demonstration window |
    """
)
