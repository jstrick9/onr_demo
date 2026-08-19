"""ONR Portfolio — Home."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml, validate_source_tables
from utils.user_helpers import init_user_session_state
from utils.ui import page_header, capability_cards, render_architecture
from utils.workspace_ops import render_page_links

set_page_config(page_title="ONR Portfolio | Compass")
setup_sidebar()

page_header(
    "ONR · Code 08",
    "ONR Portfolio",
    "Self-service grants and ERP on catalog onr_demo. Data path is Elements 3–7. Infrastructure is a glance. Secure access is the companion tape.",
)
render_page_links("home", "onr_demo")
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
    from utils.ui import provenance_note

    last = st.session_state.get("last_ingest") or {}
    stream = st.session_state.get("last_stream") or {}
    if last.get("before") is None and stream.get("before_silver") is not None:
        last = {**last, "before": stream.get("before_silver")}
    grant_delta = None
    if last.get("before") is not None and n_grants is not None:
        try:
            grant_delta = f"{int(n_grants) - int(last['before']):+d}"
        except (TypeError, ValueError):
            grant_delta = None
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active grants", f"{int(n_grants or 0):,}", delta=grant_delta)
    c2.metric("Portfolio", f"${float(total or 0)/1e6:.1f}M")
    c3.metric("ERP lines", f"{int(n_fin or 0):,}")
    c4.metric("Execution", f"{float(exe or 0):.1f}%")
    provenance_note("silver.grants", onr_catalog)
except Exception:
    from utils.portfolio_data import portfolio_kpis

    k = portfolio_kpis()
    from utils.ui import provenance_note

    a, b, c, d = st.columns(4)
    a.metric("Active grants", f"{k['grant_count']:,}")
    b.metric("Portfolio", f"${k['total_funding']/1e6:.1f}M")
    c.metric("ERP lines", f"{k['transaction_count']:,}")
    d.metric("Execution", f"{k['execution_rate']:.1f}%")
    provenance_note("silver.grants", onr_catalog, via="fixture")
    st.caption("Showing the packaged portfolio while the warehouse is unavailable.")

st.markdown("")
render_architecture("home")

capability_cards(
    [
        {"title": "Element 2 · Infrastructure", "body": "Deployed catalog, compute, and bundle inventory. Companion tape."},
        {"title": "Element 3 · Ingestion", "body": "Land files, apply quality gates, refresh silver and gold."},
        {"title": "Element 4 · Catalog", "body": "Registry, health scores, lineage, and classification tags."},
        {"title": "Element 5 · Analytics", "body": "Fund / Review / Defer, anomaly queue, FY forecast, drift, and trend IDs."},
        {"title": "Element 6 · Portfolio", "body": "Search, filter, daily brief, and AT_RISK execution."},
        {"title": "Element 7 · Export", "body": "CSV, JSON, Parquet, and Statement Execution API."},
    ]
)

with st.expander("Source tables"):
    if cursor:
        validate_source_tables(cursor, configs)
    else:
        st.caption("Connect the SQL warehouse to validate Unity Catalog tables.")
