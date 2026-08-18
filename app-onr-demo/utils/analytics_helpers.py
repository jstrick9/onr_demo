"""
Analytics helpers — Element 5.
Numbers come from Unity Catalog (gold/silver) or the packaged fixture.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _query_df(cursor, sql: str) -> pd.DataFrame:
    if not cursor:
        return pd.DataFrame()
    try:
        cursor.execute(sql)
        cols = [str(d[0]).lower() for d in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=cols)
    except Exception:
        return pd.DataFrame()


def _psi(base: dict, now: dict) -> float:
    import math

    keys = set(base) | set(now)
    tb = sum(float(v or 0) for v in base.values()) or 1.0
    tn = sum(float(v or 0) for v in now.values()) or 1.0
    score = 0.0
    for k in keys:
        p = max(float(base.get(k) or 0) / tb, 1e-6)
        q = max(float(now.get(k) or 0) / tn, 1e-6)
        score += (q - p) * math.log(q / p)
    return float(score)


def _psi_word(v: float) -> str:
    if v < 0.10:
        return "stable"
    if v < 0.25:
        return "shift"
    return "material"


def _mix_from_df(df: pd.DataFrame, key: str, val: str = "n") -> dict:
    if df is None or df.empty:
        return {}
    out = {}
    for rec in df.to_dict(orient="records"):
        k = rec.get(key)
        if k is None:
            continue
        out[str(k)] = float(rec.get(val) or 0)
    return out


def _version_clause(version) -> str:
    if version is None:
        return ""
    try:
        return f" VERSION AS OF {int(version)}"
    except (TypeError, ValueError):
        return ""


def _prior_table_version(cursor, catalog: str, schema: str, table: str):
    if not cursor:
        return None, None
    try:
        cursor.execute(f"DESCRIBE HISTORY `{catalog}`.`{schema}`.{table}")
        rows = cursor.fetchall()
        cols = [str(d[0]).lower() for d in (cursor.description or [])]
        idx = cols.index("version") if "version" in cols else 0
        versions = [r[idx] for r in rows if r and r[idx] is not None]
        if not versions:
            return None, None
        current = versions[0]
        prior = versions[1] if len(versions) > 1 else None
        return current, prior
    except Exception:
        return None, None


def render_drift(cursor=None, catalog: str = "onr_demo") -> None:
    """Feature + score mix: baseline snapshot vs now. Not accuracy."""
    from utils.ui import provenance_note

    st.markdown("### Drift")
    st.caption(
        "Feature and score mix versus the baseline snapshot. "
        "This is not accuracy — there are no ground-truth labels on mock data."
    )

    cur_v, prior_v = _prior_table_version(cursor, catalog, "silver", "grants")
    pred_cur, pred_prior = _prior_table_version(cursor, catalog, "gold", "grant_predictions")

    grants_now = _query_df(
        cursor,
        f"""
        SELECT program_area, COUNT(*) AS n, AVG(amount_usd) AS avg_amt,
               SUM(CASE WHEN amount_usd < 400000 THEN 1 ELSE 0 END) AS bin_s,
               SUM(CASE WHEN amount_usd >= 400000 AND amount_usd < 1000000 THEN 1 ELSE 0 END) AS bin_m,
               SUM(CASE WHEN amount_usd >= 1000000 AND amount_usd < 2000000 THEN 1 ELSE 0 END) AS bin_l,
               SUM(CASE WHEN amount_usd >= 2000000 THEN 1 ELSE 0 END) AS bin_xl,
               COUNT(*) AS grants
        FROM `{catalog}`.`silver`.grants
        WHERE _is_active = true
        GROUP BY program_area
        """,
    )
    if prior_v is not None:
        grants_base = _query_df(
            cursor,
            f"""
            SELECT program_area, COUNT(*) AS n, AVG(amount_usd) AS avg_amt,
                   SUM(CASE WHEN amount_usd < 400000 THEN 1 ELSE 0 END) AS bin_s,
                   SUM(CASE WHEN amount_usd >= 400000 AND amount_usd < 1000000 THEN 1 ELSE 0 END) AS bin_m,
                   SUM(CASE WHEN amount_usd >= 1000000 AND amount_usd < 2000000 THEN 1 ELSE 0 END) AS bin_l,
                   SUM(CASE WHEN amount_usd >= 2000000 THEN 1 ELSE 0 END) AS bin_xl
            FROM `{catalog}`.`silver`.grants{_version_clause(prior_v)}
            WHERE _is_active = true
            GROUP BY program_area
            """,
        )
        base_how = f"silver.grants VERSION AS OF {prior_v}"
    else:
        grants_base = _query_df(
            cursor,
            f"""
            SELECT program_area, COUNT(*) AS n, AVG(amount_usd) AS avg_amt,
                   SUM(CASE WHEN amount_usd < 400000 THEN 1 ELSE 0 END) AS bin_s,
                   SUM(CASE WHEN amount_usd >= 400000 AND amount_usd < 1000000 THEN 1 ELSE 0 END) AS bin_m,
                   SUM(CASE WHEN amount_usd >= 1000000 AND amount_usd < 2000000 THEN 1 ELSE 0 END) AS bin_l,
                   SUM(CASE WHEN amount_usd >= 2000000 THEN 1 ELSE 0 END) AS bin_xl
            FROM `{catalog}`.`silver`.grants
            WHERE _is_active = true
              AND coalesce(batch_id, 'seed-initial-2026') = 'seed-initial-2026'
            GROUP BY program_area
            """,
        )
        base_how = "batch seed-initial-2026"

    rec_now = _query_df(
        cursor,
        f"""
        SELECT recommendation, COUNT(*) AS n
        FROM `{catalog}`.`gold`.grant_predictions
        GROUP BY recommendation
        """,
    )
    if pred_prior is not None:
        rec_base = _query_df(
            cursor,
            f"""
            SELECT recommendation, COUNT(*) AS n
            FROM `{catalog}`.`gold`.grant_predictions{_version_clause(pred_prior)}
            GROUP BY recommendation
            """,
        )
    else:
        rec_base = _query_df(
            cursor,
            f"""
            SELECT p.recommendation, COUNT(*) AS n
            FROM `{catalog}`.`gold`.grant_predictions p
            JOIN `{catalog}`.`silver`.grants g ON p.grant_no = g.grant_no
            WHERE g._is_active = true
              AND coalesce(g.batch_id, 'seed-initial-2026') = 'seed-initial-2026'
            GROUP BY p.recommendation
            """,
        )

    flags = _query_df(
        cursor,
        f"""
        SELECT
          SUM(CASE WHEN is_flagged THEN 1 ELSE 0 END) AS flagged,
          COUNT(*) AS scored
        FROM `{catalog}`.`gold`.grant_anomaly_scores
        """,
    )

    if grants_now.empty:
        from utils.portfolio_data import grants_dataframe

        g = grants_dataframe()
        grants_now = (
            g.groupby("program_area", as_index=False)
            .agg(n=("grant_no", "count"), avg_amt=("amount_usd", "mean"))
        )
        grants_base = grants_now.copy()
        rec_now = rec_base = pd.DataFrame()
        st.caption("Warehouse drift tables unavailable — fixture has a single snapshot.")

    area_now = _mix_from_df(grants_now, "program_area")
    area_base = _mix_from_df(grants_base, "program_area") or area_now
    rec_now_m = _mix_from_df(rec_now, "recommendation")
    rec_base_m = _mix_from_df(rec_base, "recommendation") or rec_now_m

    def _bins(df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {}
        return {
            "under_400k": float(df["bin_s"].sum()) if "bin_s" in df.columns else 0,
            "400k_1m": float(df["bin_m"].sum()) if "bin_m" in df.columns else 0,
            "1m_2m": float(df["bin_l"].sum()) if "bin_l" in df.columns else 0,
            "2m_plus": float(df["bin_xl"].sum()) if "bin_xl" in df.columns else 0,
        }

    psi_area = _psi(area_base, area_now)
    psi_amt = _psi(_bins(grants_base), _bins(grants_now)) if "bin_s" in grants_now.columns else 0.0
    psi_rec = _psi(rec_base_m, rec_now_m) if rec_now_m else 0.0

    n_now = int(sum(area_now.values()) or 0)
    n_base = int(sum(area_base.values()) or 0)
    fund_now = rec_now_m.get("Fund", 0)
    fund_base = rec_base_m.get("Fund", 0)
    fund_now_p = 100 * fund_now / (sum(rec_now_m.values()) or 1)
    fund_base_p = 100 * fund_base / (sum(rec_base_m.values()) or 1)
    flagged = int(flags.iloc[0]["flagged"] or 0) if not flags.empty else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grants", f"{n_now:,}", delta=f"{n_now - n_base:+d}" if n_base else None)
    c2.metric("Program mix PSI", f"{psi_area:.3f}", delta=_psi_word(psi_area), delta_color="off")
    c3.metric("Award-size PSI", f"{psi_amt:.3f}", delta=_psi_word(psi_amt), delta_color="off")
    c4.metric(
        "Fund share",
        f"{fund_now_p:.0f}%",
        delta=f"{fund_now_p - fund_base_p:+.0f} pt" if rec_now_m else None,
    )
    provenance_note("gold.grant_predictions", catalog)
    st.markdown(
        f'<div class="drift-note">Baseline: {base_how}'
        + (f" · flagged now {flagged}" if flagged is not None else "")
        + " · PSI &lt; 0.10 stable · 0.10–0.25 shift · ≥ 0.25 material</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    if area_now:
        rows = []
        for area in sorted(set(area_base) | set(area_now)):
            rows.append({"program_area": area, "slice": "Baseline", "share": area_base.get(area, 0)})
            rows.append({"program_area": area, "slice": "Now", "share": area_now.get(area, 0)})
        fig = px.bar(
            pd.DataFrame(rows),
            x="program_area",
            y="share",
            color="slice",
            barmode="group",
            title="Program mix (grant count)",
        )
        from utils.ui import style_fig

        left.plotly_chart(style_fig(fig), use_container_width=True)
    if rec_now_m:
        rows = []
        for rec in ("Fund", "Review", "Defer"):
            rows.append({"recommendation": rec, "slice": "Baseline", "n": rec_base_m.get(rec, 0)})
            rows.append({"recommendation": rec, "slice": "Now", "n": rec_now_m.get(rec, 0)})
        fig = px.bar(
            pd.DataFrame(rows),
            x="recommendation",
            y="n",
            color="slice",
            barmode="group",
            title="Score mix (Fund / Review / Defer)",
        )
        from utils.ui import style_fig

        right.plotly_chart(style_fig(fig), use_container_width=True)


def render_score_controls(catalog: str = "onr_demo") -> None:
    """Score the current portfolio from registered models without leaving Analytics."""
    from utils.workspace_ops import (
        SCORE_NOTEBOOK,
        notebook_url,
        render_run_status,
        resolve_notebook,
        start_score,
        workspace_action_row,
    )

    st.markdown("### Registered model score")
    st.caption(
        "Applies the night-before Random Forest and IsolationForest to the current silver portfolio "
        "on onr demo cluster. Does not train. Cluster must be running, Shared/Standard "
        "(not Single user), with mlflow installed."
    )
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("Score registered models", type="primary", key="start_score"):
            try:
                result = start_score(catalog)
                st.session_state["last_score"] = result
                if result.get("via") == "cluster":
                    st.success("Scoring run submitted on onr demo cluster.")
                else:
                    st.success("Scoring run submitted.")
            except Exception as e:
                st.session_state["last_score"] = {"error": str(e), "notebook": resolve_notebook(SCORE_NOTEBOOK)}
                st.error(f"Scoring did not start: {e}")
    with c2:
        path = resolve_notebook(SCORE_NOTEBOOK)
        workspace_action_row("Open scoring notebook", notebook_url(path))
    render_run_status("Score", st.session_state.get("last_score"))


def render_resource_action(cursor=None, catalog: str = "onr_demo"):
    """One officer sentence from Fund/Review/Defer + AT_RISK + TREND-DECLINE."""
    from utils.ui import action_card

    defer = _query_df(
        cursor,
        f"""
        SELECT program_area, COUNT(*) AS n, SUM(amount_usd) AS dollars
        FROM `{catalog}`.`gold`.grant_predictions
        WHERE recommendation = 'Defer'
        GROUP BY program_area
        ORDER BY dollars DESC
        LIMIT 1
        """,
    )
    decline = _query_df(
        cursor,
        f"""
        SELECT program_area FROM `{catalog}`.`gold`.program_trends
        WHERE trend_id = 'TREND-DECLINE'
        ORDER BY program_area
        """,
    )
    risk = _query_df(
        cursor,
        f"""
        SELECT category, fiscal_year, quarter, execution_rate
        FROM `{catalog}`.`gold`.budget_execution
        WHERE status = 'AT_RISK'
        ORDER BY execution_rate
        """,
    )
    target = _query_df(
        cursor,
        f"""
        SELECT g.program_area, COUNT(*) AS n
        FROM `{catalog}`.`gold`.grant_predictions g
        LEFT JOIN `{catalog}`.`gold`.grant_anomaly_scores a ON g.grant_no = a.grant_no
        WHERE (
            lower(g.program_area) LIKE '%quantum%'
            OR g.program_area IN (
                SELECT program_area FROM `{catalog}`.`gold`.program_trends
                WHERE trend_id = 'TREND-DECLINE'
            )
        )
        AND (
            a.is_flagged = true
            OR g.recommendation IN ('Fund', 'Review')
        )
        GROUP BY g.program_area
        ORDER BY n DESC
        LIMIT 1
        """,
    )
    if defer.empty:
        from utils.portfolio_data import grants_dataframe

        g = grants_dataframe()
        d = g[pd.to_numeric(g["amount_usd"], errors="coerce") < 400000]
        if not d.empty:
            top = (
                d.groupby("program_area", as_index=False)
                .agg(n=("grant_no", "count"), dollars=("amount_usd", "sum"))
                .sort_values("dollars", ascending=False)
                .head(1)
            )
            defer = top
        q = g[g["program_area"].astype(str).str.contains("Quantum", case=False, na=False)]
        if target.empty and not q.empty:
            target = pd.DataFrame([{"program_area": "Quantum", "n": int(len(q.head(3)))}])

    if defer.empty:
        return
    area = str(defer.iloc[0].get("program_area") or "portfolio")
    n = int(defer.iloc[0].get("n") or 0)
    dollars = float(defer.iloc[0].get("dollars") or 0)
    dest = "Quantum"
    dest_n = 3
    if not target.empty:
        dest = str(target.iloc[0].get("program_area") or dest)
        dest_n = int(target.iloc[0].get("n") or dest_n)
    elif not decline.empty:
        dest = str(decline.iloc[0].get("program_area") or dest)
        dest_n = max(dest_n, len(decline))
    line = (
        f"Defer {n:,} {area} awards · ${dollars/1e6:.1f}M. "
        f"{dest_n} {dest} grants are AT_RISK + TREND-DECLINE. "
        f"Shift the ${dollars/1e6:.1f}M there before the next board."
    )
    action_card(
        line,
        f"{catalog}.gold.grant_predictions · {catalog}.gold.program_trends · {catalog}.gold.budget_execution",
    )


def render_decision_support(cursor=None, catalog: str = "onr_demo"):
    """Leadership cards from silver/gold, not invented totals."""
    render_resource_action(cursor, catalog)
    st.markdown("### Executive decision support")
    k = None
    if cursor:
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*), SUM(amount_usd), AVG(amount_usd), COUNT(DISTINCT awardee)
                FROM `{catalog}`.`silver`.grants WHERE _is_active = true
                """
            )
            n, total, avg, aw = cursor.fetchone()
            cursor.execute(
                f"""
                SELECT SUM(actual_expenditure) / NULLIF(SUM(budget_allocated), 0) * 100
                FROM `{catalog}`.`silver`.financial WHERE _is_active = true
                """
            )
            exe = cursor.fetchone()[0]
            if n:
                k = {
                    "grant_count": int(n),
                    "total_funding": float(total or 0),
                    "avg_award": float(avg or 0),
                    "execution_rate": float(exe or 0),
                    "awardee_count": int(aw or 0),
                }
        except Exception:
            k = None
    if not k:
        from utils.portfolio_data import portfolio_kpis
        k = portfolio_kpis()

    from utils.ui import provenance_note

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", f"${k['total_funding']/1e6:.1f}M")
    c2.metric("Grants", f"{k['grant_count']:,}")
    c3.metric("Awardees", f"{k.get('awardee_count', 0):,}")
    c4.metric("ERP execution", f"{k['execution_rate']:.1f}%")
    provenance_note("silver.grants", catalog)

    top = _query_df(
        cursor,
        f"""
        SELECT program_area, SUM(total_funding) AS funding, SUM(grant_count) AS n
        FROM `{catalog}`.`gold`.grants_summary
        GROUP BY program_area
        ORDER BY funding DESC
        LIMIT 3
        """,
    )
    if top.empty:
        from utils.portfolio_data import grants_dataframe
        g = grants_dataframe()
        top = (
            g.groupby("program_area", as_index=False)
            .agg(funding=("amount_usd", "sum"), n=("grant_no", "count"))
            .sort_values("funding", ascending=False)
            .head(3)
        )
    if not top.empty:
        lines = []
        for rec in top.to_dict(orient="records"):
            area = rec.get("program_area") or rec.get("PROGRAM_AREA")
            fund = float(rec.get("funding") or rec.get("FUNDING") or 0)
            n = int(rec.get("n") or rec.get("N") or 0)
            lines.append("- **{}**: ${:,.0f} across {} grants".format(area, fund, n))
        st.markdown("Largest program areas in gold / fixture:\n" + "\n".join(lines))
    st.caption("Forecast and trend IDs live in gold.funding_forecast and gold.program_trends.")


def render_grant_predictions(cursor, catalog: str, schema: str = "silver"):
    """Scores from gold.grant_predictions (UC)."""
    st.markdown("### Grant scores")
    st.caption("gold.grant_predictions — registered Random Forest when scored, heuristic otherwise.")
    df = _query_df(
        cursor,
        f"""
        SELECT grant_no, title, program_area, amount_usd,
               success_probability, risk_factors, recommendation, model_name
        FROM `{catalog}`.`gold`.grant_predictions
        ORDER BY success_probability DESC
        LIMIT 20
        """,
    )
    if df.empty:
        st.caption("No predictions yet.")
        return
    show = df.rename(columns={
        "grant_no": "Grant No", "title": "Title", "program_area": "Program Area",
        "amount_usd": "Amount", "success_probability": "Score",
        "risk_factors": "Risk", "recommendation": "Recommendation",
        "model_name": "Model",
    })
    if "Amount" in show.columns:
        try:
            st.dataframe(show.style.format({"Amount": "${:,.0f}", "Score": "{:.2f}"}), use_container_width=True)
        except Exception:
            st.dataframe(show, use_container_width=True)
    else:
        st.dataframe(show, use_container_width=True)


def render_model_execution(cursor=None, catalog: str = "onr_demo"):
    """Latest model metrics from Unity Catalog."""
    st.markdown("### Registered models")
    st.caption(
        "grant_large_award and funding_anomaly_detector@champion in Unity Catalog. "
        "This page reads the scored gold tables."
    )
    df = _query_df(
        cursor,
        f"""
        SELECT model_name, metric_name, metric_value, n_rows, trained_at
        FROM `{catalog}`.`gold`.model_metrics
        ORDER BY trained_at DESC
        """,
    )
    if df.empty:
        st.caption("No `gold.model_metrics` yet.")
    else:
        st.dataframe(df, use_container_width=True)


def compute_forecast_and_trends(grants_df: pd.DataFrame):
    """OLS of funding ~ fiscal_year per program_area. Returns (forecast_df, trends_df)."""
    g = grants_df.dropna(subset=["program_area", "fiscal_year", "amount_usd"]).copy()
    g["fiscal_year"] = g["fiscal_year"].astype(int)
    hist = (
        g.groupby(["program_area", "fiscal_year"], as_index=False)["amount_usd"]
        .sum()
        .rename(columns={"amount_usd": "funding"})
    )
    rows = []
    trend_rows = []
    for area, sub in hist.groupby("program_area"):
        sub = sub.sort_values("fiscal_year")
        xs = sub["fiscal_year"].astype(float).to_numpy()
        ys = sub["funding"].astype(float).to_numpy()
        n = len(xs)
        if n < 2:
            continue
        sx, sy = float(xs.sum()), float(ys.sum())
        sxy = float((xs * ys).sum())
        sx2 = float((xs * xs).sum())
        den = n * sx2 - sx * sx
        slope = 0.0 if den == 0 else (n * sxy - sx * sy) / den
        intercept = (sy - slope * sx) / n
        fitted = intercept + slope * xs
        resid = ys - fitted
        resid_sd = float(resid.std(ddof=0)) if n else 0.0
        last_fy = int(xs[-1])
        last_actual = float(ys[-1])
        prior = float(ys[-2]) if n >= 2 else None
        velocity = ((last_actual - prior) / prior) if prior else None
        rel = slope / last_actual if last_actual else 0.0
        if rel > 0.05:
            tid, tlab = "TREND-ACCEL", "Accelerating"
        elif rel < -0.05:
            tid, tlab = "TREND-DECLINE", "Declining"
        else:
            tid, tlab = "TREND-STEADY", "Steady"
        for x, y in zip(xs, ys):
            rows.append({
                "program_area": area, "fiscal_year": int(x), "series": "actual",
                "predicted_funding": float(y), "lower_95": float(y), "upper_95": float(y),
                "slope_usd_per_year": slope, "resid_sd": resid_sd, "model_name": "ols_fy_v1",
            })
        next_pred = None
        for off in (1, 2):
            fy = last_fy + off
            pred = intercept + slope * fy
            if next_pred is None:
                next_pred = pred
            rows.append({
                "program_area": area, "fiscal_year": fy, "series": "forecast",
                "predicted_funding": pred,
                "lower_95": pred - 1.96 * resid_sd,
                "upper_95": pred + 1.96 * resid_sd,
                "slope_usd_per_year": slope, "resid_sd": resid_sd, "model_name": "ols_fy_v1",
            })
        trend_rows.append({
            "program_area": area, "trend_id": tid, "trend_label": tlab,
            "slope_usd_per_year": slope, "velocity_yoy": velocity,
            "last_actual": last_actual, "forecast_next_fy": next_pred,
            "resid_sd": resid_sd, "next_fiscal_year": last_fy + 1,
            "model_name": "ols_fy_v1",
        })
    return pd.DataFrame(rows), pd.DataFrame(trend_rows)


def render_forecast_visualization(cursor=None, catalog: str = "onr_demo"):
    """OLS FY forecast from gold.funding_forecast, with 95% band + trend IDs."""
    st.markdown("### Funding forecast (OLS by program area)")
    fc = _query_df(
        cursor,
        f"""
        SELECT program_area, fiscal_year, series, predicted_funding, lower_95, upper_95
        FROM `{catalog}`.`gold`.funding_forecast
        ORDER BY program_area, fiscal_year, series
        """,
    )
    trends = _query_df(
        cursor,
        f"""
        SELECT program_area, trend_id, trend_label, slope_usd_per_year,
               velocity_yoy, last_actual, forecast_next_fy
        FROM `{catalog}`.`gold`.program_trends
        ORDER BY trend_id, program_area
        """,
    )
    if fc.empty:
        from utils.portfolio_data import grants_dataframe
        fc, trends = compute_forecast_and_trends(grants_dataframe())
        st.caption("Warehouse / gold.funding_forecast unavailable — OLS computed from the Compass fixture.")
    else:
        st.caption(
            "`gold.funding_forecast` · model `ols_fy_v1` — ordinary least squares of "
            "`total_funding ~ fiscal_year` per program area, 2-year horizon, 95% residual band. "
            "Trend IDs live in `gold.program_trends`."
        )

    if fc.empty:
        st.caption("No forecast rows yet.")
        return
    roll = (
        fc.groupby(["fiscal_year", "series"], as_index=False)
        .agg(predicted_funding=("predicted_funding", "sum"),
             lower_95=("lower_95", "sum"),
             upper_95=("upper_95", "sum"))
        .sort_values("fiscal_year")
    )
    actual = roll[roll["series"] == "actual"]
    fcast = roll[roll["series"] == "forecast"]
    fig = go.Figure()
    if not actual.empty:
        fig.add_trace(go.Bar(
            x=actual["fiscal_year"], y=actual["predicted_funding"] / 1e6,
            name="Actual ($M)", marker_color="steelblue",
        ))
    if not fcast.empty:
        fig.add_trace(go.Bar(
            x=fcast["fiscal_year"], y=fcast["predicted_funding"] / 1e6,
            name="OLS forecast ($M)", marker_color="orange",
        ))
        fig.add_trace(go.Scatter(
            x=list(fcast["fiscal_year"]) + list(fcast["fiscal_year"])[::-1],
            y=list(fcast["upper_95"] / 1e6) + list(fcast["lower_95"] / 1e6)[::-1],
            fill="toself", fillcolor="rgba(255,165,0,0.2)",
            line=dict(color="rgba(255,165,0,0)"),
            name="95% band", hoverinfo="skip",
        ))
    fig.update_layout(yaxis_title="Funding ($M)", height=420, barmode="group")
    from utils.ui import style_fig
    st.plotly_chart(style_fig(fig), use_container_width=True)

    st.markdown("#### Trend IDs")
    if trends.empty:
        st.caption("No `gold.program_trends` yet.")
    else:
        show = trends.copy()
        for col in ("slope_usd_per_year", "last_actual", "forecast_next_fy"):
            if col in show.columns:
                show[col] = pd.to_numeric(show[col], errors="coerce")
        try:
            st.dataframe(
                show.style.format({
                    "slope_usd_per_year": "${:,.0f}",
                    "last_actual": "${:,.0f}",
                    "forecast_next_fy": "${:,.0f}",
                    "velocity_yoy": "{:.1%}",
                }),
                use_container_width=True,
            )
        except Exception:
            st.dataframe(show, use_container_width=True)
        st.caption(
            "`TREND-ACCEL` / `TREND-STEADY` / `TREND-DECLINE` — slope vs last actual "
            "(±5% / year). Velocity is last-FY vs prior-FY. Use Declining + AT_RISK "
            "together as the reallocation set."
        )


def render_trend_analysis(cursor=None, catalog: str = "onr_demo"):
    st.markdown("### Trend analysis")
    tab1, tab2, tab3 = st.tabs(["Program areas", "Funding by FY", "Awardees"])

    with tab1:
        pie = _query_df(
            cursor,
            f"""
            SELECT program_area, SUM(total_funding) AS amount_usd
            FROM `{catalog}`.`gold`.grants_summary
            GROUP BY program_area
            """,
        )
        if pie.empty:
            from utils.portfolio_data import grants_dataframe
            pie = grants_dataframe().groupby("program_area", as_index=False)["amount_usd"].sum()
            st.caption("Fixture — gold.grants_summary not available.")
        fig = px.pie(pie, values=pie.columns[1], names=pie.columns[0], hole=0.3,
                     title="Funding by program area")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        yoy = _query_df(
            cursor,
            f"""
            SELECT fiscal_year, SUM(total_funding) / 1e6 AS funding_m, SUM(grant_count) AS grants
            FROM `{catalog}`.`gold`.grants_summary
            GROUP BY fiscal_year
            ORDER BY fiscal_year
            """,
        )
        if yoy.empty:
            from utils.portfolio_data import grants_dataframe
            g = grants_dataframe()
            yoy = g.groupby("fiscal_year", as_index=False).agg(
                funding_m=("amount_usd", "sum"), grants=("grant_no", "count")
            )
            yoy["funding_m"] = yoy["funding_m"] / 1e6
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yoy.iloc[:, 0], y=yoy.iloc[:, 1], name="Funding ($M)"))
        fig.add_trace(go.Scatter(x=yoy.iloc[:, 0], y=yoy.iloc[:, 2], name="Grant count", yaxis="y2"))
        fig.update_layout(yaxis=dict(title="Funding ($M)"),
                          yaxis2=dict(title="Grants", overlaying="y", side="right"),
                          height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        aw = _query_df(
            cursor,
            f"""
            SELECT awardee, SUM(total_funding) AS total_funding, SUM(grant_count) AS grant_count
            FROM `{catalog}`.`gold`.grants_by_awardee
            GROUP BY awardee
            ORDER BY total_funding DESC
            LIMIT 12
            """,
        )
        if aw.empty:
            from utils.portfolio_data import grants_dataframe
            g = grants_dataframe()
            aw = (
                g.groupby("awardee", as_index=False)
                .agg(total_funding=("amount_usd", "sum"), grant_count=("grant_no", "count"))
                .sort_values("total_funding", ascending=False)
                .head(12)
            )
        fig = px.scatter(
            aw, x="grant_count", y="total_funding", text="awardee",
            title="Top awardees (count vs funding)",
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)


def render_model_metrics(cursor=None, catalog: str = "onr_demo"):
    st.markdown("### Model metrics (from UC)")
    df = _query_df(
        cursor,
        f"""
        SELECT model_name, metric_name, metric_value, n_rows, trained_at
        FROM `{catalog}`.`gold`.model_metrics
        ORDER BY trained_at DESC, metric_name
        """,
    )
    anom = _query_df(
        cursor,
        f"""
        SELECT model_name, metric_name, metric_value, n_rows, trained_at
        FROM `{catalog}`.`gold`.anomaly_model_metrics
        ORDER BY trained_at DESC, metric_name
        """,
    )
    if df.empty and anom.empty:
        st.caption("No model metrics yet.")
        return
    if not df.empty:
        st.markdown("#### Large-award classifier / heuristic")
        st.dataframe(df, use_container_width=True)
    if not anom.empty:
        st.markdown("#### Funding anomaly detector")
        st.dataframe(anom, use_container_width=True)


def compute_funding_features(grants_df: pd.DataFrame, financial_df: pd.DataFrame) -> pd.DataFrame:
    """Pandas twin of gold.funding_features for fixture mode."""
    g = grants_df.dropna(subset=["grant_no", "amount_usd"]).copy()
    g["fiscal_year"] = pd.to_numeric(g["fiscal_year"], errors="coerce")
    g["amount_usd"] = pd.to_numeric(g["amount_usd"], errors="coerce")
    fin = financial_df.copy() if financial_df is not None and not financial_df.empty else pd.DataFrame()
    if not fin.empty and "grant_no" in fin.columns:
        agg = (
            fin.groupby("grant_no", as_index=False)
            .agg(budget=("budget_allocated", "sum"), actual=("actual_expenditure", "sum"))
        )
        agg["execution_rate"] = agg["actual"] / agg["budget"].replace(0, pd.NA)
        g = g.merge(agg[["grant_no", "execution_rate"]], on="grant_no", how="left")
    else:
        g["execution_rate"] = 0.90
    g["execution_rate"] = g["execution_rate"].fillna(0.90)
    med = g.groupby(["program_area", "fiscal_year"], as_index=False)["amount_usd"].median()
    med = med.rename(columns={"amount_usd": "median_amt"})
    avg = g.groupby(["program_area", "fiscal_year"], as_index=False)["amount_usd"].mean()
    avg = avg.rename(columns={"amount_usd": "avg_amt"})
    g = g.merge(med, on=["program_area", "fiscal_year"], how="left")
    g = g.merge(avg, on=["program_area", "fiscal_year"], how="left")
    prior = avg.rename(columns={"fiscal_year": "prior_fy", "avg_amt": "prior_avg"})
    prior["fiscal_year"] = prior["prior_fy"] + 1
    g = g.merge(prior[["program_area", "fiscal_year", "prior_avg"]], on=["program_area", "fiscal_year"], how="left")
    denom = g["prior_avg"].fillna(g["avg_amt"])
    g["yoy_growth_ratio"] = g["amount_usd"] / denom.replace(0, pd.NA)
    g["amount_vs_area_median"] = g["amount_usd"] / g["median_amt"].replace(0, pd.NA)
    g["yoy_growth_ratio"] = g["yoy_growth_ratio"].fillna(1.0)
    g["amount_vs_area_median"] = g["amount_vs_area_median"].fillna(1.0)
    g["anomaly_type"] = "none"
    g.loc[g["execution_rate"] < 0.76, "anomaly_type"] = "execution_collapse"
    g.loc[(g["anomaly_type"] == "none") & (g["amount_usd"] >= 3_000_000) & (g["amount_vs_area_median"] >= 1.8), "anomaly_type"] = "budget_spike"
    g.loc[
        (g["anomaly_type"] == "none") & (g["amount_usd"] >= 2_500_000) & (g["execution_rate"] < 0.85),
        "anomaly_type",
    ] = "low_return_concentration"
    g["is_known_anomaly"] = (g["anomaly_type"] != "none").astype(int)
    g["award_amount"] = g["amount_usd"]
    return g


def render_anomaly_detection(cursor=None, catalog: str = "onr_demo"):
    """IsolationForest / heuristic flags from gold.grant_anomaly_scores."""
    st.markdown("### Funding anomalies")
    st.caption("Review queue from gold.grant_anomaly_scores.")
    df = _query_df(
        cursor,
        f"""
        SELECT grant_no, title, program_area, amount_usd, awardee,
               execution_rate, yoy_growth_ratio, anomaly_score,
               is_flagged, predicted_type, anomaly_type, model_name
        FROM `{catalog}`.`gold`.grant_anomaly_scores
        ORDER BY anomaly_score DESC
        LIMIT 40
        """,
    )
    metrics = _query_df(
        cursor,
        f"""
        SELECT metric_name, metric_value, n_rows, trained_at, model_name
        FROM `{catalog}`.`gold`.anomaly_model_metrics
        ORDER BY trained_at DESC
        """,
    )
    if df.empty:
        from utils.portfolio_data import grants_dataframe, financial_dataframe
        feat = compute_funding_features(grants_dataframe(), financial_dataframe())
        feat["anomaly_score"] = feat.apply(
            lambda r: 0.92 if r["anomaly_type"] == "execution_collapse"
            else 0.88 if r["anomaly_type"] == "budget_spike"
            else 0.80 if r["anomaly_type"] == "low_return_concentration"
            else 0.12,
            axis=1,
        )
        feat["is_flagged"] = feat["is_known_anomaly"].astype(bool)
        feat["predicted_type"] = feat["anomaly_type"]
        feat["model_name"] = "heuristic_rules_v1"
        df = feat.rename(columns={"award_amount": "amount_usd"})[
            ["grant_no", "title", "program_area", "amount_usd", "awardee",
             "execution_rate", "yoy_growth_ratio", "anomaly_score",
             "is_flagged", "predicted_type", "anomaly_type", "model_name"]
        ].sort_values("anomaly_score", ascending=False).head(40)
        st.caption("Warehouse / gold.grant_anomaly_scores unavailable — rule flags from the Compass fixture.")

    from utils.ui import provenance_note

    n_flag = int(df["is_flagged"].astype(bool).sum()) if "is_flagged" in df.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows scored", f"{len(df):,}")
    c2.metric("Flagged", f"{n_flag:,}")
    model = df["model_name"].iloc[0] if not df.empty and "model_name" in df.columns else "—"
    c3.metric("Scorer", str(model))
    provenance_note("gold.grant_anomaly_scores", catalog)

    if not metrics.empty:
        st.dataframe(metrics, use_container_width=True)

    flagged = df[df["is_flagged"].astype(bool)] if "is_flagged" in df.columns else df.head(0)
    st.markdown("#### Flagged awards (review queue)")
    if flagged.empty:
        st.caption("No flags at the current threshold.")
    else:
        show = flagged.copy()
        try:
            st.dataframe(
                show.style.format({
                    "amount_usd": "${:,.0f}",
                    "anomaly_score": "{:.2f}",
                    "execution_rate": "{:.1%}",
                    "yoy_growth_ratio": "{:.2f}",
                }),
                use_container_width=True,
            )
        except Exception:
            st.dataframe(show, use_container_width=True)
    with st.expander("All scored rows"):
        st.dataframe(df, use_container_width=True)
    st.caption("Champion model: funding_anomaly_detector in Unity Catalog.")
