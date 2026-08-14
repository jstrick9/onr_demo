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


def render_decision_support(cursor=None, catalog: str = "onr_demo"):
    """Leadership cards from silver/gold, not invented totals."""
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", f"${k['total_funding']/1e6:.1f}M")
    c2.metric("Grants", f"{k['grant_count']:,}")
    c3.metric("Awardees", f"{k.get('awardee_count', 0):,}")
    c4.metric("ERP execution", f"{k['execution_rate']:.1f}%")

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
    st.caption(
        "Refresh gold via Process selected files or notebooks 03 / 04. "
        "Forecast + trend IDs land in `gold.funding_forecast` / `gold.program_trends`. "
        "Run `04_mlflow_grant_model.py` on **onr demo cluster** to replace heuristic scores with the RF model."
    )


def render_grant_predictions(cursor, catalog: str, schema: str = "silver"):
    """Scores from gold.grant_predictions (UC)."""
    st.markdown("### Grant scores")
    st.caption("`onr_demo.gold.grant_predictions` — heuristic after ingest, Random Forest after notebook 04.")
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
        st.info("No `gold.grant_predictions` yet. Process files or run 00_bootstrap / 03 / 04.")
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
    """Point at the cluster notebook; do not fake a training run."""
    st.markdown("### Train / refresh the model")
    st.markdown(
        "On **onr demo cluster** run `notebooks/04_mlflow_grant_model.py`. "
        "It trains on `silver.grants`, writes `gold.grant_predictions` + `gold.model_metrics`, "
        "registers `onr_demo.gold.grant_large_award` in Unity Catalog, "
        "and logs to MLflow `/Shared/onr-demo/grant-size`."
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
        st.info("No forecast rows yet. Process files or run notebook 03.")
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
    st.plotly_chart(fig, use_container_width=True)

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
    if df.empty:
        st.info("No `gold.model_metrics` yet. Process files / bootstrap writes heuristic rows; run notebook 04 for RF accuracy/f1.")
        return
    st.dataframe(df, use_container_width=True)
