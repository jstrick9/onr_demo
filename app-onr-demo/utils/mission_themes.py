"""Strategic-element chips — one compact strip at the top of each page."""

from __future__ import annotations

import html

import streamlit as st

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
            "portfolio": "Budget execution · AT_RISK · daily brief · Accept / Defer routing.",
        },
    },
    "boundary": {
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


def render_mission_ribbon(page: str) -> None:
    """One compact strip. Only themes that connect to this page."""
    themes = PAGE_THEMES.get(page) or ()
    if not themes:
        return
    chips = [
        '<div class="se-bar">',
        '<span class="se-label">Strategic Elements on this page</span>',
    ]
    for theme_id in themes:
        theme = THEMES[theme_id]
        artifact = (theme.get("on_page") or {}).get(page) or ""
        pop = (
            f'<div class="theme-title">{html.escape(theme["title"])}</div>'
            f'<div class="theme-body">{html.escape(theme["body"])}</div>'
        )
        if artifact:
            pop += f'<div class="theme-on">On this page · {html.escape(artifact)}</div>'
        pop += f'<div class="theme-letter">Theme ({html.escape(theme["letter"])})</div>'
        chips.append(
            f'<details class="se-chip">'
            f'<summary>{html.escape(theme["label"])}</summary>'
            f'<div class="se-pop">{pop}</div>'
            f"</details>"
        )
    chips.append("</div>")
    st.markdown("".join(chips), unsafe_allow_html=True)
