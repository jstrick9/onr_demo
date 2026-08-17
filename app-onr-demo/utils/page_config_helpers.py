"""Page configuration — sidebar, layout, and theme."""

from pathlib import Path
import html
import streamlit as st
from PIL import Image
from utils.user_helpers import get_current_user
from utils.ui import inject_theme

APP_ROOT = Path(__file__).resolve().parent.parent


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
        user = get_current_user() or {}
        who = html.escape(
            str(user.get("display_name") or user.get("email") or "Workspace session")
        )
        st.markdown(
            f"""
<div class="hud">
  <div class="hud-scan"></div>
  <div class="hud-row"><span class="hud-orb"></span> Link up</div>
  <div class="hud-row"><span class="hud-orb gold"></span> Console live</div>
  <div class="hud-user">{who}</div>
  <div class="hud-foot">UNCLASSIFIED // MOCK</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        logo = load_sidebar_logo()
        if logo:
            st.image(logo, use_container_width=True)


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
