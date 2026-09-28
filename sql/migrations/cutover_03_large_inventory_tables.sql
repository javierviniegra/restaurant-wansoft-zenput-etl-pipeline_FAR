-- ============================================================
-- Cutover migration, part 3 of 3: large inventory tables
-- ============================================================
-- getoutgoinginventory_salida (~37M rows) and getinputinventory_entrada
-- (~1.8M rows). Heavy on disk: run when the database machine is quiet if
-- possible, never in the same window as a backup or restore, and at
-- cutover only AFTER the FondaCroned_* tasks are disabled (nothing may
-- write to getoutgoinginventory_salida between steps A and C).
--
-- REQUIRED before the first run of the new pipeline:
-- legacy/wansoft/automaticos/getOutgoingInventory.py upserts with
-- INSERT ... ON DUPLICATE KEY UPDATE against uq_subsidiary_fecha_idsalida;
-- without that key every run would append duplicates.
--
-- Run each step as its own command and check its result before the next.
--
-- Rehearsal on wansoft_prueba, 2026-09-28 (copy of production as of
-- 2026-09-24 14:42):
--   step A  25.6 min  61,125 duplicate groups / 138,495 rows (77,370 surplus)
--   step B  seconds   all 61,125 groups identical on every business column;
--                     surplus copies were inserted in three bulk reloads
--                     (2025-04, 2026-02, 2026-07), none in 2026-08/09
--   step C  seconds   77,370 deleted
--   step D  4.8 min  both indexes, online
-- ============================================================

-- STEP A: materialise the duplicate groups and their rows once (two full
-- scans), so every later check runs against ~140K rows instead of ~37M.
DROP TABLE IF EXISTS tmp_salida_dup_keys, tmp_salida_dup_rows, tmp_salida_ids_to_delete;

CREATE TABLE tmp_salida_dup_keys (INDEX k (subsidiary_name, Fecha, IdSalida))
SELECT subsidiary_name, Fecha, IdSalida, COUNT(*) AS n, MIN(id) AS min_id, MAX(id) AS max_id
FROM getoutgoinginventory_salida
GROUP BY subsidiary_name, Fecha, IdSalida
HAVING COUNT(*) > 1;

CREATE TABLE tmp_salida_dup_rows (INDEX k (subsidiary_name, Fecha, IdSalida))
SELECT s.*
FROM getoutgoinginventory_salida s
JOIN tmp_salida_dup_keys d
  ON s.subsidiary_name = d.subsidiary_name AND s.Fecha = d.Fecha AND s.IdSalida = d.IdSalida;

SELECT (SELECT COUNT(*) FROM tmp_salida_dup_keys) AS dup_groups,
       (SELECT COUNT(*) FROM tmp_salida_dup_rows) AS dup_rows;

-- STEP B (read-only): are the duplicates exact copies? `identical` must equal
-- `dup_groups`. If not, STOP: rows sharing the key but differing in content
-- would mean the key is wrong, and deleting them would lose data.
SELECT COUNT(*) AS dup_groups, SUM(v = 1) AS identical
FROM (SELECT COUNT(DISTINCT MD5(CONCAT_WS('|',
          COALESCE(IdEntrada,'~'), COALESCE(IdAlmacen,-1), COALESCE(Almacen,'~'),
          COALESCE(Departamento,'~'), COALESCE(IdProducto,-1), COALESCE(CodigoProducto,'~'),
          COALESCE(IdUnidadDeMedida,-1), COALESCE(TipoSalida,'~'), COALESCE(Cantidad,-1),
          COALESCE(CostoUnitario,-1), COALESCE(Caducidad,'1900-01-01'),
          COALESCE(FechaSalida,'1900-01-01'), COALESCE(IdTransferencia,'~'),
          COALESCE(FolioTransferencia,'~'), COALESCE(Orden,'~'), COALESCE(IdDetalleVenta,'~'),
          COALESCE(IdUsuario,'~'), COALESCE(FechaReal,'1900-01-01')))) AS v
      FROM tmp_salida_dup_rows
      GROUP BY subsidiary_name, Fecha, IdSalida) g;

-- STEP C: delete the surplus copies by primary key, keeping the original
-- (lowest id) of each group. Expected deleted = SUM(n - 1) from step A.
CREATE TABLE tmp_salida_ids_to_delete (PRIMARY KEY (id))
SELECT r.id
FROM tmp_salida_dup_rows r
JOIN tmp_salida_dup_keys k
  ON r.subsidiary_name = k.subsidiary_name AND r.Fecha = k.Fecha
 AND r.IdSalida = k.IdSalida AND r.id > k.min_id;

SELECT COUNT(*) AS rows_to_delete FROM tmp_salida_ids_to_delete;

DELETE s
FROM tmp_salida_ids_to_delete t
JOIN getoutgoinginventory_salida s ON s.id = t.id;

SELECT ROW_COUNT() AS rows_deleted;

-- STEP D: the indexes. In place, without blocking readers or writers.
ALTER TABLE getinputinventory_entrada
    ADD INDEX idx_identrada_subsidiary (IdEntrada, subsidiary_name),
    ALGORITHM = INPLACE, LOCK = NONE;

ALTER TABLE getoutgoinginventory_salida
    ADD UNIQUE KEY uq_subsidiary_fecha_idsalida (subsidiary_name, Fecha, IdSalida),
    ALGORITHM = INPLACE, LOCK = NONE;

-- Verification: expect 2 rows (idx non_unique = 1, uq non_unique = 0).
SELECT table_name, index_name, non_unique
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND index_name IN ('idx_identrada_subsidiary', 'uq_subsidiary_fecha_idsalida')
  AND seq_in_index = 1;

-- STEP E: clean up the helper tables once step D succeeded.
DROP TABLE IF EXISTS tmp_salida_dup_keys, tmp_salida_dup_rows, tmp_salida_ids_to_delete;
