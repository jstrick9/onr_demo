"""Page configuration — sidebar, layout, and theme."""

from pathlib import Path
import streamlit as st
from PIL import Image
from utils.user_helpers import get_current_user
from utils.ui import inject_theme

APP_ROOT = Path(__file__).resolve().parent.parent
BASELINE_GRANT_COUNT = 400


def _render_grant_pulse() -> None:
    try:
        from utils.db_helpers import get_connection, read_yaml
        from utils.demo_actions import grant_count

        catalog = "onr_demo"
        try:
            cfg = read_yaml(str(APP_ROOT / "config" / "onr-conf.yaml"))
            catalog = cfg["schema"]["catalog"]
        except Exception:
            pass
        _conn, cursor = get_connection()
        n = grant_count(cursor, catalog)
        if n is None:
            st.caption("Active grants unavailable")
            return
        delta = int(n) - BASELINE_GRANT_COUNT
        st.metric(
            "Active grants",
            f"{int(n):,}",
            delta=(None if delta == 0 else f"{delta:+d}"),
        )
    except Exception:
        st.caption("Active grants unavailable")


@st.cache_data
def load_sidebar_logo():
    logo_path = APP_ROOT / "resources" / "images" / "onr_logo.png"
    if logo_path.exists():
        try:
            return Image.open(logo_path)
        except Exception:
            return None
    return None


def setup_sidebar():
    inject_theme()
    with st.sidebar:
        st.markdown("## ONR Portfolio")
        st.caption("Office of Naval Research · Code 08")
        st.caption("S&T grants and ERP")

        st.markdown("---")
        _render_grant_pulse()

        st.markdown("---")
        st.caption("Catalog `onr_demo`")
        st.caption("Warehouse `onr demo warehouse`")

        st.markdown("---")
        user = get_current_user()
        if user:
            st.markdown(
                f"**Signed in**  \n{user.get('display_name', user.get('email', 'Unknown'))}"
            )
        else:
            st.caption("Workspace identity")

        logo = load_sidebar_logo()
        if logo:
            st.markdown("---")
            st.image(logo, use_container_width=True)

        st.caption("UNCLASSIFIED // MOCK DATA")


def set_page_config(page_title=None, page_icon=None):
    if page_icon is None:
        page_icon = "⚓"
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": "ONR Portfolio — grants and ERP on Databricks.",
        },
    )
