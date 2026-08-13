-- Grant the Databricks App service principal access to onr_demo.
-- Replace <APP_SERVICE_PRINCIPAL> with the name or application ID from
--   App → onr-demo-poc → Authorization / Service principal
-- Keep the backticks.
--
-- Also in the UI: SQL Warehouses → "onr demo warehouse" → Permissions → CAN USE
-- for the same principal.

GRANT USE CATALOG ON CATALOG `onr_demo` TO `<APP_SERVICE_PRINCIPAL>`;

GRANT USE SCHEMA ON SCHEMA `onr_demo`.`bronze` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`silver` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`gold` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA `onr_demo`.`app` TO `<APP_SERVICE_PRINCIPAL>`;

-- SELECT/MODIFY/CREATE TABLE are not enough to CREATE OR REPLACE a table
-- owned by the human who ran bootstrap. MANAGE is required for the app
-- Process / Reset path.
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`bronze` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`silver` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`gold` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT, MODIFY, CREATE TABLE, MANAGE ON SCHEMA `onr_demo`.`app` TO `<APP_SERVICE_PRINCIPAL>`;

GRANT READ VOLUME, WRITE VOLUME ON VOLUME `onr_demo`.`bronze`.`landing` TO `<APP_SERVICE_PRINCIPAL>`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME `onr_demo`.`bronze`.`checkpoints` TO `<APP_SERVICE_PRINCIPAL>`;
