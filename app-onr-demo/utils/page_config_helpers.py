"""Page configuration — sidebar, layout, and theme."""

from pathlib import Path
import base64
import html
import streamlit as st
from PIL import Image
from utils.user_helpers import get_current_user
from utils.ui import inject_theme

APP_ROOT = Path(__file__).resolve().parent.parent
COMPASS_ICON = APP_ROOT / "resources" / "images" / "compass_icon.png"

_COMPASS_SVG = """<svg class="hud-compass" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="32" cy="32" r="30" fill="#0b1f3a" stroke="#f59e0b" stroke-width="3"/>
  <circle cx="32" cy="32" r="24" fill="none" stroke="#b45309" stroke-width="1.2"/>
  <polygon points="32,10 36.8,32 32,29 27.2,32" fill="#f59e0b"/>
  <polygon points="32,54 36.8,32 32,35 27.2,32" fill="#b45309"/>
  <polygon points="54,32 32,36.8 35,32 32,27.2" fill="#e8d5a3"/>
  <polygon points="10,32 32,36.8 29,32 32,27.2" fill="#e8d5a3"/>
  <circle cx="32" cy="32" r="3.2" fill="#f59e0b"/>
  <circle cx="32" cy="32" r="1.2" fill="#0b1f3a"/>
  <text x="32" y="16" text-anchor="middle" fill="#f59e0b" font-size="7" font-weight="800" font-family="Segoe UI, sans-serif">N</text>
</svg>"""


@st.cache_data
def load_sidebar_logo():
    """Optional agency mark. The Compass lockup is rendered in the HUD."""
    logo_path = APP_ROOT / "resources" / "images" / "onr_logo.png"
    if logo_path.exists():
        try:
            return Image.open(logo_path)
        except Exception:
            return None
    return None


def _compass_img_html() -> str:
    if COMPASS_ICON.exists():
        uri = "data:image/png;base64," + base64.b64encode(COMPASS_ICON.read_bytes()).decode("ascii")
        return f'<img class="hud-compass" src="{uri}" alt="" width="36" height="36"/>'
    return _COMPASS_SVG


def _apply_streamlit_logo() -> None:
    """Native Streamlit chrome — rose only. Wordmark lives in the HUD lockup."""
    if not COMPASS_ICON.exists():
        return
    try:
        st.logo(str(COMPASS_ICON), icon_image=str(COMPASS_ICON))
    except TypeError:
        try:
            st.logo(str(COMPASS_ICON))
        except Exception:
            pass
    except Exception:
        pass


def setup_sidebar():
    inject_theme()
    _apply_streamlit_logo()
    with st.sidebar:
        user = get_current_user() or {}
        who = html.escape(
            str(user.get("display_name") or user.get("email") or "Workspace session")
        )
        app_name = html.escape(
            str(
                __import__("os").getenv("DATABRICKS_APP_NAME")
                or "onr-demo-poc"
            )
        )
        st.markdown(
            f"""
<div class="hud">
  <div class="hud-brand">
    {_compass_img_html()}
    <div>
      <div class="hud-word">Compass</div>
      <div class="hud-sub">ONR · Code 08</div>
    </div>
  </div>
  <div class="hud-row"><span class="hud-orb"></span> IdP session</div>
  <div class="hud-row"><span class="hud-orb gold"></span> Console live</div>
  <div class="hud-user">{who}</div>
  <div class="hud-foot">App SP · {app_name} · not your token</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        logo = load_sidebar_logo()
        if logo:
            st.image(logo, use_container_width=True)


def set_page_config(page_title=None, page_icon=None):
    if page_icon is None:
        page_icon = str(COMPASS_ICON) if COMPASS_ICON.exists() else "🧭"
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": "Project Compass — ONR Portfolio grants and ERP on Databricks.",
        },
    )
