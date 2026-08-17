"""Navy command-center theme and How it works flows."""

from __future__ import annotations

import html
import streamlit as st

NAVY = "#0a1628"
NAVY_CARD = "#122a4a"
NAVY_EDGE = "#1e3a5f"
GOLD = "#c5a572"
GOLD_SOFT = "#e8d5a3"
INK = "#e8eef5"
MUTED = "#8b9bb4"
TEAL = "#4a90a4"
OK = "#3d9b6e"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');

html, body, [class*="css"] {{
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
}}
.stApp {{
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(197,165,114,0.08), transparent 50%),
    radial-gradient(900px 400px at 100% 0%, rgba(74,144,164,0.10), transparent 45%),
    {NAVY};
  color: {INK};
}}
[data-testid="stSidebar"] {{
  background: #071221;
  border-right: 1px solid {NAVY_EDGE};
}}
[data-testid="stSidebar"] * {{ color: {INK}; }}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}

h1, h2, h3 {{ letter-spacing: 0.01em; color: {INK} !important; }}
.stCaption, [data-testid="stCaption"] {{ color: {MUTED} !important; }}

[data-testid="stMetric"] {{
  background: {NAVY_CARD};
  border: 1px solid {NAVY_EDGE};
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}}
[data-testid="stMetric"] label {{ color: {MUTED} !important; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.06em; }}
[data-testid="stMetricValue"] {{ color: {GOLD_SOFT} !important; }}

.stTabs [data-baseweb="tab-list"] {{
  gap: 6px;
  border-bottom: 1px solid {NAVY_EDGE};
}}
.stTabs [data-baseweb="tab"] {{
  background: transparent;
  color: {MUTED};
  border-radius: 8px 8px 0 0;
}}
.stTabs [aria-selected="true"] {{
  color: {GOLD} !important;
  border-bottom: 2px solid {GOLD} !important;
}}

div.stButton > button {{
  background: linear-gradient(180deg, #d4b57e, {GOLD});
  color: #1a1208;
  border: 0;
  font-weight: 700;
  border-radius: 8px;
}}
div.stButton > button:hover {{ filter: brightness(1.06); }}
div.stButton > button[kind="secondary"] {{
  background: {NAVY_CARD};
  color: {INK};
  border: 1px solid {NAVY_EDGE};
}}

[data-testid="stDataFrame"], .stDataFrame {{
  border: 1px solid {NAVY_EDGE};
  border-radius: 10px;
}}

.page-kicker {{
  color: {GOLD};
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
  border: 1px solid {NAVY_EDGE};
  color: {MUTED};
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 999px;
}}

.hiw {{
  margin: 28px 0 8px 0;
  padding: 18px 18px 14px 18px;
  background: linear-gradient(180deg, rgba(18,42,74,0.95), rgba(10,22,40,0.92));
  border: 1px solid {NAVY_EDGE};
  border-radius: 14px;
}}
.hiw-kicker {{
  color: {GOLD};
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}}
.hiw-title {{
  color: {INK};
  font-size: 1.15rem;
  font-weight: 700;
  margin: 2px 0 14px 0;
}}
.hiw-row {{
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0;
}}
.hiw-step {{
  flex: 1 1 140px;
  min-width: 120px;
  background: rgba(7,18,33,0.65);
  border: 1px solid {NAVY_EDGE};
  border-radius: 10px;
  padding: 12px 12px 14px 12px;
}}
.hiw-num {{
  color: {GOLD};
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}}
.hiw-name {{
  color: {INK};
  font-weight: 700;
  margin: 4px 0 4px 0;
  font-size: 0.95rem;
}}
.hiw-desc {{
  color: {MUTED};
  font-size: 0.8rem;
  line-height: 1.35;
}}
.hiw-arrow {{
  flex: 0 0 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: {GOLD};
  font-size: 1.2rem;
}}
.hiw-note {{
  color: {MUTED};
  font-size: 0.8rem;
  margin: 12px 0 0 0;
}}
.cap-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin: 8px 0 20px 0;
}}
.cap-card {{
  background: {NAVY_CARD};
  border: 1px solid {NAVY_EDGE};
  border-radius: 12px;
  padding: 14px 16px;
}}
.cap-card h4 {{
  margin: 0 0 6px 0;
  color: {GOLD_SOFT};
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
    if st.session_state.get("_onr_theme"):
        return
    st.markdown(_CSS, unsafe_allow_html=True)
    st.session_state["_onr_theme"] = True
    try:
        import plotly.io as pio
        import plotly.graph_objects as go

        pio.templates["onr"] = go.layout.Template(
            layout=go.Layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(18,42,74,0.35)",
                font=dict(color=INK, family="Source Sans 3, Segoe UI, sans-serif"),
                colorway=[GOLD, TEAL, "#7aa2c4", OK, "#c45c5c", GOLD_SOFT],
                title=dict(font=dict(color=INK, size=16)),
                xaxis=dict(gridcolor=NAVY_EDGE, zerolinecolor=NAVY_EDGE),
                yaxis=dict(gridcolor=NAVY_EDGE, zerolinecolor=NAVY_EDGE),
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


def render_how_it_works(title: str, steps: list[dict], note: str = "") -> None:
    """Always-visible architecture strip. steps: [{name, detail}]."""
    parts = [
        '<div class="hiw">',
        '<div class="hiw-kicker">Architecture</div>',
        f'<div class="hiw-title">{html.escape(title)}</div>',
        '<div class="hiw-row">',
    ]
    for i, step in enumerate(steps):
        if i:
            parts.append('<div class="hiw-arrow">&#8594;</div>')
        parts.append(
            '<div class="hiw-step">'
            f'<div class="hiw-num">0{i+1}</div>'
            f'<div class="hiw-name">{html.escape(step["name"])}</div>'
            f'<div class="hiw-desc">{html.escape(step["detail"])}</div>'
            "</div>"
        )
    parts.append("</div>")
    if note:
        parts.append(f'<p class="hiw-note">{html.escape(note)}</p>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def style_fig(fig):
    try:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(18,42,74,0.35)",
            font=dict(color=INK),
            title_font=dict(color=INK),
        )
        fig.update_xaxes(gridcolor=NAVY_EDGE)
        fig.update_yaxes(gridcolor=NAVY_EDGE)
    except Exception:
        pass
    return fig
