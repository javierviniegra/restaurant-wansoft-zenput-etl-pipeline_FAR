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

-- ---------------- PART C (2026-10-05, after the night of 10-05 to 10-06) ----------------
-- Cost routing per branch, published nightly by the pipeline (guide 5.2 / 5.6).
-- The table is created by the first night run with the code of 2026-10-05; on a
-- server where tukan_wansoft already exists, run only this line (as root).
GRANT SELECT ON `wansoft`.`costs_source_by_company`                      TO 'tukan_wansoft'@'%';

-- ---------------- PART D (2026-10-08, after the night of 10-08 to 10-09) ----------------
-- Odoo stock day by day, written nightly since stock date 2026-10-08 (guide 5.4,
-- docs/inventory-coverage-by-branch.md). The table is created by the first night
-- run with the code of 2026-10-08; run only this line (as root).
GRANT SELECT ON `wansoft`.`odoo_inventory_quant_daily`                   TO 'tukan_wansoft'@'%';

-- ---------------- PART E (2026-10-13) ----------------
-- Wansoft inventory the 8 Odoo-migrated branches keep capturing in parallel,
-- loaded nightly since the night of 2026-10-12 to 10-13 (guide 5.4). Comparison
-- only: never part of the business totals.
GRANT SELECT ON `wansoft`.`wansoft_parallel_inputinventory_entrada`      TO 'tukan_wansoft'@'%';
GRANT SELECT ON `wansoft`.`wansoft_parallel_outgoinginventory_salida`    TO 'tukan_wansoft'@'%';

-- ---------------- PART F (2026-10-16) ----------------
-- Unified inventory movements, Wansoft + Odoo, full history (guide 1.4, 5.4),
-- live in production since 2026-10-14. tukanmx reported on 2026-10-16 that
-- parts C, D and E had never been applied in production (22 grants, not 26):
-- run C, D, E and F together.
GRANT SELECT ON `wansoft`.`analytics_inventory_movements`                TO 'tukan_wansoft'@'%';

-- ---------------- PART G (2026-10-16, once the table exists) ----------------
-- Odoo product -> Wansoft code equivalence, published nightly by the movements
-- build (guide 1.4, 5.4). tukanmx asked which table to use for it; dim_product
-- still carries mappings under review.
GRANT SELECT ON `wansoft`.`analytics_odoo_product_code`                  TO 'tukan_wansoft'@'%';

-- ---------------- PART H (2026-10-22, once the table exists) ----------------
-- Unified supplier invoices, Wansoft + Odoo, by Cuenta (guide 1.8), live in
-- production since 2026-10-22. Sensitive (rent, salaries, fees): tukanmx must
-- restrict it to authorised users, by expense level (guide 1.6/1.8), like
-- getexpenses_factura. The helper tables (expense_account_mapping,
-- expense_vendor_rule, odoo_vendor_bill_*, wansoft_expense_live_status) are
-- not granted.
GRANT SELECT ON `wansoft`.`analytics_expense_invoices`                   TO 'tukan_wansoft'@'%';

-- Re-running the WHOLE file is safe: CREATE USER IF NOT EXISTS leaves an
-- existing user and its password untouched (a note, not an error), and a GRANT
-- that already exists changes nothing. Do that when parts C/D/E are in doubt.
-- The list of tables is also the source of the guide's schema appendix
-- (docs/data-access-guide/build_schema_appendix.py reads the GRANT lines).

-- ---------------- VERIFY ----------------
SHOW GRANTS FOR 'tukan_wansoft'@'%';
SHOW GRANTS FOR 'tukan_zenput'@'%';
-- Expected: USAGE + 29 table grants for tukan_wansoft (28 before part H, 2026-10-22); USAGE + `zenput`.* for tukan_zenput.

-- ---------------- DIAGNOSE: "Access denied ... @'localhost'" (2026-10-13) ----------------
-- phpMyAdmin runs ON the database server, so it logs in as 'tukan_wansoft'@'localhost'.
-- An anonymous user ''@'localhost' would win over '%' and reject the password.
-- Checked in production on 2026-10-13: no anonymous user exists, only the two
-- '%' users with a password, and the VM test below logged in; the phpMyAdmin
-- failure was most likely a mistyped password. Check:
SELECT user, host, plugin, authentication_string <> '' AS has_password
FROM mysql.user
WHERE user IN ('', 'tukan_wansoft', 'tukan_zenput')
ORDER BY user, host;
-- A real test is from another machine (the tasks VM), the way tukanmx connects:
--   C:\Backups\mariadb-client\mariadb-10.4.28-winx64\bin\mysql.exe -h 192.168.100.183 -u tukan_wansoft -p -e "SHOW GRANTS"

-- ---------------- REVOKE (end of the engagement) ----------------
-- DROP USER 'tukan_wansoft'@'%';
-- DROP USER 'tukan_zenput'@'%';
