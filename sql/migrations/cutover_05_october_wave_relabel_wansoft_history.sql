-- ============================================================
-- Cutover migration, part 5: relabel the October wave's Wansoft history
-- ============================================================
-- Isabel La Católica, San Jerónimo and Vía Vallejo switch COMPANY_SOURCE to
-- "odoo" on 2026-10-01 (core/config/companies.py). Their Wansoft rows in the
-- canonical purchase tables were loaded as final_wansoft_enabled; from now on
-- they are wansoft_history_before_odoo. The nightly Wansoft canonical load only
-- reclassifies its own window (PURCHASES_LOOKBACK_DAYS), so every older row
-- would keep the old label and the canonical validation would flag it.
--
-- This replaces step 10 of the "Rollout Update Sequence" in
-- docs/purchases-company-migration-policy.md (full delete + reload), which
-- would lose the history beyond the load window. Only the status label
-- changes; amounts and dates are untouched, and every row is before the
-- 2026-10-01 start date. Names are matched without accents so the client's
-- character set cannot break the match.
--
-- Run AFTER the code with the COMPANY_SOURCE flip is deployed; then the
-- analytics purchase rebuild (the nightly cycle) propagates the label.
-- ============================================================

SELECT company_source_key, final_purchase_source_status, COUNT(*) AS lines_before
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft'
  AND (company_source_key LIKE 'Isabel La Cat%lica' OR company_source_key = 'San Jeronimo' OR company_source_key LIKE 'V%a Vallejo')
GROUP BY company_source_key, final_purchase_source_status;

UPDATE canonical_purchase_order_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key LIKE 'Isabel La Cat%lica' OR company_source_key = 'San Jeronimo' OR company_source_key LIKE 'V%a Vallejo')
  AND order_date < '2026-10-01';
SELECT ROW_COUNT() AS orders_relabelled;

UPDATE canonical_purchase_order_line_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key LIKE 'Isabel La Cat%lica' OR company_source_key = 'San Jeronimo' OR company_source_key LIKE 'V%a Vallejo')
  AND order_date < '2026-10-01';
SELECT ROW_COUNT() AS lines_relabelled;

UPDATE canonical_purchase_receipt_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key LIKE 'Isabel La Cat%lica' OR company_source_key = 'San Jeronimo' OR company_source_key LIKE 'V%a Vallejo');
SELECT ROW_COUNT() AS receipts_relabelled;

UPDATE canonical_purchase_receipt_move_snapshot
SET final_purchase_source_status = 'wansoft_history_before_odoo'
WHERE source_system = 'wansoft' AND final_purchase_source_status = 'final_wansoft_enabled'
  AND (company_source_key LIKE 'Isabel La Cat%lica' OR company_source_key = 'San Jeronimo' OR company_source_key LIKE 'V%a Vallejo');
SELECT ROW_COUNT() AS receipt_moves_relabelled;

SELECT company_source_key, final_purchase_source_status, COUNT(*) AS lines_after, MAX(order_date) AS last_order_date
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft'
  AND (company_source_key LIKE 'Isabel La Cat%lica' OR company_source_key = 'San Jeronimo' OR company_source_key LIKE 'V%a Vallejo')
GROUP BY company_source_key, final_purchase_source_status;
