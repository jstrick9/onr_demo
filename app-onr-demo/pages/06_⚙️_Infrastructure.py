"""Infrastructure — live inventory."""

from pathlib import Path

import streamlit as st
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.workspace_names import SQL_WAREHOUSE_NAME, ALL_PURPOSE_CLUSTER_NAME
from utils.ui import page_header, render_how_it_works

set_page_config(page_title="Infrastructure | ONR Portfolio")
setup_sidebar()

page_header(
    "Platform",
    "Infrastructure",
    "What is deployed in this workspace. The bundle does not create the warehouse or cluster.",
)

init_user_session_state()
get_runtime_env()

app_root = Path(__file__).resolve().parent.parent
try:
    configs = read_yaml(str(app_root / "config" / "onr-conf.yaml"))
    onr_catalog = configs["schema"]["catalog"]
except Exception as e:
    st.error(f"Configuration error: {e}")
    st.stop()

conn, cursor = get_connection()

uc_ok = False
n_tables = None
if cursor:
    try:
        cursor.execute(
            f"""
            SELECT COUNT(*) FROM system.information_schema.tables
            WHERE table_catalog = '{onr_catalog}'
              AND table_schema IN ('bronze','silver','gold','app')
            """
        )
        n_tables = int(cursor.fetchone()[0])
        uc_ok = True
    except Exception:
        uc_ok = False

c1, c2, c3, c4 = st.columns(4)
c1.metric("Catalog", onr_catalog)
c2.metric("UC tables", f"{n_tables}" if n_tables is not None else "—")
c3.metric("Warehouse", SQL_WAREHOUSE_NAME)
c4.metric("Cluster", ALL_PURPOSE_CLUSTER_NAME)
if cursor and not uc_ok:
    st.caption("Warehouse is up but information_schema was not readable.")
elif not cursor:
    st.caption("Warehouse not connected — inventory below is the intended deployment.")

tab1, tab2 = st.tabs(["Inventory", "Bundle"])

with tab1:
    st.markdown("#### Workspace objects")
    st.dataframe(
        [
            {"kind": "SQL warehouse", "name": SQL_WAREHOUSE_NAME, "role": "App and SQL path · serverless"},
            {"kind": "Cluster", "name": ALL_PURPOSE_CLUSTER_NAME, "role": "Streaming and model jobs"},
            {"kind": "App", "name": "onr-demo-poc", "role": "This console · source app-onr-demo/"},
            {"kind": "Catalog", "name": onr_catalog, "role": "Unity Catalog · mock data"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Unity Catalog")
    st.dataframe(
        [
            {"schema": "bronze", "objects": "grants, financial · volumes landing, checkpoints · grants_stream"},
            {"schema": "silver", "objects": "grants, financial · quality gates, _is_active"},
            {"schema": "gold", "objects": "summaries, budget, predictions, forecast, trends, anomalies"},
            {"schema": "app", "objects": "quality, lineage, search and export history, briefs"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Bundle-managed resources")
    st.dataframe(
        [
            {"resource": "volume", "name": f"{onr_catalog}.bronze.landing", "state": "managed"},
            {"resource": "volume", "name": f"{onr_catalog}.bronze.checkpoints", "state": "managed"},
            {"resource": "app", "name": "onr-demo-poc", "state": "source ./app-onr-demo"},
            {"resource": "job", "name": "onr-demo-grants-file-arrival", "state": "paused · file arrival"},
            {"resource": "pipeline", "name": "onr-demo-grants-stream", "state": "SDP · bronze.grants_stream"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Identity")
    st.caption(
        "This app authenticates as its own service principal. "
        "Warehouse access and catalog grants are scoped to that identity. "
        "Analysts read gold; they do not see bronze."
    )

with tab2:
    st.caption("Databricks Asset Bundle — volumes, app, paused file-arrival job, SDP pipeline.")
    dab_candidates = [
        app_root / "config" / "databricks.yml",
        app_root.parent / "databricks.yml",
    ]
    dab = next((p for p in dab_candidates if p.exists()), None)
    if dab:
        st.code(dab.read_text(), language="yaml")
    else:
        st.caption("Bundle definition is not packaged next to the app.")

render_how_it_works(
    "How this workspace is assembled",
    [
        {"name": "Compute", "detail": "Existing warehouse and cluster — not created by the bundle."},
        {"name": "Bundle", "detail": "Volumes, this app, paused file-arrival, SDP pipeline."},
        {"name": "Catalog", "detail": "onr_demo bronze → silver → gold → app."},
        {"name": "Identity", "detail": "App service principal, short-lived OAuth, least privilege."},
    ],
)
