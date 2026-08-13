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
        cols = [d[0] for d in cursor.description]
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
            lines.append(f"- **{area}**: ${fund:,.0f} across {n} grants")
        st.markdown("Largest program areas in gold / fixture:\n" + "\n".join(lines))
    st.caption("Refresh gold via Process selected files or notebooks 03 / 04. Run `04_mlflow_grant_model.py` on **onr demo cluster** to replace heuristic scores with the RF model.")


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
        "and logs to MLflow `/Shared/onr-demo/grant-size` when that experiment exists."
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


def render_forecast_visualization(cursor=None, catalog: str = "onr_demo"):
    """Actual ERP spend by FY from UC, plus a one-year extension of observed YoY."""
    st.markdown("### Budget by fiscal year")
    df = _query_df(
        cursor,
        f"""
        SELECT fiscal_year, SUM(actual_expenditure) / 1e6 AS actual_m
        FROM `{catalog}`.`silver`.financial
        WHERE _is_active = true
        GROUP BY fiscal_year
        ORDER BY fiscal_year
        """,
    )
    if df.empty:
        from utils.portfolio_data import financial_dataframe
        f = financial_dataframe()
        df = (
            f.groupby("fiscal_year", as_index=False)
            .agg(actual_m=("actual_expenditure", "sum"))
        )
        df["actual_m"] = df["actual_m"] / 1e6
        st.caption("Warehouse unavailable — Compass fixture ERP.")
    else:
        st.caption("`silver.financial` actuals. Next-year point = last year × mean YoY (not a trained forecast).")

    df = df.sort_values(df.columns[0])
    years = [int(y) for y in df.iloc[:, 0].tolist()]
    actual = [float(v) for v in df.iloc[:, 1].tolist()]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=actual, name="Actual ($M)", marker_color="steelblue"))
    if len(actual) >= 2 and actual[-2] != 0:
        growths = []
        for i in range(1, len(actual)):
            if actual[i - 1]:
                growths.append(actual[i] / actual[i - 1])
        g = sum(growths) / len(growths) if growths else 1.0
        nxt = years[-1] + 1
        fig.add_trace(go.Bar(x=[nxt], y=[actual[-1] * g], name=f"YoY extension FY{nxt}", marker_color="lightgray"))
    fig.update_layout(yaxis_title="Actual spend ($M)", height=400, barmode="group")
    st.plotly_chart(fig, use_container_width=True)


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
        st.info("Run `04_mlflow_grant_model.py` on **onr demo cluster** to populate `gold.model_metrics`.")
        return
    st.dataframe(df, use_container_width=True)
