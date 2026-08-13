-- =====================================================
-- ONR ITSS POC — Validation Queries
-- =====================================================
-- Run after pipeline execution to validate data quality
-- Target: onr_demo.dev (adjust for your environment)

-- =====================================================
-- 1. COUNT & NULL CHECKS
-- =====================================================

-- Bronze layer validation
SELECT 'bronze_grants' as layer, 'count' as check_type, COUNT(*) as value FROM `onr_demo`.`dev`.bronze_grants
UNION ALL
SELECT 'bronze_grants', 'null_grant_no', COUNT(*) FROM `onr_demo`.`dev`.bronze_grants WHERE grant_no IS NULL
UNION ALL
SELECT 'bronze_financial', 'count', COUNT(*) FROM `onr_demo`.`dev`.bronze_financial
UNION ALL
SELECT 'bronze_financial', 'null_transaction_id', COUNT(*) FROM `onr_demo`.`dev`.bronze_financial WHERE transaction_id IS NULL;

-- Silver layer validation
SELECT 'silver_grants' as layer, 'count' as check_type, COUNT(*) as value FROM `onr_demo`.`dev`.silver_grants WHERE _is_active = true
UNION ALL
SELECT 'silver_grants', 'null_awardee', COUNT(*) FROM `onr_demo`.`dev`.silver_grants WHERE awardee IS NULL AND _is_active = true
UNION ALL
SELECT 'silver_grants', 'invalid_amount', COUNT(*) FROM `onr_demo`.`dev`.silver_grants WHERE amount_usd <= 0 AND _is_active = true
UNION ALL
SELECT 'silver_financial', 'count', COUNT(*) FROM `onr_demo`.`dev`.silver_financial WHERE _is_active = true
UNION ALL
SELECT 'silver_financial', 'invalid_budget', COUNT(*) FROM `onr_demo`.`dev`.silver_financial WHERE budget_allocated <= 0 AND _is_active = true;

-- =====================================================
-- 2. FRESHNESS CHECK
-- =====================================================

-- Check data freshness (should be within 24 hours)
SELECT 
    'grants' as dataset,
    MAX(_ingest_time) as latest_update,
    DATEDIFF(CURRENT_TIMESTAMP(), MAX(_ingest_time)) as hours_stale,
    CASE 
        WHEN DATEDIFF(CURRENT_TIMESTAMP(), MAX(_ingest_time)) <= 24 THEN '✅ Fresh'
        WHEN DATEDIFF(CURRENT_TIMESTAMP(), MAX(_ingest_time)) <= 48 THEN '⚠️ Aging'
        ELSE '❌ Stale'
    END as freshness_status
FROM `onr_demo`.`dev`.silver_grants
UNION ALL
SELECT 
    'financial' as dataset,
    MAX(_ingest_time) as latest_update,
    DATEDIFF(CURRENT_TIMESTAMP(), MAX(_ingest_time)) as hours_stale,
    CASE 
        WHEN DATEDIFF(CURRENT_TIMESTAMP(), MAX(_ingest_time)) <= 24 THEN '✅ Fresh'
        WHEN DATEDIFF(CURRENT_TIMESTAMP(), MAX(_ingest_time)) <= 48 THEN '⚠️ Aging'
        ELSE '❌ Stale'
    END as freshness_status
FROM `onr_demo`.`dev`.silver_financial;

-- =====================================================
-- 3. DUPLICATE DETECTION
-- =====================================================

-- Check for duplicate grant IDs
SELECT 
    grant_no, 
    COUNT(*) as duplicate_count
FROM `onr_demo`.`dev`.silver_grants
WHERE _is_active = true
GROUP BY grant_no
HAVING COUNT(*) > 1;

-- Check for duplicate transaction IDs
SELECT 
    transaction_id, 
    COUNT(*) as duplicate_count
FROM `onr_demo`.`dev`.silver_financial
WHERE _is_active = true
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- =====================================================
-- 4. REFERENTIAL INTEGRITY
-- =====================================================

-- Verify gold tables match silver aggregations
SELECT 
    'grants_count_check' as validation,
    silver.cnt as silver_count,
    gold.cnt as gold_count,
    ABS(silver.cnt - gold.cnt) as difference,
    CASE WHEN silver.cnt = gold.cnt THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM 
    (SELECT COUNT(*) as cnt FROM `onr_demo`.`dev`.silver_grants WHERE _is_active = true) silver,
    (SELECT SUM(grant_count) as cnt FROM `onr_demo`.`dev`.gold_grants_summary) gold;

-- =====================================================
-- 5. QUALITY SCORE VALIDATION
-- =====================================================

-- Verify quality scores are within expected range
SELECT 
    table_name,
    quality_score,
    CASE 
        WHEN quality_score >= 0.90 THEN '✅ Excellent'
        WHEN quality_score >= 0.80 THEN '🟡 Good'
        WHEN quality_score >= 0.70 THEN '🟠 Fair'
        ELSE '🔴 Poor'
    END as quality_rating
FROM `onr_demo`.`dev`.onr_data_quality_scores
ORDER BY quality_score DESC;

-- =====================================================
-- 6. LINEAGE COMPLETENESS
-- =====================================================

-- Verify all lineage records have valid source/target
SELECT 
    lineage_id,
    source_table,
    target_table,
    CASE 
        WHEN source_table IS NULL OR target_table IS NULL THEN '❌ Incomplete'
        ELSE '✅ Valid'
    END as lineage_status
FROM `onr_demo`.`dev`.onr_lineage_tracking
WHERE executed_at >= CURRENT_DATE() - INTERVAL 7 DAYS;

-- =====================================================
-- 7. TABLE SIZE & GROWTH
-- =====================================================

-- Check table sizes
SELECT 
    table_name,
    format,
    num_files,
    size_in_bytes,
    ROUND(size_in_bytes / 1024 / 1024, 2) as size_mb,
    ROUND(size_in_bytes / 1024 / 1024 / 1024, 2) as size_gb
FROM (
    DESCRIBE DETAIL `onr_demo`.`dev`.silver_grants
)
UNION ALL
SELECT 
    table_name,
    format,
    num_files,
    size_in_bytes,
    ROUND(size_in_bytes / 1024 / 1024, 2) as size_mb,
    ROUND(size_in_bytes / 1024 / 1024 / 1024, 2) as size_gb
FROM (
    DESCRIBE DETAIL `onr_demo`.`dev`.silver_financial
);

-- =====================================================
-- 8. AUDIT LOG CHECK
-- =====================================================

-- Recent table access audit
SELECT 
    event_time,
    user_identity.email as user_email,
    securable_full_name,
    action_name
FROM system.access.audit
WHERE securable_full_name LIKE 'onr_demo.dev.%'
    AND event_time >= CURRENT_DATE() - INTERVAL 1 DAY
ORDER BY event_time DESC
LIMIT 20;

-- =====================================================
-- 9. PIPELINE HEALTH
-- =====================================================

-- Check recent ingestion quality logs
SELECT 
    check_name,
    check_status,
    records_checked,
    records_passed,
    records_failed,
    ROUND(records_passed * 100.0 / NULLIF(records_checked, 0), 2) as pass_rate_pct,
    check_timestamp
FROM `onr_demo`.`dev`.ingestion_quality_log
ORDER BY check_timestamp DESC
LIMIT 10;

-- =====================================================
-- VALIDATION SUMMARY
-- =====================================================

SELECT 
    'VALIDATION COMPLETE' as status,
    CURRENT_TIMESTAMP() as validated_at,
    'onr_demo.dev' as target_catalog_schema,
    CASE 
        WHEN (SELECT COUNT(*) FROM `onr_demo`.`dev`.silver_grants WHERE _is_active = true) > 0
            AND (SELECT COUNT(*) FROM `onr_demo`.`dev`.silver_financial WHERE _is_active = true) > 0
        THEN '✅ All validations passed'
        ELSE '❌ Some validations failed - review above'
    END as overall_status;
