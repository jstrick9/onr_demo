"""
ONR ITSS POC — Element 4: Governance Page
Data Governance, Quality, and Cataloging
"""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.governance_helpers import (
    render_catalog_registry,
    render_quality_scores,
    render_lineage_visualization,
    render_governance_policies,
    render_lineage_tracking,
)

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
set_page_config(page_title="Governance | ONR ITSS POC")
setup_sidebar()

# -------------------------------
# HEADER
# -------------------------------
st.title("📊 Element 4: Data Governance, Quality, and Cataloging")
st.markdown(
    """
    This element demonstrates how the platform **catalogs datasets**, captures metadata, 
    calculates data quality/health scores, and visualizes **end-to-end data lineage** 
    from raw ingestion to the visualization tier.
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
    <div style="background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107;">
        <strong>📌 Key Focus Areas:</strong>
        <ul>
            <li>Unity Catalog registry and metadata management</li>
            <li>Data quality health scores and monitoring</li>
            <li>End-to-end lineage visualization (raw → visualization)</li>
            <li>Access policies, tags, and governance controls</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# TABS
# -------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📚 Catalog Registry",
    "🏥 Quality Scores",
    "🔗 Lineage",
    "🏷️ Policies & Tags",
    "📝 Tracking"
])

with tab1:
    render_catalog_registry(cursor, onr_catalog, onr_schema)

with tab2:
    render_quality_scores(cursor, onr_catalog, onr_schema)

with tab3:
    render_lineage_visualization()

with tab4:
    render_governance_policies(cursor, onr_catalog, onr_schema)

with tab5:
    render_lineage_tracking(cursor, onr_catalog, onr_schema)

# -------------------------------
# UNITY CATALOG OVERVIEW
# -------------------------------
st.markdown("---")
st.markdown("### 🗄️ Unity Catalog Architecture")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────┐
│                        Unity Catalog (onr_demo)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                     Catalog: onr_demo                        │   │
│   │  ┌───────────────────────────────────────────────────────┐  │   │
│   │  │                   Schema: dev                          │  │   │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │   │
│   │  │  │   Bronze    │  │   Silver    │  │    Gold     │   │  │   │
│   │  │  │   Tables    │  │   Tables    │  │   Tables    │   │  │   │
│   │  │  │  ─────────  │  │  ─────────  │  │  ─────────  │   │  │   │
│   │  │  │ bronze_grants│ │ silver_grants│ │ gold_grants │   │  │   │
│   │  │  │ bronze_fin   │ │ silver_fin   │ │ gold_fin    │   │  │   │
│   │  │  └─────────────┘  └─────────────┘  └─────────────┘   │  │   │
│   │  │                                                       │  │   │
│   │  │  ┌─────────────────────────────────────────────────┐  │  │   │
│   │  │  │              Volumes (Managed)                   │  │  │   │
│   │  │  │  /Volumes/onr_demo/dev/landing/                  │  │  │   │
│   │  │  │  /Volumes/onr_demo/dev/checkpoints/              │  │  │   │
│   │  │  └─────────────────────────────────────────────────┘  │  │   │
│   │  └───────────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   Governance Features:                                              │
│   ✅ Row-Level Security    ✅ Column Masks    ✅ ABAC Tags          │
│   ✅ Data Lineage          ✅ Audit Logging   ✅ Access Policies    │
└─────────────────────────────────────────────────────────────────────┘
```
""")

# -------------------------------
# DDL EXAMPLES
# -------------------------------
st.markdown("---")
st.markdown("### 📝 Unity Catalog DDL Examples")

with st.expander("View Catalog & Schema Setup"):
    st.code(f"""
-- Create Catalog
CREATE CATALOG IF NOT EXISTS `{onr_catalog}`
    MANAGED LOCATION 's3://onr-demo-uc-bucket/{onr_catalog}';

-- Create Schema
CREATE SCHEMA IF NOT EXISTS `{onr_catalog}`.`{onr_schema}`;

-- Create Landing Volume
CREATE VOLUME IF NOT EXISTS `{onr_catalog}`.`{onr_schema}`.landing;

-- Grants
GRANT USE CATALOG ON CATALOG `{onr_catalog}` TO `data-engineers`;
GRANT USE SCHEMA, CREATE TABLE ON SCHEMA `{onr_catalog}`.`{onr_schema}` TO `data-engineers`;
GRANT SELECT ON SCHEMA `{onr_catalog}`.`{onr_schema}` TO `analysts`;
    """, language="sql")

with st.expander("View Table DDL with Quality Constraints"):
    st.code(f"""
-- Silver Table with Quality Constraints
CREATE TABLE IF NOT EXISTS `{onr_catalog}`.`{onr_schema}`.silver_grants (
    grant_id STRING NOT NULL,
    title STRING,
    principal_investigator STRING NOT NULL,
    institution STRING,
    research_area STRING,
    award_amount DOUBLE,
    status STRING,
    start_date DATE,
    end_date DATE,
    fiscal_year INT,
    _ingest_time TIMESTAMP,
    _source_file STRING,
    _is_active BOOLEAN DEFAULT true,
    CONSTRAINT valid_amount CHECK (award_amount > 0),
    CONSTRAINT valid_dates CHECK (end_date > start_date)
) USING DELTA
CLUSTER BY (research_area, fiscal_year)
TBLPROPERTIES (
    'delta.feature.allowColumnDefaults' = 'supported',
    'quality' = 'gold'
);

-- Tags for Governance
ALTER TABLE `{onr_catalog}`.`{onr_schema}`.silver_grants 
SET TAGS (
    'domain' = 'research',
    'data_sensitivity' = 'public',
    'data_source' = 'mock',
    'owner' = 'data-engineers'
);
    """, language="sql")

# -------------------------------
# EVALUATION ALIGNMENT
# -------------------------------
st.markdown("---")
st.markdown("### 📝 Evaluation Alignment")

st.markdown(
    """
    | Criterion | How Element 4 Demonstrates It |
    |-----------|-------------------------------|
    | **Technical Competence** | Key Personnel navigate catalog, demonstrate lineage tools, show quality scores |
    | **Open Architecture** | Portable metadata models, standard catalog APIs, self-describing schemas |
    | **Strategic Agility** | Governance adapts to evolving data strategies and automation needs |
    """
)
