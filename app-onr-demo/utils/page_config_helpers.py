"""
Page Configuration Helpers for ONR ITSS POC
Handles UI layout, sidebar configuration, and page settings.
"""

from pathlib import Path
import streamlit as st
from PIL import Image
from utils.user_helpers import get_current_user

# Resolve app root: utils/.. => app-onr-demo
APP_ROOT = Path(__file__).resolve().parent.parent


# -------------------------------
# UI HELPERS
# -------------------------------
@st.cache_data
def load_sidebar_logo():
    """Load sidebar logo image with caching."""
    logo_path = APP_ROOT / "resources" / "images" / "onr_logo.png"
    if logo_path.exists():
        try:
            return Image.open(logo_path)
        except Exception:
            return None
    return None


def setup_sidebar():
    """Configure sidebar with navigation, logo, and user info."""
    with st.sidebar:
        # App title
        st.markdown("## 🚢 ONR ITSS POC")
        st.caption("Office of Naval Research")
        st.caption("Code 08 IT Support Services")
        
        st.markdown("---")
        
        # Navigation info
        st.markdown("### 📑 Navigation")
        st.markdown(
            """
            - 🏠 **Home** — Overview
            - 🔍 **Ingestion** — Element 3
            - 📊 **Governance** — Element 4
            - 🤖 **Analytics** — Element 5
            - 📈 **Dashboard** — Element 6
            - 🔗 **Integration** — Element 7
            """
        )
        
        st.markdown("---")
        
        # Environment indicator
        st.markdown("### Environment: 🟢 POC")
        st.caption("UC: `onr_demo` · bronze / silver / gold / app")
        st.caption("SQL: `onr demo warehouse`")
        st.caption("Notebooks: `onr demo cluster`")
        
        st.markdown("---")
        
        # Logged-in user (from SSO headers)
        user = get_current_user()
        if user:
            st.markdown(
                f"#### 👤 **Logged in as:**  \n{user.get('display_name', user.get('email', 'Unknown'))}"
            )
        else:
            st.markdown("#### 👤 **User:** Demo Mode")
        
        st.markdown("---")
        
        # Sidebar Logo
        logo = load_sidebar_logo()
        if logo:
            st.image(logo, use_container_width=True)
        else:
            st.markdown("### 🏛️ ONR ITSS")
        
        # Footer
        st.markdown("---")
        st.caption("🔒 Mock data only — No CUI/PII")


# -------------------------------
# WEBPAGE & MENU CONFIGURATION
# -------------------------------
def set_page_config(page_title=None, page_icon=None):
    """Configure page settings.

    Must be the first Streamlit command. Do not call @st.cache_data helpers
    here — that counts as a command and raises StreamlitAPIException.
    """
    if page_icon is None:
        page_icon = "🚢"

    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": "mailto:onr-demo@company.com?subject=ONR%20Demo%20Help",
            "Report a bug": "mailto:onr-demo@company.com?subject=ONR%20Demo%20Bug%20Report",
            "About": "ONR ITSS POC — Technical Demonstration Elements 3–7 v1.0",
        },
    )
