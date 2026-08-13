"""
Page Configuration Helpers for ONR ITSS POC
Handles UI layout, sidebar configuration, and page settings.
"""

import os
from pathlib import Path
import numpy as np
import streamlit as st
from PIL import Image
from utils.user_helpers import get_current_user

# Resolve app root: utils/.. => app-onr-demo
APP_ROOT = Path(__file__).resolve().parent.parent


# -------------------------------
# UI HELPERS
# -------------------------------
def vertical_divider(height=260, color=(200, 200, 200), width=2):
    """Render a thin vertical bar as an image."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :] = color  # RGB
    st.image(arr, width=width)


# -------------------------------
# RESOURCE CACHING
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


@st.cache_data
def load_page_icon():
    """Load page icon with caching."""
    icon_path = APP_ROOT / "resources" / "images" / "onr_icon.png"
    if icon_path.exists():
        try:
            return Image.open(icon_path)
        except Exception:
            return None
    return None


# -------------------------------
# SIDEBAR CONFIGURATION
# -------------------------------
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
        st.caption("UC: `onr_demo.bronze` · `silver` · `gold` · `app`")
        
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
    """Configure page settings."""
    if page_icon is None:
        page_icon = load_page_icon()
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
