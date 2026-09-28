-- ============================================================
-- Read-only database users for tukanmx (external Q&A / chatbot ETL)
-- ============================================================
-- Two users, mirroring the project's own wansoftuser / zenputuser split:
--   tukan_wansoft -> SELECT on the documented tables of `wansoft` only
--   tukan_zenput  -> SELECT on `zenput`
-- The table list is exactly docs/data-access-guide/ (Sections 4-5); keep
-- both in sync when a table is added or retired.
--
-- Run as root on the database machine (phpMyAdmin > SQL).
--
-- BEFORE RUNNING:
--   * Replace both CHANGE_ME passwords with long random ones. Never commit
--     the real passwords; hand them to tukanmx through a private channel.
--   * If tukanmx gives you fixed IP addresses, replace '%' with them
--     (e.g. 'tukan_wansoft'@'203.0.113.10'). '%' accepts any address, and
--     this server is reachable from the internet without TLS.
--
-- Limits (protect the production database used by Power BI, the pipeline
-- and ControlPresupuestos_AP):
--   MAX_USER_CONNECTIONS 4    at most 4 simultaneous sessions per user
--   MAX_STATEMENT_TIME 1800   any single query is killed after 30 minutes;
--                             raise it temporarily for their first full
--                             extraction of getoutgoinginventory_salida if needed
--
-- Run the WHOLE file at the 2026-10-01 cutover, AFTER the migration has
-- created the analytics/dimension tables in `wansoft` (MariaDB refuses a
-- table-level GRANT on a table that does not exist yet). Parts A and B are
-- kept separate only so part A could run on its own if ever needed.
-- Tested on dev 2026-09-28: allowed SELECT works, other tables and any
-- write are denied, the Zenput user cannot open `wansoft`, limits applied.
-- ============================================================

-- ---------------- PART A ----------------

CREATE USER IF NOT EXISTS 'tukan_wansoft'@'%' IDENTIFIED BY 'CHANGE_ME_WANSOFT'
    WITH MAX_USER_CONNECTIONS 4 MAX_STATEMENT_TIME 1800;
CREATE USER IF NOT EXISTS 'tukan_zenput'@'%' IDENTIFIED BY 'CHANGE_ME_ZENPUT'
    WITH MAX_USER_CONNECTIONS 4 MAX_STATEMENT_TIME 1800;

-- Sales
GRANT SELECT ON `wansoft`.`getallordenesbyday_new_venta`        TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`getallordenesbyday_new_detalleventa` TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`getallordenesbyday_new_pago`         TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`getallordenesbyday_new_modificador`  TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`getglobalcashclosing`                TO 'tukan_wansoft'@'%';
-- Costs
GRANT SELECT ON `wansoft`.`costeomensual`                       TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`costeomensual_semanapyq`             TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`gettotalcostbydate`                  TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`gettablajeriareport`                 TO 'tukan_wansoft'@'%';
-- Wansoft invoices and inventory movements
GRANT SELECT ON `wansoft`.`getexpenses_factura`                 TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`getinputinventory_entrada`           TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`getoutgoinginventory_salida`         TO 'tukan_wansoft'@'%';

-- Zenput: the whole database (4 tables, all documented)
GRANT SELECT ON `zenput`.* TO 'tukan_zenput'@'%';

-- ---------------- PART B (after the cutover migration) ----------------

-- Unified purchases and inventory
GRANT SELECT ON `wansoft`.`analytics_purchase_order_lines`               TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`analytics_purchase_orders`                    TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`analytics_purchase_daily_company_product`     TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`analytics_inventory_current_product_location` TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`analytics_inventory_balance`                  TO 'tukan_wansoft'@'%';
-- Governance and dimensions
GRANT SELECT ON `wansoft`.`analytics_company_domain_coverage`            TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`dim_company_analytical`                       TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`dim_product`                                  TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`dim_vendor`                                   TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`dim_time`                                     TO 'tukan_wansoft'@'%';

-- ---------------- VERIFY ----------------
SHOW GRANTS FOR 'tukan_wansoft'@'%';
SHOW GRANTS FOR 'tukan_zenput'@'%';

-- ---------------- REVOKE (end of the engagement) ----------------
-- DROP USER 'tukan_wansoft'@'%';
-- DROP USER 'tukan_zenput'@'%';
