"""SQL for gold.funding_features + heuristic grant_anomaly_scores.

Adapted from the ML engineer's IsolationForest demo (ITSS_ML_Demo.dbc)
onto the Compass grants + ERP already in this catalog.
"""


def funding_features_sql(catalog: str) -> str:
    return f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.funding_features AS
        WITH fin AS (
            SELECT grant_no,
                   SUM(actual_expenditure) / NULLIF(SUM(budget_allocated), 0) AS execution_rate,
                   SUM(budget_allocated) AS budget_allocated,
                   SUM(actual_expenditure) AS actual_expenditure
            FROM `{catalog}`.`silver`.financial
            WHERE _is_active = true
            GROUP BY grant_no
        ),
        area_stats AS (
            SELECT program_area, fiscal_year,
                   approx_percentile(amount_usd, 0.5) AS median_amt,
                   AVG(amount_usd) AS avg_amt
            FROM `{catalog}`.`silver`.grants
            WHERE _is_active = true
            GROUP BY program_area, fiscal_year
        ),
        prior AS (
            SELECT program_area, fiscal_year + 1 AS fiscal_year, avg_amt AS prior_avg
            FROM area_stats
        ),
        base AS (
            SELECT
                g.grant_no,
                g.title,
                g.program_area,
                g.fiscal_year,
                g.amount_usd AS award_amount,
                g.awardee,
                g.org_unit,
                g.classification_band,
                COALESCE(f.execution_rate, 0.90) AS execution_rate,
                g.amount_usd / NULLIF(COALESCE(p.prior_avg, a.avg_amt), 0) AS yoy_growth_ratio,
                g.amount_usd / NULLIF(a.median_amt, 0) AS amount_vs_area_median
            FROM `{catalog}`.`silver`.grants g
            LEFT JOIN fin f ON f.grant_no = g.grant_no
            LEFT JOIN area_stats a
              ON a.program_area = g.program_area AND a.fiscal_year = g.fiscal_year
            LEFT JOIN prior p
              ON p.program_area = g.program_area AND p.fiscal_year = g.fiscal_year
            WHERE g._is_active = true
        )
        SELECT
            grant_no, title, program_area, fiscal_year, award_amount, awardee,
            org_unit, classification_band, execution_rate, yoy_growth_ratio,
            amount_vs_area_median,
            CASE
                WHEN execution_rate < 0.76 THEN 'execution_collapse'
                WHEN award_amount >= 3000000 AND amount_vs_area_median >= 1.8 THEN 'budget_spike'
                WHEN award_amount >= 2500000 AND execution_rate < 0.85
                    THEN 'low_return_concentration'
                ELSE 'none'
            END AS anomaly_type,
            CASE
                WHEN execution_rate < 0.76
                  OR (award_amount >= 3000000 AND amount_vs_area_median >= 1.8)
                  OR (award_amount >= 2500000 AND execution_rate < 0.85)
                THEN 1 ELSE 0
            END AS is_known_anomaly,
            CURRENT_TIMESTAMP() AS _updated_at
        FROM base
    """


def heuristic_anomaly_scores_sql(catalog: str) -> str:
    return f"""
        CREATE OR REPLACE TABLE `{catalog}`.`gold`.grant_anomaly_scores AS
        SELECT
            grant_no, title, program_area, fiscal_year,
            award_amount AS amount_usd, awardee,
            execution_rate, yoy_growth_ratio, amount_vs_area_median,
            CASE
                WHEN anomaly_type = 'execution_collapse' THEN 0.92
                WHEN anomaly_type = 'budget_spike' THEN 0.88
                WHEN anomaly_type = 'low_return_concentration' THEN 0.80
                ELSE LEAST(0.45, GREATEST(0.05,
                    0.08
                    + GREATEST(0, amount_vs_area_median - 1.0) * 0.12
                    + GREATEST(0, 0.90 - execution_rate) * 0.40
                ))
            END AS anomaly_score,
            CAST(is_known_anomaly AS BOOLEAN) AS is_flagged,
            anomaly_type AS predicted_type,
            anomaly_type,
            is_known_anomaly,
            'heuristic_rules_v1' AS model_name,
            CURRENT_TIMESTAMP() AS scored_at
        FROM `{catalog}`.`gold`.funding_features
    """
