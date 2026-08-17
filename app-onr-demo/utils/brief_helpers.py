"""
Daily Portfolio Brief — Element 6 process automation.
Tries Databricks SQL ai_query; falls back to a structured template so the
demo never hard-fails if Foundation Model APIs are not enabled.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import streamlit as st


AI_MODELS = (
    "databricks-meta-llama-3-3-70b-instruct",
    "databricks-meta-llama-3-1-70b-instruct",
    "databricks-llama-4-maverick",
)


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def _q(cursor, sql: str) -> pd.DataFrame:
    if not cursor:
        return pd.DataFrame()
    try:
        cursor.execute(sql)
        cols = [str(d[0]).lower() for d in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=cols)
    except Exception:
        return pd.DataFrame()


def _ensure_briefs_table(cursor, catalog: str) -> None:
    if not cursor:
        return
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{catalog}`.`app`.daily_briefs (
            brief_id STRING NOT NULL,
            generated_at TIMESTAMP,
            generated_by STRING,
            source STRING,
            model_name STRING,
            brief_text STRING,
            prompt_chars INT
        ) USING DELTA
        COMMENT 'Automated daily portfolio briefs (ai_query or template)'
        """
    )


def _context_from_uc(cursor, catalog: str) -> dict:
    ctx = {}
    k = _q(
        cursor,
        f"""
        SELECT COUNT(*) AS n, SUM(amount_usd) AS total, AVG(amount_usd) AS avg_award
        FROM `{catalog}`.`silver`.grants WHERE _is_active = true
        """,
    )
    if not k.empty:
        ctx["n"] = int(k.iloc[0]["n"] or 0)
        ctx["total"] = float(k.iloc[0]["total"] or 0)
        ctx["avg"] = float(k.iloc[0]["avg_award"] or 0)
    exe = _q(
        cursor,
        f"""
        SELECT SUM(actual_expenditure) / NULLIF(SUM(budget_allocated), 0) * 100 AS rate
        FROM `{catalog}`.`silver`.financial WHERE _is_active = true
        """,
    )
    ctx["exe"] = float(exe.iloc[0]["rate"] or 0) if not exe.empty else 0.0
    ctx["risk"] = _q(
        cursor,
        f"""
        SELECT fiscal_year, quarter, category, execution_rate, status
        FROM `{catalog}`.`gold`.budget_execution
        WHERE status IN ('WARNING', 'AT_RISK')
        ORDER BY execution_rate
        LIMIT 8
        """,
    )
    ctx["trends"] = _q(
        cursor,
        f"""
        SELECT program_area, trend_id, trend_label, velocity_yoy, forecast_next_fy
        FROM `{catalog}`.`gold`.program_trends
        ORDER BY trend_id, program_area
        """,
    )
    ctx["top"] = _q(
        cursor,
        f"""
        SELECT program_area, SUM(total_funding) AS funding
        FROM `{catalog}`.`gold`.grants_summary
        GROUP BY program_area
        ORDER BY funding DESC
        LIMIT 3
        """,
    )
    return ctx


def _context_from_fixture() -> dict:
    from utils.portfolio_data import grants_dataframe, financial_dataframe, portfolio_kpis
    from utils.analytics_helpers import compute_forecast_and_trends

    k = portfolio_kpis()
    g = grants_dataframe()
    f = financial_dataframe()
    _, trends = compute_forecast_and_trends(g)
    risk = (
        f.groupby(["fiscal_year", "quarter", "category"], as_index=False)
        .agg(budget=("budget_allocated", "sum"), actual=("actual_expenditure", "sum"))
    )
    risk["execution_rate"] = risk["actual"] / risk["budget"] * 100
    risk["status"] = risk["execution_rate"].map(
        lambda r: "ON_TARGET" if r >= 90 else ("WARNING" if r >= 80 else "AT_RISK")
    )
    risk = risk[risk["status"] != "ON_TARGET"].sort_values("execution_rate").head(8)
    top = (
        g.groupby("program_area", as_index=False)["amount_usd"]
        .sum()
        .rename(columns={"amount_usd": "funding"})
        .sort_values("funding", ascending=False)
        .head(3)
    )
    return {
        "n": k["grant_count"],
        "total": k["total_funding"],
        "avg": k["avg_award"],
        "exe": k["execution_rate"],
        "risk": risk,
        "trends": trends,
        "top": top,
    }


def _template_parts(ctx: dict) -> tuple[list[str], str]:
    n = ctx.get("n") or 0
    total = ctx.get("total") or 0
    exe = ctx.get("exe") or 0
    top = ctx.get("top")
    risk = ctx.get("risk")
    trends = ctx.get("trends")
    b1 = (
        f"Portfolio holds {n:,} active grants totaling ${total/1e6:.1f}M "
        f"(avg ${(total/n)/1e6 if n else 0:.2f}M). ERP execution is {exe:.1f}% of plan."
    )
    if isinstance(top, pd.DataFrame) and not top.empty:
        bits = []
        for rec in top.to_dict(orient="records"):
            area = rec.get("program_area")
            fund = float(rec.get("funding") or 0)
            bits.append(f"{area} ${fund/1e6:.1f}M")
        b2 = "Largest program areas: " + "; ".join(bits) + "."
    else:
        b2 = "Program-area mix is unchanged from the last gold refresh."
    decl = "none"
    accel = "none"
    if isinstance(trends, pd.DataFrame) and not trends.empty:
        tid = trends.get("trend_id", pd.Series(dtype=str)).astype(str)
        accel = ", ".join(trends[tid.str.contains("ACCEL", na=False)]["program_area"].astype(str)) or "none"
        decl = ", ".join(trends[tid.str.contains("DECLINE", na=False)]["program_area"].astype(str)) or "none"
    if isinstance(risk, pd.DataFrame) and not risk.empty:
        rows = []
        for rec in risk.head(3).to_dict(orient="records"):
            rows.append(
                f"{rec.get('category')} FY{rec.get('fiscal_year')} {rec.get('quarter')} "
                f"{rec.get('status')} ({float(rec.get('execution_rate') or 0):.0f}%)"
            )
        b3 = f"Trend IDs — accelerating {accel}; declining {decl}. Not ON_TARGET: " + "; ".join(rows) + "."
        action = (
            "Protect ON_TARGET categories, route AT_RISK and TREND-DECLINE to the next "
            "resource board, and hold large-award Fund recommendations until that review."
        )
    else:
        b3 = f"Trend IDs — accelerating {accel}; declining {decl}. All budget-execution rows are ON_TARGET this cycle."
        action = "Hold the current allocation. Revisit after the next gold refresh."
    return [b1, b2, b3], action


def _template_brief(ctx: dict) -> str:
    bullets, action = _template_parts(ctx)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = [f"DAILY PORTFOLIO BRIEF — {today} (UNCLASSIFIED // MOCK DATA)", ""]
    lines.extend(f"- {b}" for b in bullets)
    lines.append(f"ACTION: {action}")
    return "\n".join(lines)


def _parse_brief(text: str) -> tuple[list[str], str]:
    bullets, action = [], ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("ACTION:"):
            action = line.split(":", 1)[-1].strip()
            continue
        if line.startswith(("#", "DAILY ")):
            continue
        bullets.append(line.lstrip("-•* ").strip())
    return bullets[:3], action


def _prompt_from_ctx(ctx: dict) -> str:
    risk_txt = ""
    if isinstance(ctx.get("risk"), pd.DataFrame) and not ctx["risk"].empty:
        risk_txt = ctx["risk"].to_csv(index=False)
    trends_txt = ""
    if isinstance(ctx.get("trends"), pd.DataFrame) and not ctx["trends"].empty:
        trends_txt = ctx["trends"].to_csv(index=False)
    top_txt = ""
    if isinstance(ctx.get("top"), pd.DataFrame) and not ctx["top"].empty:
        top_txt = ctx["top"].to_csv(index=False)
    return (
        "You are a Code 08 resource officer. Use ONLY the numbers given. Mock data. "
        "Return EXACTLY three lines starting with '- ' and one line starting with 'ACTION:'. "
        "No headings. Be prescriptive.\n"
        f"Grants={ctx.get('n')} total_usd={ctx.get('total')} execution_pct={ctx.get('exe')}\n"
        f"TOP_AREAS:\n{top_txt}\nTRENDS:\n{trends_txt}\nAT_RISK:\n{risk_txt}"
    )


def _try_ai_query(cursor, prompt: str) -> tuple[str | None, str | None]:
    if not cursor:
        return None, None
    escaped = prompt.replace("'", "''")
    for model in AI_MODELS:
        try:
            cursor.execute(
                f"SELECT ai_query('{model}', '{escaped}') AS brief"
            )
            row = cursor.fetchone()
            if row and row[0]:
                return str(row[0]), model
        except Exception:
            continue
    return None, None


def _persist(cursor, catalog: str, rec: dict) -> None:
    if not cursor:
        return
    try:
        _ensure_briefs_table(cursor, catalog)
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`app`.daily_briefs
            (brief_id, generated_at, generated_by, source, model_name, brief_text, prompt_chars)
            VALUES (
                {_sql_str(rec['brief_id'])},
                CURRENT_TIMESTAMP(),
                {_sql_str(rec.get('user') or 'unknown')},
                {_sql_str(rec['source'])},
                {_sql_str(rec.get('model_name'))},
                {_sql_str(rec['brief_text'])},
                {int(rec.get('prompt_chars') or 0)}
            )
            """
        )
    except Exception:
        pass


def render_daily_brief(cursor=None, catalog: str = "onr_demo"):
    """On-demand automated summary for Element 6 + Strategic Prompt (b)."""
    st.markdown("### Daily Portfolio Brief")
    st.caption(
        "Process automation: an on-demand (and schedulable) summary from gold tables. "
        "Uses `ai_query` when Foundation Model APIs are enabled; otherwise a structured template. "
        "Persisted to `app.daily_briefs`."
    )

    if st.button("Generate daily brief", type="primary", key="gen_daily_brief"):
        ctx = _context_from_uc(cursor, catalog) if cursor else {}
        if not ctx.get("n"):
            ctx = _context_from_fixture()
            st.info("Warehouse context empty — brief built from the Compass fixture.")
        prompt = _prompt_from_ctx(ctx)
        text, model = _try_ai_query(cursor, prompt)
        if text:
            source = "ai_query"
            st.success(f"Generated with `ai_query` ({model}).")
        else:
            text = _template_brief(ctx)
            source = "template_fallback"
            model = None
            st.info(
                "`ai_query` not available in this workspace — showing the structured "
                "template brief (same gold inputs). Enable Foundation Model APIs to switch."
            )
        bullets, action = _parse_brief(text)
        if len(bullets) < 3 or not action:
            tb, ta = _template_parts(ctx)
            if len(bullets) < 3:
                bullets = (bullets + tb)[:3]
            action = action or ta
        rec = {
            "brief_id": f"brief-{uuid.uuid4().hex[:12]}",
            "source": source,
            "model_name": model,
            "brief_text": text,
            "bullets": bullets,
            "action": action,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "prompt_chars": len(prompt),
            "user": st.session_state.get("email") or "unknown",
        }
        _persist(cursor, catalog, rec)
        st.session_state["last_brief"] = rec

    rec = st.session_state.get("last_brief")
    if rec:
        from utils.ui import brief_sheet

        brief_sheet(rec)

    hist = _q(
        cursor,
        f"""
        SELECT generated_at, source, model_name, LEFT(brief_text, 160) AS preview
        FROM `{catalog}`.`app`.daily_briefs
        ORDER BY generated_at DESC
        LIMIT 8
        """,
    ) if cursor else pd.DataFrame()
    if not hist.empty:
        st.markdown("#### Recent briefs (`app.daily_briefs`)")
        st.dataframe(hist, use_container_width=True)
