"""ONR Portfolio — Home."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml, validate_source_tables
from utils.user_helpers import init_user_session_state
from utils.ui import page_header, capability_cards, render_architecture

set_page_config(page_title="Home | ONR Portfolio")
setup_sidebar()

page_header(
    "Office of Naval Research · Code 08",
    "ONR Portfolio",
    "Self-service grants and ERP on catalog onr_demo.",
)
st.markdown(
    '<span class="unclass-chip">UNCLASSIFIED // MOCK DATA</span>',
    unsafe_allow_html=True,
)

sso_user = init_user_session_state()
st.session_state["dbx_env"] = get_runtime_env()

app_root = Path(__file__).resolve().parent
try:
    configs = read_yaml(str(app_root / "config" / "onr-conf.yaml"))
    onr_catalog = configs["schema"]["catalog"]
    st.session_state["onr_configs"] = configs
except Exception as e:
    st.error(f"Configuration error: {e}")
    st.stop()

conn, cursor = get_connection()
st.session_state["onr_conn"] = conn
st.session_state["onr_cursor"] = cursor

st.markdown("")

try:
    if not cursor:
        raise RuntimeError("no warehouse")
    cursor.execute(
        f"""
        SELECT COUNT(*), SUM(amount_usd), COUNT(DISTINCT awardee)
        FROM `{onr_catalog}`.`silver`.grants WHERE _is_active
        """
    )
    n_grants, total, awardees = cursor.fetchone()
    cursor.execute(
        f"""
        SELECT COUNT(*), SUM(actual_expenditure) / NULLIF(SUM(budget_allocated), 0) * 100
        FROM `{onr_catalog}`.`silver`.financial WHERE _is_active
        """
    )
    n_fin, exe = cursor.fetchone()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active grants", f"{int(n_grants or 0):,}")
    c2.metric("Portfolio", f"${float(total or 0)/1e6:.1f}M")
    c3.metric("ERP lines", f"{int(n_fin or 0):,}")
    c4.metric("Execution", f"{float(exe or 0):.1f}%")
except Exception:
    from utils.portfolio_data import portfolio_kpis

    k = portfolio_kpis()
    a, b, c, d = st.columns(4)
    a.metric("Active grants", f"{k['grant_count']:,}")
    b.metric("Portfolio", f"${k['total_funding']/1e6:.1f}M")
    c.metric("ERP lines", f"{k['transaction_count']:,}")
    d.metric("Execution", f"{k['execution_rate']:.1f}%")
    st.caption("Showing the packaged portfolio while the warehouse is unavailable.")

st.markdown("")
render_architecture("home")

capability_cards(
    [
        {"title": "Ingestion", "body": "Land files, apply quality gates, refresh silver and gold."},
        {"title": "Catalog", "body": "Registry, health scores, lineage, and classification tags."},
        {"title": "Analytics", "body": "Fund / Review / Defer, anomaly queue, FY forecast and trend IDs."},
        {"title": "Portfolio", "body": "Search, filter, daily brief, and AT_RISK execution."},
        {"title": "Export", "body": "CSV, JSON, Parquet, and Statement Execution API."},
        {"title": "Infrastructure", "body": "Deployed catalog, compute, and bundle inventory."},
    ]
)

with st.expander("Source tables"):
    if cursor:
        validate_source_tables(cursor, configs)
    else:
        st.caption("Connect the SQL warehouse to validate Unity Catalog tables.")
