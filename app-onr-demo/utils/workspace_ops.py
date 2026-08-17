"""Workspace links and one-click runs so the console does not require tab-hunting."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import streamlit as st

STREAM_NOTEBOOK = "01b_streaming_autoloader"
SCORE_NOTEBOOK = "04c_score_registered_models"

NOTEBOOKS = {
    "01": "01_bronze_ingestion",
    "01b": "01b_streaming_autoloader",
    "02": "02_silver_quality",
    "03": "03_gold_aggregation",
    "04": "04_mlflow_grant_model",
    "04b": "04b_funding_anomaly",
    "04c": "04c_score_registered_models",
    "05": "05_reset_demo",
}


def _client():
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def workspace_host() -> str:
    try:
        host = (_client().config.host or "").strip()
    except Exception:
        host = ""
    if not host:
        return ""
    if not host.startswith("http"):
        host = "https://" + host
    return host.rstrip("/")


def notebook_url(path: str | None) -> str | None:
    if not path:
        return None
    host = workspace_host()
    if not host:
        return None
    path = path if path.startswith("/") else "/" + path
    return f"{host}/#workspace{path}"


def catalog_table_url(catalog: str, schema: str, table: str, tab: str | None = None) -> str | None:
    host = workspace_host()
    if not host:
        return None
    url = f"{host}/explore/data/{catalog}/{schema}/{table}"
    if tab:
        url += f"?activeTab={tab}"
    return url


def volume_url(catalog: str, schema: str = "bronze", volume: str = "landing") -> str | None:
    host = workspace_host()
    if not host:
        return None
    return f"{host}/explore/data/volumes/{catalog}/{schema}/{volume}"


def run_url(run_id: int | None, page_url: str | None = None) -> str | None:
    if page_url:
        return page_url
    if not run_id:
        return None
    host = workspace_host()
    if not host:
        return None
    return f"{host}/#job/run/{run_id}"


def _candidate_paths(filename: str) -> list[str]:
    env_key = "ONR_NOTEBOOK_STREAM" if "01b" in filename else "ONR_NOTEBOOK_SCORE"
    env = (os.getenv(env_key) or "").strip()
    stems = [filename, filename + ".py", filename.replace(".py", "")]
    roots = []
    if env:
        roots.append(env)
    try:
        me = _client().current_user.me()
        email = getattr(me, "user_name", None) or ""
    except Exception:
        email = ""
    if email:
        for stem in stems:
            roots.extend(
                [
                    f"/Workspace/Users/{email}/onr_demo/notebooks/{stem}",
                    f"/Users/{email}/onr_demo/notebooks/{stem}",
                    f"/Workspace/Users/{email}/Repos/onr_demo/notebooks/{stem}",
                ]
            )
    for stem in stems:
        roots.extend(
            [
                f"/Workspace/.bundle/onr_demo/poc/files/notebooks/{stem}",
                f"/Workspace/.bundle/onr_demo/dev/files/notebooks/{stem}",
                f"/Workspace/onr_demo/notebooks/{stem}",
            ]
        )
    # de-dupe, keep order
    seen, out = set(), []
    for p in roots:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def resolve_notebook(filename: str) -> str | None:
    """Return a workspace path for 01b / 04c. Cached per session."""
    key = f"_nb_path_{filename}"
    if key in st.session_state:
        return st.session_state[key]
    try:
        w = _client()
    except Exception:
        return None
    for path in _candidate_paths(filename):
        try:
            w.workspace.get_status(path)
            st.session_state[key] = path
            return path
        except Exception:
            continue
    # Full workspace walk only for the two camera notebooks.
    if filename in {STREAM_NOTEBOOK, SCORE_NOTEBOOK}:
        found = _search_notebook(w, filename)
        if found:
            st.session_state[key] = found
            return found
    st.session_state[key] = None
    return None


def _search_notebook(w, filename: str, max_nodes: int = 180) -> str | None:
    needle = filename.replace(".py", "")
    roots = ["/Workspace/Users", "/Users", "/Workspace/.bundle", "/Repos", "/Workspace"]
    seen_paths = set()
    queue = list(roots)
    scanned = 0
    while queue and scanned < max_nodes:
        path = queue.pop(0)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        try:
            items = list(w.workspace.list(path))
        except Exception:
            continue
        for it in items:
            scanned += 1
            p = getattr(it, "path", None) or ""
            name = p.rsplit("/", 1)[-1]
            if needle in name:
                return p
            kind = str(getattr(it, "object_type", "") or "").upper()
            if any(k in kind for k in ("DIRECTORY", "REPO", "PROJECT")):
                if scanned < max_nodes:
                    queue.append(p)
    return None


def start_named_cluster() -> tuple[str | None, str]:
    from utils.workspace_names import ALL_PURPOSE_CLUSTER_NAME

    try:
        w = _client()
        want = ALL_PURPOSE_CLUSTER_NAME.strip().lower()
        for c in w.clusters.list():
            if (c.cluster_name or "").strip().lower() != want:
                continue
            state = str(getattr(c, "state", "") or "").upper()
            if "RUNNING" not in state:
                try:
                    w.clusters.start(c.cluster_id)
                except Exception as e:
                    return c.cluster_id, f"Cluster start requested ({e})"
                return c.cluster_id, f"Starting {ALL_PURPOSE_CLUSTER_NAME}"
            return c.cluster_id, f"{ALL_PURPOSE_CLUSTER_NAME} is running"
        return None, f"Cluster '{ALL_PURPOSE_CLUSTER_NAME}' not found"
    except Exception as e:
        return None, str(e)


def submit_notebook(path: str, run_name: str, params: dict | None = None) -> dict:
    from databricks.sdk.service import jobs

    cluster_id, cluster_msg = start_named_cluster()
    if not cluster_id:
        raise RuntimeError(cluster_msg)
    w = _client()
    nb_kwargs = {
        "notebook_path": path,
        "base_parameters": {k: str(v) for k, v in (params or {}).items()},
    }
    source = getattr(jobs, "Source", None)
    if source is not None and hasattr(source, "WORKSPACE"):
        nb_kwargs["source"] = source.WORKSPACE
    task = jobs.SubmitTask(
        task_key="run",
        existing_cluster_id=cluster_id,
        notebook_task=jobs.NotebookTask(**nb_kwargs),
    )
    waiter = w.jobs.submit(run_name=run_name, tasks=[task])
    run_id = (
        getattr(waiter, "run_id", None)
        or getattr(getattr(waiter, "response", None), "run_id", None)
        or getattr(getattr(waiter, "_response", None), "run_id", None)
    )
    page = None
    state = "SUBMITTED"
    try:
        run = w.jobs.get_run(run_id)
        page = getattr(run, "run_page_url", None)
        life = getattr(getattr(run, "state", None), "life_cycle_state", None)
        state = str(life or state)
    except Exception:
        pass
    return {
        "run_id": run_id,
        "state": state,
        "page_url": page,
        "notebook": path,
        "cluster": cluster_msg,
    }


def get_run_state(run_id: int | None) -> dict:
    if not run_id:
        return {}
    try:
        run = _client().jobs.get_run(run_id)
        life = getattr(getattr(run, "state", None), "life_cycle_state", None)
        result = getattr(getattr(run, "state", None), "result_state", None)
        return {
            "run_id": run_id,
            "state": str(life or "UNKNOWN"),
            "result": str(result) if result else "",
            "page_url": getattr(run, "run_page_url", None),
        }
    except Exception as e:
        return {"run_id": run_id, "state": "UNKNOWN", "error": str(e)}


def copy_stream_file(catalog: str = "onr_demo") -> dict:
    """Place a new Auto Loader path on the landing Volume."""
    src_vol = f"/Volumes/{catalog}/bronze/landing/_staged/batch_live_grants.csv"
    dst = f"/Volumes/{catalog}/bronze/landing/grants/batch_live_grants_stream.csv"
    w = _client()
    data = None
    via = "volume"
    try:
        dl = w.files.download(src_vol)
        payload = getattr(dl, "contents", dl)
        data = payload.read() if hasattr(payload, "read") else payload
    except Exception:
        via = "app-packaged"
        local = Path(__file__).resolve().parents[1] / "data" / "batch_live_grants.csv"
        if not local.exists():
            local = Path(__file__).resolve().parents[2] / "resources" / "mock_data" / "batch_live_grants.csv"
        data = local.read_bytes()
    if not data:
        raise RuntimeError("No stream CSV available to land")
    bio = data if hasattr(data, "read") else BytesIO(data)
    w.files.upload(dst, bio, overwrite=True)
    return {"src": src_vol if via == "volume" else "app data/batch_live_grants.csv", "dst": dst, "via": via}


def start_stream(catalog: str = "onr_demo") -> dict:
    """Copy the live CSV and submit 01b. File drop still happens if the run cannot start."""
    landed = copy_stream_file(catalog)
    path = resolve_notebook(STREAM_NOTEBOOK)
    run = None
    error = None
    if path:
        try:
            run = submit_notebook(
                path,
                run_name="onr-demo-stream",
                params={"catalog": catalog, "processing_seconds": "30", "run_for_seconds": "90"},
            )
        except Exception as e:
            error = str(e)
    else:
        error = "Stream notebook was not found in the workspace"
    return {"file": landed, "run": run, "error": error, "notebook": path}


def start_score(catalog: str = "onr_demo") -> dict:
    path = resolve_notebook(SCORE_NOTEBOOK)
    if not path:
        raise RuntimeError("Scoring notebook was not found in the workspace")
    run = submit_notebook(path, run_name="onr-demo-score", params={"catalog": catalog})
    return {"run": run, "notebook": path}


PAGE_LINKS = {
    "home": [
        {"kind": "table", "schema": "silver", "table": "grants", "label": "silver.grants"},
        {"kind": "table", "schema": "gold", "table": "grants_summary", "label": "gold.grants_summary"},
        {"kind": "table", "schema": "gold", "table": "budget_execution", "label": "gold.budget_execution"},
    ],
    "ingestion": [
        {"kind": "notebook", "name": "01_bronze_ingestion", "label": "01 ingest"},
        {"kind": "notebook", "name": "01b_streaming_autoloader", "label": "01b stream"},
        {"kind": "notebook", "name": "02_silver_quality", "label": "02 quality"},
        {"kind": "volume", "volume": "landing", "label": "landing Volume"},
        {"kind": "table", "schema": "bronze", "table": "grants", "label": "bronze.grants"},
        {"kind": "table", "schema": "silver", "table": "grants", "label": "silver.grants"},
    ],
    "catalog": [
        {"kind": "table", "schema": "silver", "table": "grants", "tab": "lineage", "label": "Lineage"},
        {"kind": "table", "schema": "gold", "table": "grants_summary", "label": "gold.grants_summary"},
        {"kind": "table", "schema": "app", "table": "data_quality_scores", "label": "quality scores"},
        {"kind": "table", "schema": "app", "table": "lineage_tracking", "label": "lineage_tracking"},
    ],
    "analytics": [
        {"kind": "notebook", "name": "04c_score_registered_models", "label": "04c score"},
        {"kind": "notebook", "name": "04_mlflow_grant_model", "label": "04 RF"},
        {"kind": "notebook", "name": "04b_funding_anomaly", "label": "04b IsolationForest"},
        {"kind": "table", "schema": "gold", "table": "grant_predictions", "label": "grant_predictions"},
        {"kind": "table", "schema": "gold", "table": "grant_anomaly_scores", "label": "anomaly scores"},
        {"kind": "table", "schema": "gold", "table": "funding_forecast", "label": "funding_forecast"},
        {"kind": "table", "schema": "gold", "table": "program_trends", "label": "program_trends"},
    ],
    "portfolio": [
        {"kind": "table", "schema": "gold", "table": "grants_summary", "label": "grants_summary"},
        {"kind": "table", "schema": "gold", "table": "budget_execution", "label": "budget_execution"},
        {"kind": "table", "schema": "app", "table": "daily_briefs", "label": "daily_briefs"},
        {"kind": "table", "schema": "app", "table": "search_history", "label": "search_history"},
    ],
    "export": [
        {"kind": "table", "schema": "gold", "table": "grants_summary", "label": "grants_summary"},
        {"kind": "table", "schema": "silver", "table": "grants", "label": "silver.grants"},
        {"kind": "table", "schema": "app", "table": "export_history", "label": "export_history"},
    ],
    "infrastructure": [
        {"kind": "notebook", "name": "00_bootstrap", "label": "00 bootstrap"},
        {"kind": "notebook", "name": "01_bronze_ingestion", "label": "01"},
        {"kind": "notebook", "name": "01b_streaming_autoloader", "label": "01b"},
        {"kind": "notebook", "name": "02_silver_quality", "label": "02"},
        {"kind": "notebook", "name": "03_gold_aggregation", "label": "03"},
        {"kind": "notebook", "name": "04_mlflow_grant_model", "label": "04"},
        {"kind": "notebook", "name": "04b_funding_anomaly", "label": "04b"},
        {"kind": "notebook", "name": "04c_score_registered_models", "label": "04c"},
        {"kind": "volume", "volume": "landing", "label": "landing"},
        {"kind": "volume", "volume": "checkpoints", "label": "checkpoints"},
        {"kind": "table", "schema": "bronze", "table": "grants", "label": "bronze.grants"},
        {"kind": "table", "schema": "gold", "table": "grant_predictions", "label": "predictions"},
    ],
}


def render_page_links(page: str, catalog: str = "onr_demo") -> None:
    render_workspace_strip(PAGE_LINKS.get(page) or [], catalog)


def render_workspace_strip(spec: list[dict], catalog: str = "onr_demo") -> None:
    """Resolve notebooks/tables/volumes for this page and render the strip."""
    try:
        from utils.ui import workspace_strip
    except ImportError:
        def workspace_strip(items: list[dict]) -> None:
            labels = [str(i.get("label") or "") for i in (items or [])]
            if labels:
                st.caption("Workspace · " + " · ".join(labels))

    items = []
    for raw in spec:
        kind = raw.get("kind")
        label = raw.get("label") or raw.get("name") or raw.get("table") or "object"
        url = None
        if kind == "notebook":
            name = raw.get("name") or NOTEBOOKS.get(str(raw.get("key") or ""), "")
            url = notebook_url(resolve_notebook(name)) if name else None
        elif kind == "table":
            url = catalog_table_url(
                catalog,
                raw.get("schema") or "gold",
                raw.get("table"),
                tab=raw.get("tab"),
            )
        elif kind == "volume":
            url = volume_url(catalog, raw.get("schema") or "bronze", raw.get("volume") or "landing")
        elif kind == "url":
            url = raw.get("url")
        items.append({"label": label, "url": url})
    workspace_strip(items)


def workspace_action_row(label: str, url: str | None) -> None:
    if url:
        st.link_button(label, url)
    else:
        st.caption(f"{label} — workspace host not resolved")


def render_run_status(kind: str, payload: dict | None) -> None:
    if not payload:
        return
    run = payload.get("run") or {}
    run_id = run.get("run_id")
    live = get_run_state(run_id) if run_id else {}
    state = live.get("state") or run.get("state") or "—"
    result = live.get("result") or ""
    page = live.get("page_url") or run.get("page_url")
    bits = f"{kind} · {state}"
    if result:
        bits += f" · {result}"
    if run_id:
        bits += f" · run {run_id}"
    st.caption(bits)
    if page:
        st.link_button("Open run", page)
    if payload.get("error"):
        st.caption(payload["error"])
    landed = (payload.get("file") or {}).get("dst")
    if landed:
        st.caption(f"Landed {landed}")
