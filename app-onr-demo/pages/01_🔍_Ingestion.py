"""
ONR ITSS POC — Element 3: Ingestion Page
Automated Ingestion, Data Operations, and Streaming
"""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.ingestion_helpers import (
    render_ingestion_status,
    render_quality_checks,
    render_schema_evolution,
    render_streaming_metrics,
    render_ingestion_demo,
    generate_mock_grants_data,
    generate_mock_financial_data,
)

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Ingestion | ONR ITSS POC")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("🔍 Element 3: Automated Ingestion, Data Operations, and Streaming")
st.markdown(
    """
    This element demonstrates **automated ingestion pipelines (ETL/ELT)**, automated quality checks, 
    schema evolution handling, and near-real-time data streaming architecture.
    """
)

# -------------------------------
# SESSION STATE
# -------------------------------
sso_user = init_user_session_state()
dbx_env = get_runtime_env()

# Load configuration
app_root = Path(__file__).resolve().parent.parent
config_file = app_root / "config" / dbx_env / "onr-conf.yaml"

try:
    configs = read_yaml(str(config_file))
    onr_catalog = configs["schema"]["catalog"]
    onr_schema = configs["schema"].get("schema", "dev")
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
    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 5px solid #0066cc;">
        <strong>📌 Key Focus Areas:</strong>
        <ul>
            <li>Automated ingestion pipelines with Auto Loader</li>
            <li>Data quality checks on ingestion</li>
            <li>Schema evolution without manual reconfiguration</li>
            <li>Near-real-time streaming architecture support</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# TABS
# -------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Pipeline Status",
    "✅ Quality Checks", 
    "🔄 Schema & Streaming",
    "🎮 Live Demo"
])

with tab1:
    render_ingestion_status(cursor, onr_catalog, onr_schema)

with tab2:
    render_quality_checks(cursor, onr_catalog, onr_schema)

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        render_schema_evolution(cursor, onr_catalog, onr_schema)
    
    with col2:
        render_streaming_metrics()

with tab4:
    render_ingestion_demo(onr_catalog, onr_schema)

# -------------------------------
# ARCHITECTURE DIAGRAM
# -------------------------------
st.markdown("---")
st.markdown("### 🏗️ Ingestion Architecture")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────┐
│                    Automated Ingestion Pipeline                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   📁 Source Files        🔄 Auto Loader         🥉 Bronze Layer    │
│   ┌─────────┐           ┌─────────────┐        ┌─────────────┐     │
│   │  CSV    │──────────▶│  cloudFiles │───────▶│  Raw Delta  │     │
│   │  JSON   │           │  Schema     │        │  + Metadata │     │
│   │  Parquet│           │  Evolution  │        └──────┬──────┘     │
│   └─────────┘           └─────────────┘               │            │
│                                                        ▼            │
│                                               ┌──────────────┐     │
│                                               │   Quality    │     │
│                                               │   Checks     │     │
│                                               └──────┬───────┘     │
│                                                      │             │
│                              ┌───────────────────────┴──────┐      │
│                              ▼                              ▼      │
│                       ┌────────────┐                 ┌──────────┐  │
│                       │  ✅ Pass   │                 │ ❌ Quarantine││
│                       │  → Silver  │                 │  → Review  │ │
│                       └────────────┘                 └──────────┘  │
│                                                                     │
│   📡 Streaming Options:                                             │
│   • Auto Loader (default) — S3 incremental detection                │
│   • AWS Kinesis — Real-time event streaming                         │
│   • Lakeflow Connect — Managed connectors (Salesforce, etc.)        │
│   • Zerobus — High-volume Kafka replacement                         │
└─────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# MOCK DATA PREVIEW
# -------------------------------
st.markdown("---")
st.markdown("### 📋 Sample Mock Data")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### S&T Research Grants")
    grants_df = generate_mock_grants_data(10)
    st.dataframe(grants_df, use_container_width=True)

with col2:
    st.markdown("#### Financial ERP Data")
    financial_df = generate_mock_financial_data(10)
    st.dataframe(financial_df, use_container_width=True)

# -------------------------------
# EVALUATION ALIGNMENT
# -------------------------------
st.markdown("---")
st.markdown("### 📝 Evaluation Alignment")

st.markdown(
    """
    | Criterion | How Element 3 Demonstrates It |
    |-----------|-------------------------------|
    | **Technical Competence** | Key Personnel demonstrate live pipeline navigation and Auto Loader configuration |
    | **Open Architecture** | Standard streaming protocols (Kinesis, Kafka-compatible), portable data formats |
    | **Strategic Agility** | Automated detection and quality handling without manual intervention |
    """
)
