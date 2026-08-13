"""
Dashboard Helpers for ONR ITSS POC — Element 6
Unified Dashboard, Visualizations, and Process Automation
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


# -------------------------------
# EXECUTIVE KPI CARDS
# -------------------------------
def render_executive_kpis():
    """Display executive-level KPI cards from the Compass fixture."""
    from utils.portfolio_data import portfolio_kpis

    k = portfolio_kpis()
    st.markdown("### 📊 Executive Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="Total Portfolio", value=f"${k['total_funding']/1e6:.1f}M")
    with col2:
        st.metric(label="Grants", value=f"{k['grant_count']:,}")
    with col3:
        st.metric(label="ERP Execution", value=f"{k['execution_rate']:.1f}%")
    with col4:
        st.metric(label="Avg Award Size", value=f"${k['avg_award']/1e6:.2f}M")
    with col5:
        st.metric(label="Awardees", value=f"{k['awardee_count']:,}")


# -------------------------------
# INTERACTIVE FILTERS
# -------------------------------
def render_dashboard_filters():
    """Render interactive dashboard filters."""
    st.markdown("### 🔍 Filter Controls")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        from utils.portfolio_data import fiscal_years, program_areas

        fys = fiscal_years()
        fiscal_year = st.multiselect(
            "Fiscal Year",
            options=fys,
            default=fys[-2:] if len(fys) >= 2 else fys,
            key="dash_fiscal_year"
        )
    
    with col2:
        areas = program_areas()
        research_area = st.multiselect(
            "Program Area",
            options=areas,
            default=areas[:2],
            key="dash_research_area"
        )
    
    with col3:
        status = st.multiselect(
            "Classification Band",
            options=["CUI-Mock", "Public-Mock"],
            default=["CUI-Mock", "Public-Mock"],
            key="dash_status"
        )
    
    with col4:
        amount_range = st.slider(
            "Award Amount Range",
            min_value=0,
            max_value=5000000,
            value=(0, 2000000),
            step=100000,
            format="$%d",
            key="dash_amount"
        )
    
    return {
        "fiscal_year": fiscal_year,
        "research_area": research_area,
        "status": status,
        "amount_min": amount_range[0],
        "amount_max": amount_range[1]
    }


# -------------------------------
# GRANTS OVERVIEW CHART
# -------------------------------
def render_grants_overview(cursor, catalog: str, schema: str, filters: dict):
    """Display grants overview visualization."""
    st.markdown("### 📈 Grants Overview")
    
    try:
        # Build query with filters
        where_clauses = ["_is_active = true"]
        
        if filters.get("fiscal_year"):
            years = ",".join(str(y) for y in filters["fiscal_year"])
            where_clauses.append(f"fiscal_year IN ({years})")
        
        if filters.get("research_area"):
            areas = ",".join(f"'{a}'" for a in filters["research_area"])
            where_clauses.append(f"program_area IN ({areas})")
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        SELECT 
            program_area,
            COUNT(*) as grant_count,
            SUM(amount_usd) as total_funding,
            AVG(amount_usd) as avg_award
        FROM `{catalog}`.`silver`.grants
        WHERE {where_clause}
        GROUP BY program_area
        ORDER BY total_funding DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        if results:
            df = pd.DataFrame(results, columns=["Research Area", "Grant Count", "Total Funding", "Avg Award"])
            
            tab1, tab2 = st.tabs(["Chart View", "Table View"])
            
            with tab1:
                fig = px.bar(
                    df,
                    x="Research Area",
                    y="Total Funding",
                    color="Grant Count",
                    title="Funding by Research Area",
                    labels={"Total Funding": "Total Funding ($)", "Grant Count": "# Grants"},
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.dataframe(
                    df.style.format({
                        "Total Funding": "${:,.0f}",
                        "Avg Award": "${:,.0f}"
                    }),
                    use_container_width=True
                )
        else:
            render_simulated_overview()
    except Exception:
        render_simulated_overview()


def render_simulated_overview():
    """Display fixture-backed overview when warehouse is unavailable."""
    from utils.portfolio_data import grants_dataframe

    g = grants_dataframe()
    df = (
        g.groupby("program_area", as_index=False)
        .agg(grant_count=("grant_no", "count"), total_funding=("amount_usd", "sum"), avg_award=("amount_usd", "mean"))
        .rename(columns={"program_area": "Research Area", "grant_count": "Grant Count",
                         "total_funding": "Total Funding", "avg_award": "Avg Award"})
    )
    
    fig = px.bar(
        df,
        x="Research Area",
        y="Total Funding",
        color="Grant Count",
        title="Funding by Program Area (Compass fixture)",
        color_continuous_scale="Viridis"
    )
    st.plotly_chart(fig, use_container_width=True)


# -------------------------------
# BUDGET EXECUTION DASHBOARD
# -------------------------------
def render_budget_execution():
    """Display budget execution dashboard."""
    st.markdown("### 💰 Budget Execution Tracker")
    
    # Simulated budget data
    categories = ["Personnel", "Equipment", "Travel", "Contractors", "Supplies", "Training"]
    budget = [120, 85, 25, 45, 15, 10]
    actual = [115, 78, 22, 48, 14, 9]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name="Budget",
        x=categories,
        y=budget,
        marker_color="lightblue"
    ))
    
    fig.add_trace(go.Bar(
        name="Actual",
        x=categories,
        y=actual,
        marker_color="darkblue"
    ))
    
    fig.update_layout(
        title="Budget vs Actual by Category ($M)",
        barmode="group",
        yaxis_title="Amount ($M)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Execution rate gauge
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=94.2,
            title={"text": "Overall Execution Rate"},
            delta={"reference": 90},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 80], "color": "lightcoral"},
                    {"range": [80, 90], "color": "lightyellow"},
                    {"range": [90, 100], "color": "lightgreen"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90
                }
            }
        ))
        fig_gauge.update_layout(height=250)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Category Performance")
        for cat, b, a in zip(categories[:3], budget[:3], actual[:3]):
            rate = (a / b) * 100
            st.progress(rate / 100, text=f"{cat}: {rate:.1f}%")
    
    with col3:
        st.markdown("#### ⚠️ Alerts")
        st.warning("⚠️ Contractors category 6.7% over budget")
        st.success("✅ Personnel on track")
        st.info("ℹ️ Equipment 7.6% under budget")


# -------------------------------
# PROCESS AUTOMATION
# -------------------------------
def render_process_automation():
    """Display process automation features."""
    st.markdown("### 🤖 Process Automation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Automated Workflows")
        
        automations = [
            {"name": "📊 Daily Summary Report", "status": "Active", "last_run": "2 hours ago", "next_run": "Tomorrow 6 AM"},
            {"name": "🚨 Anomaly Alerts", "status": "Active", "last_run": "15 min ago", "next_run": "Continuous"},
            {"name": "📋 Approval Routing", "status": "Active", "last_run": "1 hour ago", "next_run": "On trigger"},
            {"name": "📈 Weekly Dashboard Refresh", "status": "Active", "last_run": "Yesterday", "next_run": "Monday 7 AM"},
            {"name": "🔔 Data Quality Alerts", "status": "Active", "last_run": "30 min ago", "next_run": "Hourly"},
        ]
        
        for auto in automations:
            with st.expander(auto["name"]):
                st.write(f"**Status:** {auto['status']}")
                st.write(f"**Last Run:** {auto['last_run']}")
                st.write(f"**Next Run:** {auto['next_run']}")
    
    with col2:
        st.markdown("#### Anomaly Detection")
        
        # Simulated anomaly data
        dates = pd.date_range(start="2026-07-01", end="2026-08-12", freq="D")
        values = np.random.normal(100, 10, len(dates))
        values[-3] = 150  # Anomaly
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=values,
            mode="lines+markers",
            name="Daily Metric"
        ))
        
        # Mark anomalies
        fig.add_trace(go.Scatter(
            x=[dates[-3]], y=[150],
            mode="markers",
            marker=dict(size=15, color="red", symbol="x"),
            name="Anomaly Detected"
        ))
        
        fig.update_layout(
            title="Anomaly Detection - Daily Spending",
            xaxis_title="Date",
            yaxis_title="Amount ($K)",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)


# -------------------------------
# SEARCH AND EXTRACT
# -------------------------------
def render_search_extract(cursor, catalog: str, schema: str):
    """Display search and extract functionality for non-technical users."""
    st.markdown("### 🔍 Search, Filter & Extract")
    st.caption("Designed for non-technical leadership — no code required")
    
    # Simple search interface
    search_term = st.text_input(
        "Search grants by title, awardee, grant number, or org unit:",
        placeholder="e.g., 'quantum' or 'ONRD-2024'",
        key="exec_search"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if search_term:
            try:
                query = f"""
                SELECT 
                    grant_id,
                    title,
                    principal_investigator,
                    institution,
                    research_area,
                    award_amount,
                    status
                FROM `{catalog}`.`silver`.grants
                WHERE LOWER(title) LIKE '%{search_term.lower()}%'
                    OR LOWER(principal_investigator) LIKE '%{search_term.lower()}%'
                    OR LOWER(institution) LIKE '%{search_term.lower()}%'
                LIMIT 50
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                if results:
                    df = pd.DataFrame(results, columns=[
                        "Grant ID", "Title", "PI", "Institution", 
                        "Research Area", "Amount", "Status"
                    ])
                    st.dataframe(
                        df.style.format({"Amount": "${:,.0f}"}),
                        use_container_width=True
                    )
                    
                    # Export button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results (CSV)",
                        data=csv,
                        file_name=f"grants_search_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No results found. Try a different search term.")
            except Exception:
                from utils.portfolio_data import filter_grants
                df = filter_grants(search=search_term).head(50)
                if df.empty:
                    st.info("No results found. Try a different search term.")
                else:
                    show = df[["grant_no", "title", "awardee", "org_unit", "program_area", "amount_usd", "classification_band"]]
                    st.dataframe(show, use_container_width=True)
    
    with col2:
        st.markdown("#### Quick Filters")
        if st.button("📋 All Active Grants"):
            st.session_state["exec_search"] = ""
            st.rerun()
        if st.button("🎯 High Priority"):
            st.info("Filters by priority > 80%")
        if st.button("⚠️ Needs Review"):
            st.info("Filters by status = 'Pending Review'")


# -------------------------------
# RECENT ACTIVITY LOG
# -------------------------------
def render_activity_log():
    """Display recent activity log."""
    st.markdown("### 📜 Recent Activity")
    
    activities = [
        {"time": "10 min ago", "user": "jsmith@navy.mil", "action": "Exported 250 grant records (CSV)"},
        {"time": "25 min ago", "user": "analyst@navy.mil", "action": "Generated Q3 budget report"},
        {"time": "1 hour ago", "user": "system", "action": "Anomaly detected in spending category 'Contractors'"},
        {"time": "2 hours ago", "user": "admin@navy.mil", "action": "Updated data quality thresholds"},
        {"time": "3 hours ago", "user": "system", "action": "Daily summary report generated and distributed"},
    ]
    
    for activity in activities:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 4])
            with col1:
                st.caption(activity["time"])
            with col2:
                st.caption(activity["user"])
            with col3:
                st.write(activity["action"])
            st.divider()
