-- ============================================================
-- Capture-date indexes on the Wansoft inventory tables (2026-10-16)
-- ============================================================
-- The nightly stage "Inventario - movimientos unificados" re-reads the Wansoft
-- rows captured in the last days (scripts/build_analytics_inventory_movements.py,
-- FechaEntrada / FechaSalida >= window start). Without an index on the capture
-- date, MariaDB scanned the whole exits table (37.5 M rows) every night: the
-- stage took ~30 min in production (nights of 2026-10-15 and 10-16) instead of
-- ~5 min on dev. EXPLAIN on production: type ALL.
--
-- Online in MariaDB 10.4 (ALGORITHM=INPLACE, LOCK=NONE): reads and writes go
-- on while the index builds. Run on the database server as a user with ALTER
-- on `wansoft` (phpMyAdmin as root, or wansoftuser), NOT during the nightly
-- cycle (01:30-03:00). Re-running is safe (IF NOT EXISTS).
-- Size: about 0.6-0.8 GB in total. Time: a few minutes for the exits table.
-- ============================================================

ALTER TABLE getoutgoinginventory_salida
    ADD INDEX IF NOT EXISTS idx_salida_fechasalida (FechaSalida), ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE getinputinventory_entrada
    ADD INDEX IF NOT EXISTS idx_entrada_fechaentrada (FechaEntrada), ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE wansoft_parallel_outgoinginventory_salida
    ADD INDEX IF NOT EXISTS idx_par_salida_fechasalida (FechaSalida), ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE wansoft_parallel_inputinventory_entrada
    ADD INDEX IF NOT EXISTS idx_par_entrada_fechaentrada (FechaEntrada), ALGORITHM=INPLACE, LOCK=NONE;

-- Verify: each must show its new index in "key"
EXPLAIN SELECT COUNT(*) FROM getoutgoinginventory_salida WHERE FechaSalida >= CURRENT_DATE - INTERVAL 10 DAY;
EXPLAIN SELECT COUNT(*) FROM getinputinventory_entrada WHERE FechaEntrada >= CURRENT_DATE - INTERVAL 10 DAY;
