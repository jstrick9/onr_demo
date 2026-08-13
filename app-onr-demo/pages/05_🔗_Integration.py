"""
ONR ITSS POC — Element 7: Integration Page
Interoperability, Data Portability, and Secure Export
"""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.export_helpers import (
    render_export_options,
    render_dataset_selection,
    render_export_filters,
    render_secure_export,
    render_api_documentation,
    render_interoperability,
    render_export_history,
    render_schema_documentation,
)

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Integration | ONR ITSS POC")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("🔗 Element 7: Interoperability, Data Portability, and Secure Export")
st.markdown(
    """
    This element demonstrates **secure bulk data export**, compliance with open data standards, 
    and how schemas and APIs support **seamless integration with broader enterprise cloud platforms** 
    while preventing vendor lock-in.
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

# Database connection
conn, cursor = get_connection()
if not cursor:
    st.stop()

# -------------------------------
# ELEMENT OVERVIEW
# -------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="background-color: #e2e3e5; padding: 15px; border-radius: 10px; border-left: 5px solid #6c757d;">
        <strong>📌 Key Focus Areas:</strong>
        <ul>
            <li>Non-proprietary format export (CSV, JSON, Parquet)</li>
            <li>Schema portability and self-describing data</li>
            <li>API support for Advana, Cloud One integration</li>
            <li>Secure bulk extraction aligned with Zero Trust</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# TABS
# -------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Data Export",
    "🔌 API Documentation",
    "🔄 Interoperability",
    "📖 Schema Docs",
    "📜 Export History"
])

with tab1:
    # Export workflow
    formats = render_export_options()
    
    st.markdown("---")
    
    dataset_name, dataset_table = render_dataset_selection(cursor, onr_catalog, onr_schema)
    
    st.markdown("---")
    
    filters = render_export_filters()
    
    st.markdown("---")
    
    if dataset_table and formats:
        render_secure_export(cursor, onr_catalog, onr_schema, dataset_table, formats, filters)
    else:
        st.warning("Please select at least one export format and a dataset.")

with tab2:
    render_api_documentation()

with tab3:
    render_interoperability()

with tab4:
    render_schema_documentation()

with tab5:
    render_export_history()

# -------------------------------
# EXPORT ARCHITECTURE
# -------------------------------
st.markdown("---")
st.markdown("### 🏗️ Export & Integration Architecture")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────┐
│                Interoperability & Secure Export                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   📊 Gold Layer              🔒 Secure Export          📤 Output    │
│   ┌─────────────┐          ┌─────────────┐        ┌─────────────┐  │
│   │  Business   │─────────▶│  TLS 1.3    │──────▶│    CSV      │  │
│   │  Ready Data │          │  Encrypted  │        │    JSON     │  │
│   └─────────────┘          │  Audit Log  │        │    Parquet  │  │
│                            └─────────────┘        └──────┬──────┘  │
│                                                          │         │
│          ┌───────────────────────────────────────────────┤         │
│          │               │               │               │         │
│          ▼               ▼               ▼               ▼         │
│   ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐   │
│   │   Advana    │  │  Cloud One  │  │ Tableau  │  │  Excel   │   │
│   │   (DoD)    │  │   (USAF)    │  │  PowerBI │  │  Sheets  │   │
│   └─────────────┘  └─────────────┘  └──────────┘  └──────────┘   │
│                                                                     │
│   API Endpoints (RESTful):                                          │
│   • GET /api/v1/grants — Query grants with filters                  │
│   • GET /api/v1/financial — Query financial data                    │
│   • POST /api/v1/export — Trigger secure bulk export                │
│   • GET /api/v1/schema — Get schema documentation                   │
│                                                                     │
│   Open Standards:                                                   │
│   ✅ CSV / JSON / Parquet   ✅ REST APIs    ✅ ODBC/JDBC            │
│   ✅ Delta Lake (open)      ✅ SQL          ✅ Standard Protocols   │
└─────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# ZERO TRUST COMPLIANCE
# -------------------------------
st.markdown("---")
st.markdown("### 🔐 Zero Trust Compliance")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    #### Export Security Controls
    - ✅ **TLS 1.3 Encryption** — All data in transit
    - ✅ **Audit Logging** — Every export recorded
    - ✅ **Access Control** — Role-based permissions
    - ✅ **Data Classification** — Tags applied to exports
    - ✅ **Continuous Authorization** — OAuth token-based
    - ✅ **No CUI/PII** — Mock data only in demo
    """)

with col2:
    st.markdown("""
    #### IL4/IL5 Baseline Compliance
    - ✅ **Micro-segmentation** — Network isolation
    - ✅ **Least Privilege** — Minimal permissions
    - ✅ **Encryption at Rest** — AES-256
    - ✅ **Key Management** — AWS KMS integration
    - ✅ **Continuous Monitoring** — Real-time alerts
    - ✅ **Disaster Recovery** — Multi-AZ failover
    """)

# -------------------------------
# EVALUATION ALIGNMENT
# -------------------------------
st.markdown("---")
st.markdown("### 📝 Evaluation Alignment")

st.markdown(
    """
    | Criterion | How Element 7 Demonstrates It |
    |-----------|-------------------------------|
    | **Open Architecture (Primary)** | Non-proprietary formats, standard APIs, portable schemas, no vendor lock-in |
    | **Technical Competence** | Key Personnel demonstrate secure extraction and API architecture |
    | **Strategic Alignment** | Interoperability with DoW/DoN enterprise platforms |
    """
)
