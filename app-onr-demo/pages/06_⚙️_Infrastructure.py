"""Infrastructure — IaC inventory and operator runbook."""

from pathlib import Path

import streamlit as st
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.workspace_names import SQL_WAREHOUSE_NAME, ALL_PURPOSE_CLUSTER_NAME

set_page_config(page_title="Infrastructure | ONR Portfolio")
setup_sidebar()

st.title("Infrastructure")
st.caption(
    "What is deployed, what the bundle owns, and the operator runbook. "
    "The DAB does not create the warehouse or cluster — those are existing workspace objects."
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

# Live catalog ping
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
    st.caption("Warehouse not connected — inventory below is still the intended deployment.")

st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "Inventory",
    "Bundle (DAB)",
    "Runbook",
    "How it works",
])

with tab1:
    st.markdown("### Workspace objects (created in the UI, not by the bundle)")
    st.dataframe(
        [
            {"kind": "SQL warehouse", "name": SQL_WAREHOUSE_NAME, "notes": "Serverless · app + SQL path"},
            {"kind": "All-purpose cluster", "name": ALL_PURPOSE_CLUSTER_NAME, "notes": "Notebooks 00–05, 01b, 04, 04b"},
            {"kind": "Databricks App", "name": "onr-demo-poc", "notes": "This Streamlit app · source app-onr-demo/"},
            {"kind": "Catalog", "name": onr_catalog, "notes": "Unity Catalog · mock data only"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Unity Catalog layout")
    st.dataframe(
        [
            {"schema": "bronze", "objects": "grants, financial · volumes landing, checkpoints · grants_stream (SDP)"},
            {"schema": "silver", "objects": "grants, financial (quality gates, _is_active)"},
            {"schema": "gold", "objects": "summaries, budget_execution, predictions, forecast, trends, anomalies"},
            {"schema": "app", "objects": "quality scores, lineage, search/export history, daily briefs"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Bundle-managed resources (`databricks bundle deploy -t poc`)")
    st.dataframe(
        [
            {"resource": "volume", "name": f"{onr_catalog}.bronze.landing", "state": "managed"},
            {"resource": "volume", "name": f"{onr_catalog}.bronze.checkpoints", "state": "managed"},
            {"resource": "app", "name": "onr-demo-poc", "state": "source ./app-onr-demo"},
            {"resource": "job", "name": "onr-demo-grants-file-arrival", "state": "PAUSED · file_arrival on landing/grants"},
            {"resource": "pipeline", "name": "onr-demo-grants-stream", "state": "triggered SDP · bronze.grants_stream"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Identity")
    st.markdown(
        """
The app authenticates as **its own service principal**, not the human who ran bootstrap.
After first deploy, run `sql/grant_app_principal.sql` (replace the placeholder) and grant
**CAN USE** on `onr demo warehouse` to that principal. `MANAGE` on the four schemas is a
POC concession so the app can `CREATE OR REPLACE` tables the bootstrap user owns — not
the production grant set.
        """
    )

with tab2:
    st.markdown("### Databricks Asset Bundle")
    st.caption("Slim DAB: volumes + app + paused file-arrival job + SDP pipeline. Does **not** create compute.")
    dab_candidates = [
        app_root / "config" / "databricks.yml",
        app_root.parent / "databricks.yml",
    ]
    dab = next((p for p in dab_candidates if p.exists()), None)
    if dab:
        st.code(dab.read_text(), language="yaml")
        st.caption(f"Loaded from `{dab}`")
    else:
        st.info("databricks.yml is not packaged next to the app. It lives at the repo root.")

    st.markdown("### Deploy")
    st.code(
        """# After 00_bootstrap has created schema bronze
databricks bundle deploy -t poc

# Then in Workflows:
#   onr-demo-grants-file-arrival  — leave PAUSED until you want the file-arrival beat
#   onr-demo-grants-stream        — Start to run the SDP sibling table
""",
        language="bash",
    )

with tab3:
    st.markdown("### Operator runbook")
    st.markdown(
        """
| Order | Action | Where |
|------:|--------|--------|
| 1 | Create warehouse `onr demo warehouse` and cluster `onr demo cluster` | Compute UI |
| 2 | Clone this repo on `main` | Repos / Git folder |
| 3 | Run `notebooks/00_bootstrap.py` | Cluster · expect 400 / 1,200 |
| 4 | Deploy app `onr-demo-poc` from `app-onr-demo/` | Apps |
| 5 | Run `sql/grant_app_principal.sql` + warehouse **CAN USE** | SQL editor |
| 6 | Night-before: `04` then `04b` on the cluster | RF + IsolationForest registered |
| 7 | On camera: `04c_score_registered_models.py` | Score 408 from UC models |
| 8 | Optional: `databricks bundle deploy -t poc` | CLI |

**Daily / demo loop**

1. Ingestion → Process **Live 8 grants** (400 → 408) or run `01b` for a live stream.
2. Catalog / Analytics / Portfolio / Export as needed.
3. Ingestion → Reset (or `notebooks/05_reset_demo.py`) back to 400.
4. If you trained 04 / 04b, re-run them after a Process if you want RF / IsolationForest scores instead of heuristics.
        """
    )
    st.markdown("### Notebooks")
    st.dataframe(
        [
            {"notebook": "00_bootstrap.py", "role": "Create UC + load 400 / 1,200 + stage CSVs"},
            {"notebook": "01_bronze_ingestion.py", "role": "Auto Loader availableNow"},
            {"notebook": "01b_streaming_autoloader.py", "role": "Auto Loader processingTime 30s (auto-stops)"},
            {"notebook": "02_silver_quality.py", "role": "Dedupe, gates, quality scores"},
            {"notebook": "03_gold_aggregation.py", "role": "Gold + OLS forecast + trend IDs"},
            {"notebook": "04_mlflow_grant_model.py", "role": "RF large-award → UC registry"},
            {"notebook": "04b_funding_anomaly.py", "role": "IsolationForest → champion alias"},
            {"notebook": "05_reset_demo.py", "role": "Cluster reset to seed + clear checkpoints"},
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab4:
    st.markdown("### How it works")
    st.code(
        """
+-----------------------------------------------------------------------+
|                     Platform (this workspace)                         |
+-----------------------------------------------------------------------+
|                                                                       |
|  UI-created (not in the DAB)                                          |
|    warehouse "onr demo warehouse"     cluster "onr demo cluster"      |
|                                                                       |
|  databricks bundle deploy -t poc                                      |
|    volumes landing + checkpoints                                      |
|    app onr-demo-poc                                                   |
|    job  onr-demo-grants-file-arrival  (PAUSED, file_arrival)          |
|    SDP  onr-demo-grants-stream        (bronze.grants_stream)          |
|                                                                       |
|  Unity Catalog onr_demo                                               |
|    bronze -> silver -> gold -> app                                    |
|    models: grant_large_award , funding_anomaly_detector @ champion    |
|                                                                       |
|  This app reads/writes through the warehouse as the app SP.           |
+-----------------------------------------------------------------------+
        """.strip(),
        language="text",
    )

st.caption("UNCLASSIFIED // MOCK DATA — no CUI / PII.")
