-- ============================================================
-- Cutover migration, part 3 of 3: large inventory tables
-- ============================================================
-- getoutgoinginventory_salida (~37M rows) and getinputinventory_entrada
-- (~1.8M rows). Heavy on disk: run when the database machine is quiet if
-- possible, and never in the same window as a backup or restore.
--
-- REQUIRED before the first run of the new pipeline:
-- legacy/wansoft/automaticos/getOutgoingInventory.py upserts with
-- INSERT ... ON DUPLICATE KEY UPDATE against uq_subsidiary_fecha_idsalida;
-- without that key every run would append duplicates.
--
-- Rehearsed on wansoft_prueba on 2026-09-28 (record the timings here),
-- replayed on wansoft at the 2026-10-01 cutover.
-- ============================================================

-- STEP A (read-only, run alone first): duplicates on the future unique key.
-- A full scan of ~37M rows. Expect 0; if not, STOP and decide a dedup rule
-- before running step B (the ALTER would fail with error 1062 anyway).
SELECT COUNT(*) AS duplicate_groups, COALESCE(SUM(n - 1), 0) AS surplus_rows
FROM (SELECT COUNT(*) AS n
      FROM getoutgoinginventory_salida
      GROUP BY subsidiary_name, Fecha, IdSalida
      HAVING COUNT(*) > 1) x;

-- STEP B: the indexes. In-place and without blocking readers or writers.
ALTER TABLE getinputinventory_entrada
    ADD INDEX idx_identrada_subsidiary (IdEntrada, subsidiary_name),
    ALGORITHM = INPLACE, LOCK = NONE;

ALTER TABLE getoutgoinginventory_salida
    ADD UNIQUE KEY uq_subsidiary_fecha_idsalida (subsidiary_name, Fecha, IdSalida),
    ALGORITHM = INPLACE, LOCK = NONE;

-- STEP C: verification, expect 2 rows (idx non_unique = 1, uq non_unique = 0).
SELECT table_name, index_name, non_unique
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND index_name IN ('idx_identrada_subsidiary', 'uq_subsidiary_fecha_idsalida')
  AND seq_in_index = 1;
