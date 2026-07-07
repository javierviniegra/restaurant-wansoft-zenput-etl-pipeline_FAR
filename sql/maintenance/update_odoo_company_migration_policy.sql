-- =====================================================
-- MAINTENANCE: Odoo Company Migration Policy Updates
-- Purpose:
--   Controlled updates for company migration policy.
--
-- Use cases:
--   1. Mark a company as a new Odoo branch
--   2. Adjust operational start date
--   3. Disable a company policy
--   4. Correct company migration type
--
-- Important:
--   Do not run the full file blindly in production.
--   Copy and execute only the block required for the approved change.
-- =====================================================


-- =====================================================
-- Example 1:
-- Mark an existing company as a new Odoo branch.
-- =====================================================

-- UPDATE odoo_company_migration_policy
-- SET
--     company_migration_type = 'new_odoo_branch',
--     history_source = 'odoo',
--     include_odoo_history = 1,
--     operational_start_date = '2026-07-07',
--     notes = 'New Odoo branch. Odoo history included from operational start date.'
-- WHERE company_name = 'FONDA ARGENTINA ENCUENTRO OCEANIA';


-- =====================================================
-- Example 2:
-- Adjust operational start date for a migrated branch.
-- =====================================================

-- UPDATE odoo_company_migration_policy
-- SET
--     operational_start_date = '2026-06-01',
--     notes = 'Migrated from Wansoft. Odoo included only from approved operational date.'
-- WHERE company_name = 'FONDA ARGENTINA MAQ';


-- =====================================================
-- Example 3:
-- Disable a company policy without deleting it.
-- =====================================================

-- UPDATE odoo_company_migration_policy
-- SET
--     is_active = 0,
--     notes = 'Policy disabled. Company excluded from migration-aware ETL.'
-- WHERE company_name = 'COMPANY NAME';


-- =====================================================
-- Example 4:
-- Insert a new company policy manually.
-- =====================================================

-- INSERT INTO odoo_company_migration_policy (
--     odoo_company_id,
--     company_name,
--     company_migration_type,
--     history_source,
--     include_odoo_history,
--     operational_start_date,
--     is_active,
--     notes
-- )
-- VALUES (
--     999,
--     'NEW COMPANY NAME',
--     'new_odoo_branch',
--     'odoo',
--     1,
--     '2026-07-07',
--     1,
--     'New Odoo branch. Odoo history included from operational start date.'
-- )
-- ON DUPLICATE KEY UPDATE
--     company_name = VALUES(company_name),
--     company_migration_type = VALUES(company_migration_type),
--     history_source = VALUES(history_source),
--     include_odoo_history = VALUES(include_odoo_history),
--     operational_start_date = VALUES(operational_start_date),
--     is_active = VALUES(is_active),
--     notes = VALUES(notes);


-- =====================================================
-- Validation query
-- =====================================================

SELECT
    odoo_company_id,
    company_name,
    company_migration_type,
    history_source,
    include_odoo_history,
    operational_start_date,
    is_active,
    notes
FROM odoo_company_migration_policy
ORDER BY company_name;