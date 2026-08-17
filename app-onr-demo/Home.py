"""ONR Portfolio — Home."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml, validate_source_tables
from utils.user_helpers import init_user_session_state
from utils.workspace_names import SQL_WAREHOUSE_NAME, ALL_PURPOSE_CLUSTER_NAME

set_page_config(page_title="Home | ONR Portfolio")
setup_sidebar()

st.title("ONR Portfolio")
st.caption(
    "Self-service grants and ERP · catalog `onr_demo` · mock / synthetic data only"
)

sso_user = init_user_session_state()
dbx_env = get_runtime_env()
st.session_state["dbx_env"] = dbx_env

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

st.markdown("### Live counts")

try:
    if not cursor:
        raise RuntimeError("no warehouse")
    cursor.execute(
        f"""
        SELECT 'Grants' d, COUNT(*) n, MAX(_ingest_time) t
        FROM `{onr_catalog}`.`silver`.grants WHERE _is_active
        UNION ALL
        SELECT 'Financial', COUNT(*), MAX(_ingest_time)
        FROM `{onr_catalog}`.`silver`.financial WHERE _is_active
        """
    )
    stats = cursor.fetchall()
    cols = st.columns(len(stats))
    for i, (dataset, records, last_update) in enumerate(stats):
        cols[i].metric(dataset, f"{records:,}", delta=str(last_update) if last_update else None)
except Exception:
    from utils.portfolio_data import portfolio_kpis

    k = portfolio_kpis()
    a, b, c = st.columns(3)
    a.metric("Grants (fixture)", f"{k['grant_count']:,}")
    b.metric("Portfolio", f"${k['total_funding']/1e6:.1f}M")
    c.metric("ERP lines", f"{k['transaction_count']:,}")
    st.caption("SQL warehouse not connected — showing the packaged Compass fixture.")

c1, c2, c3, c4 = st.columns(4)
c1.info(f"**Catalog**  \n`{onr_catalog}`")
c2.info("**Layers**  \nbronze · silver · gold · app")
c3.info(f"**SQL**  \n`{SQL_WAREHOUSE_NAME}`")
c4.info(f"**Jobs**  \n`{ALL_PURPOSE_CLUSTER_NAME}`")

st.markdown("### What you can do")
st.markdown(
    """
| Page | Use it to |
|------|-----------|
| **Ingestion** | Land a grants file, inspect quality, reset to the 400-grant seed |
| **Catalog** | Browse Unity Catalog, health scores, and lineage |
| **Analytics** | Fund / Review / Defer scores, anomaly queue, FY forecast + trend IDs |
| **Portfolio** | Filter, search, generate a daily brief, review AT_RISK rows |
| **Export** | Download CSV / JSON / Parquet; call the Statement Execution API |
| **Infrastructure** | See what the DAB deploys, compute names, and the operator runbook |
    """
)

with st.expander("Source table check"):
    if cursor:
        validate_source_tables(cursor, configs)
    else:
        st.warning(
            f"Connect `{SQL_WAREHOUSE_NAME}` for live Unity Catalog tables. "
            "The app still runs on fixture data."
        )

st.caption("UNCLASSIFIED // MOCK DATA — no CUI, PII, or classified information.")
