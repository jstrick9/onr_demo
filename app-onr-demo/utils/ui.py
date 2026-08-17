"""Light main canvas, blue sidebar, Draw.io-style architecture SVGs."""

from __future__ import annotations

import html
import streamlit as st

NAVY = "#0b1f3a"
NAVY_CARD = "#122a4a"
NAVY_EDGE = "#1e3a5f"
GOLD = "#c5a572"
GOLD_SOFT = "#a6864a"
INK = "#1a2332"
MUTED = "#5b6b80"
TEAL = "#2f6f86"
OK = "#2f7d57"
BRONZE = "#8a5a2b"
SILVER = "#5d738a"
GOLD_LANE = "#9a7b3c"
APP_LANE = "#3d6b8a"
SIDEBAR = "#0d2744"
CANVAS = "#f7f9fc"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');

html, body, [class*="css"] {{
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
}}
.stApp {{
  background: #ffffff;
  color: {INK};
}}
[data-testid="stAppViewContainer"] {{
  background: #ffffff;
}}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}

[data-testid="stSidebar"] {{
  background: {SIDEBAR};
  border-right: 1px solid {NAVY_EDGE};
}}
[data-testid="stSidebar"] * {{ color: #e8eef5 !important; }}
[data-testid="stSidebar"] [data-testid="stMetric"] {{
  background: {NAVY_CARD};
  border: 1px solid {NAVY_EDGE};
}}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {{ color: #e8d5a3 !important; }}
[data-testid="stSidebar"] [data-testid="stMetric"] label {{ color: #8b9bb4 !important; }}

h1, h2, h3 {{ letter-spacing: 0.01em; color: {NAVY} !important; }}
.stCaption, [data-testid="stCaption"] {{ color: {MUTED} !important; }}

[data-testid="stMetric"] {{
  background: #ffffff;
  border: 1px solid #d5deea;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 6px 18px rgba(11,31,58,0.06);
}}
[data-testid="stMetric"] label {{
  color: {MUTED} !important;
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{ color: {NAVY} !important; }}
[data-testid="stMetricDelta"] {{ font-weight: 700; }}

@keyframes metricFlash {{
  0% {{ box-shadow: 0 0 0 0 rgba(197,165,114,0.55); }}
  100% {{ box-shadow: 0 0 0 12px rgba(197,165,114,0); }}
}}
[data-testid="stMetric"]:has([data-testid="stMetricDelta"]) {{
  animation: metricFlash 1.6s ease-out 2;
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 6px;
  border-bottom: 1px solid #d5deea;
}}
.stTabs [data-baseweb="tab"] {{
  background: transparent;
  color: {MUTED};
}}
.stTabs [aria-selected="true"] {{
  color: {NAVY} !important;
  border-bottom: 2px solid {GOLD} !important;
}}

div.stButton > button {{
  background: linear-gradient(180deg, #d4b57e, {GOLD});
  color: #1a1208;
  border: 0;
  font-weight: 700;
  border-radius: 8px;
}}
div.stButton > button:hover {{ filter: brightness(1.05); }}

[data-testid="stDataFrame"], .stDataFrame {{
  border: 1px solid #d5deea;
  border-radius: 10px;
}}

.page-kicker {{
  color: {GOLD_SOFT};
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.page-rule {{
  height: 2px;
  width: 72px;
  background: linear-gradient(90deg, {GOLD}, transparent);
  margin: 8px 0 18px 0;
}}
.unclass-chip {{
  display: inline-block;
  border: 1px solid #d5deea;
  color: {MUTED};
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 999px;
}}
.live-chip {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #eef7f2;
  color: {OK};
  border: 1px solid #b7dcc8;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}}
.live-dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: {OK};
  box-shadow: 0 0 0 0 rgba(47,125,87,0.6);
  animation: pulse 1.4s infinite;
}}
@keyframes pulse {{
  0% {{ box-shadow: 0 0 0 0 rgba(47,125,87,0.55); }}
  70% {{ box-shadow: 0 0 0 8px rgba(47,125,87,0); }}
  100% {{ box-shadow: 0 0 0 0 rgba(47,125,87,0); }}
}}

.arch {{
  margin: 22px 0 8px 0;
  padding: 14px 14px 8px 14px;
  background: {CANVAS};
  border: 1px solid #d5deea;
  border-radius: 14px;
}}
.arch-kicker {{
  color: {GOLD_SOFT};
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}}
.arch-title {{
  color: {NAVY};
  font-size: 1.12rem;
  font-weight: 700;
  margin: 2px 0 10px 0;
}}
.arch svg {{ width: 100%; height: auto; display: block; }}
.arch-note {{
  color: {MUTED};
  font-size: 0.8rem;
  margin: 8px 2px 4px 2px;
}}
.flow-line {{
  animation: dash 1.15s linear infinite;
}}
@keyframes dash {{
  to {{ stroke-dashoffset: -24; }}
}}

.cap-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin: 8px 0 20px 0;
}}
.cap-card {{
  background: #ffffff;
  border: 1px solid #d5deea;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 6px 18px rgba(11,31,58,0.05);
}}
.cap-card h4 {{
  margin: 0 0 6px 0;
  color: {NAVY};
  font-size: 0.95rem;
}}
.cap-card p {{
  margin: 0;
  color: {MUTED};
  font-size: 0.84rem;
  line-height: 1.4;
}}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    try:
        import plotly.io as pio
        import plotly.graph_objects as go

        pio.templates["onr"] = go.layout.Template(
            layout=go.Layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#f4f7fb",
                font=dict(color=INK, family="Source Sans 3, Segoe UI, sans-serif"),
                colorway=[GOLD, TEAL, "#7aa2c4", OK, "#c45c5c", NAVY],
                title=dict(font=dict(color=NAVY, size=16)),
                xaxis=dict(gridcolor="#d5deea", zerolinecolor="#d5deea"),
                yaxis=dict(gridcolor="#d5deea", zerolinecolor="#d5deea"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK)),
            )
        )
        pio.templates.default = "onr"
    except Exception:
        pass


def page_header(kicker: str, title: str, caption: str) -> None:
    st.markdown(f'<div class="page-kicker">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown('<div class="page-rule"></div>', unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def capability_cards(cards: list[dict]) -> None:
    bits = ['<div class="cap-grid">']
    for card in cards:
        bits.append(
            '<div class="cap-card"><h4>{}</h4><p>{}</p></div>'.format(
                html.escape(card["title"]), html.escape(card["body"])
            )
        )
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


def live_chip(label: str = "Pipeline active") -> None:
    st.markdown(
        f'<div class="live-chip"><span class="live-dot"></span>{html.escape(label)}</div>',
        unsafe_allow_html=True,
    )


def _e(s: str) -> str:
    return html.escape(s, quote=True)


def _defs() -> str:
    return f"""
    <defs>
      <marker id="arrowGold" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="{GOLD}"/>
      </marker>
      <marker id="arrowNavy" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="{NAVY}"/>
      </marker>
      <pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">
        <path d="M 16 0 L 0 0 0 16" fill="none" stroke="#e6edf5" stroke-width="1"/>
      </pattern>
    </defs>
    """


def _lane(x, y, w, h, label, fill="#eef3f8") -> str:
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="#d5deea"/>
    <text x="{x+12}" y="{y+18}" fill="{MUTED}" font-size="11" font-weight="700"
          font-family="Segoe UI, sans-serif" letter-spacing="1.4">{_e(label.upper())}</text>
    """


def _box(x, y, w, h, title, line1="", line2="", head=NAVY) -> str:
    t2 = f'<text x="{x+10}" y="{y+56}" fill="{MUTED}" font-size="11" font-family="Segoe UI, sans-serif">{_e(line2)}</text>' if line2 else ""
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#ffffff" stroke="{NAVY}" stroke-width="1.4"/>
      <path d="M {x} {y+22} L {x} {y+8} Q {x} {y} {x+8} {y} L {x+w-8} {y} Q {x+w} {y} {x+w} {y+8} L {x+w} {y+22} Z" fill="{head}"/>
      <text x="{x+10}" y="{y+15}" fill="#f7f1e6" font-size="12" font-weight="700" font-family="Segoe UI, sans-serif">{_e(title)}</text>
      <text x="{x+10}" y="{y+40}" fill="{INK}" font-size="11" font-family="Segoe UI, sans-serif">{_e(line1)}</text>
      {t2}
    </g>
    """


def _arrow(x1, y1, x2, y2, label="") -> str:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 8
    lab = (
        f'<text x="{mx}" y="{my}" text-anchor="middle" fill="{GOLD_SOFT}" font-size="10" '
        f'font-weight="700" font-family="Segoe UI, sans-serif">{_e(label)}</text>'
        if label
        else ""
    )
    return f"""
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{GOLD}" stroke-width="2.2"
          marker-end="url(#arrowGold)" stroke-dasharray="8 6" class="flow-line"/>
    {lab}
    """


def _v_arrow(x, y1, y2, label="") -> str:
    return _arrow(x, y1, x, y2, label)


def _wrap(title: str, svg_body: str, w: int, h: int, note: str = "") -> None:
    """Render via an iframe so Streamlit cannot strip the SVG."""
    import streamlit.components.v1 as components

    doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  html, body {{ margin: 0; padding: 0; background: #f7f9fc; }}
  .board {{
    font-family: "Segoe UI", "Source Sans 3", sans-serif;
    border: 1px solid #d5deea;
    border-radius: 14px;
    background: #f7f9fc;
    padding: 12px 12px 8px 12px;
  }}
  .kicker {{
    color: #a6864a;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }}
  .title {{
    color: #0b1f3a;
    font-size: 18px;
    font-weight: 700;
    margin: 2px 0 10px 0;
  }}
  svg {{ width: 100%; height: auto; display: block; }}
  .note {{
    color: #5b6b80;
    font-size: 12px;
    margin: 8px 2px 2px 2px;
  }}
  .flow-line {{ animation: dash 1.15s linear infinite; }}
  @keyframes dash {{ to {{ stroke-dashoffset: -24; }} }}
</style>
</head>
<body>
  <div class="board">
    <div class="kicker">Architecture</div>
    <div class="title">{html.escape(title)}</div>
    <svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
      {_defs()}
      <rect width="{w}" height="{h}" fill="url(#grid)"/>
      {svg_body}
    </svg>
    {f'<div class="note">{html.escape(note)}</div>' if note else ""}
  </div>
</body>
</html>"""
    components.html(doc, height=int(h * 0.72) + 92, scrolling=False)


def _diagram_ingestion() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(8, 8, 200, 250, "Source", "#f4efe6"),
            _lane(220, 8, 250, 250, "Ingest", "#eef6f8"),
            _lane(482, 8, 230, 250, "Quality", "#f8f1ee"),
            _lane(724, 8, 248, 250, "Serve", "#eef4ea"),
            _box(24, 48, 168, 78, "Landing Volume", "CSV / JSON files", "/bronze/landing", BRONZE),
            _box(24, 150, 168, 78, "Checkpoints", "Auto Loader offsets", "resumable", SILVER),
            _box(236, 48, 218, 78, "Detect", "cloudFiles / warehouse", "addNewColumns", TEAL),
            _box(236, 150, 218, 78, "bronze.grants", "Raw Delta + metadata", "_ingest_time", BRONZE),
            _box(498, 48, 198, 78, "Quality gates", "grant_no · amount > 0", "dedupe", "#a15c4a"),
            _box(498, 160, 90, 70, "Pass", "to silver", "", OK),
            _box(600, 160, 90, 70, "Hold", "empty / dup / ≤0", "", "#a15c4a"),
            _box(740, 48, 216, 78, "silver.grants", "Cleansed, _is_active", "leadership-ready", SILVER),
            _box(740, 150, 216, 78, "gold.*", "KPIs · forecast · scores", "app reads here", GOLD_LANE),
            _arrow(192, 87, 236, 87, "arrive"),
            _arrow(192, 189, 236, 189),
            _arrow(454, 87, 498, 87, "validate"),
            _arrow(345, 126, 345, 150),
            _arrow(597, 126, 543, 160),
            _arrow(696, 87, 740, 87, "publish"),
            _arrow(848, 126, 848, 150),
        ]
    )
    return (
        "Ingestion — file to serving tables",
        body,
        980,
        270,
        "Same bronze table whether the file arrived through the console or a streaming job.",
    )


def _diagram_catalog() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(8, 8, 964, 268, "Unity Catalog  ·  onr_demo", "#eef3f8"),
            _box(28, 44, 200, 86, "bronze", "grants · financial", "landing + checkpoints", BRONZE),
            _box(268, 44, 200, 86, "silver", "quality gates", "_is_active", SILVER),
            _box(508, 44, 200, 86, "gold", "summaries · models", "forecast · anomalies", GOLD_LANE),
            _box(748, 44, 200, 86, "app", "audit · briefs", "quality · lineage", APP_LANE),
            _arrow(228, 87, 268, 87, "cleanse"),
            _arrow(468, 87, 508, 87, "aggregate"),
            _arrow(708, 87, 748, 87, "operate"),
            _box(28, 160, 320, 86, "Lineage", "landing → bronze → silver → gold", "native Catalog Explorer graph", TEAL),
            _box(368, 160, 280, 86, "Health scores", "complete · accurate", "consistent · timely", OK),
            _box(668, 160, 280, 86, "Tags & grants", "data_source · sensitivity", "least privilege", NAVY),
            _arrow(188, 130, 188, 160),
            _arrow(508, 130, 508, 160),
            _arrow(808, 130, 808, 160),
        ]
    )
    return (
        "Catalog — govern the portfolio",
        body,
        980,
        288,
        "Unity Catalog is the system of record. The native lineage graph lives in Catalog Explorer.",
    )


def _diagram_analytics() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(8, 8, 220, 268, "Features", "#eef3f8"),
            _lane(240, 8, 500, 268, "Models", "#f7f3ea"),
            _lane(752, 8, 220, 268, "Decisions", "#eef4ea"),
            _box(24, 50, 188, 90, "gold features", "grants + ERP", "funding_features", GOLD_LANE),
            _box(24, 160, 188, 86, "Same portfolio", "no second dataset", "408 after inbound", TEAL),
            _box(260, 44, 140, 100, "Random Forest", "large award ≥ $1M", "Fund / Review / Defer", NAVY),
            _box(420, 44, 140, 100, "IsolationForest", "spike · collapse", "low-return", "#a15c4a"),
            _box(580, 44, 140, 100, "OLS forecast", "2-yr + 95% band", "TREND-* IDs", TEAL),
            _box(260, 168, 140, 78, "predictions", "grant_predictions", "", SILVER),
            _box(420, 168, 140, 78, "anomalies", "grant_anomaly_scores", "", SILVER),
            _box(580, 168, 140, 78, "forecast", "funding_forecast", "program_trends", SILVER),
            _box(768, 50, 188, 90, "Resource officer", "who to fund", "what is declining", OK),
            _box(768, 160, 188, 86, "Reallocate", "AT_RISK + TREND-DECLINE", "", GOLD_LANE),
            _arrow(212, 95, 260, 95),
            _arrow(212, 203, 260, 203),
            _arrow(330, 144, 330, 168),
            _arrow(490, 144, 490, 168),
            _arrow(650, 144, 650, 168),
            _arrow(720, 94, 768, 94, "advise"),
            _arrow(720, 203, 768, 203),
        ]
    )
    return (
        "Analytics — three models, one portfolio",
        body,
        980,
        288,
        "Registered models score the ingested portfolio. Forecast is OLS, not a neural net.",
    )


def _diagram_portfolio() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(8, 8, 230, 250, "Leader", "#eef3f8"),
            _lane(250, 8, 470, 250, "Console", "#f7f3ea"),
            _lane(732, 8, 240, 250, "Act", "#eef4ea"),
            _box(24, 50, 198, 86, "No SQL required", "Code 08 officer", "signed-in identity", TEAL),
            _box(24, 156, 198, 78, "gold.*", "single catalog", "", GOLD_LANE),
            _box(270, 44, 130, 90, "Filter", "FY · area · $", "", NAVY),
            _box(420, 44, 130, 90, "Search", "quantum · ONRD", "search_history", TEAL),
            _box(570, 44, 130, 90, "Visuals", "KPIs · charts", "budget gauge", GOLD_LANE),
            _box(270, 156, 200, 78, "Daily brief", "automated summary", "daily_briefs", OK),
            _box(500, 156, 200, 78, "Flags", "AT_RISK · anomalies", "", "#a15c4a"),
            _box(748, 50, 208, 86, "Extract", "CSV from search", "", SILVER),
            _box(748, 156, 208, 78, "Follow up", "declining + AT_RISK", "", GOLD_LANE),
            _arrow(222, 93, 270, 93),
            _arrow(400, 89, 420, 89),
            _arrow(550, 89, 570, 89),
            _arrow(700, 89, 748, 89, "take away"),
            _arrow(370, 134, 370, 156),
            _arrow(635, 134, 600, 156),
        ]
    )
    return (
        "Portfolio — leadership without the warehouse",
        body,
        980,
        270,
        "Search and export writes are audited. The brief is generated, not typed.",
    )


def _diagram_export() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(8, 8, 220, 250, "Select", "#eef3f8"),
            _lane(240, 8, 360, 250, "Package", "#f7f3ea"),
            _lane(612, 8, 360, 250, "Leave the platform", "#eef4ea"),
            _box(24, 50, 188, 86, "Filtered query", "FY 2025–2026", "never SELECT *", TEAL),
            _box(24, 156, 188, 78, "gold / silver", "business-ready", "", GOLD_LANE),
            _box(260, 44, 100, 90, "CSV", "sheets", "", SILVER),
            _box(370, 44, 100, 90, "JSON", "APIs", "", SILVER),
            _box(480, 44, 100, 90, "Parquet", "analytics", "", SILVER),
            _box(260, 156, 320, 78, "export_history", "who · what · filter · count", "", NAVY),
            _box(632, 44, 160, 90, "Statement API", "POST /sql/statements", "OAuth", TEAL),
            _box(808, 44, 148, 90, "Advana / C1", "JDBC · REST", "open standards", OK),
            _box(632, 156, 324, 78, "Schema travels", "grant_no · area · amount", "", GOLD_LANE),
            _arrow(212, 93, 260, 93, "format"),
            _arrow(360, 134, 360, 156),
            _arrow(580, 89, 632, 89),
            _arrow(792, 89, 808, 89),
            _arrow(212, 195, 260, 195),
        ]
    )
    return (
        "Export — open formats, audited, integrable",
        body,
        980,
        270,
        "The live contract is Databricks Statement Execution REST on the same warehouse.",
    )


def _diagram_infrastructure() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(8, 8, 240, 250, "Compute", "#eef3f8"),
            _lane(260, 8, 300, 250, "Bundle", "#f7f3ea"),
            _lane(572, 8, 200, 250, "Catalog", "#eef4ea"),
            _lane(784, 8, 188, 250, "Identity", "#f8f1ee"),
            _box(24, 48, 208, 86, "SQL warehouse", "onr demo warehouse", "serverless", TEAL),
            _box(24, 154, 208, 78, "Cluster", "onr demo cluster", "jobs · stream", NAVY),
            _box(276, 44, 130, 78, "Volumes", "landing", "checkpoints", BRONZE),
            _box(416, 44, 128, 78, "App", "onr-demo-poc", "", APP_LANE),
            _box(276, 140, 130, 78, "File-arrival", "paused job", "", SILVER),
            _box(416, 140, 128, 78, "SDP", "grants_stream", "", SILVER),
            _box(588, 48, 168, 86, "onr_demo", "bronze → silver", "gold → app", GOLD_LANE),
            _box(588, 154, 168, 78, "Models", "RF · IsolationForest", "OLS", NAVY),
            _box(800, 48, 156, 86, "App SP", "own principal", "OAuth", "#a15c4a"),
            _box(800, 154, 156, 78, "Least privilege", "gold SELECT", "no bronze", OK),
            _arrow(232, 91, 276, 83),
            _arrow(544, 83, 588, 91, "bind"),
            _arrow(756, 91, 800, 91),
            _arrow(232, 193, 276, 179),
        ]
    )
    return (
        "Infrastructure — what this workspace is",
        body,
        980,
        270,
        "The bundle does not create the warehouse or cluster. The app has its own service principal.",
    )


def _diagram_home() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _box(20, 40, 150, 80, "Ingest", "Volume + quality", "", BRONZE),
            _box(210, 40, 150, 80, "Catalog", "UC + lineage", "", SILVER),
            _box(400, 40, 150, 80, "Analytics", "RF · IF · OLS", "", NAVY),
            _box(590, 40, 150, 80, "Portfolio", "search · brief", "", TEAL),
            _box(780, 40, 170, 80, "Export", "open formats + API", "", GOLD_LANE),
            _arrow(170, 80, 210, 80),
            _arrow(360, 80, 400, 80),
            _arrow(550, 80, 590, 80),
            _arrow(740, 80, 780, 80),
            _box(210, 160, 530, 70, "Unity Catalog  onr_demo", "bronze → silver → gold → app", "one identity plane", OK),
            _arrow(285, 120, 285, 160),
            _arrow(475, 120, 475, 160),
            _arrow(665, 120, 665, 160),
        ]
    )
    return (
        "ONR Portfolio — end to end",
        body,
        980,
        250,
        "One catalog. Leadership never leaves the console.",
    )


_DIAGRAMS = {
    "home": _diagram_home,
    "ingestion": _diagram_ingestion,
    "catalog": _diagram_catalog,
    "analytics": _diagram_analytics,
    "portfolio": _diagram_portfolio,
    "export": _diagram_export,
    "infrastructure": _diagram_infrastructure,
}


def render_architecture(kind: str) -> None:
    """Draw.io-style SVG architecture for a page."""
    builder = _DIAGRAMS.get(kind)
    if not builder:
        return
    title, body, w, h, note = builder()
    _wrap(title, body, w, h, note)


def render_how_it_works(title: str, steps: list[dict] | None = None, note: str = "", kind: str | None = None) -> None:
    """Back-compat: prefer kind= to render the SVG board."""
    if kind:
        render_architecture(kind)
        return
    # Fallback unused; pages now pass kind.
    render_architecture("home")


def style_fig(fig):
    try:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#f4f7fb",
            font=dict(color=INK),
            title_font=dict(color=NAVY),
        )
        fig.update_xaxes(gridcolor="#d5deea")
        fig.update_yaxes(gridcolor="#d5deea")
    except Exception:
        pass
    return fig
