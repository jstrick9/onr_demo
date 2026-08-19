"""Infrastructure — live inventory."""

from pathlib import Path

import streamlit as st
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.workspace_names import SQL_WAREHOUSE_NAME, ALL_PURPOSE_CLUSTER_NAME, ML_CLUSTER_NAME
from utils.ui import page_header, render_architecture, fit_metrics, provenance_note
from utils.workspace_ops import render_page_links
from utils.mission_themes import render_mission_ribbon, theme_chip
from utils.infra_estate import render_estate, render_bundle, bundle_excerpt

set_page_config(page_title="Element 2 · Infrastructure | ONR Portfolio")
setup_sidebar()

page_header(
    "Element 2 · Inventory",
    "Infrastructure",
    "Live estate and the Asset Bundle that manages volumes, this app, the paused file-arrival job, and the SDP pipeline. Warehouse and clusters are pre-existing. There is no deploy control here.",
)
render_mission_ribbon("infrastructure")
render_page_links("infrastructure", "onr_demo")

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

theme_chip("recover", "infrastructure", "inventory")
render_estate()
fit_metrics(
    [
        ("Catalog", onr_catalog),
        ("UC tables", f"{n_tables}" if n_tables is not None else "—"),
        ("Warehouse", SQL_WAREHOUSE_NAME),
        ("Cluster", ALL_PURPOSE_CLUSTER_NAME),
        ("Score cluster", ML_CLUSTER_NAME),
    ]
)
provenance_note("app inventory", onr_catalog)
if cursor and not uc_ok:
    st.caption("Warehouse is up but information_schema was not readable.")
elif not cursor:
    st.caption("Warehouse not connected — inventory below is the intended deployment.")

render_bundle()

tab1, tab2, tab3 = st.tabs(["Inventory", "Identity", "Full bundle"])

with tab1:
    st.markdown("#### Workspace objects")
    st.dataframe(
        [
            {"kind": "SQL warehouse", "name": SQL_WAREHOUSE_NAME, "role": "App and SQL path · serverless"},
            {"kind": "Cluster", "name": ALL_PURPOSE_CLUSTER_NAME, "role": "Night-before 04 / 04b · your Dedicated cluster"},
            {"kind": "Cluster", "name": ML_CLUSTER_NAME, "role": "Score 04c · Dedicated to the app SP"},
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

with tab2:
    theme_chip("boundary", "infrastructure", "identity")
    st.caption(
        "The signed-in IdP session is on Home → Access. "
        "This app authenticates as its own service principal. "
        "Warehouse access and catalog grants are scoped to that identity. "
        "Analysts read gold; they do not see bronze."
    )

with tab3:
    st.caption("Full bundle definition packaged next to the app, or the repo-root databricks.yml.")
    label, text = bundle_excerpt()
    st.caption(f"Source · {label}")
    dab_candidates = [
        app_root / "config" / "databricks.yml",
        app_root.parent / "databricks.yml",
    ]
    dab = next((p for p in dab_candidates if p.exists()), None)
    st.code(dab.read_text() if dab else text, language="yaml")

render_architecture("infrastructure")
