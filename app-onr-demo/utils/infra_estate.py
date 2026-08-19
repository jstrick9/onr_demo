"""Element 2 evidence — live estate + the bundle that manages part of it.

Warehouse and clusters are pre-existing. The DAB manages volumes, the app,
the paused file-arrival job, and the SDP pipeline. No deploy button.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils.workspace_names import (
    ALL_PURPOSE_CLUSTER_NAME,
    ML_CLUSTER_NAME,
    SQL_WAREHOUSE_NAME,
)

APP_NAME = "onr-demo-poc"
FILE_ARRIVAL_JOB = "onr-demo-grants-file-arrival"
SDP_PIPELINE = "onr-demo-grants-stream"

_PACKAGED_EXCERPT = """\
# Databricks Asset Bundle — onr_demo / target poc
# Does NOT create the warehouse or clusters.
#   databricks bundle deploy -t poc

resources:
  volumes:
    landing:     onr_demo.bronze.landing
    checkpoints: onr_demo.bronze.checkpoints
  apps:
    onr-demo-poc: ./app-onr-demo
  jobs:
    onr-demo-grants-file-arrival:
      trigger.pause_status: PAUSED
      trigger.file_arrival: /Volumes/onr_demo/bronze/landing/grants
  pipelines:
    onr-demo-grants-stream:
      serverless: true
      continuous: false
      writes: bronze.grants_stream
"""


def _state_word(raw) -> str:
    text = str(raw or "").strip()
    if not text:
        return "—"
    return text.split(".")[-1].replace("_", " ").title()


def load_estate() -> dict:
    cached = st.session_state.get("_infra_estate")
    if cached:
        return cached
    out = {
        "warehouse": SQL_WAREHOUSE_NAME,
        "warehouse_state": "—",
        "cluster": ALL_PURPOSE_CLUSTER_NAME,
        "cluster_state": "—",
        "ml_cluster": ML_CLUSTER_NAME,
        "ml_state": "—",
        "app": APP_NAME,
        "app_state": "—",
        "job": FILE_ARRIVAL_JOB,
        "job_state": "Paused",
        "pipeline": SDP_PIPELINE,
        "note": "",
    }
    notes: list[str] = []
    try:
        from utils.db_helpers import workspace_client

        w = workspace_client()
    except Exception as e:
        out["note"] = f"Workspace API not reachable ({e}). Names below are the intended estate."
        st.session_state["_infra_estate"] = out
        return out

    want_wh = SQL_WAREHOUSE_NAME.lower()
    try:
        for wh in w.warehouses.list():
            if (wh.name or "").strip().lower() == want_wh:
                out["warehouse_state"] = _state_word(getattr(wh, "state", None))
                break
        else:
            notes.append("Warehouse not listed for this principal.")
    except Exception as e:
        notes.append(f"Warehouse list: {e}")

    want = {
        ALL_PURPOSE_CLUSTER_NAME.lower(): "cluster_state",
        ML_CLUSTER_NAME.lower(): "ml_state",
    }
    try:
        for c in w.clusters.list():
            key = want.get((c.cluster_name or "").strip().lower())
            if key:
                out[key] = _state_word(getattr(c, "state", None))
    except Exception as e:
        notes.append(f"Cluster list: {e}")

    try:
        app = w.apps.get(APP_NAME)
        out["app_state"] = _state_word(
            getattr(app, "compute_status", None)
            or getattr(app, "app_status", None)
            or getattr(app, "status", None)
            or "active"
        )
    except Exception:
        try:
            for app in w.apps.list():
                if (getattr(app, "name", "") or "").strip().lower() == APP_NAME:
                    out["app_state"] = "Listed"
                    break
        except Exception as e:
            notes.append(f"App list: {e}")

    try:
        lister = getattr(w.jobs, "list", None)
        if lister:
            for job in lister():
                settings = getattr(job, "settings", None)
                name = (
                    getattr(settings, "name", None)
                    or getattr(job, "name", None)
                    or ""
                )
                if str(name).strip().lower() != FILE_ARRIVAL_JOB:
                    continue
                trig = getattr(settings, "trigger", None) if settings else None
                pause = getattr(trig, "pause_status", None) if trig else None
                out["job_state"] = _state_word(pause) if pause else "Listed"
                break
    except Exception as e:
        notes.append(f"Job list: {e}")

    out["note"] = " ".join(notes)
    st.session_state["_infra_estate"] = out
    return out


def bundle_excerpt() -> tuple[str, str]:
    """Return (source_label, yaml text). Prefer a live file, else the packaged excerpt."""
    here = Path(__file__).resolve()
    cands = [
        here.parents[1] / "config" / "bundle_excerpt.yml",
        here.parents[1] / "config" / "databricks.yml",
        here.parents[2] / "databricks.yml",
        Path.cwd() / "databricks.yml",
        Path.cwd().parent / "databricks.yml",
    ]
    for cand in cands:
        try:
            if cand.is_file():
                text = cand.read_text()
                if text.strip():
                    return cand.name, text
        except Exception:
            continue
    return "packaged excerpt", _PACKAGED_EXCERPT


def render_estate() -> None:
    from utils.ui import fit_metrics

    rec = load_estate()
    st.markdown("### Estate")
    st.caption(
        "Provisioned by Databricks Asset Bundle for volumes, this app, "
        "the paused file-arrival job, and the SDP pipeline. "
        "Warehouse and clusters are pre-existing — the bundle does not create them."
    )
    fit_metrics(
        [
            (f"Warehouse · {rec['warehouse']}", rec["warehouse_state"]),
            (f"Score · {rec['ml_cluster']}", rec["ml_state"]),
            (f"Job · {rec['job']}", rec["job_state"]),
        ],
        columns=3,
    )
    if rec.get("note"):
        st.caption(rec["note"])


def render_bundle() -> None:
    label, text = bundle_excerpt()
    st.markdown("### Bundle")
    st.caption(
        f"`databricks bundle deploy -t poc` · `{label}` · read-only. "
        "[GitHub repo](https://github.com/jstrick9/onr_demo). Full file is in the Full bundle tab."
    )
    lines = text.splitlines()
    shown = "\n".join(lines[:14])
    if len(lines) > 14:
        shown += "\n# … full file in the Full bundle tab"
    st.code(shown, language="yaml")
