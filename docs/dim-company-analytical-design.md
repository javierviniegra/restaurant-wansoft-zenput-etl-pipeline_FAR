# dim_company_analytical Design and Closeout

## Purpose

This document defines and closes the initial implementation of `dim_company_analytical`, the shared analytical company dimension for the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

The purpose of this dimension is to provide one governed analytical row per canonical company, branch, internal provider, or operational location that must be understood consistently across domains.

This dimension belongs to the MySQL analytical layer.

It does not define:

```text
Power BI
reports
dashboards
visuals
semantic models
DAX measures
presentation layers
```

Those layers belong to a separate project.

The core rule remains:

```text
Reporting does not resolve business rules.
All business rules must be governed in MySQL before reporting consumes the data.
```

---

## Current Status

Current implementation status:

```text
scripts/build_dim_company_analytical.py created
scripts/validate_dim_company_analytical.py created
dim_company_analytical table created in MySQL
build completed successfully
validation completed successfully
source aliases canonicalized
raw aliases removed from dimension
internal providers classified
Zenput-only locations classified
Puebla mapped and not Zenput-only
migrated branches validated with operational_start_date
```

Current result:

```text
BUILD RESULT: COMPLETED
VALIDATION RESULT: PASSED
```

---

# Implementation Summary

## Build Command

```bash
python -m scripts.build_dim_company_analytical
```

## Build Result

Latest validated build result:

```text
DIM COMPANY ANALYTICAL BUILD SUMMARY

table: dim_company_analytical
total_rows_prepared: 24
active_branches: 18
internal_providers: 2
zenput_locations: 21
zenput_only: 3
future_rollouts: 4

BUILD RESULT: COMPLETED
```

---

## Validation Command

```bash
python -m scripts.validate_dim_company_analytical
```

## Validation Result

Latest validated result:

```text
total_validations: 10
passed: 10
failed: 0

VALIDATION RESULT: PASSED
```

Validated checks:

```text
dim_company_analytical_exists: PASS
dim_company_analytical_has_rows: PASS
company_source_key_unique: PASS
company_source_key_not_null: PASS
required_companies_exist: PASS
zenput_only_companies_classified: PASS
puebla_classification: PASS
internal_providers_classified: PASS
migrated_branches_operational_start_date: PASS
source_value_domains_valid: PASS
```

---

# Table Purpose

`dim_company_analytical` answers these questions:

```text
What is the canonical company_source_key?
Is this company an active operating branch?
Is this company an internal provider?
Does this company participate in Purchases?
Does this company participate in Inventory?
Does this company appear in Zenput?
Is this company currently Zenput-only?
Is this company Wansoft-source, Odoo-source, migrated, new Odoo branch, or future rollout?
What is the operational_start_date for migrated branches?
How should downstream analytical tables join by company?
```

This dimension is the anchor for:

```text
analytics_company_domain_coverage
analytics_purchase_orders
analytics_purchase_order_lines
analytics_inventory_snapshot
analytics_zenput_submissions
analytics_zenput_tasks
future analytics_sales_*
```

---

# Grain

The grain of the table is:

```text
1 row = 1 canonical company_source_key
```

A `company_source_key` may represent:

```text
final operating branch
migrated branch
new Odoo branch
future rollout branch
Zenput-only operational location
internal provider
```

The table is not limited to active restaurants.

It is the governed analytical company/location dimension.

---

# Final Canonicalization Rule

## Rule

Raw source names must not enter `dim_company_analytical` as separate company rows.

The dimension stores only canonical analytical keys.

Correct:

```text
CentroMyJ
Isabel La Católica
La Esquina Coyoacán
Oceanía
Antenas
Tepeyac
Acoxpa
Bodegón
Empanadas
```

Incorrect:

```text
MARIO Y JULY
FONDA ARGENTINA
FONDA ARGENTINA COYOACAN
FONDA ARGENTINA ENCUENTRO OCEANIA
FONDA ARGENTINA LAS ANTENAS
FONDA ARGENTINA MAQ
FONDA COSTA NERA
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Those values are source aliases.

They should not exist as separate `company_source_key` rows.

---

## Validated Alias Resolution

The implementation now canonicalizes these known aliases:

```text
MARIO Y JULY -> CentroMyJ
FONDA ARGENTINA -> Isabel La Católica
FONDA ARGENTINA COYOACAN -> La Esquina Coyoacán
FONDA ARGENTINA ENCUENTRO OCEANIA -> Oceanía
FONDA ARGENTINA LAS ANTENAS -> Antenas
FONDA ARGENTINA MAQ -> Tepeyac
FONDA COSTA NERA -> Acoxpa
EL BODEGON DE FITO -> Bodegón
LAS EMPANADAS DE MARIA EVA -> Empanadas
```

Validation query for raw aliases:

```sql
SELECT
    company_source_key,
    display_name,
    is_internal_provider,
    is_zenput_location,
    is_zenput_only,
    purchases_source_system,
    inventory_source_system,
    sales_source_system,
    zenput_source_status,
    rollout_type,
    rollout_status
FROM dim_company_analytical
WHERE company_source_key IN (
    'MARIO Y JULY',
    'FONDA ARGENTINA',
    'FONDA ARGENTINA COYOACAN',
    'FONDA ARGENTINA ENCUENTRO OCEANIA',
    'FONDA ARGENTINA LAS ANTENAS',
    'FONDA ARGENTINA MAQ',
    'FONDA COSTA NERA',
    'EL BODEGON DE FITO',
    'LAS EMPANADAS DE MARIA EVA'
)
ORDER BY company_source_key;
```

Expected result:

```text
0 rows
```

This was validated.

---

# Final Known Canonical Rows

The current dimension contains:

```text
24 canonical rows
```

Validated examples:

```text
Acoxpa
Aeropuerto
Antenas
Bodegón
Cancun
CentroMyJ
Empanadas
Isabel La Católica
La Esquina Coyoacán
León
Lindavista
Metepec
Napoles
Oceanía
Perisur
Playa del Carmen
Puebla
San Jeronimo
Taquería parroquia
Taquería Viaducto
Tepeyac
Versalles
Vía Vallejo
Viaducto
```

---

# Required Business Rules

## Rule 1: company_source_key is the analytical company key

The central key is:

```text
company_source_key
```

All analytical facts should join through this key.

---

## Rule 2: Odoo/Wansoft source selection is domain-specific

A branch can have different source behaviour by domain.

Domain source rules:

```text
Sales      -> Wansoft
Purchases  -> COMPANY_SOURCE / operational_start_date rules
Inventory  -> COMPANY_SOURCE / current inventory policy
Zenput     -> core/config/zenput.py location mapping
```

Therefore, the dimension stores domain-specific fields:

```text
purchases_source_system
inventory_source_system
sales_source_system
zenput_source_status
```

It does not rely on a single generic `source_system` field.

---

## Rule 3: Migrated branches require operational_start_date

Migrated branches need:

```text
operational_start_date
```

The rule is:

```text
Wansoft before operational_start_date.
Odoo from operational_start_date onward.
```

This prevents:

```text
gaps
duplicates
double counting
incorrect source ownership
```

Validated migrated branches:

```text
Antenas
La Esquina Coyoacán
```

Validation status:

```text
migrated_branches_operational_start_date: PASS
```

---

## Rule 4: New Odoo branches do not require Wansoft history

Current active new Odoo branch:

```text
CentroMyJ
```

Future new Odoo branch:

```text
Puebla
```

Expected logic:

```text
CentroMyJ:
    purchases_source_system = odoo
    inventory_source_system = odoo
    rollout_type = new_odoo_branch
    rollout_status = active

Puebla:
    purchases_source_system = pending
    inventory_source_system = pending
    rollout_type = new_odoo_branch
    rollout_status = future
```

---

## Rule 5: Zenput is independent from COMPANY_SOURCE

Zenput should not use:

```text
COMPANY_SOURCE
is_wansoft_company
```

as its inclusion filter.

Zenput maps:

```text
submissions.location_name -> company_source_key
```

through:

```text
core/config/zenput.py
```

---

## Rule 6: Zenput-only locations are valid analytical locations

Current Zenput-only locations:

```text
León
Lindavista
Perisur
```

Rules:

```text
They are valid for Zenput operational reporting.
They do not currently have Wansoft as operational source.
They are not expected to participate in Purchases or Inventory Wansoft/Odoo pipelines yet.
They should remain future-capable.
They should not be collapsed into other branches.
They should not receive fake Wansoft IDs.
```

Validation status:

```text
zenput_only_companies_classified: PASS
```

---

## Rule 7: Puebla is not Zenput-only

Puebla appeared in Zenput as:

```text
Fonda Argentina Puebla
```

Correct mapping:

```text
Fonda Argentina Puebla -> Puebla
```

Puebla should not be classified as Zenput-only.

Reason:

```text
Puebla already exists as company_source_key.
Puebla is modeled as a future Odoo / operational branch.
Puebla should be preserved as its own canonical key.
```

Validation status:

```text
puebla_classification: PASS
```

---

## Rule 8: Internal providers are not final operating branches

Current internal providers:

```text
Bodegón
Empanadas
```

Display names:

```text
Bodegón -> EL BODEGON DE FITO
Empanadas -> LAS EMPANADAS DE MARIA EVA
```

Rules:

```text
They exist in the analytical governance model.
They are marked as internal providers.
They are not final operating branches.
They may appear as vendors.
They are excluded by default from business-facing views.
They remain available for technical or intercompany analysis.
```

Validation status:

```text
internal_providers_classified: PASS
```

---

# Final Field Groups

## Identity Fields

```text
company_analytical_key
company_source_key
display_name
normalized_name
brand_group
```

---

## Branch Classification Fields

```text
is_active_branch
is_internal_provider
is_final_operating_branch
is_future_rollout
rollout_type
rollout_status
operational_start_date
```

---

## Source Domain Fields

```text
purchases_source_system
inventory_source_system
sales_source_system
zenput_source_status
```

---

## System Presence Flags

```text
is_wansoft_company
is_odoo_company
is_zenput_location
is_zenput_only
```

---

## Analytical Governance Fields

```text
include_in_business_views
exclude_reason
notes
created_at
updated_at
```

---

# Refresh Strategy

The current implementation uses exact rebuild semantics:

```text
DELETE FROM dim_company_analytical
INSERT / UPSERT current canonical rows
```

Reason:

```text
Section 17 is still in initial analytical design.
No downstream analytics facts depend on dim_company_analytical yet.
Exact rebuild removes stale aliases and prevents semantic duplicates.
```

Future consideration:

```text
Once analytics facts depend on dim_company_analytical, consider soft-deactivation instead of full delete.
```

Potential future fields:

```text
is_current
valid_from
valid_to
deactivated_at
deactivation_reason
```

---

# Current Scripts

## Build Script

```text
scripts/build_dim_company_analytical.py
```

Purpose:

```text
Create or refresh dim_company_analytical from configuration and validated source tables.
```

Current behaviour:

```text
canonicalizes aliases
applies Wansoft/Odoo source rules
applies migration policy data
applies rollout expectations
applies Zenput mapping
applies Zenput-only classification
applies internal provider flags
uses exact rebuild semantics
```

---

## Validation Script

```text
scripts/validate_dim_company_analytical.py
```

Purpose:

```text
Validate the analytical company dimension after build.
```

Current validations:

```text
dim_company_analytical_exists
dim_company_analytical_has_rows
company_source_key_unique
company_source_key_not_null
required_companies_exist
zenput_only_companies_classified
puebla_classification
internal_providers_classified
migrated_branches_operational_start_date
source_value_domains_valid
```

---

# Validation Query Examples

## 1. Raw aliases should not exist

```sql
SELECT
    company_source_key,
    display_name
FROM dim_company_analytical
WHERE company_source_key IN (
    'MARIO Y JULY',
    'FONDA ARGENTINA',
    'FONDA ARGENTINA COYOACAN',
    'FONDA ARGENTINA ENCUENTRO OCEANIA',
    'FONDA ARGENTINA LAS ANTENAS',
    'FONDA ARGENTINA MAQ',
    'FONDA COSTA NERA',
    'EL BODEGON DE FITO',
    'LAS EMPANADAS DE MARIA EVA'
);
```

Expected result:

```text
0 rows
```

---

## 2. Canonical keys should exist

```sql
SELECT
    company_source_key,
    display_name,
    is_internal_provider,
    is_zenput_location,
    is_zenput_only,
    purchases_source_system,
    inventory_source_system,
    sales_source_system,
    zenput_source_status,
    rollout_type,
    rollout_status
FROM dim_company_analytical
WHERE company_source_key IN (
    'CentroMyJ',
    'Isabel La Católica',
    'La Esquina Coyoacán',
    'Oceanía',
    'Antenas',
    'Tepeyac',
    'Acoxpa',
    'Bodegón',
    'Empanadas'
)
ORDER BY company_source_key;
```

Expected result:

```text
Acoxpa
Antenas
Bodegón
CentroMyJ
Empanadas
Isabel La Católica
La Esquina Coyoacán
Oceanía
Tepeyac
```

---

## 3. Zenput-only locations

```sql
SELECT
    company_source_key,
    is_zenput_location,
    is_zenput_only,
    zenput_source_status,
    purchases_source_system,
    inventory_source_system,
    sales_source_system
FROM dim_company_analytical
WHERE company_source_key IN ('León', 'Lindavista', 'Perisur');
```

Expected result:

```text
is_zenput_location = 1
is_zenput_only = 1
zenput_source_status = zenput_only
purchases_source_system = none
inventory_source_system = none
sales_source_system = none
```

---

## 4. Puebla

```sql
SELECT
    company_source_key,
    is_zenput_location,
    is_zenput_only,
    zenput_source_status,
    rollout_type,
    rollout_status,
    purchases_source_system,
    inventory_source_system
FROM dim_company_analytical
WHERE company_source_key = 'Puebla';
```

Expected result:

```text
is_zenput_location = 1
is_zenput_only = 0
zenput_source_status = mapped
rollout_type = new_odoo_branch
rollout_status = future
purchases_source_system = pending
inventory_source_system = pending
```

---

## 5. Internal providers

```sql
SELECT
    company_source_key,
    display_name,
    is_internal_provider,
    include_in_business_views,
    exclude_reason
FROM dim_company_analytical
WHERE is_internal_provider = TRUE;
```

Expected result:

```text
Bodegón
Empanadas

is_internal_provider = 1
include_in_business_views = 0
exclude_reason = internal_provider
```

---

# Relationship to analytics_company_domain_coverage

`dim_company_analytical` is now ready to serve as the base dimension for:

```text
analytics_company_domain_coverage
```

Recommended relationship:

```text
dim_company_analytical.company_source_key
    -> analytics_company_domain_coverage.company_source_key
```

`analytics_company_domain_coverage` should not create company classifications.

It should inherit them from:

```text
dim_company_analytical
```

and add domain coverage metrics such as:

```text
has_purchases
has_inventory
has_zenput_submissions
has_zenput_tasks
purchase_order_count
purchase_line_count
inventory_snapshot_count
zenput_submission_count
zenput_task_count
```

---

# Prepared Design for analytics_company_domain_coverage

## Purpose

`analytics_company_domain_coverage` will show which canonical companies have data coverage by domain.

It will help answer:

```text
Which companies have Purchases?
Which companies have Inventory?
Which companies have Zenput submissions?
Which companies have Zenput tasks?
Which companies are Zenput-only?
Which companies are future rollouts?
Which companies are internal providers?
Which companies are active business branches?
```

---

## Proposed Grain

```text
1 row = 1 company_source_key
```

It should have the same primary key grain as:

```text
dim_company_analytical
```

---

## Candidate Fields

```text
company_source_key
display_name
is_active_branch
is_internal_provider
is_final_operating_branch
is_future_rollout
is_zenput_location
is_zenput_only

purchases_source_system
inventory_source_system
sales_source_system
zenput_source_status
rollout_type
rollout_status
operational_start_date

has_purchases
has_purchase_orders
has_purchase_lines
has_inventory
has_zenput_submissions
has_zenput_tasks
has_sales_future_placeholder

purchase_order_count
purchase_line_count
inventory_snapshot_count
zenput_submission_count
zenput_task_count

coverage_status
coverage_notes
updated_at
```

---

## Candidate Source Tables

```text
dim_company_analytical
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
odoo_inventory_snapshot
submissions
zenput_tasks
```

Future:

```text
analytics_sales_*
sales canonical tables
```

---

## Initial Coverage Rules

### Purchases

```text
has_purchase_orders = true if canonical_purchase_order_snapshot has rows for company_source_key
has_purchase_lines = true if canonical_purchase_order_line_snapshot has rows for company_source_key
has_purchases = has_purchase_orders OR has_purchase_lines
```

### Inventory

```text
has_inventory = true if odoo_inventory_snapshot has rows for company_source_key
```

### Zenput

```text
has_zenput_submissions = true if mapped submissions exist for company_source_key
has_zenput_tasks = true if mapped zenput_tasks can be associated to company_source_key
```

### Sales

For now:

```text
has_sales_future_placeholder = null or false
```

Reason:

```text
analytics_sales_* is deferred to a future section.
```

---

## Expected Examples

### Acoxpa

```text
is_zenput_location = true
is_zenput_only = false
has_purchases = true
has_inventory = true
has_zenput_submissions = true
coverage_status = multi_domain
```

### Antenas

```text
rollout_type = migrated_from_wansoft
purchases_source_system = mixed_by_operational_start_date
has_purchases = true
has_inventory = true
has_zenput_submissions = true
coverage_status = multi_domain
```

### León

```text
is_zenput_only = true
has_purchases = false
has_inventory = false
has_zenput_submissions = true
coverage_status = zenput_only
```

### Puebla

```text
rollout_type = new_odoo_branch
rollout_status = future
zenput_source_status = mapped
has_purchases = false or pending
has_inventory = false or pending
has_zenput_submissions = true
coverage_status = future_with_zenput_activity
```

### Bodegón

```text
is_internal_provider = true
has_purchases may be false as company
coverage_status = internal_provider
include_in_business_views = false
```

---

## Coverage Status Suggested Values

```text
multi_domain
purchases_only
inventory_only
zenput_only
future_with_zenput_activity
future_no_activity
internal_provider
no_domain_activity
pending_review
```

---

## Validation Requirements for analytics_company_domain_coverage

The future validator should check:

```text
1 row per company_source_key
no duplicate company_source_key
all dim_company_analytical rows represented
all purchase companies represented
all inventory companies represented
all Zenput mapped companies represented
Zenput-only companies have has_zenput_submissions or has_zenput_tasks where applicable
internal providers are marked as internal_provider
Puebla is future_with_zenput_activity if only Zenput coverage exists
```

---

# Step 17.4 Closeout

This step is complete when:

```text
[x] dim_company_analytical build result documented
[x] dim_company_analytical validation result documented
[x] alias canonicalization rule documented
[x] internal provider rule documented
[x] Zenput-only rule documented
[x] Puebla rule documented
[x] refresh strategy documented
[x] analytics_company_domain_coverage initial design prepared
```

---

# Recommended Next Step

```text
Paso 17.5 — Implementar analytics_company_domain_coverage
```

Suggested files:

```text
scripts/build_analytics_company_domain_coverage.py
scripts/validate_analytics_company_domain_coverage.py
```

Expected flow:

```text
1. Build from dim_company_analytical.
2. Count coverage from Purchases canonical tables.
3. Count coverage from Inventory snapshot.
4. Count coverage from Zenput submissions.
5. Count coverage from Zenput tasks if location mapping is available.
6. Derive coverage_status.
7. Validate one row per company_source_key.
8. Validate key expected companies.
```