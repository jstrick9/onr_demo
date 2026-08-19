"""Operating themes — only the chips that connect to the current page.

Chips use operator names. Official prompt letters live only inside the
popover footer. Copy is operator rationale plus this page's live artifact.
"""

from __future__ import annotations

import html

import streamlit as st

THEME_ORDER = ("coexist", "budget", "boundary", "recover", "vendor")

PAGE_LABEL = {
    "home": "Home",
    "infrastructure": "Infrastructure",
    "ingestion": "Ingestion",
    "catalog": "Catalog",
    "analytics": "Analytics",
    "portfolio": "Portfolio",
    "export": "Export",
}

# Themes that have a live artifact on this page. Nothing else is rendered.
PAGE_THEMES: dict[str, tuple[str, ...]] = {
    "home": ("boundary",),
    "infrastructure": ("recover", "boundary"),
    "ingestion": ("coexist", "recover"),
    "catalog": ("vendor", "boundary"),
    "analytics": ("budget",),
    "portfolio": ("budget", "vendor"),
    "export": ("coexist", "boundary", "vendor"),
}

THEMES: dict[str, dict] = {
    "coexist": {
        "id": "coexist",
        "label": "Coexist",
        "letter": "a",
        "title": "Legacy coexistence",
        "body": (
            "Legacy ETL and this console write the same bronze table. "
            "New files land on the Unity Catalog Volume, not a DBFS mount. "
            "Rollback is delete-the-batch, not rewrite-the-estate."
        ),
        "on_page": {
            "ingestion": "Inbound files and Start stream write the same bronze.grants table.",
            "export": "CSV, JSON, Parquet — the portal keeps consuming gold until it is retired.",
        },
    },
    "budget": {
        "id": "budget",
        "label": "Budget",
        "letter": "b",
        "title": "Budget formulation",
        "body": (
            "Financial execution is a first-class feed — ERP lines sit next to the grants. "
            "Three models on this portfolio: Fund / Review / Defer, anomaly flags, and an OLS forecast. "
            "Protect ON_TARGET. Move dollars off AT_RISK and TREND-DECLINE."
        ),
        "on_page": {
            "analytics": "Scores strip · Resource action · gold.grant_predictions.",
            "portfolio": "AT_RISK rows · daily brief · Accept / Defer routing.",
        },
    },
    "boundary": {
        "id": "boundary",
        "label": "Boundary",
        "letter": "c",
        "title": "Least-privilege boundary",
        "body": (
            "Three planes, same identity. This app has its own service principal. "
            "Unity Catalog is the data-plane firewall — analysts SELECT gold, they never see bronze. "
            "This cell is unclassified mock on commercial AWS. IL5 is the GovCloud target, not this workspace."
        ),
        "on_page": {
            "home": "Access strip — signed-in IdP user. The app principal is a different identity.",
            "infrastructure": "Identity tab · App SP · warehouse · cluster. Analysts never see bronze.",
            "catalog": "Access policies — gold SELECT. Tags travel with the table.",
            "export": "Statement API · OAuth · app.export_history.",
        },
    },
    "recover": {
        "id": "recover",
        "label": "Recover",
        "letter": "d",
        "title": "Recoverable serving path",
        "body": (
            "Landing is durable object storage. RPO is the previous Delta version — "
            "time travel, not a backup truck. The warehouse is serverless; the app is already deployed. "
            "An annual exercise clones gold. We do not take this console down."
        ),
        "on_page": {
            "ingestion": "Delta time travel · landing Volume. Do not restore on camera.",
            "infrastructure": "Paused file-arrival job · databricks.yml · serverless warehouse.",
        },
    },
    "vendor": {
        "id": "vendor",
        "label": "Vendor",
        "letter": "e",
        "title": "Licensed feed",
        "body": (
            "Every external feed is a licensed product — owner, renewal date, quality SLO. "
            "A lapsed subscription shows up as a timeliness drop, not a blank dashboard. "
            "Last-good gold stays. We do not auto-delete."
        ),
        "on_page": {
            "catalog": "vendor · license_id · renewal_date tags · quality scores.",
            "portfolio": "Search writes app.search_history — the usage meter.",
            "export": "History writes app.export_history — the renewal meter.",
        },
    },
}


def page_has_theme(page: str, theme_id: str) -> bool:
    return theme_id in PAGE_THEMES.get(page, ())


def _body_html(theme: dict, page: str) -> str:
    artifact = (theme.get("on_page") or {}).get(page) or ""
    on_page = (
        f'<div class="theme-on">On this page · {html.escape(artifact)}</div>'
        if artifact
        else ""
    )
    return (
        f'<div class="theme-title">{html.escape(theme["title"])}</div>'
        f'<div class="theme-body">{html.escape(theme["body"])}</div>'
        f"{on_page}"
        f'<div class="theme-letter">Theme ({html.escape(theme["letter"])})</div>'
    )


def _open_popover(theme: dict, page: str, key: str, wide: bool = False) -> None:
    with st.popover(theme["label"], use_container_width=wide, key=key):
        st.markdown(_body_html(theme, page), unsafe_allow_html=True)


def theme_chip(theme_id: str, page: str, slot: str = "chip") -> None:
    """One click-to-open chip next to a live artifact. No-op if it does not apply."""
    if not page_has_theme(page, theme_id):
        return
    theme = THEMES[theme_id]
    st.markdown('<div class="mission-pri"></div>', unsafe_allow_html=True)
    _open_popover(theme, page, key=f"mt_{page}_{theme_id}_{slot}", wide=False)


def themed_heading(title: str, theme_id: str, page: str, slot: str | None = None) -> None:
    """Section title with the matching theme chip on the right."""
    if not page_has_theme(page, theme_id):
        st.markdown(f"### {title}")
        return
    left, right = st.columns([5.4, 1.15])
    with left:
        st.markdown(f"### {title}")
    with right:
        theme_chip(theme_id, page, slot or title.lower().replace(" ", "_"))


def render_mission_ribbon(page: str) -> None:
    """Chips that connect to this page only."""
    themes = PAGE_THEMES.get(page) or ()
    if not themes:
        return
    st.markdown(
        '<div class="mission-kicker">On this page</div>',
        unsafe_allow_html=True,
    )
    if len(themes) == 1:
        theme_chip(themes[0], page, "ribbon")
        return
    cols = st.columns(len(themes), gap="small")
    for col, theme_id in zip(cols, themes):
        theme = THEMES[theme_id]
        with col:
            st.markdown('<div class="mission-pri"></div>', unsafe_allow_html=True)
            _open_popover(theme, page, key=f"mt_{page}_{theme_id}_ribbon", wide=True)
