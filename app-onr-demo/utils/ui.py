"""Light main canvas, blue sidebar, Draw.io-style architecture SVGs."""

from __future__ import annotations

import html
import streamlit as st

NAVY = "#0b1f3a"
NAVY_CARD = "#122a4a"
NAVY_EDGE = "#1e3a5f"
GOLD = "#b45309"
GOLD_SOFT = "#7c2d12"
GOLD_BRIGHT = "#f59e0b"
INK = "#1a2332"
MUTED = "#5b6b80"
TEAL = "#2f6f86"
OK = "#2f7d57"
BRONZE = "#8a5a2b"
SILVER = "#5d738a"
GOLD_LANE = "#b45309"
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
[data-testid="stHeader"] {{
  background: transparent;
  z-index: 999;
}}
#MainMenu, footer {{ visibility: hidden; height: 0; }}
/* Keep the toolbar box so the sidebar reopen control is not height:0 clipped. */
[data-testid="stToolbar"] {{
  visibility: visible !important;
  height: auto !important;
}}
[data-testid="stToolbar"] [data-testid="stToolbarActions"],
[data-testid="stToolbar"] [data-testid="stAppDeployButton"],
[data-testid="stDecoration"] {{
  visibility: hidden !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {{
  visibility: visible !important;
  display: flex !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  height: auto !important;
  width: auto !important;
  z-index: 2147483646 !important;
}}
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"] {{
  background: {SIDEBAR} !important;
  color: {GOLD_BRIGHT} !important;
  border: 1px solid {GOLD_BRIGHT} !important;
  border-radius: 8px !important;
  box-shadow: 0 6px 16px rgba(11,31,58,0.35) !important;
}}

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
[data-testid="stSidebarNav"] {{
  padding-top: 4px;
}}
[data-testid="stSidebarNav"] a {{
  border-radius: 8px;
  border-left: 2px solid transparent;
  letter-spacing: 0.04em;
}}
[data-testid="stSidebarNav"] a:hover {{
  background: rgba(180,83,9,0.16) !important;
}}
[data-testid="stSidebarNav"] [aria-current="page"] {{
  border-left: 3px solid {GOLD_BRIGHT} !important;
  background: rgba(180,83,9,0.22) !important;
}}
.hud {{
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, #123152, #0b1f3a);
  border: 1px solid #2a4a70;
  border-radius: 12px;
  padding: 12px 12px 10px 12px;
  margin-bottom: 10px;
  box-shadow: 0 0 24px rgba(74,144,164,0.18);
}}
.hud-row {{
  display: flex; align-items: center; gap: 8px;
  color: #cfe6f2; font-size: 0.72rem; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase;
  margin: 4px 0;
}}
.hud-orb {{
  width: 7px; height: 7px; border-radius: 50%;
  background: #3d9b6e;
  box-shadow: 0 0 8px #3d9b6e;
  animation: pulse 1.6s infinite;
}}
.hud-orb.gold {{
  background: {GOLD};
  box-shadow: 0 0 8px {GOLD};
}}
.hud-brand {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 10px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid #2a4a70;
}}
.hud-compass {{
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  display: block;
  border-radius: 50%;
  filter: drop-shadow(0 0 8px rgba(245,158,11,0.40));
}}
.hud-word {{
  font-size: 1.12rem;
  font-weight: 800;
  letter-spacing: 0.20em;
  line-height: 1;
  text-transform: uppercase;
}}
.hud-sub {{
  font-size: 0.66rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 4px;
}}
[data-testid="stSidebar"] .hud-word {{ color: #f59e0b !important; }}
[data-testid="stSidebar"] .hud-sub {{ color: #8b9bb4 !important; }}
[data-testid="stSidebar"] .hud-user {{ color: #f59e0b !important; }}
[data-testid="stSidebar"] .hud-foot {{ color: #8b9bb4 !important; }}
.hud-user {{
  color: {GOLD_BRIGHT}; font-size: 0.82rem; margin-top: 6px; font-weight: 700;
}}
.hud-foot {{
  color: #8b9bb4; font-size: 0.68rem; letter-spacing: 0.12em;
  margin-top: 8px;
}}

h1, h2, h3 {{ letter-spacing: 0.01em; color: {NAVY} !important; }}
.stCaption, [data-testid="stCaption"] {{ color: {MUTED} !important; }}

div[data-testid="stHorizontalBlock"] > div,
div[data-testid="column"] {{
  min-width: 0 !important;
}}
[data-testid="stMetric"] {{
  background: #ffffff;
  border: 1.5px solid #475569;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 8px 22px rgba(15,23,42,0.12);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  min-width: 0;
  overflow: visible;
}}
[data-testid="stMetric"]:hover {{
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15,23,42,0.16);
}}
[data-testid="stMetric"] label {{
  color: {MUTED} !important;
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{
  color: {NAVY} !important;
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  line-height: 1.2 !important;
}}
[data-testid="stMetricDelta"] {{ font-weight: 700; }}

.inv-grid {{
  display: grid;
  grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr));
  gap: 12px;
  margin: 2px 0 14px 0;
}}
.inv-metric {{
  container-type: inline-size;
  container-name: inv;
  background: #ffffff;
  border: 1.5px solid #475569;
  border-radius: 12px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 8px 22px rgba(15,23,42,0.12);
  min-width: 0;
  min-height: 96px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}}
.inv-metric:hover {{
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15,23,42,0.16);
}}
.inv-label {{
  color: {MUTED};
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  font-weight: 700;
  margin-bottom: 8px;
}}
.inv-value {{
  color: {NAVY};
  font-weight: 800;
  line-height: 1.22;
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: normal;
  font-size: clamp(0.86rem, calc(1.72rem - 0.034rem * var(--n, 12)), 1.55rem);
}}
@container inv (max-width: 168px) {{
  .inv-value {{ font-size: 0.9rem !important; }}
}}
@media (max-width: 900px) {{
  .inv-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}

@keyframes metricFlash {{
  0% {{ box-shadow: 0 0 0 0 rgba(180,83,9,0.55); }}
  100% {{ box-shadow: 0 0 0 12px rgba(180,83,9,0); }}
}}
[data-testid="stMetric"]:has([data-testid="stMetricDelta"]) {{
  animation: metricFlash 1.6s ease-out 2;
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 6px;
  border-bottom: 2px solid #475569;
}}
.stTabs [aria-selected="true"] {{
  color: {GOLD} !important;
  border-bottom: 3px solid {GOLD} !important;
  font-weight: 700;
}}

div.stButton > button {{
  background: linear-gradient(180deg, {GOLD_BRIGHT}, {GOLD});
  color: #1c1004;
  border: 1px solid #7c2d12;
  font-weight: 800;
  border-radius: 8px;
  box-shadow: 0 6px 16px rgba(180,83,9,0.35);
}}
div.stButton > button:hover {{
  filter: brightness(1.08);
  box-shadow: 0 8px 20px rgba(180,83,9,0.45);
}}

[data-testid="stDataFrame"], .stDataFrame {{
  border: 1.5px solid #334155 !important;
  border-radius: 10px;
  box-shadow: 0 8px 22px rgba(15,23,42,0.12);
}}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div {{
  border: 1.5px solid #475569 !important;
  box-shadow: 0 4px 14px rgba(15,23,42,0.10) !important;
  background: #ffffff !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-baseweb="select"] > div:focus-within {{
  border-color: {GOLD} !important;
  box-shadow: 0 0 0 3px rgba(180,83,9,0.28) !important;
}}

[data-testid="stExpander"] {{
  border: 1.5px solid #475569 !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 16px rgba(15,23,42,0.08);
}}

[data-testid="stFileUploader"] {{
  border: 1.5px dashed {GOLD} !important;
  border-radius: 10px;
  background: #fffbeb;
}}

.page-kicker {{
  color: {GOLD};
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.page-rule {{
  height: 3px;
  width: 88px;
  background: linear-gradient(90deg, {GOLD_BRIGHT}, {GOLD});
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
  border: 1.5px solid #475569;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 8px 20px rgba(15,23,42,0.10);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}}
.cap-card:hover {{
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(15,23,42,0.16);
  border-color: {GOLD};
}}
.cap-card h4 {{
  margin: 0 0 6px 0;
  color: {GOLD};
  font-size: 0.95rem;
}}
.cap-card p {{
  margin: 0;
  color: {MUTED};
  font-size: 0.84rem;
  line-height: 1.4;
}}

.hold-tray, .action-card, .brief-sheet, .receipt-card, .hb-strip, .tt-strip {{
  background: #ffffff;
  border: 1.5px solid #475569;
  border-radius: 12px;
  box-shadow: 0 8px 22px rgba(15,23,42,0.10);
  padding: 14px 16px;
  margin: 8px 0 16px 0;
}}
.hold-kicker, .action-kicker, .brief-kicker, .receipt-kicker, .hb-kicker, .tt-kicker {{
  color: {GOLD};
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}}
.hold-title, .action-title, .receipt-title, .tt-title {{
  color: {NAVY};
  font-size: 1.05rem;
  font-weight: 800;
  margin: 2px 0 10px 0;
}}
.hold-row {{
  display: grid;
  grid-template-columns: 64px minmax(0, 1.1fr) minmax(0, 1.6fr) 110px;
  gap: 10px;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid #e2e8f0;
}}
.hold-id {{
  color: {NAVY};
  font-weight: 700;
  font-size: 0.86rem;
  overflow-wrap: anywhere;
}}
.hold-name {{
  color: {MUTED};
  font-size: 0.86rem;
  overflow-wrap: anywhere;
}}
.hold-amt {{
  color: {NAVY};
  font-weight: 700;
  text-align: right;
  font-size: 0.86rem;
}}
.chip {{
  display: inline-block;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: center;
}}
.chip-empty {{ background: #f1f5f9; color: #334155; border: 1px solid #94a3b8; }}
.chip-dup {{ background: #fff7ed; color: #9a3412; border: 1px solid {GOLD}; }}
.chip-amt {{ background: #fef2f2; color: #991b1b; border: 1px solid #dc2626; }}

.action-card {{
  border-left: 4px solid {GOLD};
  background: #fffbeb;
}}
.action-line {{
  color: {NAVY};
  font-size: 1.12rem;
  font-weight: 800;
  line-height: 1.35;
  margin: 8px 0 10px 0;
}}
.action-foot, .prov, .receipt-foot, .tt-note {{
  color: {MUTED};
  font-size: 0.75rem;
  letter-spacing: 0.02em;
}}
.prov {{
  margin: -6px 0 14px 2px;
  cursor: help;
}}

.brief-sheet {{
  padding: 0;
  overflow: hidden;
}}
.brief-banner {{
  background: {NAVY};
  color: #fff7ed;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 8px 16px;
}}
.brief-head {{
  padding: 14px 16px 8px 16px;
  border-bottom: 3px solid {GOLD};
}}
.brief-office {{
  color: {MUTED};
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.brief-name {{
  color: {NAVY};
  font-size: 1.28rem;
  font-weight: 800;
  margin: 2px 0 0 0;
}}
.brief-body {{ padding: 12px 16px 8px 16px; }}
.brief-body ul {{
  margin: 0 0 8px 0;
  padding-left: 18px;
  color: {INK};
}}
.brief-body li {{
  margin: 6px 0;
  line-height: 1.4;
}}
.brief-action {{
  margin: 10px 16px 14px 16px;
  background: #fffbeb;
  border: 1px solid {GOLD};
  border-radius: 10px;
  padding: 10px 12px;
}}
.brief-action-label {{
  color: {GOLD};
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}}
.brief-action p {{
  margin: 4px 0 0 0;
  color: {NAVY};
  font-weight: 700;
  line-height: 1.35;
}}
.brief-foot {{
  background: #f8fafc;
  color: {MUTED};
  font-size: 0.75rem;
  padding: 8px 16px 10px 16px;
  border-top: 1px solid #e2e8f0;
}}

.receipt-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px 14px;
  margin-top: 8px;
}}
.receipt-grid label {{
  display: block;
  color: {MUTED};
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
}}
.receipt-grid div.value {{
  color: {NAVY};
  font-weight: 800;
  font-size: 0.95rem;
  overflow-wrap: anywhere;
}}
.receipt-ok {{ color: {OK} !important; }}

.hb-strip {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px 18px;
}}
.hb-count {{
  color: {NAVY};
  font-size: 1.7rem;
  font-weight: 800;
  line-height: 1;
}}
.hb-meta {{ color: {MUTED}; font-size: 0.88rem; font-weight: 600; }}

.tt-cols {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 8px;
}}
.tt-col {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
}}
.tt-col .lbl {{
  color: {MUTED};
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 700;
}}
.tt-col .num {{
  color: {NAVY};
  font-size: 1.45rem;
  font-weight: 800;
}}

.ws-strip {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 0;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
}}
.ws-kicker {{
  color: {GOLD};
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin-right: 6px;
}}
.ws-strip a, .ws-chip {{
  display: inline-block;
  border: 1px solid #475569;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 0.78rem;
  font-weight: 700;
  color: {NAVY};
  text-decoration: none;
  background: #ffffff;
}}
.ws-strip a:hover {{
  border-color: {GOLD};
  color: {GOLD};
}}
.ws-chip.dead {{
  color: {MUTED};
  border-style: dashed;
}}
.drift-note {{
  color: {MUTED};
  font-size: 0.78rem;
  margin: -4px 0 12px 0;
}}
</style>
"""


def _inject_sidebar_reopen() -> None:
    """When the sidebar is closed, pin a Nav tab that clicks Streamlit's expand control."""
    import streamlit.components.v1 as components

    components.html(
        """
<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head><body>
<script>
(function () {
  const doc = window.parent.document;
  function findExpand() {
    return doc.querySelector(
      '[data-testid="stExpandSidebarButton"],' +
      '[data-testid="collapsedControl"] button,' +
      '[data-testid="stSidebarCollapsedControl"] button,' +
      '[data-testid="stSidebarCollapsedControl"]'
    );
  }
  function sidebarOpen() {
    const sb = doc.querySelector('[data-testid="stSidebar"]');
    if (!sb) return true;
    if (sb.getAttribute("aria-expanded") === "false") return false;
    return sb.getBoundingClientRect().width > 48;
  }
  let tab = doc.getElementById("onr-nav-tab");
  if (!tab) {
    tab = doc.createElement("button");
    tab.id = "onr-nav-tab";
    tab.type = "button";
    tab.textContent = "Nav";
    tab.setAttribute("aria-label", "Open navigation");
    Object.assign(tab.style, {
      position: "fixed",
      left: "0",
      top: "76px",
      zIndex: "2147483647",
      background: "#0d2744",
      color: "#f59e0b",
      border: "1px solid #f59e0b",
      borderLeft: "none",
      borderRadius: "0 8px 8px 0",
      padding: "12px 8px",
      font: "800 11px/1 Segoe UI, sans-serif",
      letterSpacing: "0.16em",
      textTransform: "uppercase",
      cursor: "pointer",
      boxShadow: "0 6px 16px rgba(11,31,58,0.35)",
      display: "none"
    });
    tab.onclick = function () {
      const b = findExpand();
      if (b) b.click();
    };
    doc.body.appendChild(tab);
  }
  function tick() {
    tab.style.display = sidebarOpen() ? "none" : "block";
  }
  tick();
  setInterval(tick, 350);
})();
</script>
</body></html>
        """,
        height=0,
    )


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    try:
        _inject_sidebar_reopen()
    except Exception:
        pass
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


def workspace_strip(items: list[dict]) -> None:
    """Compact row of workspace links (notebooks, tables, volumes)."""
    if not items:
        return
    chips = ['<div class="ws-strip"><span class="ws-kicker">Workspace</span>']
    for item in items:
        label = html.escape(str(item.get("label") or ""))
        url = item.get("url")
        if url:
            chips.append(
                f'<a href="{html.escape(str(url), quote=True)}" target="_blank" rel="noopener">{label}</a>'
            )
        else:
            chips.append(
                f'<span class="ws-chip dead" title="Workspace host or path not resolved">{label}</span>'
            )
    chips.append("</div>")
    st.markdown("".join(chips), unsafe_allow_html=True)


def page_header(kicker: str, title: str, caption: str) -> None:
    st.markdown(f'<div class="page-kicker">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown('<div class="page-rule"></div>', unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def _fit_font_ch(value: str) -> int:
    """Character count used by CSS to scale a name into its tile."""
    return max(len((value or "").strip()), 1)


def fit_metrics(items: list[tuple[str, str]], columns: int | None = None) -> None:
    """KPI tiles that wrap and shrink so long workspace names stay fully visible.

    Streamlit ``st.metric`` is sized for short numbers and clips strings such as
    warehouse / cluster names. These cards keep the same chrome, then scale
    type from the value length and the live column width.
    """
    cols = columns or max(len(items), 1)
    bits = [f'<div class="inv-grid" style="--cols:{cols}">']
    for label, value in items:
        text = "" if value is None else str(value)
        bits.append(
            '<div class="inv-metric" style="--n:{n}" title="{tip}">'
            '<div class="inv-label">{lab}</div>'
            '<div class="inv-value">{val}</div>'
            "</div>".format(
                n=_fit_font_ch(text),
                tip=html.escape(text, quote=True),
                lab=html.escape(str(label)),
                val=html.escape(text),
            )
        )
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


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


def provenance_note(table: str, catalog: str = "onr_demo", when=None, via: str | None = None) -> None:
    """Muted lineage line under a KPI row. Hover repeats the full path."""
    from utils.workspace_names import SQL_WAREHOUSE_NAME

    via = via or SQL_WAREHOUSE_NAME
    when_s = ""
    if when is not None:
        raw = str(when)
        when_s = raw[11:16] if len(raw) >= 16 and raw[10:11] in {"T", " "} else raw[:16]
    bits = [f"{catalog}.{table}"]
    if when_s:
        bits.append(when_s)
    bits.append(via)
    text = " · ".join(bits)
    st.markdown(
        f'<div class="prov" title="{html.escape(text)}">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def hold_tray(rows: list[dict]) -> None:
    """Quality-gate Hold inbox. Chips use the architecture words: empty · dup · amt."""
    if not rows:
        return
    bits = [
        '<div class="hold-tray">',
        '<div class="hold-kicker">Hold</div>',
        '<div class="hold-title">Quarantine — error log, not bronze</div>',
    ]
    for rec in rows:
        code = str(rec.get("code") or "hold").lower()
        if code not in {"empty", "dup", "amt"}:
            code = "empty"
        gn = rec.get("grant_no") or "—"
        title = rec.get("title") or rec.get("detail") or ""
        amt = rec.get("amount_usd")
        try:
            amt_s = f"${float(amt):,.0f}" if amt is not None and str(amt) != "" else ""
        except (TypeError, ValueError):
            amt_s = ""
        bits.append(
            '<div class="hold-row">'
            f'<span class="chip chip-{code}">{html.escape(code)}</span>'
            f'<span class="hold-id">{html.escape(str(gn))}</span>'
            f'<span class="hold-name">{html.escape(str(title))}</span>'
            f'<span class="hold-amt">{html.escape(amt_s)}</span>'
            "</div>"
        )
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


def action_card(line: str, source: str) -> None:
    st.markdown(
        '<div class="action-card">'
        '<div class="action-kicker">Resource action</div>'
        f'<p class="action-line">{html.escape(line)}</p>'
        f'<div class="action-foot" title="{html.escape(source)}">{html.escape(source)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def brief_sheet(rec: dict) -> None:
    """Leadership letterhead: banner, three bullets, one action, audit footer."""
    bullets = rec.get("bullets") or []
    action = rec.get("action") or ""
    body = rec.get("brief_text") or ""
    if not bullets and body:
        for raw in str(body).splitlines():
            line = raw.strip().lstrip("-•* ").strip()
            if line.upper().startswith("ACTION:"):
                action = action or line.split(":", 1)[-1].strip()
            elif line:
                bullets.append(line)
        bullets = bullets[:3]
    lis = "".join(f"<li>{html.escape(str(b))}</li>" for b in bullets[:3])
    action_html = (
        '<div class="brief-action"><div class="brief-action-label">Recommended action</div>'
        f"<p>{html.escape(str(action))}</p></div>"
        if action
        else ""
    )
    model = rec.get("model_name") or ""
    short = (
        str(model)
        .replace("databricks-", "")
        .replace("meta-", "")
        .replace("-instruct", "")
        if model
        else ""
    )
    when = rec.get("generated_at") or rec.get("time") or ""
    clock = str(when)[11:16] if len(str(when)) >= 16 else str(when)
    foot = " · ".join(
        p for p in (rec.get("brief_id"), rec.get("source"), short or None, clock or None) if p
    )
    st.markdown(
        '<div class="brief-sheet">'
        '<div class="brief-banner">Unclassified // mock data</div>'
        '<div class="brief-head">'
        '<div class="brief-office">Office of Naval Research · Code 08</div>'
        '<div class="brief-name">Daily Portfolio Brief</div>'
        "</div>"
        f'<div class="brief-body"><ul>{lis}</ul></div>'
        f"{action_html}"
        f'<div class="brief-foot">{html.escape(foot)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def receipt_card(fields: dict) -> None:
    cells = []
    for label, value in fields.items():
        klass = "value receipt-ok" if str(value).upper() == "SUCCEEDED" else "value"
        cells.append(
            f"<div><label>{html.escape(str(label))}</label>"
            f'<div class="{klass}">{html.escape("" if value is None else str(value))}</div></div>'
        )
    st.markdown(
        '<div class="receipt-card">'
        '<div class="receipt-kicker">Statement receipt</div>'
        '<div class="receipt-title">Databricks Statement Execution REST</div>'
        f'<div class="receipt-grid">{"".join(cells)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def heartbeat_strip(bronze: str, last2: str, ago: str, kicker: str = "Bronze") -> None:
    st.markdown(
        '<div class="hb-strip">'
        f'<div><div class="hb-kicker">{html.escape(kicker)}</div>'
        f'<div class="hb-count">{html.escape(str(bronze))}</div></div>'
        f'<div class="hb-meta">bronze grants</div>'
        f'<div class="hb-meta">last 2 min · {html.escape(str(last2))}</div>'
        f'<div class="hb-meta">last file · {html.escape(str(ago))}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def time_travel_strip(baseline: dict, current: dict, note: str) -> None:
    def _col(rec: dict) -> str:
        return (
            '<div class="tt-col">'
            f'<div class="lbl">{html.escape(str(rec.get("label") or ""))}</div>'
            f'<div class="num">{html.escape(str(rec.get("value") or "—"))}</div>'
            f'<div class="tt-note">{html.escape(str(rec.get("detail") or ""))}</div>'
            "</div>"
        )

    st.markdown(
        '<div class="tt-strip">'
        '<div class="tt-kicker">Delta time travel</div>'
        '<div class="tt-title">Baseline snapshot vs now</div>'
        f'<div class="tt-cols">{_col(baseline)}{_col(current)}</div>'
        f'<div class="tt-note" style="margin-top:10px">{html.escape(note)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def _e(s: str) -> str:
    return html.escape(s, quote=True)


def _defs() -> str:
    return f"""
    <defs>
      <marker id="arrowGold" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="4" markerHeight="4" orient="auto-start-reverse">
        <path d="M 0 1.2 L 8 5 L 0 8.8 z" fill="#b45309"/>
      </marker>
      <pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">
        <path d="M 16 0 L 0 0 0 16" fill="none" stroke="#e6edf5" stroke-width="1"/>
      </pattern>
    </defs>
    """


def _lane(x, y, w, h, label, fill="#eef3f8") -> str:
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="#cbd5e1"/>
    <text x="{x+14}" y="{y+20}" fill="{MUTED}" font-size="11" font-weight="700"
          font-family="Segoe UI, sans-serif" letter-spacing="1.6">{_e(label.upper())}</text>
    """


def _box(x, y, w, h, title, line1="", line2="", head=NAVY, fs=14, bullets=None) -> str:
    title_fs = max(fs, 13)
    body_fs = max(fs - 1, 12)
    body = []
    if bullets:
        gap = 20 if len(bullets) <= 3 else 16
        start = y + 48
        for i, item in enumerate(bullets):
            cy = start + i * gap
            body.append(
                f'<circle cx="{x + 16}" cy="{cy - 4}" r="2.6" fill="{GOLD}"/>'
                f'<text x="{x + 26}" y="{cy}" fill="{INK}" font-size="{body_fs}" '
                f'font-weight="600" font-family="Segoe UI, sans-serif">{_e(item)}</text>'
            )
    else:
        if line1:
            body.append(
                f'<text x="{x+10}" y="{y+50}" fill="{INK}" font-size="{body_fs}" '
                f'font-weight="600" font-family="Segoe UI, sans-serif">{_e(line1)}</text>'
            )
        if line2:
            body.append(
                f'<text x="{x+10}" y="{y+70}" fill="{MUTED}" font-size="{body_fs}" '
                f'font-weight="600" font-family="Segoe UI, sans-serif">{_e(line2)}</text>'
            )
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#ffffff" stroke="{NAVY}" stroke-width="1.4"/>
      <path d="M {x} {y+26} L {x} {y+8} Q {x} {y} {x+8} {y} L {x+w-8} {y} Q {x+w} {y} {x+w} {y+8} L {x+w} {y+26} Z" fill="{head}"/>
      <text x="{x+10}" y="{y+18}" fill="#fff7ed" font-size="{title_fs}" font-weight="800" font-family="Segoe UI, sans-serif">{_e(title)}</text>
      {''.join(body)}
    </g>
    """


def _arrow(x1, y1, x2, y2, label="") -> str:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 8
    lab = (
        f'<text x="{mx}" y="{my}" text-anchor="middle" fill="#ffffff" stroke="#ffffff" '
        f'stroke-width="3" paint-order="stroke" font-size="13" font-weight="800" '
        f'font-family="Segoe UI, sans-serif">{_e(label)}</text>'
        f'<text x="{mx}" y="{my}" text-anchor="middle" fill="{GOLD}" font-size="13" '
        f'font-weight="800" font-family="Segoe UI, sans-serif">{_e(label)}</text>'
        if label
        else ""
    )
    return f"""
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{GOLD}" stroke-width="2.2"
          marker-end="url(#arrowGold)" stroke-dasharray="8 6" class="flow-line"
          stroke-linecap="round"/>
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
    border: 1.5px solid #475569;
    border-radius: 14px;
    background: #f7f9fc;
    padding: 8px 8px 6px 8px;
    box-shadow: 0 8px 22px rgba(15,23,42,0.10);
  }}
  .kicker {{
    color: #b45309;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }}
  .title {{
    color: #0b1f3a;
    font-size: 20px;
    font-weight: 800;
    margin: 2px 0 8px 0;
  }}
  svg {{ width: 100%; height: {h}px; display: block; }}
  .note {{
    color: #5b6b80;
    font-size: 14px;
    margin: 6px 2px 2px 2px;
  }}
  .flow-line {{ animation: dash 1.15s linear infinite; }}
  @keyframes dash {{ to {{ stroke-dashoffset: -24; }} }}
</style>
</head>
<body>
  <div class="board">
    <div class="kicker">Architecture</div>
    <div class="title">{html.escape(title)}</div>
    <svg viewBox="0 0 {w} {h}" width="100%" height="{h}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
      {_defs()}
      <rect width="{w}" height="{h}" fill="url(#grid)"/>
      {svg_body}
    </svg>
    {f'<div class="note">{html.escape(note)}</div>' if note else ""}
  </div>
</body>
</html>"""
    components.html(doc, height=h + 108, scrolling=False)


def _diagram_ingestion() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(12, 10, 270, 340, "Source", "#f4efe6"),
            _lane(314, 10, 270, 340, "Ingest", "#eef6f8"),
            _lane(616, 10, 270, 340, "Quality", "#f8f1ee"),
            _lane(918, 10, 270, 340, "Serve", "#eef4ea"),
            _box(28, 48, 238, 130, "Landing Volume", "CSV / JSON files", "/bronze/landing", BRONZE),
            _box(28, 202, 238, 128, "Checkpoints", "Auto Loader offsets", "resumable", SILVER),
            _box(330, 48, 238, 130, "Detect", "cloudFiles / warehouse", "addNewColumns", TEAL),
            _box(330, 202, 238, 128, "bronze.grants", "Raw Delta + metadata", "_ingest_time", BRONZE),
            _box(632, 48, 238, 110, "Quality gates", "grant_no, amount positive", "dedupe", "#a15c4a"),
            _box(632, 186, 110, 144, "Pass", "to silver", "", OK),
            _box(760, 186, 110, 144, "Hold", head="#a15c4a", bullets=["empty", "dup", "amt"]),
            _box(934, 48, 238, 130, "silver.grants", "Cleansed, _is_active", "leadership-ready", SILVER),
            _box(934, 202, 238, 128, "gold.*", "KPIs, forecast, scores", "app reads here", GOLD_LANE),
            _arrow(266, 113, 330, 113, "arrive"),
            _arrow(266, 266, 330, 266),
            _arrow(568, 103, 632, 103, "validate"),
            _arrow(449, 178, 449, 202),
            _arrow(751, 158, 687, 186),
            _arrow(870, 103, 934, 103, "publish"),
            _arrow(1053, 178, 1053, 202),
        ]
    )
    return (
        "Ingestion — file to serving tables",
        body,
        1200,
        360,
        "Same bronze table whether the file arrived through the console or a streaming job.",
    )


def _diagram_catalog() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(12, 10, 1176, 350, "Unity Catalog   onr_demo", "#eef3f8"),
            _box(32, 46, 250, 130, "bronze", "grants · financial", "landing + checkpoints", BRONZE),
            _box(326, 46, 250, 130, "silver", "quality gates", "_is_active", SILVER),
            _box(620, 46, 250, 130, "gold", "summaries · models", "forecast · anomalies", GOLD_LANE),
            _box(914, 46, 250, 130, "app", "audit · briefs", "quality · lineage", APP_LANE),
            _arrow(282, 111, 326, 111, "cleanse"),
            _arrow(576, 111, 620, 111, "aggregate"),
            _arrow(870, 111, 914, 111, "operate"),
            _box(32, 210, 360, 130, "Lineage", "landing to bronze to silver to gold", "native Catalog Explorer graph", TEAL),
            _box(424, 210, 360, 130, "Health scores", "complete · accurate", "consistent · timely", OK),
            _box(816, 210, 348, 130, "Tags and grants", "data_source · sensitivity", "least privilege", NAVY),
            _arrow(157, 176, 157, 210),
            _arrow(745, 176, 604, 210),
            _arrow(1039, 176, 990, 210),
        ]
    )
    return (
        "Catalog — govern the portfolio",
        body,
        1200,
        370,
        "Unity Catalog is the system of record. The native lineage graph lives in Catalog Explorer.",
    )


def _diagram_analytics() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(12, 10, 250, 350, "Features", "#eef3f8"),
            _lane(302, 10, 586, 350, "Models", "#f7f3ea"),
            _lane(928, 10, 260, 350, "Decisions", "#eef4ea"),
            _box(28, 50, 218, 136, "gold features", "grants + ERP", "funding_features", GOLD_LANE),
            _box(28, 210, 218, 130, "Same portfolio", "no second dataset", "408 after inbound", TEAL),
            _box(322, 48, 166, 136, "Random Forest", "large award >= $1M", "Fund / Review / Defer", NAVY),
            _box(512, 48, 166, 136, "IsolationForest", "spike · collapse", "low-return", "#a15c4a"),
            _box(702, 48, 166, 136, "OLS forecast", "2-yr + 95% band", "TREND-* IDs", TEAL),
            _box(322, 214, 166, 126, "predictions", "grant_predictions", "", SILVER),
            _box(512, 214, 166, 126, "anomalies", "grant_anomaly_scores", "", SILVER),
            _box(702, 214, 166, 126, "forecast", "funding_forecast", "program_trends", SILVER),
            _box(944, 50, 228, 136, "Resource officer", "who to fund", "what is declining", OK),
            _box(944, 214, 228, 126, "Reallocate", "AT_RISK + TREND-DECLINE", "", GOLD_LANE),
            _arrow(246, 118, 322, 118),
            _arrow(246, 275, 322, 275),
            _arrow(405, 184, 405, 214),
            _arrow(595, 184, 595, 214),
            _arrow(785, 184, 785, 214),
            _arrow(868, 118, 944, 118, "advise"),
            _arrow(868, 277, 944, 277),
        ]
    )
    return (
        "Analytics — three models, one portfolio",
        body,
        1200,
        370,
        "Registered models score the ingested portfolio. Forecast is OLS, not a neural net.",
    )


def _diagram_portfolio() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(12, 10, 260, 340, "Leader", "#eef3f8"),
            _lane(312, 10, 560, 340, "Console", "#f7f3ea"),
            _lane(912, 10, 276, 340, "Act", "#eef4ea"),
            _box(28, 50, 228, 130, "No SQL required", "Code 08 officer", "signed-in identity", TEAL),
            _box(28, 206, 228, 124, "gold.*", "single catalog", "", GOLD_LANE),
            _box(332, 48, 160, 130, "Filter", "FY · area · amount", "", NAVY),
            _box(516, 48, 160, 130, "Search", "quantum · ONRD", "search_history", TEAL),
            _box(700, 48, 152, 130, "Visuals", "KPIs · charts", "budget gauge", GOLD_LANE),
            _box(332, 206, 252, 124, "Daily brief", "automated summary", "daily_briefs", OK),
            _box(608, 206, 244, 124, "Flags", "AT_RISK · anomalies", "", "#a15c4a"),
            _box(928, 50, 244, 130, "Extract", "CSV from search", "", SILVER),
            _box(928, 206, 244, 124, "Follow up", "declining + AT_RISK", "", GOLD_LANE),
            _arrow(256, 115, 332, 115),
            _arrow(492, 113, 516, 113),
            _arrow(676, 113, 700, 113),
            _arrow(852, 113, 928, 113, "take away"),
            _arrow(412, 178, 412, 206),
            _arrow(776, 178, 730, 206),
        ]
    )
    return (
        "Portfolio — leadership without the warehouse",
        body,
        1200,
        360,
        "Search and export writes are audited. The brief is generated, not typed.",
    )


def _diagram_export() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(12, 10, 260, 340, "Select", "#eef3f8"),
            _lane(312, 10, 420, 340, "Package", "#f7f3ea"),
            _lane(772, 10, 416, 340, "Leave the platform", "#eef4ea"),
            _box(28, 50, 228, 130, "Filtered query", "FY 2025-2026", "never SELECT *", TEAL),
            _box(28, 206, 228, 124, "gold / silver", "business-ready", "", GOLD_LANE),
            _box(332, 48, 120, 130, "CSV", "sheets", "", SILVER),
            _box(468, 48, 120, 130, "JSON", "APIs", "", SILVER),
            _box(604, 48, 112, 130, "Parquet", "analytics", "", SILVER),
            _box(332, 206, 384, 124, "export_history", "who · what · filter · count", "", NAVY),
            _box(792, 48, 188, 130, "Statement API", "POST /sql/statements", "OAuth", TEAL),
            _box(996, 48, 176, 130, "Advana / C1", "JDBC · REST", "open standards", OK),
            _box(792, 206, 380, 124, "Schema travels", "grant_no · area · amount", "", GOLD_LANE),
            _arrow(256, 115, 332, 115, "format"),
            _arrow(524, 178, 524, 206),
            _arrow(716, 113, 792, 113),
            _arrow(980, 113, 996, 113),
            _arrow(256, 268, 332, 268),
        ]
    )
    return (
        "Export — open formats, audited, integrable",
        body,
        1200,
        360,
        "The live contract is Databricks Statement Execution REST on the same warehouse.",
    )


def _diagram_infrastructure() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _lane(12, 10, 276, 340, "Compute", "#eef3f8"),
            _lane(324, 10, 312, 340, "Bundle", "#f7f3ea"),
            _lane(672, 10, 246, 340, "Catalog", "#eef4ea"),
            _lane(954, 10, 234, 340, "Identity", "#f8f1ee"),
            _box(28, 50, 244, 130, "Warehouse", "onr demo warehouse", "serverless SQL", TEAL, fs=10),
            _box(28, 206, 244, 124, "Cluster", "onr demo cluster", "jobs / stream", NAVY, fs=10),
            _box(340, 48, 136, 130, "Volumes", "landing", "checkpoints", BRONZE),
            _box(492, 48, 128, 130, "App", "onr-demo-poc", "", APP_LANE),
            _box(340, 206, 136, 124, "File-arrival", "paused job", "", SILVER),
            _box(492, 206, 128, 124, "SDP", "grants_stream", "", SILVER),
            _box(688, 50, 214, 130, "onr_demo", "bronze to silver", "gold to app", GOLD_LANE),
            _box(688, 206, 214, 124, "Models", "RF · IsolationForest", "OLS", NAVY),
            _box(970, 50, 202, 130, "App SP", "own principal", "OAuth", "#a15c4a"),
            _box(970, 206, 202, 124, "Least privilege", "gold SELECT", "no bronze", OK),
            _arrow(272, 115, 340, 113),
            _arrow(636, 113, 688, 115, "bind"),
            _arrow(902, 115, 970, 115),
            _arrow(272, 268, 340, 268),
        ]
    )
    return (
        "Infrastructure — what this workspace is",
        body,
        1200,
        360,
        "The bundle does not create the warehouse or cluster. The app has its own service principal.",
    )


def _diagram_home() -> tuple[str, int, int, str, str]:
    body = "".join(
        [
            _box(16, 36, 168, 140, "Infra", "warehouse · cluster", "Element 2", NAVY),
            _box(208, 36, 168, 140, "Ingest", "Volume + quality", "Element 3", BRONZE),
            _box(400, 36, 168, 140, "Catalog", "UC + lineage", "Element 4", SILVER),
            _box(592, 36, 168, 140, "Analytics", "RF · IF · OLS", "Element 5", TEAL),
            _box(784, 36, 168, 140, "Portfolio", "search · brief", "Element 6", APP_LANE),
            _box(976, 36, 204, 140, "Export", "open formats + API", "Element 7", GOLD_LANE),
            _arrow(184, 106, 208, 106),
            _arrow(376, 106, 400, 106),
            _arrow(568, 106, 592, 106),
            _arrow(760, 106, 784, 106),
            _arrow(952, 106, 976, 106),
            _box(208, 214, 776, 116, "Unity Catalog  onr_demo", "bronze to silver to gold to app", "one identity plane", OK),
            _arrow(292, 176, 292, 214),
            _arrow(484, 176, 484, 214),
            _arrow(676, 176, 676, 214),
            _arrow(868, 176, 868, 214),
        ]
    )
    return (
        "ONR Portfolio — end to end",
        body,
        1200,
        350,
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
