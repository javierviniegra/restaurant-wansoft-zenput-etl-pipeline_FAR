-- ============================================================
-- Cutover migration, part 6: November wave (Aeropuerto, Taquería Viaducto)
-- ============================================================
-- Owner, 2026-10-12: both start on Odoo on Sunday 2026-11-01. In Odoo they are
-- branches (res.company 32 and 33) of the legal entity FONDA ARGENTINA
-- AEROPUERTO (8); their warehouses exist since October (Aerop, Taque) and on
-- 2026-10-28 they had no purchase orders, stock moves or journal entries yet.
--
-- 1. odoo_company_migration_policy: one active row each, migrated_from_wansoft,
--    operational_start_date 2026-11-01 (company names exactly as in Odoo).
-- 2. Relabel their Wansoft canonical purchase history from
--    final_wansoft_enabled to wansoft_history_before_odoo (same as cutover_05;
--    never the full delete-and-reload, which loses the history since 2021).
--    Only the label changes; every relabelled order is before 2026-11-01.
--
-- Run AFTER the code with the COMPANY_SOURCE flip is deployed (git log on the
-- VM shows it); then the nightly cycle rebuilds the analytics layer:
-- purchases and expenses split at 2026-11-01, the daily stock table relabels
-- the Wansoft history and starts the Odoo series (late-cutover guard in
-- scripts/build_analytics_inventory_stock_daily.py), costs stay on Wansoft
-- until Odoo has a complete invoiced month (COSTS_AUTO_SWITCH_TO_ODOO).
-- Names are matched without accents so the client's character set cannot
-- break the match; the accented insert uses a byte literal for the same reason.
-- Checklist: docs/odoo-wave-2026-11-01-checklist.md.
-- ============================================================

SELECT odoo_company_id, company_name, operational_start_date, is_active
FROM odoo_company_migration_policy
WHERE odoo_company_id IN (32, 33);
-- Expected before: 0 rows.

INSERT INTO odoo_company_migration_policy
    (odoo_company_id, company_name, company_migration_type, history_source, include_odoo_history,
     operational_start_date, is_active, notes)
VALUES
    (32, 'Aeropuerto', 'migrated_from_wansoft', 'wansoft', 0, '2026-11-01', 1,
     'November wave (owner, 2026-10-12): branch of FONDA ARGENTINA AEROPUERTO (8). Wansoft history kept until 2026-10-31.'),
    (33, CONCAT('Taquer', _utf8mb4 X'C3AD', 'a Viaducto'), 'migrated_from_wansoft', 'wansoft', 0, '2026-11-01', 1,
     'November wave (owner, 2026-10-12): branch of FONDA ARGENTINA AEROPUERTO (8). Wansoft history kept until 2026-10-31.');
SELECT ROW_COUNT() AS policy_rows_inserted_expected_2;

SELECT company_source_key, final_purchase_source_status, COUNT(*) AS lines_before
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft' AND (company_source_key = 'Aeropuerto' OR company_source_key LIKE 'Taquer%a Viaducto')
GROUP BY company_source_key, final_purchase_source_status;

UPDATE canonical_purchase_order_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key = 'Aeropuerto' OR company_source_key LIKE 'Taquer%a Viaducto')
  AND order_date < '2026-11-01';
SELECT ROW_COUNT() AS orders_relabelled;

UPDATE canonical_purchase_order_line_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key = 'Aeropuerto' OR company_source_key LIKE 'Taquer%a Viaducto')
  AND order_date < '2026-11-01';
SELECT ROW_COUNT() AS lines_relabelled;

UPDATE canonical_purchase_receipt_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key = 'Aeropuerto' OR company_source_key LIKE 'Taquer%a Viaducto');
SELECT ROW_COUNT() AS receipts_relabelled;

UPDATE canonical_purchase_receipt_move_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key = 'Aeropuerto' OR company_source_key LIKE 'Taquer%a Viaducto');
SELECT ROW_COUNT() AS receipt_moves_relabelled;

SELECT company_source_key, final_purchase_source_status, COUNT(*) AS lines_after, MAX(order_date) AS last_order_date
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft' AND (company_source_key = 'Aeropuerto' OR company_source_key LIKE 'Taquer%a Viaducto')
GROUP BY company_source_key, final_purchase_source_status;
-- Expected after: only wansoft_history_before_odoo for both.

SELECT odoo_company_id, company_name, HEX(company_name) AS name_bytes, operational_start_date, is_active
FROM odoo_company_migration_policy
WHERE odoo_company_id IN (32, 33);
-- Expected: 2 rows; Taquería Viaducto's bytes contain C3AD (the accented i).
