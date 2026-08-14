-- OLS FY forecast + trend IDs (Element 5).
-- Ordinary least squares of total_funding ~ fiscal_year, per program_area.
-- Horizon = last observed FY + 1 and + 2, with a 95% residual band.
-- Trend IDs: TREND-ACCEL / TREND-STEADY / TREND-DECLINE.
-- Catalog is parameterized by the caller (app / notebooks use f-strings).

-- See Python: utils/demo_actions.py → _write_forecast_and_trends
--             notebooks/03_gold_aggregation.py (same SQL)
