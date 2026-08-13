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
render_decision_support()

# -------------------------------
# TABS
# -------------------------------
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Predictions",
    "📈 Forecasting",
    "📊 Trend Analysis",
    "📏 Model Metrics"
])

with tab1:
    render_grant_predictions(cursor, onr_catalog, onr_schema)
    
    st.markdown("---")
    render_model_execution()

with tab2:
    render_forecast_visualization()

with tab3:
    render_trend_analysis()

with tab4:
    render_model_metrics()

# -------------------------------
# ANALYTICS ARCHITECTURE
# -------------------------------
st.markdown("---")
st.markdown("### 🏗️ Analytics Architecture")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────┐
│                    Decision-Support Analytics                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   🥇 Gold Layer             🤖 ML Pipeline          📊 Output       │
│   ┌─────────────┐          ┌─────────────┐        ┌─────────────┐  │
│   │ Aggregated  │─────────▶│   Feature   │──────▶│ Predictions │  │
│   │   Data      │          │ Engineering │        │ Forecasts   │  │
│   └─────────────┘          └──────┬──────┘        │ Trends      │  │
│                                   │               └──────┬──────┘  │
│                                   ▼                      │         │
│                          ┌─────────────┐                 ▼         │
│                          │ MLflow 3    │          ┌─────────────┐  │
│                          │ Tracking    │          │  Executive  │  │
│                          │ + Registry  │          │  Dashboard  │  │
│                          └─────────────┘          └─────────────┘  │
│                                                                     │
│   Models Available:                                                  │
│   • Grant Success Predictor (Random Forest, 92% accuracy)           │
│   • Budget Forecaster (Time Series, 95% accuracy)                   │
│   • Anomaly Detector (Isolation Forest, 97% accuracy)               │
│   • Trend Analyzer (ARIMA + ML, 89% accuracy)                       │
│                                                                     │
│   MLflow Integration:                                               │
│   • Experiment tracking with parameters, metrics, artifacts         │
│   • Model registry (UC-governed)                                    │
│   • Batch inference via ai_query() SQL functions                    │
│   • Model serving endpoints (REST API)                              │
└─────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# MLFLOW EXAMPLE
# -------------------------------
st.markdown("---")
st.markdown("### 🔬 MLflow Integration Example")

with st.expander("View MLflow Tracking Code"):
    st.code(f"""
import mlflow
from sklearn.ensemble import RandomForestClassifier

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment("/Workspace/experiments/onr-demo/grant-predictor")

with mlflow.start_run(run_name="rf-grant-success") as run:
    # Log parameters
    mlflow.log_params({{"n_estimators": 100, "max_depth": 10, "random_state": 42}})
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=10)
    model.fit(X_train, y_train)
    
    # Evaluate
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)
    
    # Register model in Unity Catalog
    mlflow.sklearn.log_model(
        model, 
        "model", 
        registered_model_name="{onr_catalog}.{onr_schema}.grant_success_predictor"
    )

# SQL AI Functions (Zero-Cluster)
SELECT 
    grant_no,
    ai_query('grant_success_predictor', 
             struct(program_area, amount_usd, awardee)) as prediction
FROM `{onr_catalog}`.`silver`.grants;
    """, language="python")

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
