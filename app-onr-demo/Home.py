"""ONR ITSS POC — Home (60-second opener)."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml, validate_source_tables
from utils.user_helpers import init_user_session_state
from utils.workspace_names import SQL_WAREHOUSE_NAME, ALL_PURPOSE_CLUSTER_NAME

set_page_config(page_title="Home | ONR ITSS POC Demo")
setup_sidebar()

st.title("ONR ITSS Proof of Concept")
st.caption("Office of Naval Research — Code 08 · Elements 3–7 · mock / synthetic data only")

st.markdown(
    """
### The story (say this first)

A new S&T grants file lands. **Auto Loader** picks it up. **Quality gates** drop bad rows.
**Gold** KPIs refresh. Leadership **searches, models, and exports** in open formats —
without recoding the pipeline.
"""
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

c1, c2, c3, c4 = st.columns(4)
c1.info("**Catalog**  \nonr_demo")
c2.info("**Medallion**  \nbronze · silver · gold · app")
c3.info(f"**SQL**  \n`{SQL_WAREHOUSE_NAME}`")
c4.info(f"**Notebooks**  \n`{ALL_PURPOSE_CLUSTER_NAME}`")

st.markdown("### Start here")
st.markdown(
    """
| Order | Page | Element | Click this |
|-------|------|---------|------------|
| 1 | **Ingestion** | 3 | **Drop live file (8 grants)** — watch 400 → 408 |
| 2 | **Governance** | 4 | Catalog, quality, lineage |
| 3 | **Analytics** | 5 | Decision aids + optional MLflow on the cluster |
| 4 | **Dashboard** | 6 | Filter / search `quantum` |
| 5 | **Integration** | 7 | Export CSV · JSON · Parquet |
"""
)

st.markdown("---")
st.markdown("### Live counts")

try:
    if not cursor:
        raise RuntimeError("no warehouse")
    cursor.execute(
        f"""
        SELECT 'Grants' d, COUNT(*) n, MAX(_ingest_time) t FROM `{onr_catalog}`.`silver`.grants WHERE _is_active
        UNION ALL
        SELECT 'Financial', COUNT(*), MAX(_ingest_time) FROM `{onr_catalog}`.`silver`.financial WHERE _is_active
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
    st.caption("SQL warehouse not connected — showing packaged Compass fixture.")

with st.expander("Source table check"):
    if cursor:
        validate_source_tables(cursor, configs)
    else:
        st.warning(f"Connect `{SQL_WAREHOUSE_NAME}` for live UC tables. App still runs on fixture data.")

st.caption("UNCLASSIFIED // MOCK DATA — no CUI, PII, or classified information.")
