"""
Page configuration — sidebar, layout, and page settings.
"""

from pathlib import Path
import streamlit as st
from PIL import Image
from utils.user_helpers import get_current_user

APP_ROOT = Path(__file__).resolve().parent.parent
SEED_GRANT_COUNT = 400


def _render_grant_pulse() -> None:
    """Sticky 400 → 408 readout. Visible on every page."""
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
            st.caption("Active grants — warehouse not connected")
            return
        delta = int(n) - SEED_GRANT_COUNT
        st.metric(
            "Active grants",
            f"{int(n):,}",
            delta=("seed" if delta == 0 else f"{delta:+d} vs seed"),
        )
    except Exception:
        st.caption("Active grants — unavailable")


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
    """Sidebar for the self-service portfolio tool."""
    with st.sidebar:
        st.markdown("## ONR Portfolio")
        st.caption("Office of Naval Research · Code 08")
        st.caption("S&T grants and ERP — mock data")

        st.markdown("---")
        st.markdown("### Navigate")
        st.markdown(
            """
- **Home** — portfolio status
- **Ingestion** — land files, quality, reset
- **Catalog** — registry, scores, lineage
- **Analytics** — scores, anomalies, forecast
- **Portfolio** — search, brief, flags
- **Export** — CSV / JSON / Parquet, APIs
- **Infrastructure** — IaC, compute, runbook
            """
        )

        st.markdown("---")
        _render_grant_pulse()

        st.markdown("---")
        st.markdown("### Environment")
        st.caption("Catalog `onr_demo` · bronze / silver / gold / app")
        st.caption("SQL `onr demo warehouse`")
        st.caption("Notebooks `onr demo cluster`")
        st.caption("App `onr-demo-poc`")

        st.markdown("---")
        user = get_current_user()
        if user:
            st.markdown(
                f"**Signed in**  \n{user.get('display_name', user.get('email', 'Unknown'))}"
            )
        else:
            st.caption("Signed in via workspace SSO when running as a Databricks App.")

        st.markdown("---")
        logo = load_sidebar_logo()
        if logo:
            st.image(logo, use_container_width=True)

        st.caption("UNCLASSIFIED // MOCK DATA — no CUI / PII")


def set_page_config(page_title=None, page_icon=None):
    """Must be the first Streamlit command on the page."""
    if page_icon is None:
        page_icon = "⚓"

    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": "mailto:onr-demo@company.com?subject=ONR%20Portfolio%20Help",
            "Report a bug": "mailto:onr-demo@company.com?subject=ONR%20Portfolio%20Bug",
            "About": "ONR Portfolio — self-service grants & ERP on Databricks (mock data).",
        },
    )
