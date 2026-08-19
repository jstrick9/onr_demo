"""
Dashboard Helpers for ONR ITSS POC — Element 6
Unified Dashboard, Visualizations, and Process Automation
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import uuid
from datetime import datetime


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def _like_term(term: str) -> str:
    """Escape quotes and LIKE wildcards so user input cannot change the predicate."""
    return (
        (term or "")
        .replace("\\", "\\\\")
        .replace("'", "''")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .lower()
    )


def _ensure_search_history_table(cursor, catalog: str) -> None:
    if not cursor:
        return
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.search_history (
            search_id STRING NOT NULL,
            user_email STRING,
            search_type STRING,
            search_params STRING,
            results_count INT,
            execution_time_ms INT,
            created_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Search history for audit and replay'
        """
    )


def _persist_search(cursor, catalog: str, rec: dict) -> None:
    if not cursor:
        return
    try:
        _ensure_search_history_table(cursor, catalog)
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.search_history
            (search_id, user_email, search_type, search_params, results_count,
             execution_time_ms, created_at)
            VALUES (
                {_sql_str(rec.get("search_id"))},
                {_sql_str(rec.get("user"))},
                {_sql_str(rec.get("search_type") or "grants")},
                {_sql_str(rec.get("term"))},
                {int(rec.get("results") or 0)},
                {int(rec.get("execution_time_ms") or 0)},
                CURRENT_TIMESTAMP()
            )
            """
        )
    except Exception:
        pass


# -------------------------------
# EXECUTIVE KPI CARDS
# -------------------------------
def render_executive_kpis(cursor=None, catalog: str = "onr_demo"):
    """Executive KPIs from silver when the warehouse is up (tracks 400 → 408)."""
    from utils.portfolio_data import portfolio_kpis

    k = None
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*), SUM(amount_usd), AVG(amount_usd), COUNT(DISTINCT awardee)
                FROM `{catalog}`.`silver`.grants WHERE _is_active = true
                """
            )
            n, total, avg, awardees = cursor.fetchone()
            cursor.execute(
                f"""
                SELECT SUM(actual_expenditure) / NULLIF(SUM(budget_allocated), 0) * 100
                FROM `{catalog}`.`silver`.financial WHERE _is_active = true
                """
            )
            exe = cursor.fetchone()[0]
            if n:
                k = {
                    "grant_count": int(n),
                    "total_funding": float(total or 0),
                    "avg_award": float(avg or 0),
                    "execution_rate": float(exe or 0),
                    "awardee_count": int(awardees or 0),
                }
        except Exception:
            k = None
    if not k:
        k = portfolio_kpis()
    from utils.ui import provenance_note

    st.markdown("### Portfolio pulse")
    
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
    provenance_note("gold.budget_execution", catalog)


# -------------------------------
# INTERACTIVE FILTERS
# -------------------------------
def render_dashboard_filters():
    """Render interactive dashboard filters."""
    st.markdown("### Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        from utils.portfolio_data import fiscal_years, program_areas

        fys = fiscal_years()
        fiscal_year = st.multiselect(
            "Fiscal Year",
            options=fys,
            default=fys,
            key="dash_fiscal_year"
        )
    
    with col2:
        areas = program_areas()
        research_area = st.multiselect(
            "Program Area",
            options=areas,
            default=areas,
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
            max_value=8000000,
            value=(0, 8000000),
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
    st.markdown("### Grants overview")
    
    try:
        # Build query with filters
        where_clauses = ["_is_active = true"]
        
        if filters.get("fiscal_year"):
            years = ",".join(str(y) for y in filters["fiscal_year"])
            where_clauses.append(f"fiscal_year IN ({years})")
        
        if filters.get("research_area"):
            areas = ",".join(f"'{a}'" for a in filters["research_area"])
            where_clauses.append(f"program_area IN ({areas})")
        if filters.get("status"):
            bands = ",".join(f"'{s}'" for s in filters["status"])
            where_clauses.append(f"classification_band IN ({bands})")
        if filters.get("amount_min") is not None:
            where_clauses.append(f"amount_usd >= {float(filters['amount_min'])}")
        if filters.get("amount_max") is not None:
            where_clauses.append(f"amount_usd <= {float(filters['amount_max'])}")
        
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
        if not cursor:
            raise RuntimeError("no warehouse")
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
                from utils.ui import style_fig
                st.plotly_chart(style_fig(fig), use_container_width=True)
            
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
def render_budget_execution(cursor=None, catalog: str = "onr_demo"):
    """Budget vs actual from gold (falls back to derived ERP fixture)."""
    st.markdown("### Budget execution")

    categories, budget, actual = None, None, None
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT category,
                       SUM(budget_plan) / 1e6,
                       SUM(actual_spend) / 1e6
                FROM `{catalog}`.`gold`.budget_execution
                GROUP BY category
                ORDER BY 2 DESC
                """
            )
            rows = cursor.fetchall()
            if rows:
                categories = [r[0] for r in rows]
                budget = [float(r[1] or 0) for r in rows]
                actual = [float(r[2] or 0) for r in rows]
        except Exception:
            pass
    if not categories:
        from utils.portfolio_data import financial_dataframe

        f = financial_dataframe()
        g = f.groupby("category", as_index=False).agg(
            budget=("budget_allocated", "sum"), actual=("actual_expenditure", "sum")
        )
        categories = g["category"].tolist()
        budget = (g["budget"] / 1e6).tolist()
        actual = (g["actual"] / 1e6).tolist()
    
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
    
    from utils.ui import style_fig
    st.plotly_chart(style_fig(fig), use_container_width=True)

    # Execution rate gauge
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=round(100 * sum(actual) / sum(budget), 1) if sum(budget) else 0,
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
            rate = (a / b) * 100 if b else 0
            st.progress(min(rate / 100, 1.0), text=f"{cat}: {rate:.1f}%")
    
    with col3:
        st.markdown("#### Category vs plan")
        shown = 0
        for cat, b, a in zip(categories, budget, actual):
            if not b:
                continue
            rate = (a / b) * 100
            label = f"{cat}: {rate:.1f}%"
            if rate >= 100:
                st.warning(label + " over plan")
            elif rate >= 90:
                st.success(label)
            else:
                st.info(label + " under plan")
            shown += 1
            if shown >= 4:
                break


# -------------------------------
# PROCESS AUTOMATION
# -------------------------------
def render_process_automation(cursor=None, catalog: str = "onr_demo"):
    """Pipeline health from app.ingestion_quality_log and gold.budget_execution."""
    st.markdown("### Pipeline health (Unity Catalog)")
    q = pd.DataFrame()
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT check_name, check_status, records_checked, records_passed,
                       records_failed, check_timestamp, pipeline_name
                FROM `{catalog}`.`app`.ingestion_quality_log
                ORDER BY check_timestamp DESC
                LIMIT 15
                """
            )
            cols = [str(d[0]).lower() for d in cursor.description]
            q = pd.DataFrame(cursor.fetchall(), columns=cols)
        except Exception:
            q = pd.DataFrame()
    if q.empty:
        st.caption("No pipeline health rows yet.")
    else:
        st.dataframe(q, use_container_width=True)

    risk = pd.DataFrame()
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT fiscal_year, quarter, category, execution_rate, status
                FROM `{catalog}`.`gold`.budget_execution
                WHERE status IN ('WARNING', 'AT_RISK')
                ORDER BY execution_rate
                LIMIT 12
                """
            )
            cols = [str(d[0]).lower() for d in cursor.description]
            risk = pd.DataFrame(cursor.fetchall(), columns=cols)
        except Exception:
            risk = pd.DataFrame()
    st.markdown("#### Budget rows not ON_TARGET")
    if risk.empty:
        st.caption("No WARNING / AT_RISK rows (or gold.budget_execution not built).")
    else:
        st.dataframe(risk, use_container_width=True)

    flags = pd.DataFrame()
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT grant_no, program_area, amount_usd, anomaly_score,
                       predicted_type, model_name
                FROM `{catalog}`.`gold`.grant_anomaly_scores
                WHERE is_flagged = true
                ORDER BY anomaly_score DESC
                LIMIT 12
                """
            )
            cols = [str(d[0]).lower() for d in cursor.description]
            flags = pd.DataFrame(cursor.fetchall(), columns=cols)
        except Exception:
            flags = pd.DataFrame()
    st.markdown("#### Flagged funding anomalies")
    if flags.empty:
        st.caption("No flagged awards.")
    else:
        st.dataframe(flags, use_container_width=True)
        st.caption("Same review queue as Analytics → Anomalies.")


# -------------------------------
# SEARCH AND EXTRACT
# -------------------------------
def _ensure_routing_table(cursor, catalog: str) -> None:
    if not cursor:
        return
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.routing_log (
            action_id STRING NOT NULL,
            grant_no STRING,
            action STRING,
            user_email STRING,
            note STRING,
            created_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Officer Accept / Defer routing — Element 6 approval path'
        """
    )


def render_routing(cursor=None, catalog: str = "onr_demo") -> None:
    """Accept / Defer a flagged grant. Writes app.routing_log. Not ServiceNow."""
    st.markdown("### Routing")
    st.caption(
        "Accept or Defer one flagged award. The row lands in app.routing_log — "
        "who, grant, action, time. That is the approval path on this console."
    )
    flags = pd.DataFrame()
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT grant_no, program_area, amount_usd, predicted_type, anomaly_score
                FROM `{catalog}`.`gold`.grant_anomaly_scores
                WHERE is_flagged = true
                ORDER BY anomaly_score DESC
                LIMIT 12
                """
            )
            cols = [str(d[0]).lower() for d in (cursor.description or [])]
            flags = pd.DataFrame(cursor.fetchall() or [], columns=cols)
        except Exception:
            flags = pd.DataFrame()
    if flags.empty:
        st.caption("No flagged awards to route. Score registered models on Analytics first.")
        return
    ids = [str(x) for x in flags["grant_no"].tolist()]
    pick = st.selectbox("Flagged grant", ids, key="route_grant")
    row = flags[flags["grant_no"].astype(str) == pick]
    if not row.empty:
        rec = row.iloc[0]
        try:
            amt = f"${float(rec.get('amount_usd') or 0):,.0f}"
        except (TypeError, ValueError):
            amt = "—"
        st.caption(
            f"{rec.get('program_area') or '—'} · {amt} · "
            f"{rec.get('predicted_type') or 'flagged'}"
        )
    c1, c2 = st.columns(2)
    acted = None
    if c1.button("Accept", key="route_accept"):
        acted = "ACCEPT"
    if c2.button("Defer", key="route_defer"):
        acted = "DEFER"
    if acted:
        rec = {
            "action_id": f"rt-{uuid.uuid4().hex[:12]}",
            "grant_no": pick,
            "action": acted,
            "user": st.session_state.get("email") or "unknown",
        }
        try:
            if cursor:
                _ensure_routing_table(cursor, catalog)
                cursor.execute(
                    f"""
                    INSERT INTO `{catalog}`.`app`.routing_log
                    (action_id, grant_no, action, user_email, note, created_at)
                    VALUES (
                        {_sql_str(rec['action_id'])},
                        {_sql_str(rec['grant_no'])},
                        {_sql_str(rec['action'])},
                        {_sql_str(rec['user'])},
                        {_sql_str('officer routing')},
                        CURRENT_TIMESTAMP()
                    )
                    """
                )
            st.session_state.setdefault("routing_history", []).append(rec)
            st.success(f"{acted} {pick} · {rec['action_id']}")
        except Exception as e:
            st.error(f"Routing did not write: {e}")
    log = pd.DataFrame()
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT created_at, grant_no, action, user_email, action_id
                FROM `{catalog}`.`app`.routing_log
                ORDER BY created_at DESC
                LIMIT 8
                """
            )
            cols = [str(d[0]).lower() for d in (cursor.description or [])]
            log = pd.DataFrame(cursor.fetchall() or [], columns=cols)
        except Exception:
            log = pd.DataFrame(st.session_state.get("routing_history") or [])
    if not log.empty:
        st.dataframe(log, use_container_width=True, hide_index=True)


def render_search_extract(cursor, catalog: str, schema: str):
    """Display search and extract functionality for non-technical users."""
    st.markdown("### Search")
    st.caption("No SQL. Search gold-backed silver.grants. Writes app.search_history.")
    
    # Clear must happen *before* the widget is instantiated
    if st.session_state.pop("clear_exec_search", False):
        st.session_state["exec_search"] = ""

    search_term = st.text_input(
        "Search grants by title, awardee, grant number, or org unit:",
        placeholder="e.g., 'quantum' or 'ONRD-2024'",
        key="exec_search"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if search_term:
            t0 = time.perf_counter()
            n_results = 0
            try:
                like = _like_term(search_term)
                query = f"""
                SELECT 
                    grant_no,
                    title,
                    awardee,
                    org_unit,
                    program_area,
                    amount_usd,
                    classification_band
                FROM `{catalog}`.`silver`.grants
                WHERE LOWER(title) LIKE '%{like}%' ESCAPE '\\\\'
                    OR LOWER(awardee) LIKE '%{like}%' ESCAPE '\\\\'
                    OR LOWER(grant_no) LIKE '%{like}%' ESCAPE '\\\\'
                    OR LOWER(org_unit) LIKE '%{like}%' ESCAPE '\\\\'
                LIMIT 50
                """
                if not cursor:
                    raise RuntimeError("no warehouse")
                cursor.execute(query)
                results = cursor.fetchall()
                
                if results:
                    df = pd.DataFrame(results, columns=[
                        "Grant No", "Title", "Awardee", "Org Unit",
                        "Program Area", "Amount", "Classification"
                    ])
                    n_results = len(df)
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
                    n_results = len(df)
                    show = df[["grant_no", "title", "awardee", "org_unit", "program_area", "amount_usd", "classification_band"]]
                    st.dataframe(show, use_container_width=True)
            rec = {
                "search_id": f"srch-{uuid.uuid4().hex[:12]}",
                "term": search_term,
                "search_type": "grants",
                "results": n_results,
                "execution_time_ms": int((time.perf_counter() - t0) * 1000),
                "user": st.session_state.get("email") or "unknown",
            }
            st.session_state.setdefault("search_history", []).append(rec)
            _persist_search(cursor, catalog, rec)
    
    with col2:
        st.markdown("#### Quick Filters")
        if st.button("📋 Clear search"):
            st.session_state["clear_exec_search"] = True
            st.rerun()


# -------------------------------
# RECENT ACTIVITY LOG
# -------------------------------
def render_activity_log(cursor=None, catalog: str = "onr_demo"):
    """Officer audit on this page: search + routing. Export history lives on Export."""
    st.markdown("### Officer activity")
    st.caption("Search and Accept / Defer on this console. Export history is on Export.")

    def _uc(sql: str) -> pd.DataFrame:
        if not cursor:
            return pd.DataFrame()
        try:
            cursor.execute(sql)
            cols = [str(d[0]).lower() for d in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=cols)
        except Exception:
            return pd.DataFrame()

    session_search = st.session_state.get("search_history") or []
    if session_search:
        st.markdown("#### This session (searches)")
        st.dataframe(pd.DataFrame(session_search), use_container_width=True, hide_index=True)

    searches = _uc(
        f"""
        SELECT created_at, user_email, search_type, search_params, results_count, execution_time_ms
        FROM `{catalog}`.`app`.search_history
        ORDER BY created_at DESC
        LIMIT 20
        """
    )
    st.markdown("#### Search audit (`app.search_history`)")
    if searches.empty:
        st.caption("No persisted searches yet.")
    else:
        st.dataframe(searches, use_container_width=True)

    routes = _uc(
        f"""
        SELECT created_at, grant_no, action, user_email, action_id
        FROM `{catalog}`.`app`.routing_log
        ORDER BY created_at DESC
        LIMIT 20
        """
    )
    st.markdown("#### Routing audit (`app.routing_log`)")
    if routes.empty:
        session_rt = st.session_state.get("routing_history") or []
        if session_rt:
            st.dataframe(pd.DataFrame(session_rt), use_container_width=True, hide_index=True)
        else:
            st.caption("No routing rows yet. Accept or Defer a flagged grant above.")
    else:
        st.dataframe(routes, use_container_width=True, hide_index=True)
