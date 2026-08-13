-- =====================================================
-- ONR ITSS POC — Unity Catalog Setup
-- =====================================================
-- Run as Account Admin or Metastore Admin
-- Target: Databricks on AWS (Serverless-first)

-- =====================================================
-- 1. CATALOG & SCHEMA
-- =====================================================

-- Create Catalog
CREATE CATALOG IF NOT EXISTS `onr_demo`
    MANAGED LOCATION 's3://onr-demo-uc-bucket/onr_demo'
    COMMENT 'ONR ITSS POC — Technical Demonstration Catalog';

-- Create Schemas
CREATE SCHEMA IF NOT EXISTS `onr_demo`.`dev`
    COMMENT 'Development environment for ONR POC';

CREATE SCHEMA IF NOT EXISTS `onr_demo`.`prod`
    COMMENT 'Production environment for ONR POC';

-- =====================================================
-- 2. VOLUMES (Landing Zone)
-- =====================================================

-- Landing Volume for raw file ingestion
CREATE VOLUME IF NOT EXISTS `onr_demo`.`dev`.landing
    COMMENT 'Landing zone for raw file ingestion'
    VOLUME_TYPE MANAGED;

-- Checkpoint Volume for streaming
CREATE VOLUME IF NOT EXISTS `onr_demo`.`dev`.checkpoints
    COMMENT 'Checkpoint location for streaming queries'
    VOLUME_TYPE MANAGED;

-- =====================================================
-- 3. BRONZE LAYER (Raw Ingestion)
-- =====================================================

-- Bronze: Grants (Raw) — Compass fixture schema
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.bronze_grants (
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
COMMENT 'Bronze layer: Raw S&T grants data from ingestion pipeline';

-- Bronze: Financial (Raw)
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.bronze_financial (
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
COMMENT 'Bronze layer: Raw financial ERP data from ingestion pipeline';

-- =====================================================
-- 4. SILVER LAYER (Cleansed & Validated)
-- =====================================================

-- Silver: Grants (Cleansed)
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.silver_grants (
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
COMMENT 'Silver layer: Cleansed and validated grants data';

-- Silver: Financial (Cleansed)
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.silver_financial (
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
COMMENT 'Silver layer: Cleansed and validated financial data';

-- =====================================================
-- 5. GOLD LAYER (Business-Ready Aggregates)
-- =====================================================

-- Gold: Grants Summary
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.gold_grants_summary (
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
COMMENT 'Gold layer: Aggregated grants summary by research area and fiscal year';

-- Gold: Financial Summary
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.gold_financial_summary (
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
COMMENT 'Gold layer: Aggregated financial summary by cost center';

-- Gold: Grants by PI
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.gold_grants_by_awardee (
    awardee STRING,
    org_unit STRING,
    grant_count INT,
    total_funding DOUBLE,
    program_areas ARRAY<STRING>,
    latest_grant_date TIMESTAMP,
    _updated_at TIMESTAMP
) USING DELTA
CLUSTER BY (awardee)
COMMENT 'Gold layer: Grant performance aggregated by awardee organization';

-- Gold: Budget Execution
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.gold_budget_execution (
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
COMMENT 'Gold layer: Budget execution tracking for financial planning';

-- =====================================================
-- 6. APP TABLES (Application State)
-- =====================================================

-- Search History
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.onr_app_search_history (
    search_id STRING NOT NULL,
    user_email STRING,
    search_type STRING,
    search_params STRING,
    results_count INT,
    execution_time_ms INT,
    created_at TIMESTAMP
) USING DELTA
COMMENT 'Application table: Search history for audit and replay';

-- Export History
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.onr_app_export_history (
    export_id STRING NOT NULL,
    user_email STRING,
    dataset_name STRING,
    format STRING,
    record_count INT,
    file_size_bytes BIGINT,
    created_at TIMESTAMP
) USING DELTA
COMMENT 'Application table: Export history for audit trail';

-- Data Quality Scores
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.onr_data_quality_scores (
    table_name STRING,
    quality_score DOUBLE,
    completeness DOUBLE,
    accuracy DOUBLE,
    consistency DOUBLE,
    timeliness DOUBLE,
    last_assessed TIMESTAMP
) USING DELTA
COMMENT 'Application table: Data quality health scores';

-- Lineage Tracking
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.onr_lineage_tracking (
    lineage_id STRING NOT NULL,
    source_table STRING,
    target_table STRING,
    transformation_type STRING,
    records_processed INT,
    processing_time_ms INT,
    executed_at TIMESTAMP,
    executed_by STRING
) USING DELTA
COMMENT 'Application table: Data lineage tracking records';

-- Ingestion Quality Log
CREATE TABLE IF NOT EXISTS `onr_demo`.`dev`.ingestion_quality_log (
    check_id STRING NOT NULL,
    check_name STRING,
    check_status STRING,
    records_checked INT,
    records_passed INT,
    records_failed INT,
    check_timestamp TIMESTAMP,
    pipeline_name STRING
) USING DELTA
COMMENT 'Application table: Ingestion quality check results';

-- =====================================================
-- 7. GRANTS (Access Control)
-- =====================================================

-- Grant to data engineers (full access)
GRANT ALL PRIVILEGES ON CATALOG `onr_demo` TO `data-engineers`;

-- Grant to analysts (read access to gold)
GRANT USE CATALOG ON CATALOG `onr_demo` TO `analysts`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`dev` TO `analysts`;
GRANT SELECT ON SCHEMA `onr_demo`.`dev` TO `analysts`;

-- Grant to viewers (read access to specific tables)
GRANT USE CATALOG ON CATALOG `onr_demo` TO `viewers`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`dev` TO `viewers`;
GRANT SELECT ON TABLE `onr_demo`.`dev`.gold_grants_summary TO `viewers`;
GRANT SELECT ON TABLE `onr_demo`.`dev`.gold_financial_summary TO `viewers`;

-- =====================================================
-- 8. TAGS (Data Classification)
-- =====================================================

-- Apply tags to tables
ALTER TABLE `onr_demo`.`dev`.silver_grants SET TAGS (
    'domain' = 'research',
    'data_sensitivity' = 'public',
    'data_source' = 'mock',
    'owner' = 'data-engineers',
    'refresh_frequency' = 'daily'
);

ALTER TABLE `onr_demo`.`dev`.silver_financial SET TAGS (
    'domain' = 'finance',
    'data_sensitivity' = 'internal',
    'data_source' = 'mock',
    'owner' = 'data-engineers',
    'refresh_frequency' = 'daily'
);

ALTER TABLE `onr_demo`.`dev`.gold_grants_summary SET TAGS (
    'domain' = 'research',
    'data_sensitivity' = 'public',
    'data_source' = 'mock',
    'owner' = 'analysts'
);

ALTER TABLE `onr_demo`.`dev`.gold_financial_summary SET TAGS (
    'domain' = 'finance',
    'data_sensitivity' = 'internal',
    'data_source' = 'mock',
    'owner' = 'analysts'
);

-- =====================================================
-- 9. ROW-LEVEL SECURITY (Example)
-- =====================================================

-- Create row filter function
CREATE FUNCTION IF NOT EXISTS `onr_demo`.`dev`.region_filter(region STRING)
    RETURN current_user() LIKE '%@navy.mil%' OR region = 'ALL';

-- Apply row filter (commented out - enable as needed)
-- ALTER TABLE `onr_demo`.`dev`.gold_grants_summary 
-- SET ROW FILTER `onr_demo`.`dev`.region_filter ON (research_area);

-- Create column mask function
CREATE FUNCTION IF NOT EXISTS `onr_demo`.`dev`.mask_pi_name(name STRING)
    RETURN CASE 
        WHEN IS_MEMBER('analysts') THEN name 
        ELSE CONCAT(LEFT(name, 1), '****') 
    END;

-- Apply column mask (commented out - enable as needed)
-- ALTER TABLE `onr_demo`.`dev`.silver_grants 
-- ALTER COLUMN principal_investigator 
-- SET MASK `onr_demo`.`dev`.mask_pi_name;

-- =====================================================
-- SETUP COMPLETE
-- =====================================================
-- Next steps:
-- 1. Run mock data generator: resources/mock_data/generate_mock_data.py
-- 2. Run notebooks: notebooks/01_bronze_ingestion.py through 03_gold_aggregation.py
-- 3. Deploy Streamlit app via DABs: databricks bundle deploy -t dev
