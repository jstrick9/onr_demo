"""
Database Helpers for ONR ITSS POC
Handles SQL Warehouse connections, queries, and data operations.
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import streamlit as st
from databricks import sql
from databricks.sdk import WorkspaceClient


# -------------------------------
# READ CONFIG FILES
# -------------------------------
def read_yaml(file_path: str):
    """Read and parse a YAML configuration file."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def _app_root() -> Path:
    """Get the application root directory."""
    return Path(__file__).resolve().parent.parent


def _get_env(default: str = "dev") -> str:
    """Get current environment from env var."""
    return os.getenv("ENVIRONMENT", default)


def _get_configs(dbx_env: str):
    """Load environment-specific configuration."""
    cfg_path = _app_root() / "config" / dbx_env / "onr-conf.yaml"

    if not cfg_path.exists():
        raise FileNotFoundError(f"Configuration file not found for environment: {dbx_env}")

    try:
        cfg = read_yaml(str(cfg_path))
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {e}")

    if "schema" not in cfg:
        raise KeyError("Missing required config section: schema")
    if "catalog" not in cfg["schema"]:
        raise KeyError("Missing required key: schema.catalog")

    return cfg


def _normalize_host(host: str | None) -> str | None:
    """Normalize Databricks host URL."""
    if not host:
        return None
    return host.replace("https://", "").replace("http://", "").rstrip("/")


# -------------------------------
# SQL VALUE ESCAPING
# -------------------------------
def sql_escape(value) -> str:
    """Escape a value for safe SQL string interpolation."""
    if value is None:
        return ""
    return str(value).replace("\\", "\\\\").replace("'", "''")


# -------------------------------
# TEMP MESSAGES
# -------------------------------
def show_temp_message(message_type, message, seconds=3):
    """Show a temporary message that disappears after specified seconds."""
    placeholder = st.empty()
    getattr(placeholder, message_type, placeholder.info)(message)
    time.sleep(seconds)
    placeholder.empty()


# -------------------------------
# DB CONNECTION WITH AUTO-RECONNECT
# -------------------------------
def _resolve_http_path_by_name(w: WorkspaceClient, name: str) -> str:
    """Resolve SQL Warehouse HTTP path by warehouse name."""
    matches = [wh for wh in w.warehouses.list() if (wh.name or "").strip() == name.strip()]
    if not matches:
        raise ValueError(f"No SQL Warehouse found with name '{name}'")
    if len(matches) > 1:
        ids = ", ".join(getattr(m, "id", "unknown") for m in matches)
        raise ValueError(f"Multiple SQL Warehouses match name '{name}'. Matches: {ids}")
    wh = matches[0]
    http_path = getattr(wh.odbc_params, "http_path", None) or getattr(wh.odbc_params, "path", None)
    if not http_path:
        raise ValueError(f"Warehouse '{name}' has no http_path")
    return http_path


def _create_fresh_connection():
    """
    Create a new SQL Warehouse connection.
    Uses the app's service principal (OAuth) for auth.
    """
    w = WorkspaceClient()

    host = _normalize_host(w.config.host)
    if not host:
        raise ValueError("Unable to determine Databricks host")

    wname = os.getenv("DATABRICKS_WAREHOUSE_NAME")
    if not wname:
        raise ValueError("DATABRICKS_WAREHOUSE_NAME environment variable not set")

    http_path = _resolve_http_path_by_name(w, wname)

    headers = w.config.authenticate()
    token = headers.get("Authorization", "").split(" ", 1)[-1]
    if not token:
        raise ValueError("Failed to obtain OAuth token from WorkspaceClient")

    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )


def _is_connection_alive(conn) -> bool:
    """Check if the connection is still valid with a lightweight query."""
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except Exception:
        return False


def _close_connection_safely(conn):
    """Close a connection without raising errors."""
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def get_connection(max_retries: int = 3, retry_delay_seconds: int = 2):
    """
    Get Databricks SQL Warehouse connection with auto-reconnect.
    Returns: (connection, cursor) tuple
    """
    cached_conn = st.session_state.get("_db_connection")

    if cached_conn is not None and _is_connection_alive(cached_conn):
        return cached_conn, cached_conn.cursor()

    if cached_conn is not None:
        _close_connection_safely(cached_conn)
        st.session_state.pop("_db_connection", None)

    status_placeholder = st.empty()

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            status_placeholder.info(f"🔄 Connecting to SQL Warehouse... (attempt {attempt}/{max_retries})")

            conn = _create_fresh_connection()

            if _is_connection_alive(conn):
                st.session_state["_db_connection"] = conn
                status_placeholder.empty()
                return conn, conn.cursor()
            else:
                raise ValueError("Connection created but health check failed")

        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = retry_delay_seconds * attempt
                status_placeholder.warning(f"⏳ Retrying in {wait_time}s... ({attempt}/{max_retries})")
                time.sleep(wait_time)

    status_placeholder.empty()
    st.warning(
        "SQL Warehouse unavailable — running in **fixture mode** using "
        "`grants_portfolio.json` (400 synthetic grants + derived ERP)."
    )
    with st.expander("🔍 Technical Details"):
        st.code(str(last_error))
    st.session_state["fixture_mode"] = True
    return None, None


def clear_connection_cache():
    """Manually clear the cached connection."""
    cached_conn = st.session_state.get("_db_connection")
    if cached_conn is not None:
        _close_connection_safely(cached_conn)
        st.session_state.pop("_db_connection", None)


# -------------------------------
# QUERY HELPERS
# -------------------------------
def execute_query(cursor, query: str, params: dict = None):
    """Execute a SQL query and return results."""
    try:
        if params:
            query = query.format(**params)
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Query execution failed: {str(e)}")
        return None


def execute_query_to_df(cursor, query: str, params: dict = None):
    """Execute a SQL query and return results as a pandas DataFrame."""
    import pandas as pd
    try:
        if params:
            query = query.format(**params)
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
    except Exception as e:
        st.error(f"Query execution failed: {str(e)}")
        return pd.DataFrame()


# -------------------------------
# SOURCE TABLE VALIDATION
# -------------------------------
def validate_source_tables(cursor, configs):
    """Verify source tables exist and contain data."""
    catalog = configs["schema"]["catalog"]
    schema = configs["schema"].get("schema", "dev")
    
    tables_to_check = [
        ("silver_grants", "Grants Data"),
        ("silver_financial", "Financial Data"),
    ]
    
    all_valid = True
    
    for table_name, display_name in tables_to_check:
        full_table = f"`{catalog}`.`{schema}`.{table_name}"
        try:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as record_count,
                    MAX(_ingest_time) as latest_update
                FROM {full_table}
                WHERE _is_active = true
            """)
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                st.success(f"✅ **{display_name}**: {result[0]:,} records | Last update: {result[1]}")
            else:
                st.warning(f"⚠️ **{display_name}**: Table exists but contains no active records")
                all_valid = False
                
        except Exception as e:
            st.error(f"❌ **{display_name}**: Table not found or query failed")
            with st.expander("Technical Details"):
                st.code(str(e))
            all_valid = False
    
    if not all_valid:
        st.info("💡 Run the mock data generator or pipeline to populate source tables.")
    
    return all_valid
