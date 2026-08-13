"""On-page evaluator prompt so the 50-minute story stays visible."""

import streamlit as st


def render_eval_prompt(element: str, prompt: str, show_this: str):
    st.markdown(
        f"""
<div style="background:#0b1f33;color:#e8eef4;padding:14px 16px;border-radius:8px;
            border-left:6px solid #c5a46e;margin:0 0 16px 0;">
  <div style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;opacity:.8;">
    Evaluator prompt — {element}
  </div>
  <div style="font-size:16px;font-weight:600;margin:6px 0 8px 0;">{prompt}</div>
  <div style="font-size:13px;opacity:.9;"><b>Show this:</b> {show_this}</div>
</div>
""",
        unsafe_allow_html=True,
    )
