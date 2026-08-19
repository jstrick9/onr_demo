"""Element 1 evidence — who is signed in, who the app is, what gold allows.

This is the result of workspace IdP authentication. It is not an MFA form.
"""

from __future__ import annotations

import os

import streamlit as st


def signed_in_label() -> str:
    from utils.user_helpers import get_current_user

    user = get_current_user() or {}
    return (
        str(user.get("email") or user.get("display_name") or "").strip()
        or "Workspace session"
    )


def app_principal_label() -> str:
    """Short name for the Databricks App service principal."""
    cached = st.session_state.get("_app_principal_label")
    if cached:
        return cached
    name = (
        (os.getenv("DATABRICKS_APP_NAME") or "").strip()
        or "onr-demo-poc"
    )
    cid = (os.getenv("DATABRICKS_CLIENT_ID") or "").strip()
    try:
        from utils.db_helpers import workspace_client

        me = workspace_client().current_user.me()
        for attr in ("display_name", "displayName", "user_name", "userName"):
            val = str(getattr(me, attr, "") or "").strip()
            if val:
                name = val
                break
        if not cid:
            cid = str(getattr(me, "id", "") or "").strip()
    except Exception:
        pass
    if cid and cid.lower() not in name.lower():
        short = cid if len(cid) <= 12 else cid[:8]
        label = f"{name} · {short}"
    else:
        label = name
    st.session_state["_app_principal_label"] = label
    return label


def _last_audit(cursor, catalog: str, table: str) -> str | None:
    if not cursor:
        return None
    try:
        cursor.execute(
            f"""
            SELECT * FROM `{catalog}`.`app`.{table}
            ORDER BY 1 DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [str(d[0]).lower() for d in (cursor.description or [])]
        rec = {c: row[i] for i, c in enumerate(cols)}
        who = rec.get("user_email") or rec.get("requested_by") or rec.get("generated_by") or ""
        when = rec.get("exported_at") or rec.get("searched_at") or rec.get("created_at") or ""
        when_s = str(when)[:16] if when else ""
        bits = [b for b in (str(who).strip(), when_s) if b]
        return " · ".join(bits) if bits else "row present"
    except Exception:
        return None


def render_access_plane(cursor=None, catalog: str = "onr_demo") -> None:
    """Four tiles: signed-in user, IdP, app SP, gold-only scope."""
    from utils.ui import fit_metrics

    st.markdown("### Access")
    st.caption(
        "Workspace IdP session. This app has its own service principal. "
        "MFA is the identity provider, not this form. "
        "This cell is unclassified mock on commercial AWS — not IL5."
    )
    fit_metrics(
        [
            ("Signed in", signed_in_label()),
            ("Via", "Workspace IdP"),
            ("App principal", app_principal_label()),
            ("Data scope", "gold SELECT · no bronze"),
        ],
        columns=4,
    )
    last_search = _last_audit(cursor, catalog, "search_history")
    last_export = _last_audit(cursor, catalog, "export_history")
    if last_search or last_export:
        bits = []
        if last_search:
            bits.append(f"search {last_search}")
        if last_export:
            bits.append(f"export {last_export}")
        st.caption("Continuous authorization · " + " · ".join(bits))
