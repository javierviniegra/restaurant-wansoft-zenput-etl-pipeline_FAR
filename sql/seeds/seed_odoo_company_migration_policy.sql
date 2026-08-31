-- =====================================================
-- SEED: Odoo Company Migration Policy
-- Purpose:
--   Defines the initial company-level migration policy for
--   Odoo/Wansoft transition domains.
--
-- Important:
--   This file is a controlled seed.
--   It should be reviewed before production execution.
--
-- Rules:
--   migrated_from_wansoft:
--     - historical source remains Wansoft
--     - Odoo data is included only from operational_start_date
--
--   new_odoo_branch:
--     - historical source is Odoo
--     - Odoo data is included from operational_start_date
-- =====================================================

INSERT INTO odoo_company_migration_policy (
    odoo_company_id,
    company_name,
    company_migration_type,
    history_source,
    include_odoo_history,
    operational_start_date,
    is_active,
    notes
)
VALUES
(
    2,
    'EL BODEGON DE FITO',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-01',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    5,
    'FONDA ARGENTINA',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-24',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    36,
    'FONDA ARGENTINA COYOACAN',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-01',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    11,
    'FONDA ARGENTINA ENCUENTRO OCEANIA',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-30',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    9,
    'FONDA ARGENTINA LAS ANTENAS',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-01',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    10,
    'FONDA ARGENTINA MAQ',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-01',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    34,
    'FONDA ARGENTINA PUEBLA',
    'new_odoo_branch',
    'odoo',
    1,
    '2026-06-10',
    1,
    'Activated 2026-08-31. No Wansoft purchase/inventory history ever existed for Puebla (confirmed: 0 rows in getinputinventory_entrada / getOutgoingInventory_Salida) -- pure new_odoo_branch, same pattern as CentroMyJ. operational_start_date matches the value already active in production (differs from the original seed of 2026-07-22, kept as-is per the same policy already used for Acoxpa/Tepeyac/Oceania).'
),
(
    6,
    'FONDA ARGENTINA SAN JERONIMO',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-23',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    7,
    'FONDA COSTA NERA',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-07-01',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    3,
    'LAS EMPANADAS DE MARIA EVA',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-05',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
),
(
    35,
    'MARIO Y JULY',
    'new_odoo_branch',
    'odoo',
    1,
    '2026-06-01',
    1,
    'Initial policy seed from current purchase snapshot. Review company type before production.'
)
ON DUPLICATE KEY UPDATE
    company_name = VALUES(company_name),
    company_migration_type = VALUES(company_migration_type),
    history_source = VALUES(history_source),
    include_odoo_history = VALUES(include_odoo_history),
    operational_start_date = VALUES(operational_start_date),
    is_active = VALUES(is_active),
    notes = VALUES(notes);