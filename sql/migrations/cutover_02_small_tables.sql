-- ============================================================
-- Cutover migration, part 2 of 3: small legacy tables
-- ============================================================
-- Brings production's legacy Wansoft tables in line with dev
-- (see sql/maintenance/add_unique_keys_dedup_protection.sql for why
-- these keys exist). Run AFTER part 1 (the 41 new tables + 2 views
-- loaded from dev's dump) and BEFORE the first pipeline run.
--
-- Rehearsed on wansoft_prueba on 2026-09-28; replayed on wansoft at
-- the 2026-10-01 cutover. Every table here is under 300K rows, so the
-- whole file runs in seconds.
--
-- Run with the target database selected, e.g.:
--   mysql --defaults-extra-file=C:\Backups\mysql\backup.cnf --database=wansoft_prueba
--         --execute="source C:/.../cutover_02_small_tables.sql"
--
-- Deliberately NOT included:
--   getexpenses_factura.uq_iddocumento_sucursal -- already exists in production.
-- ============================================================

-- 0) Drop the three old Sales backup tables (the live ones are the *_new_*
--    tables) and the empty getallordenesbyday_new_pagos (the live payments
--    table is getallordenesbyday_new_pago, singular). Owner's decision
--    2026-09-28; no code in this repository uses them, and they remain in
--    the 2026-09-24 backup. The owner reports nothing writes to them any
--    more (row counts confirm it), but at cutover this still runs only
--    AFTER the FondaCroned_* tasks are disabled.
DROP TABLE IF EXISTS getallordenesbyday_venta,
                     getallordenesbyday_detalleventa,
                     getallordenesbyday_modificador,
                     getallordenesbyday_new_pagos;

-- 1) costeomensual_semanapyq: 48 duplicate (subsidiary_id, day) pairs in
--    production (checked 2026-09-28), all captured 2025-05-06..08, exactly 2 rows each.
--    In all 48 the LOWER id is an all-zero capture and the higher id is the
--    later, real one, so this keeps the HIGHEST id per pair (the opposite of the
--    getglobalcashclosing dedup, where rows were identical).
SELECT COUNT(*) AS rows_to_delete_expected_48
FROM costeomensual_semanapyq t
JOIN (SELECT * FROM (SELECT subsidiary_id s, DATE(created_at) d, MAX(id) keep_id
                     FROM costeomensual_semanapyq
                     GROUP BY subsidiary_id, DATE(created_at)
                     HAVING COUNT(*) > 1) x) g
  ON t.subsidiary_id = g.s AND DATE(t.created_at) = g.d AND t.id < g.keep_id;

DELETE t
FROM costeomensual_semanapyq t
JOIN (SELECT * FROM (SELECT subsidiary_id s, DATE(created_at) d, MAX(id) keep_id
                     FROM costeomensual_semanapyq
                     GROUP BY subsidiary_id, DATE(created_at)
                     HAVING COUNT(*) > 1) x) g
  ON t.subsidiary_id = g.s AND DATE(t.created_at) = g.d AND t.id < g.keep_id;

SELECT ROW_COUNT() AS rows_deleted;

-- 2) Generated business-date column + unique key (same definition as dev).
ALTER TABLE costeomensual_semanapyq
    ADD COLUMN created_date DATE AS (DATE(created_at)) PERSISTENT,
    ADD UNIQUE KEY uq_subsidiary_created_date (subsidiary_id, created_date);

ALTER TABLE costeomensual
    ADD COLUMN created_date DATE AS (DATE(created_at)) PERSISTENT,
    ADD UNIQUE KEY uq_subsidiary_created_date (subsidiary_id, created_date);

ALTER TABLE gettotalcostbydate
    ADD COLUMN created_date DATE AS (DATE(created_at)) PERSISTENT,
    ADD UNIQUE KEY uq_subsidiary_created_date (subsidiary_id, created_date);

-- 3) Cash closing: real business-date column, no generated column needed.
--    Production had 0 duplicates on 2026-09-28.
ALTER TABLE getglobalcashclosing
    ADD UNIQUE KEY uq_subsidiary_fecha_corte (subsidiary_id, fecha_corte);

-- 4) Verification: expect 4 rows, all non_unique = 0.
SELECT table_name, index_name, non_unique
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND index_name IN ('uq_subsidiary_created_date', 'uq_subsidiary_fecha_corte')
  AND seq_in_index = 1
ORDER BY table_name;
