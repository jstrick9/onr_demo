"""Export — filtered bulk extract and Statement Execution API."""

import streamlit as st
from pathlib import Path
from utils.page_config_helpers import setup_sidebar, set_page_config
from utils.runtime_env import get_runtime_env
from utils.db_helpers import get_connection, read_yaml
from utils.user_helpers import init_user_session_state
from utils.export_helpers import (
    render_export_options,
    render_dataset_selection,
    render_export_filters,
    render_secure_export,
    render_api_documentation,
    render_interoperability,
    render_export_history,
    render_schema_documentation,
)
from utils.api_helpers import render_live_statement_api

set_page_config(page_title="Export | ONR Portfolio")
setup_sidebar()

st.title("Export & APIs")
st.caption(
    "Filtered bulk export in CSV, JSON, or Parquet. Audit rows land in app.export_history. "
    "The live API is Databricks Statement Execution REST."
)

sso_user = init_user_session_state()
dbx_env = get_runtime_env()

app_root = Path(__file__).resolve().parent.parent
config_file = app_root / "config" / "onr-conf.yaml"

try:
    configs = read_yaml(str(config_file))
    onr_catalog = configs["schema"]["catalog"]
    onr_schema = "silver"
except Exception as e:
    st.error(f"Configuration error: {str(e)}")
    st.stop()

conn, cursor = get_connection()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Data Export",
    "API",
    "Interoperability",
    "Schema Docs",
    "Export History",
])

with tab1:
    formats = render_export_options()
    st.markdown("---")
    dataset_name, dataset_table = render_dataset_selection(cursor, onr_catalog, onr_schema)
    st.markdown("---")
    filters = render_export_filters()
    st.markdown("---")
    if dataset_table and formats:
        render_secure_export(cursor, onr_catalog, onr_schema, dataset_table, formats, filters)
    else:
        st.warning("Please select at least one export format and a dataset.")

with tab2:
    render_live_statement_api(cursor, onr_catalog)
    st.markdown("---")
    render_api_documentation()

with tab3:
    render_interoperability()

with tab4:
    render_schema_documentation()

with tab5:
    render_export_history(cursor, onr_catalog)

st.markdown("---")
with st.expander("How it works"):
    st.caption(
        "Filtered gold/silver query → TLS + export_history → CSV / JSON / Parquet. "
        "Live open API: POST /api/2.0/sql/statements on the same warehouse (OAuth). "
        "Open standards: Delta, CSV, JSON, Parquet, SQL, JDBC/ODBC, REST."
    )

st.markdown("### Security")
st.markdown(
    """
Exports use TLS to the warehouse, OAuth (short-lived tokens), and a row in
`app.export_history` (who, dataset, filter, count). Unity Catalog tags travel
with the table (`data_source=mock`). This workspace is unclassified mock data
on commercial AWS — not an IL5 cell.
    """
)
