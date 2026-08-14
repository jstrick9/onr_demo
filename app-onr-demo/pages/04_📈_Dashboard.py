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
from utils.eval_prompt import render_eval_prompt
from utils.dashboard_helpers import (
    render_executive_kpis,
    render_dashboard_filters,
    render_grants_overview,
    render_budget_execution,
    render_process_automation,
    render_search_extract,
    render_activity_log,
)

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Dashboard | ONR ITSS POC")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("📈 Element 6: Unified Dashboard, Visualizations, and Process Automation")
st.markdown(
    """
    This element demonstrates how a **non-technical leader** can search, filter, and extract 
    insights, and how the platform **automates repetitive workflows** to drive efficiency.
    """
)
render_eval_prompt(
    "Element 6",
    "Can a non-technical leader search, filter, and extract without writing SQL?",
    "Use the filters and search `quantum` or `ONRD-2025`. Export the result as CSV.",
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
    <div style="background-color: #f8d7da; padding: 15px; border-radius: 10px; border-left: 5px solid #dc3545;">
        <strong>📌 Key Focus Areas:</strong>
        <ul>
            <li>Executive BI dashboard for non-technical users</li>
            <li>Search, filter, and extract without code</li>
            <li>Automated summaries, approval routing, anomaly flagging</li>
            <li>Process automation driving efficiency</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)

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
    render_process_automation(cursor, onr_catalog)

with tab3:
    render_search_extract(cursor, onr_catalog, onr_schema)

with tab4:
    render_activity_log(cursor, onr_catalog)

# -------------------------------
# DASHBOARD ARCHITECTURE
# -------------------------------
st.markdown("---")
st.markdown("### 🏗️ Dashboard Architecture")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────┐
│                    Unified Executive Dashboard                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   👤 Non-Technical Leader                                           │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  🔍 Search  │  📊 Filter  │  📥 Extract  │  📋 Reports    │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Streamlit Dashboard (No Code)                   │   │
│   │  ┌───────────┬───────────┬───────────┬───────────┐          │   │
│   │  │   KPIs    │  Charts   │  Tables   │  Alerts   │          │   │
│   │  └───────────┴───────────┴───────────┴───────────┘          │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Process Automation Engine                       │   │
│   │  • 📊 Daily Summary Reports    • 🚨 Anomaly Detection       │   │
│   │  • 📋 Approval Workflows       • 📈 Auto-refresh             │   │
│   │  • 🔔 Alert Notifications      • 📑 Scheduled Reports       │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Gold Layer (Business-Ready Data)                 │   │
│   │  • gold.grants_summary       • gold.financial_summary        │   │
│   │  • gold.grants_by_awardee    • gold.budget_execution         │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# EVALUATION ALIGNMENT
# -------------------------------
st.markdown("---")
st.markdown("### 📝 Evaluation Alignment")

st.markdown(
    """
    | Criterion | How Element 6 Demonstrates It |
    |-----------|-------------------------------|
    | **Technical Competence** | Key Personnel explain architecture behind dashboard and automation |
    | **Strategic Alignment** | Automated summaries, routing, and anomaly detection meet workforce automation needs |
    | **Completeness** | Dashboard operations execute smoothly in sequence |
    """
)
