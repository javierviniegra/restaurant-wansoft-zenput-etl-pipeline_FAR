-- ============================================================
-- Cutover migration, part 4: Odoo start date 2026-10-01 for the branches
-- migrated from Wansoft (owner's decision 2026-09-29)
-- ============================================================
-- Acoxpa (FONDA COSTA NERA), Antenas, Tepeyac (MAQ), Oceanía and La Esquina
-- Coyoacán kept entering purchases, inventory and costs in Wansoft in
-- parallel until the cutover, so production already holds their complete
-- Wansoft history. They read Odoo only from 2026-10-01, like the October
-- wave (Isabel La Católica, San Jerónimo, Vía Vallejo, already 2026-10-01).
-- Puebla and CentroMyJ (born on Odoo) keep their opening dates, and the two
-- internal providers (El Bodegón de Fito, Las Empanadas de María Eva) are not
-- branches and are left as they are.
--
-- Effect, through odoo_company_migration_policy.operational_start_date:
--   purchases  Odoo orders before 2026-10-01 drop out of the canonical/analytics
--              layer on the next run; Wansoft invoices before it are kept
--              (wansoft_history_before_odoo) once the Wansoft side is reloaded
--   costs      extract/costs/cost_routing.py uses Wansoft before 2026-10-01
--              (Antenas stays on Wansoft after it too: temporary exception)
--
-- REQUIRED right after this file: one run of the purchases pipeline with a
-- Wansoft window reaching back before 2026-06-01, so June-September Wansoft
-- invoices of these branches are reclassified into the canonical layer, then
-- the analytics purchase rebuild. Do NOT use
-- scripts/reload_purchase_canonical_wansoft_side.py: it deletes the whole
-- Wansoft side, and the ETL only reloads its window (history since 2021 would
-- be lost). See docs/production-cutover-runbook.md, cutover step 3c.
-- ============================================================

SELECT company_name, operational_start_date AS before_change
FROM odoo_company_migration_policy
WHERE company_name IN ('FONDA COSTA NERA', 'FONDA ARGENTINA LAS ANTENAS', 'FONDA ARGENTINA MAQ',
                       'FONDA ARGENTINA ENCUENTRO OCEANIA', 'FONDA ARGENTINA COYOACAN')
ORDER BY company_name;

UPDATE odoo_company_migration_policy
SET operational_start_date = '2026-10-01',
    notes = LEFT(CONCAT(COALESCE(notes, ''),
                        CASE WHEN notes IS NULL OR notes = '' THEN '' ELSE ' | ' END,
                        'Start moved to 2026-10-01 on 2026-09-29 (owner): Wansoft history kept in production until the cutover.'), 500)
WHERE company_name IN ('FONDA COSTA NERA', 'FONDA ARGENTINA LAS ANTENAS', 'FONDA ARGENTINA MAQ',
                       'FONDA ARGENTINA ENCUENTRO OCEANIA', 'FONDA ARGENTINA COYOACAN')
  AND operational_start_date <> '2026-10-01';

SELECT ROW_COUNT() AS rows_updated_expected_5;

SELECT company_name, company_migration_type, operational_start_date
FROM odoo_company_migration_policy
WHERE is_active = 1
ORDER BY operational_start_date, company_name;
