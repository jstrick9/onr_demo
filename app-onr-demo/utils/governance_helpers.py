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
    st.markdown("### Registry")
    
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
    st.markdown("### Quality")
    
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
                with st.expander(f"{table} — Score: {score:.1%}", expanded=False):
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
            st.caption("No quality scores yet.")
    except Exception:
        st.caption("Quality scores appear after the next ingest.")

    st.markdown("#### Published with a finding")
    st.caption(
        "These rows still landed in silver and gold. The finding is the error log — "
        "missing abstract, unknown program area, or amount over $5M."
    )
    try:
        from utils.demo_actions import load_quality_findings

        warns = load_quality_findings(cursor, catalog) if cursor else []
        if warns:
            show = pd.DataFrame(warns)
            keep = [
                c
                for c in (
                    "grant_no",
                    "check_name",
                    "detail",
                    "program_area",
                    "amount_usd",
                    "severity",
                    "published",
                )
                if c in show.columns
            ]
            st.dataframe(show[keep] if keep else show, use_container_width=True, hide_index=True)
        else:
            st.caption("No published warning findings. Ingest inbound grants to populate this log.")
    except Exception:
        st.caption("Published findings appear after ingest.")


# -------------------------------
# DATA LINEAGE VISUALIZATION
# -------------------------------
def render_lineage_launch(catalog: str = "onr_demo") -> None:
    """One workspace jump: native Catalog Explorer lineage for silver.grants."""
    from utils.workspace_ops import catalog_table_url, workspace_action_row

    st.markdown("### Lineage")
    st.caption(
        "Native Catalog Explorer graph — not a drawing here. "
        "Open gold.grants_summary after ingest so the graph is populated. "
        "If it is empty, ingest inbound grants on Ingestion, then reopen."
    )
    c1, c2 = st.columns(2)
    with c1:
        workspace_action_row(
            "Open lineage · gold.grants_summary",
            catalog_table_url(catalog, "gold", "grants_summary", tab="lineage"),
        )
    with c2:
        workspace_action_row(
            "Open lineage · silver.grants",
            catalog_table_url(catalog, "silver", "grants", tab="lineage"),
        )


def render_lineage_visualization():
    """Display end-to-end data lineage visualization."""
    st.markdown("### End-to-end lineage")
    st.caption(
        "Unity Catalog lineage is the system of record — landing through gold. "
        "Open Catalog Explorer on a table to see the native graph."
    )

    with st.expander("Sketch and hop list (not the native graph)"):
        st.markdown(
            """
```
/Volumes/onr_demo/bronze/landing/grants
        -> bronze.grants -> silver.grants -> gold.grants_summary
                                |                    |
                                v                    v
                        silver.financial      Portfolio / Analytics / Export
```
            """
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Source": "/Volumes/onr_demo/bronze/landing",
                        "Pipeline": "Auto Loader / Process",
                        "Target": "onr_demo.bronze.grants",
                        "Quality": "grant_no NOT NULL",
                    },
                    {
                        "Source": "onr_demo.bronze.grants",
                        "Pipeline": "Silver quality",
                        "Target": "onr_demo.silver.grants",
                        "Quality": "amount > 0, awardee not null, dedupe",
                    },
                    {
                        "Source": "onr_demo.silver.grants",
                        "Pipeline": "Gold aggregation",
                        "Target": "onr_demo.gold.grants_summary",
                        "Quality": "count + freshness",
                    },
                    {
                        "Source": "onr_demo.gold.*",
                        "Pipeline": "Registered models / OLS",
                        "Target": "predictions, anomalies, forecast",
                        "Quality": "registered model + trend IDs",
                    },
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


# -------------------------------
# CATALOG TAGS & POLICIES
# -------------------------------
def render_governance_policies(cursor, catalog: str, schema: str):
    """Display governance tags and access policies."""
    st.markdown("### Tags and policies")
    
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
            {"Table": "silver.grants", "Tag": "data_source", "Value": "mock"},
            {"Table": "silver.grants", "Tag": "vendor", "Value": "compass.synthetic"},
            {"Table": "silver.grants", "Tag": "license_id", "Value": "MOCK-LIC-08"},
            {"Table": "silver.grants", "Tag": "renewal_date", "Value": "2026-09-30"},
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
