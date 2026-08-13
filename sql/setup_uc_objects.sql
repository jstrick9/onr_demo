-- Optional empty DDL. Prefer notebooks/00_bootstrap.py on a new workspace
-- (see FIRST_RUN.md). Do not run this after bootstrap unless you need tags
-- on tables that already exist.
--
-- CLUSTER BY requires Databricks SQL / DBR 13.3+ liquid clustering.
-- If a CREATE TABLE fails on CLUSTER BY, skip this file and use bootstrap.

-- =====================================================
-- 1. CATALOG & SCHEMAS
-- =====================================================

-- Uses the workspace metastore default location (no extra S3 bucket required)
CREATE CATALOG IF NOT EXISTS `onr_demo`
    COMMENT 'ONR ITSS POC — Technical Demonstration Catalog';

CREATE SCHEMA IF NOT EXISTS `onr_demo`.`bronze`
    COMMENT 'Bronze — raw ingested S&T grants and ERP';

CREATE SCHEMA IF NOT EXISTS `onr_demo`.`silver`
    COMMENT 'Silver — cleansed, validated, deduplicated';

CREATE SCHEMA IF NOT EXISTS `onr_demo`.`gold`
    COMMENT 'Gold — business-ready aggregates for analytics';

CREATE SCHEMA IF NOT EXISTS `onr_demo`.`app`
    COMMENT 'Application state, quality scores, lineage, audit';

-- =====================================================
-- 2. VOLUMES (landing in bronze)
-- =====================================================

CREATE VOLUME IF NOT EXISTS `onr_demo`.`bronze`.landing
    COMMENT 'Landing zone for raw file ingestion';

CREATE VOLUME IF NOT EXISTS `onr_demo`.`bronze`.checkpoints
    COMMENT 'Auto Loader / streaming checkpoints';

-- =====================================================
-- 3. BRONZE
-- =====================================================

CREATE TABLE IF NOT EXISTS `onr_demo`.`bronze`.grants (
    grant_no STRING NOT NULL,
    title STRING,
    abstract STRING,
    program_area STRING,
    fiscal_year INT,
    amount_usd DOUBLE,
    awardee STRING,
    org_unit STRING,
    classification_band STRING,
    batch_id STRING,
    created_at STRING,
    _ingest_time TIMESTAMP,
    _source_file STRING,
    _batch_id STRING
) USING DELTA
TBLPROPERTIES (
    'delta.feature.allowColumnDefaults' = 'supported',
    'quality' = 'bronze'
)
COMMENT 'Bronze: raw Compass S&T grants fixture';

CREATE TABLE IF NOT EXISTS `onr_demo`.`bronze`.financial (
    transaction_id STRING NOT NULL,
    grant_no STRING,
    cost_center STRING,
    program_area STRING,
    category STRING,
    fiscal_year INT,
    quarter STRING,
    budget_allocated DOUBLE,
    actual_expenditure DOUBLE,
    execution_rate DOUBLE,
    variance DOUBLE,
    status STRING,
    batch_id STRING,
    _ingest_time TIMESTAMP,
    _source_file STRING,
    _batch_id STRING
) USING DELTA
TBLPROPERTIES (
    'delta.feature.allowColumnDefaults' = 'supported',
    'quality' = 'bronze'
)
COMMENT 'Bronze: raw ERP derived from grants';

-- =====================================================
-- 4. SILVER
-- =====================================================

CREATE TABLE IF NOT EXISTS `onr_demo`.`silver`.grants (
    grant_no STRING NOT NULL,
    title STRING NOT NULL,
    abstract STRING,
    program_area STRING,
    fiscal_year INT,
    amount_usd DOUBLE,
    awardee STRING NOT NULL,
    org_unit STRING,
    classification_band STRING,
    batch_id STRING,
    created_at TIMESTAMP,
    _ingest_time TIMESTAMP,
    _source_file STRING,
    _is_active BOOLEAN DEFAULT true,
    _quality_score DOUBLE,
    CONSTRAINT valid_amount CHECK (amount_usd > 0),
    CONSTRAINT valid_awardee CHECK (awardee IS NOT NULL)
) USING DELTA
CLUSTER BY (program_area, fiscal_year)
TBLPROPERTIES (
    'delta.feature.allowColumnDefaults' = 'supported',
    'quality' = 'silver'
)
COMMENT 'Silver: cleansed grants';

CREATE TABLE IF NOT EXISTS `onr_demo`.`silver`.financial (
    transaction_id STRING NOT NULL,
    grant_no STRING,
    cost_center STRING NOT NULL,
    program_area STRING,
    category STRING NOT NULL,
    fiscal_year INT,
    quarter STRING,
    budget_allocated DOUBLE,
    actual_expenditure DOUBLE,
    execution_rate DOUBLE,
    variance DOUBLE,
    status STRING,
    _ingest_time TIMESTAMP,
    _source_file STRING,
    _is_active BOOLEAN DEFAULT true,
    _quality_score DOUBLE,
    CONSTRAINT valid_budget CHECK (budget_allocated > 0),
    CONSTRAINT valid_execution CHECK (execution_rate >= 0)
) USING DELTA
CLUSTER BY (fiscal_year, quarter)
TBLPROPERTIES (
    'delta.feature.allowColumnDefaults' = 'supported',
    'quality' = 'silver'
)
COMMENT 'Silver: cleansed ERP';

-- =====================================================
-- 5. GOLD
-- =====================================================

CREATE TABLE IF NOT EXISTS `onr_demo`.`gold`.grants_summary (
    program_area STRING,
    fiscal_year INT,
    grant_count INT,
    total_funding DOUBLE,
    avg_award DOUBLE,
    min_award DOUBLE,
    max_award DOUBLE,
    cui_mock_count INT,
    public_mock_count INT,
    _updated_at TIMESTAMP
) USING DELTA
CLUSTER BY (program_area, fiscal_year)
COMMENT 'Gold: grants by program area and FY';

CREATE TABLE IF NOT EXISTS `onr_demo`.`gold`.financial_summary (
    cost_center STRING,
    category STRING,
    fiscal_year INT,
    quarter STRING,
    total_budget DOUBLE,
    total_actual DOUBLE,
    overall_execution_rate DOUBLE,
    variance_amount DOUBLE,
    transaction_count INT,
    _updated_at TIMESTAMP
) USING DELTA
CLUSTER BY (fiscal_year, quarter)
COMMENT 'Gold: ERP by cost center';

CREATE TABLE IF NOT EXISTS `onr_demo`.`gold`.grants_by_awardee (
    awardee STRING,
    org_unit STRING,
    grant_count INT,
    total_funding DOUBLE,
    program_areas ARRAY<STRING>,
    latest_grant_date TIMESTAMP,
    _updated_at TIMESTAMP
) USING DELTA
CLUSTER BY (awardee)
COMMENT 'Gold: grants by awardee';

CREATE TABLE IF NOT EXISTS `onr_demo`.`gold`.grant_predictions (
    grant_no STRING NOT NULL,
    title STRING,
    program_area STRING,
    amount_usd DOUBLE,
    awardee STRING,
    success_probability DOUBLE,
    risk_factors STRING,
    recommendation STRING,
    model_name STRING,
    scored_at TIMESTAMP
) USING DELTA
COMMENT 'Gold: per-grant scores (heuristic from silver, or RF from notebook 04)';

CREATE TABLE IF NOT EXISTS `onr_demo`.`gold`.model_metrics (
    model_name STRING,
    metric_name STRING,
    metric_value DOUBLE,
    n_rows INT,
    trained_at TIMESTAMP
) USING DELTA
COMMENT 'Gold: last model run metrics for the Streamlit app';

CREATE TABLE IF NOT EXISTS `onr_demo`.`gold`.budget_execution (
    fiscal_year INT,
    quarter STRING,
    category STRING,
    budget_plan DOUBLE,
    actual_spend DOUBLE,
    execution_rate DOUBLE,
    variance DOUBLE,
    variance_pct DOUBLE,
    status STRING,
    _updated_at TIMESTAMP
) USING DELTA
CLUSTER BY (fiscal_year, quarter)
COMMENT 'Gold: budget execution';

-- =====================================================
-- 6. APP
-- =====================================================

CREATE TABLE IF NOT EXISTS `onr_demo`.`app`.search_history (
    search_id STRING NOT NULL,
    user_email STRING,
    search_type STRING,
    search_params STRING,
    results_count INT,
    execution_time_ms INT,
    created_at TIMESTAMP
) USING DELTA
COMMENT 'Search history for audit and replay';

CREATE TABLE IF NOT EXISTS `onr_demo`.`app`.export_history (
    export_id STRING NOT NULL,
    user_email STRING,
    dataset_name STRING,
    format STRING,
    record_count INT,
    file_size_bytes BIGINT,
    created_at TIMESTAMP
) USING DELTA
COMMENT 'Export audit trail';

CREATE TABLE IF NOT EXISTS `onr_demo`.`app`.data_quality_scores (
    table_name STRING,
    quality_score DOUBLE,
    completeness DOUBLE,
    accuracy DOUBLE,
    consistency DOUBLE,
    timeliness DOUBLE,
    last_assessed TIMESTAMP
) USING DELTA
COMMENT 'Data quality health scores';

CREATE TABLE IF NOT EXISTS `onr_demo`.`app`.lineage_tracking (
    lineage_id STRING NOT NULL,
    source_table STRING,
    target_table STRING,
    transformation_type STRING,
    records_processed INT,
    processing_time_ms INT,
    executed_at TIMESTAMP,
    executed_by STRING
) USING DELTA
COMMENT 'Lineage tracking records';

CREATE TABLE IF NOT EXISTS `onr_demo`.`app`.ingestion_quality_log (
    check_id STRING NOT NULL,
    check_name STRING,
    check_status STRING,
    records_checked INT,
    records_passed INT,
    records_failed INT,
    check_timestamp TIMESTAMP,
    pipeline_name STRING
) USING DELTA
COMMENT 'Ingestion quality check results';

-- =====================================================
-- 7. GRANTS (Access Control)
-- =====================================================

-- Optional: uncomment after you create these account groups
-- GRANT ALL PRIVILEGES ON CATALOG `onr_demo` TO `data-engineers`;
-- GRANT USE CATALOG ON CATALOG `onr_demo` TO `analysts`;
-- GRANT SELECT ON SCHEMA `onr_demo`.`gold` TO `analysts`;

-- =====================================================
-- 8. TAGS
-- =====================================================

ALTER TABLE `onr_demo`.`silver`.grants SET TAGS (
    'domain' = 'research',
    'data_sensitivity' = 'public',
    'data_source' = 'mock',
    'owner' = 'data-engineers',
    'refresh_frequency' = 'daily',
    'medallion' = 'silver'
);

ALTER TABLE `onr_demo`.`silver`.financial SET TAGS (
    'domain' = 'finance',
    'data_sensitivity' = 'internal',
    'data_source' = 'mock',
    'owner' = 'data-engineers',
    'refresh_frequency' = 'daily',
    'medallion' = 'silver'
);

ALTER TABLE `onr_demo`.`gold`.grants_summary SET TAGS (
    'domain' = 'research',
    'data_sensitivity' = 'public',
    'data_source' = 'mock',
    'owner' = 'analysts',
    'medallion' = 'gold'
);

ALTER TABLE `onr_demo`.`gold`.financial_summary SET TAGS (
    'domain' = 'finance',
    'data_sensitivity' = 'internal',
    'data_source' = 'mock',
    'owner' = 'analysts',
    'medallion' = 'gold'
);

-- =====================================================
-- 9. ROW / COLUMN SECURITY EXAMPLES
-- =====================================================

-- Optional (requires appropriate metastore privileges):
-- CREATE FUNCTION IF NOT EXISTS `onr_demo`.`app`.region_filter(region STRING)
--     RETURN current_user() LIKE '%@navy.mil%' OR region = 'ALL';
-- CREATE FUNCTION IF NOT EXISTS `onr_demo`.`app`.mask_awardee(name STRING)
--     RETURN CASE WHEN IS_MEMBER('analysts') THEN name ELSE CONCAT(LEFT(name, 1), '****') END;

-- ALTER TABLE `onr_demo`.`silver`.grants
-- ALTER COLUMN awardee SET MASK `onr_demo`.`app`.mask_awardee;

-- =====================================================
-- SETUP COMPLETE
-- Next: run notebooks/00_bootstrap.py (loads 400 grants + ERP, stages a live file)
-- =====================================================
