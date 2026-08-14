"""OLS FY forecast + trend-ID SQL (Element 5). Shared by the app SQL path."""


def forecast_sql(catalog: str) -> str:
    return f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_forecast AS
        WITH hist AS (
            SELECT program_area,
                   CAST(fiscal_year AS DOUBLE) AS fy,
                   CAST(SUM(total_funding) AS DOUBLE) AS funding
            FROM `{catalog}`.`gold`.grants_summary
            GROUP BY program_area, fiscal_year
        ),
        stats AS (
            SELECT program_area,
                   COUNT(*) AS n,
                   SUM(fy) AS sx,
                   SUM(funding) AS sy,
                   SUM(fy * funding) AS sxy,
                   SUM(fy * fy) AS sx2,
                   MAX(fy) AS last_fy
            FROM hist
            GROUP BY program_area
        ),
        fit AS (
            SELECT program_area, n, last_fy, sx, sy,
                   CASE WHEN (n * sx2 - sx * sx) = 0 THEN 0.0
                        ELSE (n * sxy - sx * sy) / (n * sx2 - sx * sx) END AS slope
            FROM stats
        ),
        fit2 AS (
            SELECT *, (sy - slope * sx) / NULLIF(n, 0) AS intercept
            FROM fit
        ),
        resid AS (
            SELECT h.program_area,
                   STDDEV_POP(h.funding - (f.intercept + f.slope * h.fy)) AS resid_sd
            FROM hist h
            JOIN fit2 f ON h.program_area = f.program_area
            GROUP BY h.program_area
        ),
        actuals AS (
            SELECT h.program_area,
                   CAST(h.fy AS INT) AS fiscal_year,
                   'actual' AS series,
                   h.funding AS predicted_funding,
                   h.funding AS lower_95,
                   h.funding AS upper_95,
                   f.slope AS slope_usd_per_year,
                   f.intercept AS intercept_usd,
                   COALESCE(r.resid_sd, 0.0) AS resid_sd,
                   'ols_fy_v1' AS model_name
            FROM hist h
            JOIN fit2 f ON h.program_area = f.program_area
            LEFT JOIN resid r ON r.program_area = h.program_area
        ),
        horizon AS (
            SELECT f.program_area,
                   CAST(f.last_fy AS INT) + off AS fiscal_year,
                   f.slope, f.intercept,
                   COALESCE(r.resid_sd, 0.0) AS resid_sd
            FROM fit2 f
            LEFT JOIN resid r ON r.program_area = f.program_area
            LATERAL VIEW EXPLODE(ARRAY(1, 2)) t AS off
        ),
        forecasts AS (
            SELECT program_area,
                   fiscal_year,
                   'forecast' AS series,
                   intercept + slope * fiscal_year AS predicted_funding,
                   (intercept + slope * fiscal_year) - 1.96 * resid_sd AS lower_95,
                   (intercept + slope * fiscal_year) + 1.96 * resid_sd AS upper_95,
                   slope AS slope_usd_per_year,
                   intercept AS intercept_usd,
                   resid_sd,
                   'ols_fy_v1' AS model_name
            FROM horizon
        )
        SELECT * FROM actuals
        UNION ALL
        SELECT * FROM forecasts
    """


def trends_sql(catalog: str) -> str:
    return f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.program_trends AS
        WITH last2 AS (
            SELECT program_area, fiscal_year, SUM(total_funding) AS funding,
                   ROW_NUMBER() OVER (PARTITION BY program_area ORDER BY fiscal_year DESC) AS rn
            FROM `{catalog}`.`gold`.grants_summary
            GROUP BY program_area, fiscal_year
        ),
        vel AS (
            SELECT a.program_area,
                   a.funding AS last_actual,
                   b.funding AS prior_actual,
                   CASE WHEN b.funding IS NULL OR b.funding = 0 THEN NULL
                        ELSE (a.funding - b.funding) / b.funding END AS velocity_yoy
            FROM last2 a
            LEFT JOIN last2 b ON a.program_area = b.program_area AND b.rn = 2
            WHERE a.rn = 1
        ),
        next_fy AS (
            SELECT program_area, predicted_funding, slope_usd_per_year, resid_sd, fiscal_year
            FROM `{catalog}`.`gold`.funding_forecast
            WHERE series = 'forecast'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY program_area ORDER BY fiscal_year) = 1
        )
        SELECT
            n.program_area,
            CASE
                WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) > 0.05 THEN 'TREND-ACCEL'
                WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) < -0.05 THEN 'TREND-DECLINE'
                ELSE 'TREND-STEADY'
            END AS trend_id,
            CASE
                WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) > 0.05 THEN 'Accelerating'
                WHEN n.slope_usd_per_year / NULLIF(v.last_actual, 0) < -0.05 THEN 'Declining'
                ELSE 'Steady'
            END AS trend_label,
            n.slope_usd_per_year,
            v.velocity_yoy,
            v.last_actual,
            n.predicted_funding AS forecast_next_fy,
            n.resid_sd,
            n.fiscal_year AS next_fiscal_year,
            'ols_fy_v1' AS model_name,
            CURRENT_TIMESTAMP() AS computed_at
        FROM next_fy n
        JOIN vel v ON n.program_area = v.program_area
    """
