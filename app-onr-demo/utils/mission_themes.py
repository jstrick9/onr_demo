"""Operating themes — product-native surface for the five 11.4 answers.

Chips use operator names. Official prompt letters live only inside the
popover footer. Copy is operator rationale, never the 11.4 quote.
"""

from __future__ import annotations

import html

import streamlit as st

THEME_ORDER = ("coexist", "budget", "boundary", "recover", "vendor")

PAGE_LABEL = {
    "home": "Home",
    "ingestion": "Ingestion",
    "catalog": "Catalog",
    "analytics": "Analytics",
    "portfolio": "Portfolio",
    "export": "Export",
    "infrastructure": "Infrastructure",
}

# Filled chips = this page is a primary proof. All five stay clickable.
PAGE_PRIMARY: dict[str, tuple[str, ...]] = {
    "home": (),
    "ingestion": ("coexist", "recover"),
    "catalog": ("vendor",),
    "analytics": ("budget",),
    "portfolio": ("budget",),
    "export": ("boundary", "coexist"),
    "infrastructure": ("recover", "boundary"),
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
        "primary_pages": ("ingestion", "export"),
        "on_page": {
            "home": "Same catalog from ingest through export.",
            "ingestion": "Landing Volume · bronze.grants — warehouse ingest and Auto Loader.",
            "catalog": "Silver and gold stay the serving contract while legacy reports catch up.",
            "analytics": "Models score the same silver the warehouse and the stream just wrote.",
            "portfolio": "Leadership reads gold — the same table JDBC reports already use.",
            "export": "CSV, JSON, Parquet — the portal keeps consuming gold until it is retired.",
            "infrastructure": "Volumes and the paused file-arrival job are the coexistence path.",
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
        "primary_pages": ("analytics", "portfolio"),
        "on_page": {
            "home": "Portfolio dollars and execution rate on the KPI row.",
            "ingestion": "Inbound grants become the portfolio the models will score.",
            "catalog": "gold.budget_execution and gold.grants_summary are registered here.",
            "analytics": "Scores strip · Resource action · gold.grant_predictions.",
            "portfolio": "AT_RISK rows · daily brief · Accept / Defer routing.",
            "export": "Filtered gold extract is what a budget workbook would consume.",
            "infrastructure": "Score cluster onr demo ml applies the registered models.",
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
        "primary_pages": ("export", "infrastructure"),
        "on_page": {
            "home": "HUD name is the signed-in user. The app principal is different.",
            "ingestion": "Warehouse path and Jobs run as the app, not your personal token.",
            "catalog": "Tags, grants, and gold-only analyst scope.",
            "analytics": "Score runs on a cluster dedicated to the app principal.",
            "portfolio": "Search writes app.search_history — continuous authorization, not a password file.",
            "export": "Statement API · OAuth · app.export_history.",
            "infrastructure": "App SP · warehouse · cluster. Analysts never see bronze.",
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
        "primary_pages": ("ingestion", "infrastructure"),
        "on_page": {
            "home": "Fixture mode is the degrade path if the warehouse is cold.",
            "ingestion": "Delta time travel · landing Volume. Do not restore on camera.",
            "catalog": "Last-good gold stays if a feed pauses.",
            "analytics": "Registered models rescore from this console after a restore.",
            "portfolio": "Last-good gold is what the officer still sees.",
            "export": "Re-run the same filtered extract after gold is rebuilt.",
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
        "primary_pages": ("catalog",),
        "on_page": {
            "home": "data_source=mock travels with the catalog.",
            "ingestion": "Quality gates and published-with-a-finding are the feed SLO.",
            "catalog": "vendor · license_id · renewal_date tags · quality scores.",
            "analytics": "A stale feed would move timeliness and then the score mix.",
            "portfolio": "app.search_history is the usage meter.",
            "export": "app.export_history is the usage meter a contracting officer renews against.",
            "infrastructure": "Tags live in Unity Catalog, not a spreadsheet.",
        },
    },
}


def _body_html(theme: dict, page: str) -> str:
    artifact = (theme.get("on_page") or {}).get(page) or ""
    primaries = theme.get("primary_pages") or ()
    primary_note = ""
    if page not in primaries and primaries:
        names = " · ".join(PAGE_LABEL.get(p, p) for p in primaries)
        primary_note = (
            f'<div class="theme-on">Primary proof · {html.escape(names)}</div>'
        )
    on_page = (
        f'<div class="theme-on">On this page · {html.escape(artifact)}</div>'
        if artifact
        else ""
    )
    return (
        f'<div class="theme-title">{html.escape(theme["title"])}</div>'
        f'<div class="theme-body">{html.escape(theme["body"])}</div>'
        f"{on_page}"
        f"{primary_note}"
        f'<div class="theme-letter">Theme ({html.escape(theme["letter"])})</div>'
    )


def _open_popover(theme: dict, page: str, key: str, wide: bool = False) -> None:
    with st.popover(theme["label"], use_container_width=wide, key=key):
        st.markdown(_body_html(theme, page), unsafe_allow_html=True)


def theme_chip(theme_id: str, page: str, slot: str = "chip") -> None:
    """One click-to-open chip next to a live artifact."""
    theme = THEMES[theme_id]
    filled = theme_id in PAGE_PRIMARY.get(page, ())
    klass = "mission-pri" if filled else "mission-sec"
    st.markdown(f'<div class="{klass}"></div>', unsafe_allow_html=True)
    _open_popover(theme, page, key=f"mt_{page}_{theme_id}_{slot}", wide=False)


def themed_heading(title: str, theme_id: str, page: str, slot: str | None = None) -> None:
    """Section title with the matching theme chip on the right."""
    left, right = st.columns([5.4, 1.15])
    with left:
        st.markdown(f"### {title}")
    with right:
        theme_chip(theme_id, page, slot or title.lower().replace(" ", "_"))


def render_mission_ribbon(page: str) -> None:
    """Five chips under the page header. Filled = this page is a primary proof."""
    st.markdown(
        '<div class="mission-kicker">Operating themes'
        '<span class="mission-hint">filled = this page</span></div>',
        unsafe_allow_html=True,
    )
    primary = set(PAGE_PRIMARY.get(page, ()))
    cols = st.columns(len(THEME_ORDER), gap="small")
    for col, theme_id in zip(cols, THEME_ORDER):
        theme = THEMES[theme_id]
        klass = "mission-pri" if theme_id in primary else "mission-sec"
        with col:
            st.markdown(f'<div class="{klass}"></div>', unsafe_allow_html=True)
            _open_popover(theme, page, key=f"mt_{page}_{theme_id}_ribbon", wide=True)
