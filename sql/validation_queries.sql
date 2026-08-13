-- =====================================================
-- ONR ITSS POC — Validation Queries (medallion)
-- Target: onr_demo.bronze / silver / gold / app
-- =====================================================

-- 1. COUNT & NULL CHECKS
SELECT 'bronze.grants' as layer, 'count' as check_type, COUNT(*) as value FROM `onr_demo`.`bronze`.grants
UNION ALL
SELECT 'bronze.grants', 'null_grant_no', COUNT(*) FROM `onr_demo`.`bronze`.grants WHERE grant_no IS NULL
UNION ALL
SELECT 'bronze.financial', 'count', COUNT(*) FROM `onr_demo`.`bronze`.financial
UNION ALL
SELECT 'bronze.financial', 'null_transaction_id', COUNT(*) FROM `onr_demo`.`bronze`.financial WHERE transaction_id IS NULL;

SELECT 'silver.grants' as layer, 'count' as check_type, COUNT(*) as value FROM `onr_demo`.`silver`.grants WHERE _is_active = true
UNION ALL
SELECT 'silver.grants', 'null_awardee', COUNT(*) FROM `onr_demo`.`silver`.grants WHERE awardee IS NULL AND _is_active = true
UNION ALL
SELECT 'silver.grants', 'invalid_amount', COUNT(*) FROM `onr_demo`.`silver`.grants WHERE amount_usd <= 0 AND _is_active = true
UNION ALL
SELECT 'silver.financial', 'count', COUNT(*) FROM `onr_demo`.`silver`.financial WHERE _is_active = true
UNION ALL
SELECT 'silver.financial', 'invalid_budget', COUNT(*) FROM `onr_demo`.`silver`.financial WHERE budget_allocated <= 0 AND _is_active = true;

-- 2. FRESHNESS
SELECT
    'grants' as dataset,
    MAX(_ingest_time) as latest_update,
    CAST((unix_timestamp(CURRENT_TIMESTAMP()) - unix_timestamp(MAX(_ingest_time))) / 3600 AS INT) as hours_stale,
    CASE
        WHEN (unix_timestamp(CURRENT_TIMESTAMP()) - unix_timestamp(MAX(_ingest_time))) / 3600 <= 24 THEN '✅ Fresh'
        WHEN (unix_timestamp(CURRENT_TIMESTAMP()) - unix_timestamp(MAX(_ingest_time))) / 3600 <= 48 THEN '⚠️ Aging'
        ELSE '❌ Stale'
    END as freshness_status
FROM `onr_demo`.`silver`.grants
UNION ALL
SELECT
    'financial',
    MAX(_ingest_time),
    CAST((unix_timestamp(CURRENT_TIMESTAMP()) - unix_timestamp(MAX(_ingest_time))) / 3600 AS INT),
    CASE
        WHEN (unix_timestamp(CURRENT_TIMESTAMP()) - unix_timestamp(MAX(_ingest_time))) / 3600 <= 24 THEN '✅ Fresh'
        WHEN (unix_timestamp(CURRENT_TIMESTAMP()) - unix_timestamp(MAX(_ingest_time))) / 3600 <= 48 THEN '⚠️ Aging'
        ELSE '❌ Stale'
    END
FROM `onr_demo`.`silver`.financial;

-- 3. DUPLICATES
SELECT grant_no, COUNT(*) as duplicate_count
FROM `onr_demo`.`silver`.grants
WHERE _is_active = true
GROUP BY grant_no
HAVING COUNT(*) > 1;

SELECT transaction_id, COUNT(*) as duplicate_count
FROM `onr_demo`.`silver`.financial
WHERE _is_active = true
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- 4. REFERENTIAL INTEGRITY (gold vs silver)
SELECT
    'grants_count_check' as validation,
    silver.cnt as silver_count,
    gold.cnt as gold_count,
    ABS(silver.cnt - gold.cnt) as difference,
    CASE WHEN silver.cnt = gold.cnt THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM
    (SELECT COUNT(*) as cnt FROM `onr_demo`.`silver`.grants WHERE _is_active = true) silver,
    (SELECT SUM(grant_count) as cnt FROM `onr_demo`.`gold`.grants_summary) gold;

-- 5. QUALITY SCORES
SELECT
    table_name,
    quality_score,
    CASE
        WHEN quality_score >= 0.90 THEN '✅ Excellent'
        WHEN quality_score >= 0.80 THEN '🟡 Good'
        WHEN quality_score >= 0.70 THEN '🟠 Fair'
        ELSE '🔴 Poor'
    END as quality_rating
FROM `onr_demo`.`app`.data_quality_scores
ORDER BY quality_score DESC;

-- 6. LINEAGE
SELECT lineage_id, source_table, target_table,
    CASE WHEN source_table IS NULL OR target_table IS NULL THEN '❌ Incomplete' ELSE '✅ Valid' END as lineage_status
FROM `onr_demo`.`app`.lineage_tracking
WHERE executed_at >= CURRENT_DATE() - INTERVAL 7 DAYS;

-- 7. TABLE SIZE
SELECT table_name, format, num_files, size_in_bytes,
    ROUND(size_in_bytes / 1024 / 1024, 2) as size_mb
FROM (DESCRIBE DETAIL `onr_demo`.`silver`.grants)
UNION ALL
SELECT table_name, format, num_files, size_in_bytes,
    ROUND(size_in_bytes / 1024 / 1024, 2)
FROM (DESCRIBE DETAIL `onr_demo`.`silver`.financial);

-- 8. AUDIT
SELECT event_time, user_identity.email as user_email, securable_full_name, action_name
FROM system.access.audit
WHERE securable_full_name LIKE 'onr_demo.%'
    AND event_time >= CURRENT_DATE() - INTERVAL 1 DAY
ORDER BY event_time DESC
LIMIT 20;

-- 9. PIPELINE HEALTH
SELECT check_name, check_status, records_checked, records_passed, records_failed,
    ROUND(records_passed * 100.0 / NULLIF(records_checked, 0), 2) as pass_rate_pct,
    check_timestamp
FROM `onr_demo`.`app`.ingestion_quality_log
ORDER BY check_timestamp DESC
LIMIT 10;

-- SUMMARY
SELECT
    'VALIDATION COMPLETE' as status,
    CURRENT_TIMESTAMP() as validated_at,
    'onr_demo.{bronze,silver,gold,app}' as target,
    CASE
        WHEN (SELECT COUNT(*) FROM `onr_demo`.`silver`.grants WHERE _is_active = true) > 0
            AND (SELECT COUNT(*) FROM `onr_demo`.`silver`.financial WHERE _is_active = true) > 0
        THEN '✅ All validations passed'
        ELSE '❌ Some validations failed - review above'
    END as overall_status;
