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
from utils.api_helpers import render_live_statement_api

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Export | ONR Portfolio")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("Export & APIs")
st.caption(
    "Filtered bulk export in CSV, JSON, or Parquet. Audit rows land in app.export_history. "
    "The live API is Databricks Statement Execution REST."
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
    render_live_statement_api(cursor, onr_catalog)
    st.markdown("---")
    render_api_documentation()

with tab3:
    render_interoperability()

with tab4:
    render_schema_documentation()

with tab5:
    render_export_history(cursor, onr_catalog)

# -------------------------------
# EXPORT ARCHITECTURE
# -------------------------------
st.markdown("---")
st.markdown("### How it works")

st.markdown("""
```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                         Interoperability and Secure Export                        │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  gold / silver                     Secure export                      Open files  │
│  +--------------------+         +--------------------+         +---------------+  │
│  | Business-ready     | ------> | TLS 1.3            | ------> | CSV           |  │
│  | filtered query     |         | date + LIMIT       |         | JSON          |  │
│  +--------------------+         | export_history     |         | Parquet       |  │
│                                 +--------------------+         +-------+-------+  │
│                                                                        |          │
│                  +--------------------------+-------------+------------+          │
│                  |                          |             |            |          │
│                  v                          v             v            v          │
│           +-----------------+        +-----------------+ +-------+ +---------+    │
│           | Advana          |        | Cloud One       | |Tableau| | Excel / |    │
│           | JDBC / REST     |        | S3 / REST       | |PowerBI| | Sheets  |    │
│           +-----------------+        +-----------------+ +-------+ +---------+    │
│                                                                                   │
│  Live open API (not fictional hosts)                                              │
│    POST /api/2.0/sql/statements      Databricks Statement Execution               │
│    same warehouse the dashboard uses; OAuth, short-lived token                    │
│                                                                                   │
│  Open standards: Delta | CSV | JSON | Parquet | SQL | JDBC/ODBC | REST            │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# ZERO TRUST COMPLIANCE
# -------------------------------
st.markdown("---")
st.markdown("### Security")

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
    #### Hosting note
    - ✅ **Micro-segmentation** — Network isolation
    - ✅ **Least Privilege** — Minimal permissions
    - ✅ **Encryption at Rest** — AES-256
    - ✅ **Key Management** — AWS KMS integration
    - ✅ **Continuous Monitoring** — Real-time alerts
    - ✅ **Disaster Recovery** — Multi-AZ failover
    """)

