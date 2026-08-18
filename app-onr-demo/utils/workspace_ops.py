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
    from utils.db_helpers import workspace_client

    return workspace_client()


def workspace_host() -> str:
    cached = st.session_state.get("_ws_host")
    if cached:
        return cached
    host = (
        os.getenv("DATABRICKS_HOST")
        or os.getenv("DATABRICKS_SERVER_HOSTNAME")
        or os.getenv("DATABRICKS_WORKSPACE_URL")
        or ""
    ).strip()
    if not host:
        try:
            host = (_client().config.host or "").strip()
        except Exception:
            host = ""
    if host and not host.startswith("http"):
        host = "https://" + host
    host = host.rstrip("/")
    if host:
        st.session_state["_ws_host"] = host
    return host


def _conf_repo_root() -> str:
    env = (os.getenv("ONR_REPO_ROOT") or os.getenv("DATABRICKS_REPO_ROOT") or "").strip()
    if env:
        return env.rstrip("/")
    try:
        from utils.db_helpers import read_yaml

        here = Path(__file__).resolve()
        for cand in (
            here.parents[1] / "config" / "onr-conf.yaml",
            here.parents[2] / "app-onr-demo" / "config" / "onr-conf.yaml",
        ):
            if cand.exists():
                cfg = read_yaml(str(cand)) or {}
                root = ((cfg.get("workspace") or {}).get("repo_root") or "").strip()
                if root:
                    return root.rstrip("/")
    except Exception:
        pass
    return ""


def _app_source_repo_root() -> str:
    try:
        w = _client()
        names = [os.getenv("DATABRICKS_APP_NAME") or "", "onr-demo-poc"]
        app = None
        for name in names:
            if not name:
                continue
            try:
                app = w.apps.get(name)
                break
            except Exception:
                continue
        if not app:
            return ""
        paths = []
        for attr in (
            "default_source_code_path",
            "source_code_path",
            "source_code_dir",
        ):
            val = getattr(app, attr, None)
            if val:
                paths.append(str(val))
        dep = getattr(app, "active_deployment", None) or getattr(app, "deployment", None)
        if dep is not None:
            for attr in ("source_code_path", "default_source_code_path", "path"):
                val = getattr(dep, attr, None)
                if val:
                    paths.append(str(val))
        for p in paths:
            p = p.rstrip("/")
            if p.endswith("/app-onr-demo"):
                return p[: -len("/app-onr-demo")]
            if p.endswith("app-onr-demo"):
                return p.rsplit("/", 1)[0]
            if p.endswith("/onr_demo") or p.endswith("/onr-demo"):
                return p
            if "/notebooks" in p:
                return p.split("/notebooks")[0]
            if p:
                return p
    except Exception:
        return ""
    return ""


def _repo_from_repos_api() -> str:
    try:
        w = _client()
        lister = getattr(w.repos, "list", None)
        if not lister:
            return ""
        for repo in lister():
            path = str(getattr(repo, "path", "") or "")
            url = str(getattr(repo, "url", "") or "")
            blob = f"{path} {url}".lower()
            if "onr_demo" in blob or "onr-demo" in blob:
                return path.rstrip("/")
    except Exception:
        return ""
    return ""


def repo_root() -> str:
    cached = st.session_state.get("_ws_repo_root")
    if cached:
        return cached
    root = _conf_repo_root() or _app_source_repo_root() or _repo_from_repos_api()
    if root:
        st.session_state["_ws_repo_root"] = root
    return root


def guessed_notebook_path(filename: str) -> str | None:
    """Build a clickable workspace path. Does not require the app SP to list the folder."""
    stem = (filename or "").replace(".py", "").strip()
    if not stem:
        return None
    root = repo_root()
    if not root:
        return None
    if not root.startswith("/"):
        root = "/" + root
    return f"{root.rstrip('/')}/notebooks/{stem}"


def notebook_url(path: str | None) -> str | None:
    host = workspace_host()
    if not host:
        return None
    if not path:
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
    env = (
        os.getenv("ONR_NOTEBOOK_STREAM" if "01b" in filename else "")
        or os.getenv("ONR_NOTEBOOK_SCORE" if "04c" in filename else "")
        or ""
    ).strip()
    stems = [filename, filename + ".py", filename.replace(".py", "")]
    roots = []
    if env:
        roots.append(env)
    repo = repo_root()
    if repo:
        for stem in stems:
            roots.append(f"{repo.rstrip('/')}/notebooks/{stem}")
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
                f"/Workspace/Shared/onr-demo/notebooks/{stem}",
                f"/Shared/onr-demo/notebooks/{stem}",
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
    """Workspace path for a notebook.

    Prefer a path the app SP can see (for job submit). If listing fails —
    usual for an app service principal — return the constructed Git-folder
    path so the presenter's browser can still open the file.
    """
    key = f"_nb_path_{filename}"
    if key in st.session_state:
        return st.session_state[key]
    guessed = guessed_notebook_path(filename)
    try:
        w = _client()
    except Exception:
        w = None
    candidates = _candidate_paths(filename)
    if guessed:
        candidates = [guessed, f"{guessed}.py"] + candidates
    if w is not None:
        for path in candidates:
            try:
                w.workspace.get_status(path)
                st.session_state[key] = path
                return path
            except Exception:
                continue
        if filename in {STREAM_NOTEBOOK, SCORE_NOTEBOOK}:
            found = _search_notebook(w, filename)
            if found:
                st.session_state[key] = found
                return found
    if guessed:
        st.session_state[key] = guessed
        return guessed
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


def notebook_accessible(path: str | None) -> bool:
    """True only if the *app* identity can read this workspace path."""
    if not path:
        return False
    try:
        _client().workspace.get_status(path)
        return True
    except Exception:
        return False


def _local_notebook_bytes(filename: str) -> bytes | None:
    stem = filename.replace(".py", "")
    here = Path(__file__).resolve()
    for cand in (
        here.parents[1] / "notebooks" / f"{stem}.py",
        here.parents[2] / "notebooks" / f"{stem}.py",
    ):
        if cand.exists():
            return cand.read_bytes()
    return None


def publish_notebook_for_app(filename: str) -> str | None:
    """Import the packaged notebook to Shared so the app SP owns a runnable copy.

    Jobs run as the app principal. That identity cannot read
    /Workspace/Users/<human>/onr_demo/.... A Shared copy it imported itself can.
    """
    raw = _local_notebook_bytes(filename)
    if not raw:
        return None
    import base64

    stem = filename.replace(".py", "")
    dests = [
        f"/Workspace/Shared/onr-demo/notebooks/{stem}",
        f"/Shared/onr-demo/notebooks/{stem}",
    ]
    try:
        me = _client().current_user.me()
        who = getattr(me, "user_name", None) or ""
        if who:
            dests.append(f"/Workspace/Users/{who}/onr_demo/notebooks/{stem}")
    except Exception:
        pass
    w = _client()
    payload = base64.b64encode(raw).decode("ascii")
    try:
        from databricks.sdk.service.workspace import ImportFormat, Language

        fmt, lang = ImportFormat.SOURCE, Language.PYTHON
    except Exception:
        fmt, lang = "SOURCE", "PYTHON"
    for dest in dests:
        parent = dest.rsplit("/", 1)[0]
        try:
            w.workspace.mkdirs(parent)
        except Exception:
            pass
        try:
            w.workspace.import_(
                path=dest,
                format=fmt,
                language=lang,
                content=payload,
                overwrite=True,
            )
            if notebook_accessible(dest):
                return dest
        except Exception:
            continue
    return None


def runnable_notebook_path(filename: str, refresh: bool = False) -> str | None:
    """Workspace path the app SP can actually read — required for job submit.

    When refresh=True (Start stream), always overwrite the Shared copy from
    the packaged notebook so a stale .schema() 01b cannot keep failing.
    """
    key = f"_nb_run_{filename}"
    if refresh:
        published = publish_notebook_for_app(filename)
        if published:
            st.session_state[key] = published
            return published
    cached = st.session_state.get(key)
    if cached and notebook_accessible(cached):
        return cached
    published = publish_notebook_for_app(filename)
    if published:
        st.session_state[key] = published
        return published
    guessed = guessed_notebook_path(filename)
    for path in [guessed, f"{guessed}.py" if guessed else None, *_candidate_paths(filename)]:
        if notebook_accessible(path):
            st.session_state[key] = path
            return path
    return None


def _norm_name(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _configured_cluster_id() -> str:
    env = (os.getenv("ONR_CLUSTER_ID") or os.getenv("DATABRICKS_CLUSTER_ID") or "").strip()
    if env:
        return env
    try:
        from utils.db_helpers import read_yaml

        here = Path(__file__).resolve()
        for cand in (
            here.parents[1] / "config" / "onr-conf.yaml",
            here.parents[2] / "app-onr-demo" / "config" / "onr-conf.yaml",
        ):
            if cand.exists():
                cfg = read_yaml(str(cand)) or {}
                cid = ((cfg.get("workspace") or {}).get("cluster_id") or "").strip()
                if cid:
                    return cid
    except Exception:
        pass
    return ""


def start_named_cluster() -> tuple[str | None, str]:
    from utils.workspace_names import ALL_PURPOSE_CLUSTER_NAME

    configured = _configured_cluster_id()
    try:
        w = _client()
    except Exception as e:
        return None, f"Cannot reach cluster API ({e})"

    if configured:
        try:
            info = w.clusters.get(cluster_id=configured)
            state = str(getattr(info, "state", "") or "").upper()
            if "RUNNING" not in state:
                try:
                    w.clusters.start(configured)
                except Exception as e:
                    return configured, f"Cluster start requested ({e})"
                return configured, f"Starting configured cluster {configured}"
            return configured, f"Configured cluster {configured} is running"
        except Exception as e:
            return None, f"Configured cluster id {configured} is not usable ({e})"

    try:
        clusters = list(w.clusters.list())
    except Exception as e:
        return None, (
            f"App principal cannot list clusters ({e}). "
            "Set workspace.cluster_id or ONR_CLUSTER_ID."
        )

    want = ALL_PURPOSE_CLUSTER_NAME.strip().lower()
    want_n = _norm_name(ALL_PURPOSE_CLUSTER_NAME)
    exact, fuzzy = [], []
    for c in clusters:
        name = (c.cluster_name or "").strip()
        if name.lower() == want:
            exact.append(c)
        elif want_n and want_n in _norm_name(name):
            fuzzy.append(c)
    picked = (exact or fuzzy)
    if not picked:
        listed = ", ".join((c.cluster_name or c.cluster_id or "?") for c in clusters[:8]) or "none"
        return None, (
            f"Cluster '{ALL_PURPOSE_CLUSTER_NAME}' is not visible to the app principal "
            f"(listed {len(clusters)}: {listed}). "
            "Set workspace.cluster_id so Score can attach to onr demo cluster."
        )
    c = picked[0]
    state = str(getattr(c, "state", "") or "").upper()
    if "RUNNING" not in state:
        try:
            w.clusters.start(c.cluster_id)
        except Exception as e:
            return c.cluster_id, f"Cluster start requested ({e})"
        return c.cluster_id, f"Starting {c.cluster_name}"
    return c.cluster_id, f"{c.cluster_name} is running"


def _notebook_task_kwargs(path: str, params: dict | None) -> dict:
    from databricks.sdk.service import jobs

    nb_kwargs = {
        "notebook_path": path,
        "base_parameters": {k: str(v) for k, v in (params or {}).items()},
    }
    source = getattr(jobs, "Source", None)
    if source is not None and hasattr(source, "WORKSPACE"):
        nb_kwargs["source"] = source.WORKSPACE
    return nb_kwargs


def _finish_submit(w, waiter, path: str, compute: str) -> dict:
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
        "cluster": compute,
        "via": "serverless" if "serverless" in compute.lower() else "cluster",
    }


def submit_notebook_serverless(path: str, run_name: str, params: dict | None = None) -> dict:
    """Submit 01b on Jobs serverless. Do not use this for 04c — Score needs the cluster."""
    from databricks.sdk.service import jobs

    params = dict(params or {})
    # Jobs serverless / Spark Connect rejects ProcessingTime
    # (INFINITE_STREAMING_TRIGGER_NOT_SUPPORTED). availableNow is the
    # only legal streaming trigger on this cluster type.
    if "01b" in path or "streaming_autoloader" in path:
        params.setdefault("trigger_mode", "availableNow")

    w = _client()
    nb = jobs.NotebookTask(**_notebook_task_kwargs(path, params))
    JobEnvironment = getattr(jobs, "JobEnvironment", None)
    Environment = getattr(jobs, "Environment", None)
    # 04c needs mlflow on Jobs serverless (standard env does not ship it).
    # 01b does not. Extra deps are ignored if the Environment ctor rejects them.
    score_deps = None
    if "04c" in path or "score_registered" in path:
        score_deps = ["mlflow>=2.14,<3", "scikit-learn", "pandas"]
    errors: list[str] = []
    if JobEnvironment and Environment:
        for version in ("3", "2", "1"):
            try:
                spec_kwargs = {"environment_version": version}
                if score_deps:
                    spec_kwargs["dependencies"] = score_deps
                try:
                    spec = Environment(**spec_kwargs)
                except TypeError:
                    spec = Environment(environment_version=version)
                waiter = w.jobs.submit(
                    run_name=run_name,
                    tasks=[
                        jobs.SubmitTask(
                            task_key="run",
                            notebook_task=nb,
                            environment_key="default",
                        )
                    ],
                    environments=[JobEnvironment(environment_key="default", spec=spec)],
                )
                return _finish_submit(w, waiter, path, f"serverless jobs env {version}")
            except TypeError as e:
                errors.append(f"env {version} type: {e}")
            except Exception as e:
                errors.append(f"env {version}: {e}")
    try:
        waiter = w.jobs.submit(
            run_name=run_name,
            tasks=[jobs.SubmitTask(task_key="run", notebook_task=nb)],
        )
        return _finish_submit(w, waiter, path, "serverless jobs default")
    except Exception as e:
        errors.append(str(e))
    raise RuntimeError("Serverless job submit failed: " + " | ".join(errors[:4]))


def submit_notebook_cluster(path: str, run_name: str, params: dict | None = None) -> dict:
    """Submit a notebook on onr demo cluster. Never Jobs serverless."""
    from databricks.sdk.service import jobs

    cluster_id, cluster_msg = start_named_cluster()
    if not cluster_id:
        raise RuntimeError(
            f"{cluster_msg} Score registered models runs 04c on onr demo cluster "
            "(mlflow is installed there). Start that cluster and grant the app SP "
            "CAN ATTACH TO / CAN RESTART."
        )
    w = _client()
    task = jobs.SubmitTask(
        task_key="run",
        existing_cluster_id=cluster_id,
        notebook_task=jobs.NotebookTask(**_notebook_task_kwargs(path, params)),
    )
    waiter = w.jobs.submit(run_name=run_name, tasks=[task])
    rec = _finish_submit(w, waiter, path, cluster_msg)
    rec["via"] = "cluster"
    return rec


def submit_notebook(path: str, run_name: str, params: dict | None = None) -> dict:
    """Prefer Jobs serverless, then the named all-purpose cluster."""
    from databricks.sdk.service import jobs

    serverless_error = None
    try:
        return submit_notebook_serverless(path, run_name, params)
    except Exception as e:
        serverless_error = e

    cluster_id, cluster_msg = start_named_cluster()
    if not cluster_id:
        raise RuntimeError(
            f"{cluster_msg} Serverless job also failed ({serverless_error})."
        )
    w = _client()
    task = jobs.SubmitTask(
        task_key="run",
        existing_cluster_id=cluster_id,
        notebook_task=jobs.NotebookTask(**_notebook_task_kwargs(path, params)),
    )
    waiter = w.jobs.submit(run_name=run_name, tasks=[task])
    rec = _finish_submit(w, waiter, path, cluster_msg)
    rec["serverless_error"] = str(serverless_error)
    return rec


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
    """Place a *new* Auto Loader path on the landing Volume.

    Auto Loader checkpoints by file path. Overwriting
    ``batch_live_grants_stream.csv`` after Restore looks like the same file,
    so availableNow loads 0 rows. A timestamped name is always new.
    """
    from datetime import datetime, timezone

    src_vol = f"/Volumes/{catalog}/bronze/landing/_staged/batch_live_grants.csv"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dst = f"/Volumes/{catalog}/bronze/landing/grants/batch_live_grants_stream_{stamp}.csv"
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
    """Land the stream CSV, try Auto Loader on serverless/cluster, else warehouse load.

    SQL warehouses cannot run spark.readStream / cloudFiles. They can still
    INSERT the same Volume file into bronze.grants so the heartbeat ticks.
    """
    landed = copy_stream_file(catalog)
    # Browser link can point at the human Git folder. Job submit cannot —
    # the app SP is not that user.
    path = resolve_notebook(STREAM_NOTEBOOK)
    # Always overwrite Shared 01b so a stale processingTime copy cannot keep failing.
    run_path = runnable_notebook_path(STREAM_NOTEBOOK, refresh=True)
    run = None
    error = None
    via = None
    warehouse = None
    if run_path:
        try:
            run = submit_notebook(
                run_path,
                run_name="onr-demo-stream",
                params={
                    "catalog": catalog,
                    "processing_seconds": "30",
                    "run_for_seconds": "90",
                    # File is already landed. Serverless cannot run ProcessingTime.
                    "trigger_mode": "availableNow",
                },
            )
            via = (run or {}).get("via") or "cluster"
        except Exception as e:
            error = str(e)
    else:
        error = (
            "App principal cannot read the stream notebook under the user folder. "
            "Open stream notebook runs as you. Bronze will load on the warehouse."
        )

    if run is None:
        try:
            from utils.db_helpers import get_connection
            from utils.demo_actions import ingest_volume_csv_sql

            _conn, cursor = get_connection()
            if not cursor:
                raise RuntimeError("SQL warehouse is not connected")
            warehouse = ingest_volume_csv_sql(cursor, catalog, landed["dst"], "stream-demo-2026")
            try:
                from utils.demo_actions import refresh_silver_gold_sql

                refresh_silver_gold_sql(cursor, catalog, quality_pipeline="stream_warehouse")
                warehouse["silver_published"] = True
            except Exception as pub_e:
                warehouse["silver_published"] = False
                warehouse["publish_error"] = str(pub_e)
            via = "warehouse"
            # Bronze loaded. Cluster/serverless miss is an explanation, not a hard fail.
            error = None
        except Exception as e:
            extra = str(e)
            error = f"{error} Warehouse file load also failed ({extra})." if error else extra

    return {
        "file": landed,
        "run": run,
        "error": error,
        "notebook": path,
        "via": via,
        "warehouse": warehouse,
        "bronze": (warehouse or {}).get("after"),
        "inserted": (warehouse or {}).get("inserted"),
    }


def start_score(catalog: str = "onr_demo") -> dict:
    """Score UC models by running 04c on onr demo cluster. Not serverless."""
    path = resolve_notebook(SCORE_NOTEBOOK)
    run_path = runnable_notebook_path(SCORE_NOTEBOOK, refresh=True)
    if not run_path:
        raise RuntimeError(
            "App principal cannot read 04c. Open the scoring notebook on "
            "onr demo cluster and Run all, or grant the app CAN READ on the Shared copy."
        )
    try:
        run = submit_notebook_cluster(
            run_path, run_name="onr-demo-score", params={"catalog": catalog}
        )
        return {
            "run": run,
            "via": "cluster",
            "notebook": path,
        }
    except Exception as e:
        raise RuntimeError(
            f"Could not submit 04c on onr demo cluster ({e}). "
            "Start that cluster and grant the app SP CAN ATTACH TO / CAN RESTART. "
            "Or open the scoring notebook and Run all as yourself."
        ) from e


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
        {"kind": "table", "schema": "app", "table": "quarantine_log", "label": "quarantine_log"},
        {"kind": "table", "schema": "app", "table": "quality_findings", "label": "quality_findings"},
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
            path = resolve_notebook(name) if name else None
            url = notebook_url(path or guessed_notebook_path(name or ""))
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
    missing_nb = [
        raw.get("label")
        for raw, item in zip(spec, items)
        if raw.get("kind") == "notebook" and not item.get("url")
    ]
    if missing_nb and not repo_root():
        st.caption(
            "Notebook links need the Git folder path. Set `workspace.repo_root` in "
            "`config/onr-conf.yaml` to `/Workspace/Users/<you>/onr_demo` and restart the app."
        )


def workspace_action_row(label: str, url: str | None) -> None:
    if url:
        st.link_button(label, url)
    else:
        st.caption(f"{label} — workspace host not resolved")


def render_run_status(kind: str, payload: dict | None) -> None:
    if not payload:
        return
    scored = payload.get("scored") or {}
    if scored:
        bits = (
            f"{kind} · warehouse · "
            f"RF {scored.get('n_rf', '—')} · IF {scored.get('n_if', '—')} · "
            f"flagged {scored.get('n_flag', '—')}"
        )
        st.caption(bits)
        if scored.get("rf_uri"):
            st.caption(f"{scored.get('rf_uri')} · {scored.get('if_uri')}")
        if payload.get("error"):
            st.caption(payload["error"])
        return
    if payload.get("via") == "warehouse" and payload.get("file"):
        inserted = payload.get("inserted")
        bronze = payload.get("bronze")
        st.caption(
            f"{kind} · warehouse file load · bronze {bronze if bronze is not None else '—'} · "
            f"+{inserted if inserted is not None else '—'}"
        )
        st.caption(
            "SQL warehouses cannot run Auto Loader (cloudFiles). "
            "The same Volume file was appended to bronze.grants so the landing heartbeat ticks. "
            "Open the stream notebook for the Spark Auto Loader run."
        )
        landed = (payload.get("file") or {}).get("dst")
        if landed:
            st.caption(f"Landed {landed}")
        if payload.get("error"):
            st.caption(payload["error"])
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
    cluster = (run.get("cluster") or payload.get("cluster") or "")
    if payload.get("via") == "cluster" or (cluster and "serverless" not in str(cluster).lower()):
        if cluster:
            bits += f" · {cluster}"
    st.caption(bits)
    if page:
        st.link_button("Open run", page)
    if payload.get("error"):
        st.caption(payload["error"])
    landed = (payload.get("file") or {}).get("dst")
    if landed:
        st.caption(f"Landed {landed}")
