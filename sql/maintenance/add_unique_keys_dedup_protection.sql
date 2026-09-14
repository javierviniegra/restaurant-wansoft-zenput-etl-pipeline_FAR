-- ============================================================
-- Unique-key dedup protection, 6 legacy Wansoft tables
-- ============================================================
-- Applied to dev on 2026-09-14. Documented here for reference and for
-- replaying on production once that side of the project is promoted --
-- see docs/production-orchestration-plan.md for the promotion gate.
--
-- Why: getoutgoinginventory_salida had a real, confirmed duplicate-insert
-- bug (found 2026-09-09, recurred in a different form 2026-09-10) caused
-- by relying on an in-memory Python dict to detect "does this row already
-- exist" before insert/update. A real unique constraint makes duplicate
-- inserts structurally impossible regardless of what the Python-side
-- logic does. The other 5 tables use the same "check in Python, then
-- INSERT" pattern for their own natural keys and were never proven
-- broken, but carry the identical structural risk -- added here as
-- defense in depth, not because a bug was confirmed in each of them.
--
-- Run once each, in order. Each ALTER is independent; if one table
-- already has existing duplicate rows for its intended key, the ALTER
-- will fail with error 1062 -- deduplicate first (keep the lowest `id`
-- per key group) before retrying. getglobalcashclosing needed this on
-- dev (1,170 duplicate rows found and removed before the index applied
-- cleanly).
-- ============================================================


-- getoutgoinginventory_salida: getOutgoingInventory.py now upserts
-- against this key directly (INSERT ... ON DUPLICATE KEY UPDATE),
-- replacing the old preload-into-a-dict approach.
ALTER TABLE getoutgoinginventory_salida
    ADD UNIQUE KEY uq_subsidiary_fecha_idsalida (subsidiary_name, Fecha, IdSalida);


-- getexpenses_factura: had zero indexes of any kind before this,
-- including no PRIMARY KEY. getExpenses.py's own existence check
-- (WHERE IdDocumento = %s AND Sucursal = %s) already matches this key.
ALTER TABLE getexpenses_factura
    ADD UNIQUE KEY uq_iddocumento_sucursal (IdDocumento, Sucursal);


-- costeomensual_semanapyq, costeomensual, gettotalcostbydate: these
-- three key on (subsidiary_id, business date), but the business date is
-- only available as DATE(created_at) -- MariaDB 10.4 does not support
-- indexing a raw expression directly in ADD INDEX, so a generated
-- column carries the date and gets indexed instead.
ALTER TABLE costeomensual_semanapyq
    ADD COLUMN created_date DATE AS (DATE(created_at)) PERSISTENT,
    ADD UNIQUE KEY uq_subsidiary_created_date (subsidiary_id, created_date);

ALTER TABLE costeomensual
    ADD COLUMN created_date DATE AS (DATE(created_at)) PERSISTENT,
    ADD UNIQUE KEY uq_subsidiary_created_date (subsidiary_id, created_date);

ALTER TABLE gettotalcostbydate
    ADD COLUMN created_date DATE AS (DATE(created_at)) PERSISTENT,
    ADD UNIQUE KEY uq_subsidiary_created_date (subsidiary_id, created_date);


-- getglobalcashclosing: keys on a real business-date column
-- (fecha_corte, not created_at), no generated column needed. Had 1,170
-- duplicate rows on dev before this ran -- see the dedup query below if
-- this needs to be replayed anywhere that also has existing duplicates.
--
-- Dedup query used on dev before this ALTER (keeps the lowest `id` per
-- (subsidiary_id, fecha_corte) group):
--   DELETE t1 FROM getglobalcashclosing t1
--   INNER JOIN getglobalcashclosing t2
--     ON t1.subsidiary_id <=> t2.subsidiary_id
--     AND t1.fecha_corte <=> t2.fecha_corte
--     AND t1.id > t2.id;
-- (Applied via a Python in-memory-group + batched-PK-delete script on
-- dev instead of this raw SQL, for consistency with how the
-- getoutgoinginventory_salida cleanups were done -- see project memory
-- project_scheduler_legacy_chaining_plan.)
ALTER TABLE getglobalcashclosing
    ADD UNIQUE KEY uq_subsidiary_fecha_corte (subsidiary_id, fecha_corte);


-- ============================================================
-- Not included here, deliberately:
--
-- getinputinventory_entrada -- already has a supporting (non-unique)
-- index (idx_identrada_subsidiary) and its own code checks existence
-- per-row in real time (not a batch preload into a dict), which is a
-- structurally safer pattern even without a hard constraint. Lower
-- priority; revisit if it's ever shown to actually duplicate.
--
-- gettablajeriareport -- has no single Wansoft-provided row ID; its
-- existence check uses 7 columns together (InputDate, ProductBase,
-- GeneratedProduct, subsidiary_id, QuantityOfBaseProduct,
-- QuantityDecrease, QuantityOfGeneratedProduct). A hard unique
-- constraint on all 7 is possible but was not attempted here -- needs
-- its own decision, not a drop-in copy of this pattern.
--
-- Sales domain (getallordenesbyday_new_venta/_pago/_detalleventa/
-- _modificador) -- already has real unique keys (Movimento, Pagos_Id,
-- Movimiento_Id) and uses INSERT IGNORE. No action needed; this is why
-- Sales has never shown a duplication bug.
-- ============================================================
