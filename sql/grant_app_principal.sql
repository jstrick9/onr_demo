-- Grant the Databricks App service principal access to onr_demo.
-- Replace <APP_SERVICE_PRINCIPAL> with the name or application ID from
--   App → onr-demo-poc → Authorization / Service principal
-- Keep the backticks.
--
-- Also in the UI: SQL Warehouses → "onr demo warehouse" → Permissions → CAN USE
-- for the same principal.
--
-- ---------------------------------------------------------------------------
-- Least-privilege / Zero Trust talking point (Strategic Prompt (c))
-- ---------------------------------------------------------------------------
-- MANAGE on the four schemas is a POC concession: CREATE OR REPLACE TABLE on a
-- table owned by the human who ran bootstrap requires ownership or MANAGE.
-- This is NOT the IL5 production grant set.
--
-- In production we would do one of:
--   1. Have the job / app identity OWN the silver/gold tables it rebuilds, OR
--   2. GRANT SELECT, MODIFY only and use INSERT OVERWRITE / MERGE, OR
--   3. Run rebuilds as a dedicated pipeline principal that owns the tables.
-- The app SP would then be: USE CATALOG + USE SCHEMA + SELECT on gold/silver
-- + MODIFY on app.* (audit tables) + READ VOLUME on landing.
-- Do not copy MANAGE-on-schema into an IL5 production grant set.
-- ---------------------------------------------------------------------------

GRANT USE CATALOG ON CATALOG `onr_demo` TO `<APP_SERVICE_PRINCIPAL>`;

GRANT USE SCHEMA ON SCHEMA `onr_demo`.`bronze` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`silver` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`gold` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`app` TO `<APP_SERVICE_PRINCIPAL>`;

-- SELECT/MODIFY/CREATE TABLE are not enough to CREATE OR REPLACE a table
-- owned by the human who ran bootstrap. MANAGE is required for the app
-- Process / Reset path in this POC only (see note above).
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`bronze` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`silver` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`gold` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`app` TO `<APP_SERVICE_PRINCIPAL>`;

GRANT READ VOLUME, WRITE VOLUME ON VOLUME `onr_demo`.`bronze`.`landing` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME `onr_demo`.`bronze`.`checkpoints` TO `<APP_SERVICE_PRINCIPAL>`;

-- Required for Analytics → Score registered models (in-app / warehouse path).
-- UC registered models are granted as FUNCTIONs in this workspace — not MODEL.
-- Objects exist only after night-before 04 + 04b. Skip these two if register failed.
GRANT EXECUTE ON FUNCTION `onr_demo`.`gold`.`grant_large_award` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT EXECUTE ON FUNCTION `onr_demo`.`gold`.`funding_anomaly_detector` TO `<APP_SERVICE_PRINCIPAL>`;
