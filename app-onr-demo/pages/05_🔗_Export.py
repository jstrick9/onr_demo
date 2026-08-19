"""Export."""

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
from utils.ui import page_header, render_architecture
from utils.workspace_ops import render_page_links

set_page_config(page_title="Element 7 · Export | ONR Portfolio")
setup_sidebar()

page_header(
    "Element 7 · Interoperability",
    "Export & APIs",
    "Integrator view. Execute export and the live Statement API on this screen. History is below.",
)

init_user_session_state()
get_runtime_env()

app_root = Path(__file__).resolve().parent.parent
try:
    configs = read_yaml(str(app_root / "config" / "onr-conf.yaml"))
    onr_catalog = configs["schema"]["catalog"]
    onr_schema = "silver"
except Exception as e:
    st.error(f"Configuration error: {str(e)}")
    st.stop()

render_page_links("export", onr_catalog)

conn, cursor = get_connection()

st.markdown("### Bulk extract")
formats = render_export_options()
dataset_name, dataset_table = render_dataset_selection(cursor, onr_catalog, onr_schema)
filters = render_export_filters()
if dataset_table and formats:
    render_secure_export(cursor, onr_catalog, onr_schema, dataset_table, formats, filters)
else:
    st.caption("Select a dataset and at least one format.")

render_live_statement_api(cursor, onr_catalog)

with st.expander("History"):
    render_export_history(cursor, onr_catalog)
with st.expander("Schema"):
    render_schema_documentation()
with st.expander("Interoperability and Advana contract"):
    render_interoperability()
    render_api_documentation()

render_architecture("export")
