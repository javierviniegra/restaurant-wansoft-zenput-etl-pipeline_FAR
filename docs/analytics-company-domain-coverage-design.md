# analytics_company_domain_coverage Design and Closeout

## Purpose

This document defines and closes the initial implementation of `analytics_company_domain_coverage`, the first analytical coverage table of the unified MySQL analytical layer.

The purpose of this table is to show, for each canonical `company_source_key`, which operational domains currently have data coverage.

This table belongs to the MySQL analytical layer.

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
scripts/build_analytics_company_domain_coverage.py created
scripts/validate_analytics_company_domain_coverage.py created
analytics_company_domain_coverage table created in MySQL
build completed successfully
validation completed successfully
coverage_status values clarified
Zenput tasks mapped through zenput_tasks.account_name
Versalles correctly classified as zenput_activity_only
Puebla correctly classified as future_with_zenput_activity
León, Lindavista and Perisur correctly classified as zenput_only_location
Bodegón and Empanadas correctly classified as internal_provider
Inventory coverage identified as pending because odoo_inventory_snapshot lacks company_source_key
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
python -m scripts.build_analytics_company_domain_coverage
```

## Build Result

Latest validated build result:

```text
ANALYTICS COMPANY DOMAIN COVERAGE BUILD SUMMARY

table: analytics_company_domain_coverage
total_rows_prepared: 24
has_purchases: 17
has_inventory: 0
has_zenput_submissions: 21
has_zenput_tasks: 20

coverage_status_counts:
  future_with_zenput_activity: 1
  internal_provider: 2
  multi_domain: 16
  purchases_only: 1
  zenput_activity_only: 1
  zenput_only_location: 3

BUILD RESULT: COMPLETED
```

---

## Validation Command

```bash
python -m scripts.validate_analytics_company_domain_coverage
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
analytics_company_domain_coverage_exists: PASS
row_count_matches_dim_company_analytical: PASS
company_source_key_unique: PASS
all_dim_companies_represented: PASS
coverage_status_values_valid: PASS
coverage_counts_non_negative: PASS
required_examples_valid: PASS
purchase_flags_consistent: PASS
inventory_flags_consistent: PASS
zenput_flags_consistent: PASS
```

---

# Table Purpose

`analytics_company_domain_coverage` answers these questions:

```text
Which companies have Purchases coverage?
Which companies have Inventory coverage?
Which companies have Zenput submissions coverage?
Which companies have Zenput tasks coverage?
Which companies are Zenput-only locations?
Which companies are future rollouts?
Which companies are internal providers?
Which companies have multi-domain coverage?
Which companies have only one operational domain represented?
```

This table is the first practical analytical layer object built on top of:

```text
dim_company_analytical
```

It provides a domain coverage view for:

```text
Purchases
Inventory
Zenput
future Sales
```

---

# Grain

The grain of the table is:

```text
1 row = 1 company_source_key
```

The table must have the same row count as:

```text
dim_company_analytical
```

Current validated row count:

```text
analytics_company_domain_coverage: 24
dim_company_analytical: 24
```

---

# Source Tables

Current source tables:

```text
dim_company_analytical
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
odoo_inventory_snapshot
zenput.submissions
zenput.zenput_tasks
```

Future source tables may include:

```text
analytics_sales_*
sales canonical tables
future inventory analytical tables with company_source_key
```

---

# Current Field Groups

## Identity Fields

```text
company_source_key
display_name
```

---

## Classification Fields from dim_company_analytical

```text
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
```

---

## Domain Coverage Flags

```text
has_purchases
has_purchase_orders
has_purchase_lines
has_inventory
has_zenput_submissions
has_zenput_tasks
has_sales_future_placeholder
```

---

## Domain Counts

```text
purchase_order_count
purchase_line_count
inventory_snapshot_count
zenput_submission_count
zenput_task_count
```

---

## Coverage Classification

```text
coverage_status
coverage_notes
```

---

# Coverage Status Values

Current valid values:

```text
multi_domain
purchases_only
inventory_only
zenput_only_location
zenput_activity_only
future_with_zenput_activity
future_no_activity
internal_provider
no_domain_activity
pending_review
```

---

## multi_domain

Meaning:

```text
The company has data in two or more currently mapped domains.
```

Current domains considered:

```text
Purchases
Inventory
Zenput submissions/tasks
```

Current result:

```text
multi_domain: 16
```

---

## purchases_only

Meaning:

```text
The company currently has Purchases coverage only.
```

Current result:

```text
purchases_only: 1
```

---

## inventory_only

Meaning:

```text
The company currently has Inventory coverage only.
```

Current result:

```text
inventory_only: 0
```

Reason:

```text
Inventory coverage by company_source_key is not yet available because odoo_inventory_snapshot does not expose a governed company_source_key.
```

---

## zenput_only_location

Meaning:

```text
The company is officially classified as a Zenput-only location.
```

Current expected companies:

```text
León
Lindavista
Perisur
```

Current result:

```text
zenput_only_location: 3
```

Important:

```text
This status means the company is classified as Zenput-only.
It does not simply mean that the company currently only has Zenput activity.
```

---

## zenput_activity_only

Meaning:

```text
The company is not classified as Zenput-only, but currently only has Zenput activity in analytics_company_domain_coverage.
```

Current expected case:

```text
Versalles
```

Business rule:

```text
Versalles is the canonical company_source_key for Taqueria Exhibimex.
Taqueria Exhibimex appears in Zenput as Taqueria Exhibimex.
Versalles / Exhibimex does not currently make purchases operationally.
Purchases are currently handled by Taquería Parroquia.
Versalles may make purchases in the future.
```

Current result:

```text
zenput_activity_only: 1
```

This is correct.

---

## future_with_zenput_activity

Meaning:

```text
The company is a future rollout but already appears in Zenput.
```

Current expected case:

```text
Puebla
```

Business rule:

```text
Puebla appears in Zenput.
Puebla maps to company_source_key = Puebla.
Puebla is not Zenput-only.
Puebla is a future Odoo / operational rollout candidate.
Purchases and Inventory activation remain controlled by COMPANY_SOURCE and rollout expectations.
```

Current result:

```text
future_with_zenput_activity: 1
```

---

## internal_provider

Meaning:

```text
The company is an internal provider, not a final operating branch.
```

Current expected companies:

```text
Bodegón
Empanadas
```

Display names:

```text
Bodegón -> EL BODEGON DE FITO
Empanadas -> LAS EMPANADAS DE MARIA EVA
```

Current result:

```text
internal_provider: 2
```

---

# Domain Coverage Rules

## Purchases Coverage

Purchases coverage is derived from:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
```

Rules:

```text
has_purchase_orders = true when purchase_order_count > 0
has_purchase_lines = true when purchase_line_count > 0
has_purchases = has_purchase_orders OR has_purchase_lines
```

Current result:

```text
has_purchases: 17
```

Validation status:

```text
purchase_flags_consistent: PASS
```

---

## Purchases Orphan Key Check

Manual checks confirmed that Purchases has no `company_source_key` values missing from:

```text
dim_company_analytical
```

Queries used:

```sql
SELECT
    company_source_key,
    COUNT(*) AS purchase_orders
FROM canonica*_purchase_order_snapshot
WHERE com*any_source_key NOT IN (
    SELECT*company_source_key
    FROM dim_co*pany_analytical
)
GROUP BY company*source_key
ORDER BY company_source*key;
```

```sql
SELECT
    compan*_source_key,
    COUNT(*) AS purch*se_lines
FROM canonical_purchase_o*der_line_snapshot
WHERE company_so*rce_key NOT IN (
    SELECT compan*_source_key
    FROM dim_company_a*alytical
)
GROUP BY company_source*key
ORDER BY company_source_key;
`*`

Expected result:

```text
0 row*
```

Observed result:

```text
0 *ows
```

---

## Versalles / Exhib*mex Purchases Check

Manual checks*confirmed that there are currently*no Purchases rows for:

```text
Ve*salles
Taqueria Exhibimex
Taquería*Exhibimex
```

Queries used:

```s*l
SELECT
    company_source_key,
 *  COUNT(*) AS purchase_orders
FROM*canonical_purchase_order_snapshot
*HERE company_source_key IN (
    '*ersalles',
    'Taqueria Exhibimex*,
    'Taquería Exhibimex'
)
GROUP*BY company_source_key
ORDER BY com*any_source_key;
```

```sql
SELECT*    company_source_key,
    COUNT(*) AS purchase_lines
FROM canonical*purchase_order_line_snapshot
WHERE*company_source_key IN (
    'Versa*les',
    'Taqueria Exhibimex',
  * 'Taquería Exhibimex'
)
GROUP BY c*mpany_source_key
ORDER BY company_*ource_key;
```

Observed result:

*``text
0 rows
```

Interpretation:*
```text
Versalles / Exhibimex cur*ently does not have purchases.
Thi* is operationally correct because *urchases are handled by Taquería P*rroquia.
```

---

## Inventory Co*erage

Inventory coverage currentl* reads from:

```text
odoo_invento*y_snapshot
```

Current result:

`*`text
has_inventory: 0
inventory_s*apshot_count: 0
```

This does not*mean Inventory has no data.

It me*ns:

```text
odoo_inventory_snapsh*t does not currently expose a gove*ned company_source_key.
```

Obser*ed columns include:

```text
sourc*_location_id
location_name
```

Ob*erved `location_name` examples are*Odoo logistical locations such as:*
```text
Partners/Vendors
Partners*Customers
Virtual Locations/Inter-*ompany transit
Virtual Locations/I*ventory adjustment
Virtual Locatio*s/Production
```

These are not fi*al analytical branch keys.

Decisi*n:

```text
Do not force an Invent*ry company mapping yet.
Inventory *overage by company_source_key rema*ns pending until a governed rule e*ists.
```

Validation status:

```*ext
inventory_flags_consistent: PA*S
```

---

## Zenput Submissions *overage

Zenput submissions covera*e is derived from:

```text
zenput*submissions.location_name
```

usi*g mapping in:

```text
core/config*zenput.py
```

Current result:

``*text
has_zenput_submissions: 21
``*

Validation status:

```text
zenp*t_flags_consistent: PASS
```

---
*## Zenput Tasks Coverage

Zenput t*sks coverage is derived from:

```*ext
zenput.zenput_tasks.account_na*e
```

This was added after valida*ing that `account_name` contains o*erational names such as:

```text
*onda Argentina Viaducto
Fonda Arge*tina Tepeyac
Taqueria Viaducto
Taq*eria Parroquia
Fonda Argentina Isa*el
Fonda Argentina Acoxpa
Fonda Ar*entina Perisur
Taqueria Exhibimex
*onda Argentina Vallejo
Fonda Argen*ina San Jeronimo
Fonda Argentina N*poles
Fonda Argentina Aeropuerto
F*nda Argentina Antenas
Fonda Argent*na Lindavista
Fonda Argentina Ocea*ia
Fonda Argentina León
Fonda Arge*tina Playa
Fonda Argentina Coyoacá*
Fonda Argentina Cancun
Fonda Arge*tina Tollocan
```

These names mat*h the same operational naming fami*y used by Zenput submissions.

Cur*ent result:

```text
has_zenput_ta*ks: 20
```

Decision:

```text
zen*ut.zenput_tasks.account_name is ac*epted as the current mapping field*for task coverage.
```

Validation*status:

```text
zenput_flags_cons*stent: PASS
```

---

# Current Kn*wn Limitations

## Inventory cover*ge is pending

Current limitation:*
```text
Inventory snapshot data e*ists, but company_source_key is no* available directly in odoo_invent*ry_snapshot.
```

Decision:

```te*t
Do not force mapping from Odoo l*gistical location names.
Resolve I*ventory company coverage later as *art of Inventory analytical design*
```

Possible future options:

``*text
add company_source_key to inv*ntory snapshot upstream
derive com*any_source_key from Odoo warehouse*location if a reliable rule exists*create a warehouse/location analyt*cal dimension
build a separate inv*ntory analytical grain before cove*age aggregation
```

---

## Sales*coverage is deferred

Sales remain* a future analytical domain.

Curr*nt field:

```text
has_sales_futur*_placeholder
```

Current behaviou*:

```text
placeholder only
not im*lemented
```

Decision:

```text
a*alytics_sales_* is deferred to a l*ter section.
```

---

# Current S*ripts

## Build Script

```text
sc*ipts/build_analytics_company_domai*_coverage.py
```

Purpose:

```tex*
Create and refresh analytics_comp*ny_domain_coverage from dim_compan*_analytical and available domain t*bles.
```

Current behaviour:

```*ext
starts from dim_company_analyt*cal
adds purchase counts
adds inve*tory counts when mappable
adds Zen*ut submission counts
adds Zenput task counts using account_name
derives domain coverage flags
derives coverage_status
uses exact rebuild semantics
```

---

## Validation Script

```text
scripts/validate_analytics_company_domain_coverage.py
```

Purpose:

```text
Validate coverage table consistency and expected examples.
```

Current validations:

```text
analytics_company_domain_coverage_exists
row_count_matches_dim_company_analytical
company_source_key_unique
all_dim_companies_represented
coverage_status_values_valid
coverage_counts_non_negative
required_examples_valid
purchase_flags_consistent
inventory_flags_consistent
zenput_flags_consistent
```

---

# Validation Query Examples

## 1. Coverage status summary

```sql
SELECT
    coverage_status,
    COUNT(*) AS total_companies
FROM analytics_company_domain_coverage
GROUP BY coverage_status
ORDER BY coverage_status;
```

Expected current result:

```text
future_with_zenput_activity: 1
internal_provider: 2
multi_domain: 16
purchases_only: 1
zenput_activity_only: 1
zenput_only_location: 3
```

---

## 2. Full company coverage

```sql
SELECT
    company_source_key,
    display_name,
    has_purchases,
    has_inventory,
    has_zenput_submissions,
    has_zenput_tasks,
    purchase_order_count,
    purchase_line_count,
    inventory_snapshot_count,
    zenput_submission_count,
    zenput_task_count,
    coverage_status
FROM analytics_company_domain_coverage
ORDER BY company_source_key;
```

---

## 3. Key examples

```sql
SELECT
    company_source_key,
    is_internal_provider,
    is_zenput_only,
    has_purchases,
    has_inventory,
    has_zenput_submissions,
    has_zenput_tasks,
    coverage_status,
    coverage_notes
FROM analytics_company_domain_coverage
WHERE company_source_key IN (
    'Acoxpa',
    'Antenas',
    'CentroMyJ',
    'Puebla',
    'León',
    'Lindavista',
    'Perisur',
    'Bodegón',
    'Empanadas',
    'Versalles',
    'Taquería parroquia'
)
ORDER BY company_source_key;
```

---

# Relationship to dim_company_analytical

`analytics_company_domain_coverage` depends on:

```text
dim_company_analytical
```

Relationship:

```text
dim_company_analytical.company_source_key
    -> analytics_company_domain_coverage.company_source_key
```

Validation confirms:

```text
all dim_company_analytical rows are represented
row count matches dim_company_analytical
company_source_key is unique
```

Current validated counts:

```text
dim_company_analytical: 24
analytics_company_domain_coverage: 24
```

---

# Refresh Strategy

Current implementation uses exact rebuild semantics:

```text
DELETE FROM analytics_company_domain_coverage
INSERT current coverage rows
```

Reason:

```text
Section 17 is still in initial analytical design.
No downstream analytics facts depend on this table yet.
Exact rebuild prevents stale coverage rows.
```

Future consideration:

```text
Once downstream facts or views depend on this table, evaluate soft-deactivation or transactional rebuild strategy.
```

---

# Step 17.6 Closeout

Step 17.6 is complete when:

```text
[x] build compiles
[x] validation compiles
[x] build completes successfully
[x] validation passes
[x] coverage_status values are semantically separated
[x] Zenput tasks are mapped using account_name
[x] Versalles is correctly interpreted as zenput_activity_only
[x] Puebla is correctly interpreted as future_with_zenput_activity
[x] León, Lindavista and Perisur are correctly interpreted as zenput_only_location
[x] Bodegón and Empanadas are correctly interpreted as internal_provider
[x] Purchases orphan company keys are checked
[x] Inventory limitation is documented
```

---

# Step 17.7 Closeout

This documentation step is complete when:

```text
[x] analytics_company_domain_coverage implementation result documented
[x] real build result documented
[x] real validation result documented
[x] coverage_status meanings documented
[x] Versalles / Exhibimex operating rule documented
[x] Zenput tasks account_name mapping documented
[x] Inventory coverage limitation documented
[x] commit package prepared
```

---

# Recommended Next Step

```text
Paso 17.8 — Validación final de Sección 17 parcial y preparación de commit
```

Recommended commit scope:

```text
docs/unified-analytical-layer-plan.md
docs/dim-company-analytical-design.md
docs/analytics-company-domain-coverage-design.md
scripts/build_dim_company_analytical.py
scripts/validate_dim_company_analytical.py
scripts/build_analytics_company_domain_coverage.py
scripts/validate_analytics_company_domain_coverage.py
```