"""
Governance Helpers for ONR ITSS POC — Element 4
Data Governance, Quality, and Cataloging
"""

import streamlit as st
import pandas as pd


# -------------------------------
# CATALOG REGISTRY DISPLAY
# -------------------------------
def render_catalog_registry(cursor, catalog: str, schema: str):
    """Display the data catalog registry."""
    st.markdown("### 📚 Data Catalog Registry")
    
    try:
        query = f"""
        SELECT
            table_schema,
            table_name,
            table_type,
            comment,
            created,
            last_altered
        FROM system.information_schema.tables
        WHERE table_catalog = '{catalog}'
          AND table_schema IN ('bronze', 'silver', 'gold', 'app')
        ORDER BY table_schema, table_name
        """
        if not cursor:
            raise RuntimeError("no warehouse")
        cursor.execute(query)
        tables = cursor.fetchall()
        
        if tables:
            df = pd.DataFrame(tables, columns=[
                "Schema", "Table", "Type", "Comment", "Created", "Last Altered"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No tables found in catalog.")
    except Exception as e:
        st.info("Catalog information will appear once tables are registered.")


# -------------------------------
# DATA QUALITY SCORES
# -------------------------------
def render_quality_scores(cursor, catalog: str, schema: str):
    """Display data quality health scores."""
    st.markdown("### 🏥 Data Quality Health Scores")
    
    try:
        query = f"""
        SELECT 
            table_name,
            quality_score,
            completeness,
            accuracy,
            consistency,
            timeliness,
            last_assessed
        FROM `{catalog}`.`app`.data_quality_scores
        ORDER BY table_name
        """
        if not cursor:
            raise RuntimeError("no warehouse")
        cursor.execute(query)
        scores = cursor.fetchall()
        
        if scores:
            for table, score, completeness, accuracy, consistency, timeliness, assessed in scores:
                with st.expander(f"📊 {table} — Score: {score:.1%}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Completeness", f"{completeness:.1%}")
                    with col2:
                        st.metric("Accuracy", f"{accuracy:.1%}")
                    with col3:
                        st.metric("Consistency", f"{consistency:.1%}")
                    with col4:
                        st.metric("Timeliness", f"{timeliness:.1%}")
                    
                    st.caption(f"Last assessed: {assessed}")
        else:
            st.info("No `app.data_quality_scores` yet. Run `02_silver_quality.py` on **onr demo cluster**.")
    except Exception:
        st.info("Quality scores appear after notebook 02 writes `app.data_quality_scores`.")


# -------------------------------
# DATA LINEAGE VISUALIZATION
# -------------------------------
def render_lineage_visualization():
    """Display end-to-end data lineage visualization."""
    st.markdown("### 🔗 End-to-End Data Lineage")
    
    # Create a visual lineage diagram using Streamlit native components
    st.markdown("""
    ```mermaid
    graph LR
        A[📁 Raw Files<br/>CSV/JSON] -->|Auto Loader| B[🥉 Bronze<br/>Raw Ingestion]
        B -->|Quality Checks| C[🥈 Silver<br/>Cleansed]
        C -->|Business Logic| D[🥇 Gold<br/>Aggregated]
        D --> E[📊 Dashboard]
        D --> F[🤖 Analytics]
        D --> G[📤 Export]
    ```
    """)
    
    # Detailed lineage table
    st.markdown("#### Lineage Details")
    
    lineage_data = [
        {
            "Source": "S3 Landing Zone",
            "Pipeline": "Auto Loader",
            "Target": "onr_demo.bronze.grants",
            "Transformations": "Schema inference, file metadata",
            "Quality Gates": "Null check on grant_no"
        },
        {
            "Source": "onr_demo.bronze.grants",
            "Pipeline": "Silver Transform",
            "Target": "onr_demo.silver.grants",
            "Transformations": "Deduplication, type casting, validation",
            "Quality Gates": "Positive amounts, awardee not null"
        },
        {
            "Source": "onr_demo.silver.grants",
            "Pipeline": "Gold Aggregation",
            "Target": "onr_demo.gold.grants_summary",
            "Transformations": "Group by program_area, fiscal_year",
            "Quality Gates": "Count validation, freshness check"
        },
        {
            "Source": "onr_demo.gold.grants_summary",
            "Pipeline": "Analytics Model",
            "Target": "ML Predictions",
            "Transformations": "Feature engineering, model scoring",
            "Quality Gates": "Model accuracy threshold"
        },
    ]
    
    df = pd.DataFrame(lineage_data)
    st.dataframe(df, use_container_width=True)


# -------------------------------
# CATALOG TAGS & POLICIES
# -------------------------------
def render_governance_policies(cursor, catalog: str, schema: str):
    """Display governance tags and access policies."""
    st.markdown("### 🏷️ Governance Tags & Policies")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Data Classification Tags")
        tags_data = [
            {"Table": "silver.grants", "Tag": "data_sensitivity", "Value": "public"},
            {"Table": "silver.grants", "Tag": "domain", "Value": "research"},
            {"Table": "silver.financial", "Tag": "data_sensitivity", "Value": "internal"},
            {"Table": "silver.financial", "Tag": "domain", "Value": "finance"},
            {"Table": "gold.grants_summary", "Tag": "data_sensitivity", "Value": "public"},
            {"Table": "gold.financial_summary", "Tag": "data_sensitivity", "Value": "internal"},
        ]
        st.dataframe(pd.DataFrame(tags_data), use_container_width=True)
    
    with col2:
        st.markdown("#### Access Policies")
        policies_data = [
            {"Principal": "data-engineers", "Permission": "CAN_MANAGE", "Scope": "All tables"},
            {"Principal": "analysts", "Permission": "SELECT", "Scope": "Gold tables"},
            {"Principal": "viewers", "Permission": "SELECT", "Scope": "Gold views only"},
            {"Principal": "admin", "Permission": "ALL", "Scope": "Full catalog"},
        ]
        st.dataframe(pd.DataFrame(policies_data), use_container_width=True)
    
    # Row-level security example
    st.markdown("#### Row-Level Security Example")
    st.code("""
-- Row filter: Users only see their region's data
ALTER TABLE `{catalog}`.`gold`.grants_summary 
SET ROW FILTER region_filter ON (region = current_user_region());

-- Column mask: Mask PI names for viewers
CREATE FUNCTION mask_pi_name(name STRING) 
RETURN CASE 
    WHEN IS_MEMBER('analysts') THEN name 
    ELSE CONCAT(LEFT(name, 1), '****') 
END;

ALTER TABLE `{catalog}`.`silver`.grants 
ALTER COLUMN awardee 
SET MASK mask_awardee;
    """, language="sql")


# -------------------------------
# LINEAGE TRACKING TABLE
# -------------------------------
def render_lineage_tracking(cursor, catalog: str, schema: str):
    """Display lineage tracking records."""
    st.markdown("### 📝 Lineage Tracking Records")
    
    try:
        query = f"""
        SELECT 
            source_table,
            target_table,
            transformation_type,
            records_processed,
            processing_time_ms,
            executed_at
        FROM `{catalog}`.`app`.lineage_tracking
        ORDER BY executed_at DESC
        LIMIT 20
        """
        if not cursor:
            raise RuntimeError("no warehouse")
        cursor.execute(query)
        records = cursor.fetchall()
        
        if records:
            df = pd.DataFrame(records, columns=[
                "Source", "Target", "Transform", "Records", "Time (ms)", "Executed At"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Lineage tracking records will appear after pipeline execution.")
    except Exception:
        st.info("Lineage tracking requires pipeline execution history.")
