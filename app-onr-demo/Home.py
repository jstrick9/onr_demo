"""
ONR ITSS POC — Home Page
Office of Naval Research (ONR) Code 08 IT Support Services
Technical Demonstration: Elements 3–7

Main entry point for the Databricks Streamlit application.
"""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import (
    setup_sidebar,
    set_page_config,
    vertical_divider,
)
from utils.runtime_env import get_runtime_env
from utils.db_helpers import (
    get_connection,
    read_yaml,
    validate_source_tables,
)
from utils.user_helpers import init_user_session_state

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Home | ONR ITSS POC Demo")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("🚢 ONR ITSS Proof of Concept")
st.markdown("### Office of Naval Research — Code 08 IT Support Services")
st.markdown("#### Technical Demonstration: Elements 3–7")

st.markdown(
    """
    ---
    Welcome to the **ONR ITSS Technical Demonstration** environment. This application showcases 
    a comprehensive Data and Analytics platform built on **Databricks on AWS**, demonstrating 
    capabilities across five critical scenario elements required for the ONR Code 08 IT Support 
    Services contract.
    """
)

# -------------------------------
# ELEMENTS OVERVIEW
# -------------------------------
st.markdown("### 📋 Demonstration Elements")

col1, col_div1, col2 = st.columns([1, 0.06, 1])

with col1:
    st.markdown("#### 🔍 Element 3: Ingestion")
    st.markdown(
        """
        **Automated Ingestion, Data Operations, and Streaming**
        
        - Auto Loader for incremental file detection
        - Automated quality checks on ingestion
        - Schema evolution handling
        - Near-real-time streaming architecture
        """
    )

    st.markdown("#### 📊 Element 4: Governance")
    st.markdown(
        """
        **Data Governance, Quality, and Cataloging**
        
        - Unity Catalog registry and metadata
        - Data quality health scores
        - End-to-end lineage visualization
        - Automated cataloging workflows
        """
    )

with col_div1:
    vertical_divider(height=400, color=(210, 210, 210), width=2)

with col2:
    st.markdown("#### 🤖 Element 5: Analytics")
    st.markdown(
        """
        **Decision-Support Analytics and Modeling**
        
        - Statistical and ML model execution
        - Predictive forecasting
        - Executive decision support
        - Structured analytical outputs
        """
    )

    st.markdown("#### 📈 Element 6: Dashboard")
    st.markdown(
        """
        **Unified Dashboard, Visualizations, and Process Automation**
        
        - Executive BI dashboard
        - Search, filter, extract capabilities
        - Automated summaries and alerts
        - Non-technical leader usability
        """
    )

st.markdown("---")

col3, _ = st.columns([1, 2])
with col3:
    st.markdown("#### 🔗 Element 7: Integration")
    st.markdown(
        """
        **Interoperability, Data Portability, and Secure Export**
        
        - Non-proprietary format export (CSV/JSON/Parquet)
        - API support for Advana/Cloud One
        - Schema portability
        - Secure bulk extraction
        """
    )

# -------------------------------
# ENVIRONMENT & CONNECTION
# -------------------------------
st.markdown("---")
st.markdown("### ⚙️ Environment Status")

# SSO User
sso_user = init_user_session_state()

# Environment detection
dbx_env = get_runtime_env()
st.session_state["dbx_env"] = dbx_env

# Load configuration
app_root = Path(__file__).resolve().parent
config_file = app_root / "config" / "onr-conf.yaml"

try:
    configs = read_yaml(str(config_file))
    onr_catalog = configs["schema"]["catalog"]
    layers = configs["schema"].get("layers", {"bronze": "bronze", "silver": "silver", "gold": "gold", "app": "app"})
    st.session_state["onr_configs"] = configs
    st.session_state["onr_layers"] = layers
except FileNotFoundError:
    st.error(f"Configuration file not found for environment: {dbx_env}")
    st.stop()
except KeyError as e:
    st.error(f"Invalid configuration: missing required key {e}")
    st.stop()

# Database connection (falls back to Compass fixture if warehouse is down)
conn, cursor = get_connection()
st.session_state["onr_conn"] = conn
st.session_state["onr_cursor"] = cursor

# Environment indicator
col_env1, col_env2, col_env3 = st.columns(3)
with col_env1:
    st.info("🟢 **Environment:** POC")
with col_env2:
    st.info(f"📦 **Catalog:** {onr_catalog}")
with col_env3:
    st.info("🗄️ **Schemas:** bronze · silver · gold · app")

# -------------------------------
# DATA SOURCE VALIDATION
# -------------------------------
st.markdown("---")
st.markdown("### <u>Source Data Validation</u>", unsafe_allow_html=True)

with st.expander("Click to View Source Table Status"):
    if cursor:
        validate_source_tables(cursor, configs)
    else:
        from utils.portfolio_data import portfolio_kpis
        k = portfolio_kpis()
        st.success(
            f"✅ Compass fixture loaded: {k['grant_count']} grants, "
            f"{k['transaction_count']} ERP transactions "
            f"(FY{k['fy_min']}–{k['fy_max']})."
        )

# -------------------------------
# NAVIGATION GUIDE
# -------------------------------
st.markdown("---")
st.markdown("### 🧭 Navigation Guide")

st.markdown(
    """
    Use the **sidebar** on the left to navigate between demonstration elements:
    
    | Page | Element | What You'll See |
    |------|---------|-----------------|
    | **🔍 Ingestion** | Element 3 | Live data ingestion pipeline, Auto Loader demo, quality checks |
    | **📊 Governance** | Element 4 | Data catalog, lineage visualization, quality scores |
    | **🤖 Analytics** | Element 5 | ML model execution, forecasting, decision support |
    | **📈 Dashboard** | Element 6 | Executive dashboard, search/filter, process automation |
    | **🔗 Integration** | Element 7 | Data export, API demo, interoperability showcase |
    """
)

# -------------------------------
# QUICK STATS
# -------------------------------
st.markdown("---")
st.markdown("### 📊 Quick Statistics")

try:
    # Get table counts
    stats_query = f"""
    SELECT 
        'Grants' as dataset, COUNT(*) as records, MAX(_ingest_time) as last_update
        FROM `{onr_catalog}`.`silver`.grants
        WHERE _is_active = true
        UNION ALL
        SELECT 
        'Financial' as dataset, COUNT(*) as records, MAX(_ingest_time) as last_update
        FROM `{onr_catalog}`.`silver`.financial
        WHERE _is_active = true
    """
    cursor.execute(stats_query)
    stats = cursor.fetchall()
    
    cols = st.columns(len(stats))
    for idx, (dataset, records, last_update) in enumerate(stats):
        with cols[idx]:
            st.metric(
                label=f"📋 {dataset} Records",
                value=f"{records:,}",
                delta=f"Updated: {last_update}" if last_update else "No data"
            )
except Exception:
    from utils.portfolio_data import portfolio_kpis
    k = portfolio_kpis()
    c1, c2, c3 = st.columns(3)
    c1.metric("📋 Grants Records", f"{k['grant_count']:,}")
    c2.metric("💰 Total Funding", f"${k['total_funding']/1e6:.1f}M")
    c3.metric("📒 ERP Transactions", f"{k['transaction_count']:,}")

# -------------------------------
# FOOTER
# -------------------------------
st.markdown("---")
st.caption(
    "🔒 This environment uses **sanitized mock data only** — no CUI, PII, or classified information is displayed. "
    "Architecture supports DoD IL4/IL5 security baselines."
)
