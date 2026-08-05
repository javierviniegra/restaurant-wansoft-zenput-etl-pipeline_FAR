# Unified Analytical Layer Plan

## Purpose

This document defines the design plan for the unified analytical layer of the Wansoft + Odoo + Zenput Data Warehouse and ETL Pipeline project.

The purpose is to define how validated operational data from multiple systems and domains should be exposed inside MySQL for stable analytical consumption.

This document focuses only on the MySQL analytical layer.

It does not design:

```text
Power BI
Power BI semantic models
Power BI relationships
Power BI DAX measures
Power BI visuals
dashboards
reports
Excel models
presentation layers
```

Those layers belong to a separate project.

The core rule for this project is:

```text
Reporting does not resolve business rules.
All business rules must be governed in MySQL before reporting consumes the data.
```

---

## Project Scope

The primary scope of this project is to build a unified MySQL analytical layer that combines operational data from:

```text
Wansoft
Odoo
Zenput
future operational sources
```

The analytical layer must hide source-system complexity from downstream consumers.

Consumers should not need to know:

```text
which branch still uses Wansoft
which branch migrated from Wansoft to Odoo
which branch started directly in Odoo
which branch appears only in Zenput
which data is historical
which data is current
which source system produced each record
which raw or canonical table stores the original source data
```

The unified analytical layer must provide clean, governed, validated, and auditable MySQL outputs.

---

## Explicit Non-Scope

This document does not cover:

```text
Power BI model design
Power BI relationships
DAX measures
dashboard design
visual design
report pages
Power BI refresh configuration
Excel pivot design
presentation layer rules
user interface design
```

Power BI, Excel, SQL notebooks, dashboards, APIs, and other tools may consume the MySQL analytical layer later.

However, they are not part of Section 17.

Section 17 only designs:

```text
MySQL dimensions
MySQL analytical tables
MySQL analytical views
refresh order
validation rules
internal vs public data contracts
naming conventions
performance expectations
```

---

## Core Principle

The central principle is:

```text
Every business rule must be resolved before data reaches reporting.
```

This means:

```text
branch mapping is resolved in MySQL/config
source-system selection is resolved in MySQL/config
migration timing is resolved in MySQL
product equivalence is resolved in MySQL
vendor classification is resolved in MySQL
Zenput location mapping is resolved in MySQL/config
internal provider treatment is resolved in MySQL
```

Reporting tools should consume governed analytical outputs, not raw operational complexity.

---

## Current Inputs Available

The project currently has validated or controlled inputs from:

```text
Purchases
Inventory
Zenput
```

Sales remains strategically important, but the initial unified analytical layer should not include `analytics_sales_*` unless explicitly scoped in a later section.

Current decision:

```text
Sales is recognised as a future analytical domain.
Sales coverage can be documented conceptually.
analytics_sales_* tables are deferred to a later section.
```

Reason:

```text
Purchases, Inventory and Zenput have recent validated pipelines or controlled wrappers.
Sales deserves its own analytical design because Wansoft remains the source of truth and sales analytics will require its own grain, product logic, date logic and validation rules.
```

---

# Section 17 Goal

The goal of Section 17 is to design the first version of the MySQL analytical layer.

This includes:

```text
shared dimensions
domain-level analytical tables
domain coverage table
refresh order
validation rules
contract of consumption
naming conventions
performance expectations
```

The first version should be practical, auditable, and incremental.

It should not attempt to solve every future analytical requirement.

---

# Analytical Layer Naming Convention

The analytical layer should use consistent naming:

```text
dim_*          shared dimensions
analytics_*    analytical tables or materialized outputs
vw_*           semantic or business-facing views
```

Recommended meaning:

```text
dim_*:
    reusable descriptive dimensions

analytics_*:
    stable physical analytical tables inside MySQL

vw_*:
    views that expose business-friendly subsets or cleaned consumption views
```

Internal technical tables should keep their existing names and should not be exposed as normal consumption objects.

---

# Public vs Internal Contract

## Public Analytical Objects

The following object patterns may be consumed by downstream tools:

```text
dim_*
analytics_*
vw_*
```

Examples:

```text
dim_company_analytical
dim_time
dim_product
dim_vendor

analytics_company_domain_coverage
analytics_purchase_orders
analytics_purchase_order_lines
analytics_inventory_snapshot
analytics_zenput_submissions
analytics_zenput_tasks

vw_business_company_domain_coverage
vw_business_purchase_order_lines
vw_business_inventory_snapshot
vw_business_zenput_activity
```

---

## Internal Objects

These objects are internal and should not be consumed directly by downstream reporting tools:

```text
raw source tables
legacy tables
technical snapshots
canonical staging details
backlogs
bridge tables
validation-only outputs
pipeline logs
temporary diagnostic tables
```

Examples:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
odoo_inventory_snapshot
odoo_inventory_backlog

canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot

form_templates
submissions
submission_answers
zenput_tasks

inventory_mapping_dictionary
odoo_purchase_inventory_mapping_backlog
logs/*
```

Important:

```text
Canonical tables may be used as internal upstream sources for analytics_* tables.
They should not be the default public contract for reporting.
```

---

# Shared Dimensions

The unified analytical layer must not only define a branch dimension.

It should define shared dimensions that can be reused across Purchases, Inventory, Zenput, and future Sales.

Initial shared dimensions:

```text
dim_company_analytical
dim_time
dim_product
dim_vendor
```

---

# dim_company_analytical

## Purpose

`dim_company_analytical` provides one governed row per analytical company, branch, internal provider, or operational location that needs to be understood consistently across domains.

It is the central company dimension for analytical consumption.

---

## Granularity

```text
1 row = 1 company_source_key
```

---

## Candidate Fields

```text
company_source_key
display_name
normalized_name
brand_group
is_active_branch
is_internal_provider
is_wansoft_company
is_odoo_company
is_zenput_location
is_zenput_only
purchases_source_system
inventory_source_system
sales_source_system
zenput_source_status
rollout_type
rollout_status
operational_start_date
is_future_rollout
notes
created_at
updated_at
```

---

## Example Rows

```text
Antenas:
    purchases_source_system = odoo
    inventory_source_system = odoo
    sales_source_system = wansoft
    zenput_source_status = mapped
    rollout_type = migrated_from_wansoft
    operational_start_date = configured in migration policy

La Esquina Coyoacán:
    purchases_source_system = odoo
    inventory_source_system = odoo
    sales_source_system = wansoft
    zenput_source_status = mapped
    rollout_type = migrated_from_wansoft
    operational_start_date = configured in migration policy

CentroMyJ:
    purchases_source_system = odoo
    inventory_source_system = odoo
    sales_source_system = pending
    zenput_source_status = pending_or_not_detected
    rollout_type = new_odoo_branch

León:
    purchases_source_system = none
    inventory_source_system = none
    sales_source_system = none
    zenput_source_status = zenput_only
    is_zenput_only = true

Lindavista:
    purchases_source_system = none
    inventory_source_system = none
    sales_source_system = none
    zenput_source_status = zenput_only
    is_zenput_only = true

Perisur:
    purchases_source_system = none
    inventory_source_system = none
    sales_source_system = none
    zenput_source_status = zenput_only
    is_zenput_only = true

Puebla:
    purchases_source_system = pending
    inventory_source_system = pending
    sales_source_system = pending
    zenput_source_status = mapped
    rollout_type = new_odoo_branch
    rollout_status = future
```

---

## Key Rules

```text
company_source_key is the main analytical company key.
Zenput location_name values must map to company_source_key before reaching analytics tables.
Puebla is not Zenput-only.
León, Lindavista and Perisur are Zenput-only for now, but future-capable.
Bodegón and Empanadas are internal providers, not final operating branches.
```

---

# dim_time

## Purpose

`dim_time` provides a reusable calendar dimension for all analytical tables.

This avoids inconsistent date logic across analytical outputs.

---

## Granularity

```text
1 row = 1 calendar date
```

---

## Candidate Fields

```text
date_key
calendar_date
year
quarter
month_number
month_name
year_month
day_of_month
day_of_week_number
day_of_week_name
is_weekend
is_month_start
is_month_end
is_quarter_start
is_quarter_end
is_year_start
is_year_end
created_at
updated_at
```

---

## Required Use

All analytics tables with dates should be able to join to:

```text
dim_time.calendar_date
```

or:

```text
dim_time.date_key
```

The exact key should be standardised during implementation.

---

## Candidate Sources

```text
generated calendar table
min / max date ranges from Purchases
min / max date ranges from Inventory
min / max date ranges from Zenput
future Sales date ranges
```

---

## Design Rule

```text
dim_time should cover more dates than the current data range.
```

This prevents refresh failures when future dates appear.

---

# dim_product

## Purpose

`dim_product` provides one unified analytical product row where possible.

It should support products that exist in:

```text
Wansoft
Odoo
both systems
future systems
```

---

## Granularity

Recommended target:

```text
1 row = 1 governed analytical product identity
```

This does not necessarily mean one row per raw source product.

---

## Candidate Fields

```text
product_analytical_key
company_scope
product_display_name
normalized_product_name
wansoft_code
wansoft_product_name
wansoft_department
odoo_product_id
odoo_product_name
odoo_default_code
mapping_status
mapping_source
is_mapped
is_unmapped
is_active
created_at
updated_at
```

---

## Source Inputs

Potential inputs:

```text
inventory_mapping_dictionary
canonical_purchase_order_line_snapshot
odoo_inventory_snapshot
odoo_purchase_order_line_snapshot
wansoft purchase product fields
future sales dictionary
```

---

## Key Rules

```text
Explicit reference beats name similarity.
Do not create automatic product aliases.
If a product lacks explicit mapping, keep it unmapped or backlog-visible.
Reporting tools must not resolve product equivalence.
```

---

## Open Design Question

The implementation must decide whether `dim_product` should be:

```text
global across all companies
```

or:

```text
scope-aware by company/domain
```

Recommendation:

```text
Start scope-aware where inventory mapping already implies scope.
Avoid forcing a single global product identity too early.
```

---

# dim_vendor

## Purpose

`dim_vendor` provides a governed vendor dimension for Purchases and future analytical domains.

It must identify internal vendors.

---

## Granularity

```text
1 row = 1 analytical vendor identity
```

---

## Candidate Fields

```text
vendor_analytical_key
vendor_name
normalized_vendor_name
vendor_rfc
vendor_source_system
wansoft_vendor_id
odoo_vendor_id
is_internal_vendor
is_active
created_at
updated_at
```

---

## Internal Vendor Rule

Current internal providers:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

These should be marked as:

```text
is_internal_vendor = true
```

---

## Analytical Rule

Internal vendors should be:

```text
preserved in internal analytical facts
excluded by default from business-facing views
available for technical or intercompany analysis
```

This means they should not disappear from the data.

Instead, they should be flagged and filtered intentionally.

---

# Temporal Rule for Migrated Branches

Simple flags like:

```text
is_odoo_company
is_wansoft_company
```

are not enough.

Migrated branches require a temporal rule.

The key field is:

```text
operational_start_date
```

The central rule is:

```text
Use Wansoft before operational_start_date.
Use Odoo from operational_start_date onward.
```

This prevents:

```text
gaps
duplicates
double counting
incorrect source ownership
```

Confirmed examples:

```text
Antenas
La Esquina Coyoacán
```

This rule must be reflected in:

```text
dim_company_analytical
analytics_purchase_*
future analytics_inventory_* if source transitions require it
validation logic
```

---

## Temporal Validation Requirements

For migrated branches:

```text
No Wansoft final rows on or after operational_start_date.
No Odoo final rows before operational_start_date unless explicitly allowed.
No unassigned date gaps around operational_start_date.
No overlapping Wansoft/Odoo final rows for the same company and date grain.
```

Validation examples:

```text
Antenas:
    Wansoft before operational_start_date
    Odoo from operational_start_date onward

La Esquina Coyoacán:
    Wansoft before operational_start_date
    Odoo from operational_start_date onward
```

---

# Sales Domain Decision

Sales is strategically important.

However, for Section 17, Sales should not be implemented as `analytics_sales_*` yet.

Decision:

```text
Sales is recognised as a future analytical domain.
Sales coverage can be documented conceptually.
analytics_sales_* tables are deferred to a later section.
```

Reason:

```text
Purchases, Inventory and Zenput already have current validated pipelines or controlled wrappers.
Sales deserves its own dedicated design because Wansoft remains the source of truth and sales analytics will require its own grain, product logic, date logic and validation rules.
```

Therefore, Section 17 should focus initial implementation design on:

```text
Purchases
Inventory
Zenput
shared dimensions
domain coverage
```

---

# Analytical Tables and Views

The initial analytical layer may include:

```text
analytics_company_domain_coverage
analytics_purchase_orders
analytics_purchase_order_lines
analytics_inventory_snapshot
analytics_zenput_submissions
analytics_zenput_tasks
```

Optional future views:

```text
vw_business_company_domain_coverage
vw_business_purchase_order_lines
vw_business_inventory_snapshot
vw_business_zenput_activity
```

---

# analytics_company_domain_coverage

## Purpose

Show which companies or branches have data coverage by domain.

This table provides a project-level control view.

---

## Granularity

```text
1 row = 1 company_source_key
```

---

## Candidate Fields

```text
company_source_key
has_purchases
has_inventory
has_zenput_submissions
has_zenput_tasks
has_sales_future_placeholder
purchase_order_count
purchase_line_count
inventory_snapshot_count
zenput_submission_count
zenput_task_count
purchases_source_status
inventory_source_status
zenput_source_status
sales_source_status
is_zenput_only
is_internal_provider
rollout_status
updated_at
```

---

## Example Interpretation

```text
Acoxpa:
    has_purchases = true
    has_inventory = true
    has_zenput_submissions = true

León:
    has_purchases = false
    has_inventory = false
    has_zenput_submissions = true
    is_zenput_only = true

Puebla:
    has_purchases = pending_or_false
    has_inventory = pending_or_false
    has_zenput_submissions = true
    rollout_status = future
```

---

## Main Use

```text
governance dashboard inside MySQL
data coverage review
branch readiness review
rollout review
source completeness checks
```

---

# analytics_purchase_orders

## Purpose

Expose purchase order level analytical data.

---

## Granularity

```text
1 row = 1 purchase order
```

---

## Candidate Sources

```text
canonical_purchase_order_snapshot
dim_company_analytical
dim_time
dim_vendor
```

---

## Candidate Fields

```text
purchase_order_key
company_source_key
vendor_analytical_key
order_date
order_date_key
purchase_order_name
purchase_order_status
total_amount
final_purchase_source_status
internal_vendor_flag
source_system_internal
created_at
updated_at
```

---

## source_system Rule

`source_system` should be preserved internally for traceability.

Business-facing views may hide it.

Technical analytical tables may retain it if needed for debugging.

---

# analytics_purchase_order_lines

## Purpose

Expose purchase line level analytical data.

---

## Granularity

```text
1 row = 1 purchase order line
```

This is the correct grain for product-level purchase analysis.

---

## Candidate Sources

```text
canonical_purchase_order_line_snapshot
canonical_purchase_order_snapshot
dim_company_analytical
dim_time
dim_product
dim_vendor
```

---

## Candidate Fields

```text
purchase_order_line_key
purchase_order_key
company_source_key
product_analytical_key
vendor_analytical_key
order_date
order_date_key
quantity
unit_cost
line_amount
wansoft_code
odoo_product_id
mapping_status
final_purchase_source_status
internal_vendor_flag
source_system_internal
created_at
updated_at
```

---

## Key Rule

Do not aggregate purchase lines before the analytical line table.

Aggregation should happen in:

```text
daily aggregate tables
monthly aggregate tables
consumer views
```

not in the base line table.

---

# analytics_inventory_snapshot

## Purpose

Expose governed inventory snapshot data.

---

## Granularity

Recommended:

```text
1 row = 1 company_source_key / product_analytical_key / snapshot_date
```

If the source snapshot has more granular location or warehouse detail, the design must explicitly preserve or aggregate that grain.

---

## Candidate Sources

```text
odoo_inventory_snapshot
inventory_mapping_dictionary
dim_company_analytical
dim_time
dim_product
```

---

## Candidate Fields

```text
company_source_key
product_analytical_key
snapshot_date
snapshot_date_key
quantity_on_hand
inventory_value
mapping_status
scope_bucket
is_unmapped
created_at
updated_at
```

---

## Important Rule

The exact grain must be validated before implementation.

If the snapshot has multiple rows per company/product/date due to warehouse or location, the design must decide whether to:

```text
preserve warehouse granularity
aggregate to company/product/date
create a separate warehouse dimension
```

No implicit aggregation should be done without documenting it.

---

# analytics_zenput_submissions

## Purpose

Expose Zenput form submission activity at submission level.

---

## Granularity

```text
1 row = 1 Zenput submission
```

---

## Candidate Sources

```text
submissions
form_templates
core/config/zenput.py mapping
dim_company_analytical
dim_time
```

---

## Candidate Fields

```text
submission_id
form_template_id
form_template_name
company_source_key
location_name
submitted_at
submitted_date_key
submitted_by
submission_status
is_zenput_only
created_at
updated_at
```

---

## Key Rule

Raw `location_name` should be preserved for traceability.

But analytical joins should use:

```text
company_source_key
```

---

# analytics_zenput_tasks

## Purpose

Expose Zenput task activity at task level.

---

## Granularity

```text
1 row = 1 Zenput task
```

---

## Candidate Sources

```text
zenput_tasks
core/config/zenput.py mapping if location fields are available
dim_company_analytical
dim_time
```

---

## Candidate Fields

```text
task_id
company_source_key
location_name
task_title
task_status
created_at_source
last_updated
completed_at
due_date
task_date_key
is_completed
is_overdue
is_zenput_only
created_at
updated_at
```

---

## Current Caveat

`last_run_timestamp.txt` did not change after the first controlled real execution.

This is not blocking for analytical design, but timestamp behaviour should be reviewed before production scheduling.

---

# source_system Rule

The project should preserve `source_system` internally.

Internal analytical or diagnostic tables may include:

```text
source_system
source_domain
source_table
source_record_id
```

However, final business-facing views should not require users to reason about `source_system`.

Rule:

```text
Keep source_system for debugging and auditability.
Hide or simplify source_system in final business-facing views.
```

Examples:

```text
analytics_purchase_order_lines:
    may include source_system_internal for traceability

vw_business_purchase_order_lines:
    may hide source_system_internal and expose business-ready fields only
```

---

# Internal Provider Rule

Bodegón and Empanadas should be treated carefully.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Rules:

```text
Mark them in dim_vendor using is_internal_vendor.
Preserve them in analytical facts for traceability.
Exclude them by default in business-facing views.
Do not treat them as final operating branches.
```

This prevents internal provider activity from contaminating branch-level business views while preserving auditability.

---

# Refresh Strategy

The analytical layer should refresh only after upstream pipelines and validations succeed.

Recommended order:

```text
1. Run source/domain pipelines.
2. Run required canonical and output validators.
3. Refresh shared dimensions.
4. Refresh analytics_* tables.
5. Run analytics validation.
6. Refresh vw_* views if materialized or dependent.
7. Release analytical outputs for downstream consumption.
```

Initial domain dependency order:

```text
Purchases pipeline and validation
Inventory pipeline and validation
Zenput validation-only or controlled execution result
Shared dimensions
Analytics tables
Analytics validation
```

Important:

```text
analytics_* should not refresh from failed upstream outputs.
```

---

# Refresh Eligibility Rules

## Purchases

Analytics refresh can proceed when:

```text
scripts.run_purchases_pipeline completed successfully
scripts.validate_purchases_canonical_layer passed
```

---

## Inventory

Analytics refresh can proceed when:

```text
scripts.run_inventory_pipeline completed successfully
scripts.validate_inventory_outputs passed
```

---

## Zenput

Analytics refresh can proceed when:

```text
scripts.validate_zenput_location_mapping passed
scripts.validate_zenput_outputs passed
```

or:

```text
scripts.run_zenput_pipeline --execute --validation-only completed successfully
```

If full legacy execution is run:

```text
analytics refresh should only proceed if final Zenput output validation passes.
```

---

# Validation Requirements

The unified analytical layer must include its own validations.

---

## Required Validations

```text
analytics totals vs canonical/source outputs
foreign key orphan checks
company coverage checks
date coverage checks
temporal migration gap checks
temporal migration duplicate checks
internal provider exclusion checks
Zenput location mapping checks
grain duplication checks
```

---

## Tolerance Rules

For numeric reconciliation:

```text
analytics vs canonical difference should be less than 0.01%
```

This applies to metrics such as:

```text
purchase amount
line count
quantity totals where appropriate
```

The exact tolerance should be documented per metric.

---

## Foreign Key Validation

Expected:

```text
orphan company keys = 0
orphan date keys = 0
orphan product keys = 0 where product is required
orphan vendor keys = 0 where vendor is required
```

---

## Temporal Migration Validation

For migrated branches:

```text
No gaps around operational_start_date.
No duplicate final-source records across Wansoft and Odoo for the same company/date grain.
Wansoft appears before operational_start_date.
Odoo appears from operational_start_date onward.
```

Confirmed branches requiring this logic:

```text
Antenas
La Esquina Coyoacán
```

Future branches:

```text
any branch activated as migrated_from_wansoft
```

---

# Performance Requirements

The analytical layer should be designed for query stability.

Recommended indexes:

```text
company_source_key
date_key
calendar_date
product_analytical_key
vendor_analytical_key
purchase_order_key
submission_id
task_id
```

Recommended composite indexes:

```text
company_source_key, date_key
company_source_key, product_analytical_key
company_source_key, vendor_analytical_key
product_analytical_key, date_key
vendor_analytical_key, date_key
```

Recommended aggregate tables or views:

```text
daily purchases by company/product
monthly purchases by company/product
daily inventory by company/product
monthly inventory snapshots if required
daily Zenput submissions by company/form
monthly Zenput activity by company
```

These aggregates are for MySQL analytical performance.

They are not Power BI design.

---

# Table Design Template

Each analytical table should have a ficha before implementation.

Template:

```text
Table name:
Purpose:
Grain:
Public or internal:
Source tables:
Shared dimensions used:
Primary key:
Foreign keys:
Date field:
Refresh method:
Validation rules:
Expected consumers:
Example query:
```

---

## Example: analytics_company_domain_coverage

```text
Table name:
    analytics_company_domain_coverage

Purpose:
    Show domain coverage by company_source_key.

Grain:
    1 row = 1 company_source_key

Public or internal:
    public analytical table

Source tables:
    dim_company_analytical
    canonical_purchase_order_snapshot
    odoo_inventory_snapshot
    submissions
    zenput_tasks

Shared dimensions used:
    dim_company_analytical

Primary key:
    company_source_key

Validation rules:
    one row per company_source_key
    no duplicate company_source_key
    all Zenput mapped companies included
    all purchase companies included
    all inventory companies included

Example query:
```

```sql
SELECT
    company_source_key,
    has_purchases,
    has_inventory,
    has_zenput_submissions,
    zenput_source_status,
    rollout_status
FROM analytics_company_domain_coverage
ORDER BY company_source_key;
```

---

# Implementation Order

Recommended implementation order:

```text
1. docs/unified-analytical-layer-plan.md
2. Design dim_company_analytical
3. Design dim_time
4. Design dim_product
5. Design dim_vendor
6. Design analytics_company_domain_coverage
7. Design analytics_purchase_order_lines
8. Design analytics_inventory_snapshot
9. Design analytics_zenput_submissions
10. Design analytics_zenput_tasks
11. Create analytics validation script
12. Add orchestration plan for analytics refresh
```

---

# Future Scripts

Possible future scripts:

```text
scripts/build_dim_company_analytical.py
scripts/build_dim_time.py
scripts/build_dim_product.py
scripts/build_dim_vendor.py
scripts/build_analytics_company_domain_coverage.py
scripts/build_analytics_purchase_order_lines.py
scripts/build_analytics_inventory_snapshot.py
scripts/build_analytics_zenput_submissions.py
scripts/build_analytics_zenput_tasks.py
scripts/validate_unified_analytical_layer.py
scripts/run_analytics_pipeline.py
scripts/test_run_analytics_pipeline.py
```

---

# Future Documentation

Possible future documentation:

```text
docs/unified-analytical-layer-plan.md
docs/unified-analytical-layer-runbook.md
docs/analytics-table-catalog.md
docs/analytics-validation-policy.md
```

---

# Current Decision

Section 17 starts with planning, not SQL.

Current decision:

```text
Do not write SQL or Python before the analytical layer plan is documented.
```

The next implementation step after this plan should be:

```text
Design dim_company_analytical
```

This dimension should anchor all domain coverage and source governance decisions.

---

# Section 17 Current Status

Current status:

```text
Step 17.1 - Unified analytical layer plan created
```

Current next recommended step:

```text
Step 17.2 - Design dim_company_analytical
```

This should include:

```text
field list
source inputs
business rules
expected rows
validation queries
implementation approach
```

---

# Related Documentation

```text
README.md
docs/project-status-and-todo.md
docs/project-technical-guide.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/zenput-legacy-assessment.md
docs/zenput-runbook.md
docs/purchases-canonical-layer.md
docs/purchases-company-migration-policy.md
docs/inventory-runbook.md
docs/branch-rollout-playbook.md
```