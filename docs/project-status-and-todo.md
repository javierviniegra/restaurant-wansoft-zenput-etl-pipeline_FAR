# Project Status and TODO

## Purpose

This document explains the current status of the Wansoft + Odoo Data Warehouse and ETL Pipeline project.

It answers three practical questions:

```text
Where are we now?
What has already been completed?
What is still pending?
```

This document should be used as the project checkpoint before continuing with production orchestration, Power BI integration, or additional domain development.

---

## Current Project Phase

The project is currently in the transition point between:

```text
validated domain ETLs
```

and:

```text
production-style orchestration and BI consumption
```

The project is no longer in early discovery.

The following foundations are already in place:

```text
Odoo read-only extraction
Wansoft source integration strategy
MySQL governance layer
inventory dictionary governance
company source governance
purchase canonical layer
technical documentation package
```

The next major project stage is:

```text
controlled orchestration and consumption
```

This means:

```text
turn validated scripts into a repeatable execution flow
define refresh order
define validation gates
prepare Power BI consumption
keep manual governance decisions controlled
```

---

## Current Overall Status

| Area | Status |
|---|---|
| Sales | Functionally established |
| Inventory | Technically stable and functionally advanced |
| Purchases | Canonical layer implemented and validated |
| Wansoft SOAP/WSDL | Local WSDL setup documented |
| Documentation | Main documentation package completed |
| Production orchestration | Pending |
| Power BI semantic layer | Pending |
| Automated monitoring | Pending |
| Controlled governance process | Partially defined, needs operating cadence |

---

## Completed Work

## 1. Repository Architecture

Completed:

```text
core/
analysis/
extract/
scripts/
docs/
sql/
resources/wsdl/
```

The project now has a structured repository layout separating:

```text
database clients
source clients
configuration
analysis scripts
ETL modules
test runners
SQL seeds and maintenance scripts
documentation
WSDL resources
```

---

## 2. Odoo Read-Only Principle

Completed:

```text
Odoo is treated as a read-only source.
ETLs do not update Odoo.
Catalog governance decisions are stored in MySQL.
```

Current rule:

```text
No ETL should write back to Odoo products, inventory, company data, or catalog references.
```

---

## 3. MySQL Governance Layer

Completed:

```text
MySQL stores dictionaries, snapshots, canonical tables, backlogs, lifecycle outputs, and company policies.
```

Main governance objects include:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
odoo_company_migration_policy
odoo_purchase_inventory_mapping_backlog
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

---

## 4. Source Governance

Completed:

```text
core/config/companies.py
COMPANY_SOURCE
Odoo company-source mapping
Wansoft subsidiary-source mapping
internal provider handling
```

Current source rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

Important validated rule:

```text
operational_start_date only applies when COMPANY_SOURCE = 'odoo'
```

---

## 5. Wansoft Subsidiary Mapping

Completed:

```text
WANSOFT_SUBSIDIARY_SOURCE_KEY is derived from CUENTAS_SUCURSALES.
```

Validated examples:

```text
4960 -> Antenas
6175 -> Cancun
5320 -> Acoxpa
6560 -> Tepeyac
5943 -> Oceanía
12806 -> Puebla
```

This avoids maintaining a second manual Wansoft subsidiary mapping.

---

## 6. Internal Provider Handling

Completed:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

are treated as:

```text
internal providers
```

and not as final operating branches.

Rules:

```text
Exclude as company_name.
Keep as vendor_name if the buying company is final-eligible.
```

---

## 7. Inventory Domain

Completed or advanced:

```text
Odoo inventory extraction
inventory scope classification
dictionary lookup
snapshot generation
backlog generation
not_found analysis
bridge report pattern
controlled promotion pattern
inventory lifecycle support
inventory closeout documentation
inventory runbook
```

Current validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Status:

```text
Inventory is technically stable.
Inventory is good enough to support Purchases.
Residual products remain visible and controlled.
```

---

## 8. Purchases Domain

Completed:

```text
Odoo purchase order extraction
Odoo purchase order line extraction
Odoo purchase receipt extraction
Odoo purchase receipt move extraction
purchase product mapping
purchase inventory backlog
company migration policy
company source eligibility report
Odoo canonical purchase load
Wansoft canonical purchase load
canonical purchase tables
```

Current validated Odoo canonical load:

```text
orders_inserted: 282
lines_inserted: 1381
receipts_inserted: 268
receipt_moves_inserted: 1184
```

Current validated Wansoft canonical load:

```text
orders_inserted: 145047
lines_inserted: 745344
receipts_inserted: 145047
receipt_moves_inserted: 745344
```

Current Wansoft status summary:

```text
final_wansoft_enabled        693059
wansoft_history_before_odoo   52285
```

---

## 9. Antenas Source Split

Completed and validated:

```text
Antenas Wansoft history before 2026-06-01
Antenas Odoo final source from 2026-06-01 onward
```

Validated ranges:

```text
Wansoft Antenas max_order_date: 2026-05-31 22:51:54
Odoo Antenas min_order_date: 2026-06-01 16:10:54
```

This confirms:

```text
Wansoft does not invade the Odoo period for Antenas.
Odoo does not replace historical Wansoft purchases.
```

---

## 10. Purchases Product Mapping Policy

Completed:

```text
No automatic aliases
Explicit reference beats name similarity
Odoo products map only through inventory_mapping_dictionary
Wansoft rows are native Wansoft products
Unmapped Odoo products remain in backlog
```

Current validated reference result:

```text
new_product_no_reference = 233 products
has_reference_candidate = 0 products
```

---

## 11. Wansoft Local WSDL

Completed:

```text
resources/wsdl/wansoft.wsdl
core/clients/wansoft_client.py
scripts/test_wansoft_wsdl_client.py
docs/wansoft-local-wsdl.md
```

Current principle:

```text
Do not instantiate Zeep clients directly inside ETL scripts.
Use the central Wansoft client.
```

---

## 12. Documentation Package

Completed or drafted:

```text
README.md
docs/project-technical-guide.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/wansoft-local-wsdl.md
```

New documents added in this phase:

```text
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
```

---

# Current TODO

## Priority 1: Documentation Consistency

Status:

```text
In progress
```

TODO:

```text
[ ] Add docs/project-status-and-todo.md
[ ] Add docs/production-orchestration-plan.md
[ ] Add both files to README.md
[ ] Add both files to docs/project-technical-guide.md
[ ] Confirm all docs are listed consistently
[ ] Commit documentation package
```

---

## Priority 2: Production Orchestration Planning

Status:

```text
Pending
```

TODO:

```text
[ ] Define official execution order
[ ] Separate daily refresh tasks from controlled governance tasks
[ ] Define validation gates after each domain
[ ] Define what should stop the pipeline
[ ] Define what should only generate warnings
[ ] Define logging strategy
[ ] Define run output tables or audit tables
[ ] Define operator checklist
[ ] Define rollback or reload strategy by source_system
```

Related document:

```text
docs/production-orchestration-plan.md
```

---

## Priority 3: Purchases Refresh Orchestration

Status:

```text
Pending
```

TODO:

```text
[ ] Decide if Odoo purchases canonical refresh runs daily
[ ] Decide if Wansoft canonical purchases refresh runs daily
[ ] Decide refresh sequence:
    1. Odoo snapshots
    2. Odoo receipts
    3. Purchase backlog
    4. Odoo canonical
    5. Wansoft mapping report
    6. Wansoft canonical
    7. SQL validation
[ ] Create one orchestration script for purchases
[ ] Add safety checks before deleting source_system rows
[ ] Add run summary output
[ ] Add failed-run diagnostics
```

---

## Priority 4: Inventory Source Governance Alignment

Status:

```text
Pending
```

TODO:

```text
[ ] Review how Inventory should apply COMPANY_SOURCE
[ ] Confirm whether Odoo inventory should be canonical only for Odoo-source companies
[ ] Define Wansoft inventory canonical future layer if required
[ ] Avoid mixing Odoo inventory with Wansoft-source companies in final facts
[ ] Document final Inventory canonical policy
```

---

## Priority 5: Power BI Integration Layer

Status:

```text
Pending
```

TODO:

```text
[ ] Define BI-facing tables
[ ] Define whether Power BI consumes canonical_purchase_* directly
[ ] Define canonical inventory tables if needed
[ ] Define relationships:
    company
    product
    date
    vendor
    source_system
[ ] Define measures:
    purchase amount
    received quantity
    mapped/unmapped products
    source split
    provider purchases
[ ] Define validation dashboard
[ ] Define refresh dependencies
```

---

## Priority 6: Monitoring and Data Quality

Status:

```text
Pending
```

TODO:

```text
[ ] Create ETL run log table
[ ] Store ETL start/end timestamps
[ ] Store row counts by table
[ ] Store source_system counts
[ ] Store validation status
[ ] Store error messages
[ ] Add duplicate-key diagnostics
[ ] Add unmapped product summary
[ ] Add source governance exceptions
```

Possible future table:

```text
etl_run_log
```

Possible future table:

```text
etl_validation_result
```

---

## Priority 7: Catalog Governance Process

Status:

```text
Partially defined
```

TODO:

```text
[ ] Define review owner for product backlog
[ ] Define approval process for dictionary promotion
[ ] Define frequency of backlog review
[ ] Define criteria for high-priority unresolved products
[ ] Define when a product remains permanently in backlog
[ ] Define when a product becomes operational_non_inventory
[ ] Define when a product becomes historical_only
```

---

## Priority 8: Operational Odoo Issues Outside ETL

Status:

```text
Ongoing operational follow-up
```

TODO:

```text
[ ] Continue monitoring inventory valuation differences
[ ] Continue reviewing orders that fail because of stock issues
[ ] Continue reviewing receipts with mismatched quantities
[ ] Continue reviewing manual payment or reconciliation errors
[ ] Keep these issues separate from ETL mapping logic
```

Important note:

```text
These are operational Odoo process issues.
They should not be solved by writing directly to Odoo from the ETL.
```

---

## Priority 9: Sales Domain Future Work

Status:

```text
Stable but not final
```

TODO:

```text
[ ] Review if sales dictionary needs final documentation
[ ] Define sales canonical strategy if needed
[ ] Keep Sales as Wansoft source of truth
[ ] Monitor Wansoft to Odoo order-processing issues separately
[ ] Document sales integration assumptions
```

---

## Priority 10: Final Production Readiness

Status:

```text
Not started
```

TODO:

```text
[ ] Define production schedule
[ ] Define responsible operator
[ ] Define notification process
[ ] Define failure response process
[ ] Define database backup expectations
[ ] Define release checklist
[ ] Define branch/tag/versioning strategy
[ ] Define dependency on Odoo operational readiness
```

---

# What Should Not Be Automated Yet

The following should remain controlled:

```text
dictionary promotions
scope rule changes
product equivalence decisions
COMPANY_SOURCE changes
company migration policy changes
historical-only decisions
Odoo catalog cleanup
manual correction of Odoo inventory movements
accounting reconciliation adjustments
```

---

# Suggested Next Work Sequence

Recommended next sequence:

```text
1. Commit documentation package
2. Create purchases orchestration script
3. Add ETL run logging
4. Add purchases validation summary script
5. Define Power BI consumption layer
6. Review Inventory canonical/source-governance alignment
7. Define production runbook
```

---

# Current Decision Point

The project is ready to move from:

```text
validated scripts
```

to:

```text
controlled orchestration
```

The next technical decision is whether to prioritise:

```text
production orchestration
```

or:

```text
Power BI semantic modelling
```

Recommended priority:

```text
production orchestration first
Power BI modelling second
```

Reason:

```text
Power BI should consume stable, repeatable, validated outputs.
```

---

# Related Documentation

```text
README.md
docs/project-technical-guide.md
docs/production-orchestration-plan.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/wansoft-local-wsdl.md
```

---

# Recommended Commit

```bash
git add README.md docs/

git commit -m "docs(project): add project status and todo documentation"

git push
```