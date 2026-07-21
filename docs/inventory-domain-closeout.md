# Inventory Domain Closeout

## Purpose

This document closes the current technical phase of the Inventory domain.

It explains what has been implemented, what has been validated, what remains intentionally controlled, and how the Inventory domain supports the rest of the data warehouse project.

This document is not an operational runbook.

For day-to-day execution, validation, and troubleshooting, use:

```text
docs/inventory-runbook.md
```

For the full project architecture, use:

```text
docs/project-technical-guide.md
```

---

## Executive Summary

The Inventory domain is considered technically stable and functionally advanced.

The domain now supports:

```text
Odoo inventory extraction
scope-aware inventory classification
dictionary-based product mapping
inventory snapshot generation
inventory backlog generation
not_found analysis
bridge report preparation
controlled dictionary promotion
inventory lifecycle analysis
```

The current Inventory baseline is good enough to support downstream domains such as Purchases.

Current validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Interpretation:

```text
The inventory ETL is stable.
The majority of relevant inventory items are governed.
Residual unresolved products remain visible.
Further improvements should continue through controlled review, not automatic matching.
```

---

## Domain Principles

The Inventory domain follows these principles:

```text
Odoo is read-only.
MySQL is the governance layer.
Scope must be resolved before mapping.
Dictionary lookup must be controlled.
Unresolved products must remain visible.
Dictionary promotion must be reviewed.
Sales remain Wansoft.
Inventory follows COMPANY_SOURCE.
```

The ETL must not update Odoo products, stock quantities, categories, references, locations, or mappings.

All governance outputs are stored in MySQL.

---

## Source Governance

Inventory source governance is defined in:

```text
core/config/companies.py
```

Main source rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

This means:

```text
Sales does not switch to Odoo.
Inventory can use Odoo or Wansoft depending on COMPANY_SOURCE.
Purchases can use Odoo or Wansoft depending on COMPANY_SOURCE.
```

Important rule:

```text
COMPANY_SOURCE is authoritative.
operational_start_date only applies when COMPANY_SOURCE = 'odoo'.
```

This is now shared across Purchases and Inventory.

---

## Current Scope of This Closeout

This closeout covers the Inventory domain work related to:

```text
Odoo inventory extraction
inventory product scope classification
inventory dictionary lookup
snapshot generation
backlog generation
not_found analysis
bridge reports
dictionary promotion flow
inventory lifecycle support
documentation handoff
```

It does not close future production orchestration, Power BI final modelling, or accounting reconciliation.

---

## Main Inventory Tables

The Inventory domain currently depends on these core tables:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

Supporting or bridge tables may include:

```text
inventory_not_found_priority_backlog
inventory_not_found_p1_bridge
inventory_not_found_p2_bridge
inventory_not_found_residual_bridge
inventory_bridge_report
```

The exact bridge tables may evolve, but the controlled promotion pattern remains the same.

---

## Inventory Mapping Dictionary

The authoritative product mapping table is:

```text
inventory_mapping_dictionary
```

This table stores approved mapping relationships between Odoo products and Wansoft product references.

Expected relationship:

```text
Odoo product
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

The dictionary is not automatically generated from fuzzy or name-similarity logic.

Approved mappings must be controlled and auditable.

---

## Odoo Inventory Scope Classification

Odoo inventory products are classified before mapping.

Classification output is stored in:

```text
odoo_inventory_scope_classification
```

The scope model prevents unrelated product universes from being mapped as if they were the same.

Final refined scope buckets:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

---

## Scope Definitions

### restaurantes

Products associated with the public-sale or restaurant sales-reference universe.

These products should not be blindly mapped as standard purchase/inventory items.

### bodegon

Products strongly associated with Bodegón operational flows.

### empanadas

Products strongly associated with Empanadas operational flows.

### shared_cross_company

Products used across operating companies and eligible for main inventory dictionary lookup.

This is currently the primary dictionary-eligible universe.

### review_scope

Products that require manual review before being assigned to a final operational scope.

### operational_non_inventory

Products that may exist operationally but should not be treated as core inventory mapping candidates.

---

## Current Inclusion Logic

Dictionary lookup is currently applied primarily to:

```text
shared_cross_company
```

Other scope buckets are routed to backlog or review handling.

Examples:

```text
scope_restaurantes_sales_reference
scope_bodegon
scope_bodegon_candidate
scope_empanadas
scope_empanadas_candidate
scope_review_scope
scope_operational_non_inventory
```

This prevents sales-reference products, provider-specific products, or operational non-inventory products from polluting the main inventory dictionary.

---

## Snapshot Output

The main inventory snapshot is:

```text
odoo_inventory_snapshot
```

The snapshot represents governed Odoo inventory after:

```text
extraction
consolidation
scope classification
dictionary lookup
mapping enrichment
```

The snapshot is intended to support analysis and downstream domain work.

It should not be treated as a writeback mechanism to Odoo.

---

## Backlog Output

The main inventory backlog is:

```text
odoo_inventory_backlog
```

The backlog captures products that are excluded, unresolved, or pending review.

Backlog categories may include:

```text
scope backlog
functional backlog
not_found
pending_review
historical_only
operational_non_inventory
```

The backlog is intentional.

It exists to keep unresolved products visible instead of hiding or forcing incorrect mappings.

---

## Current Baseline Results

Current validated Inventory closeout baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Interpretation:

```text
Inventory ETL is technically stable.
Dictionary governance is functioning.
Most relevant products are already mapped or classified.
Residual unresolved products remain visible for controlled review.
```

---

## Residual Product Handling

Residual products are not considered an ETL failure.

They represent remaining governance work.

Residual products should be reviewed through controlled processes such as:

```text
not_found analysis
priority backlog review
bridge report review
lifecycle analysis
manual approval
dictionary promotion
```

The project should not force-map residual products by name similarity.

---

## Not Found Analysis

The not_found analyser supports review of products that did not resolve through the dictionary.

Relevant script:

```bash
python -m scripts.test_inventory_not_found_analyzer
```

Expected purpose:

```text
analyse unresolved products
prioritise high-impact candidates
support manual review
prepare bridge or promotion workflows
```

---

## Priority Backlog

The priority backlog identifies high-impact unresolved products.

Relevant script:

```bash
python -m scripts.test_inventory_not_found_priority_backlog
```

Expected purpose:

```text
rank unresolved products
focus manual review on meaningful candidates
avoid spending review time on low-impact residual noise
```

---

## Bridge Reports

Bridge reports compare unresolved products against lifecycle or known product references to support candidate mapping review.

Relevant scripts may include:

```bash
python -m scripts.test_inventory_not_found_p1_bridge
python -m scripts.test_inventory_not_found_p2_bridge
python -m scripts.test_inventory_not_found_residual_bridge
```

Expected purpose:

```text
generate candidate relationships
support controlled manual review
avoid direct automatic mapping
```

Bridge reports do not update the dictionary by themselves.

---

## Controlled Dictionary Promotion

Dictionary promotion must remain controlled.

Relevant scripts may include:

```bash
python -m scripts.test_promote_inventory_bridge_to_dictionary
python -m scripts.test_promote_inventory_not_found_p1_to_dictionary
python -m scripts.test_promote_inventory_not_found_p2_to_dictionary
python -m scripts.test_promote_inventory_not_found_residual_to_dictionary
```

Allowed promotion flow:

```text
not_found backlog
→ prioritise
→ build bridge
→ manual review
→ promote approved candidate
→ rerun inventory ETL
→ measure backlog reduction
```

Not allowed:

```text
automatic promotion without review
mapping by name only
mapping by supplier only
mapping by category only
updating Odoo from ETL
```

---

## Inventory Lifecycle Analysis

Inventory lifecycle analysis supports decisions about whether products are active, dormant, historical, or candidates for review.

Relevant table:

```text
inventory_product_lifecycle
```

Lifecycle analysis can support decisions such as:

```text
historical-only product
active product
candidate for dictionary promotion
candidate for backlog closure
candidate for manual review
```

Lifecycle analysis should support governance decisions, not replace manual approval.

---

## Relationship With Purchases

The Inventory domain directly supports the Purchases domain.

Purchases product mapping uses:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

Therefore:

```text
Inventory dictionary quality directly affects Purchases mapping quality.
```

The Purchases domain does not create automatic aliases.

Purchases follows the same rule:

```text
Explicit reference beats name similarity.
```

Related documentation:

```text
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
```

---

## Relationship With Sales

Sales always remain Wansoft.

Inventory must not assume that public-sale products belong to the same universe as purchase/inventory products.

Sales-reference products should be routed through scope-aware logic.

Important rule:

```text
Sales always use Wansoft.
Inventory follows COMPANY_SOURCE.
```

---

## Relationship With Internal Providers

Bodegón and Empanadas are operationally important but should not be treated as regular final operating companies in the same way as Fonda Argentina branches.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Inventory decisions involving Bodegón or Empanadas should remain scope-aware.

They may appear as operational/provider universes, but they should not pollute the main shared inventory dictionary unless explicitly reviewed and approved.

---

## Operational Odoo Considerations

Odoo inventory movements may have operational states that affect inventory and accounting alignment.

Operational states to review include:

```text
ready / listo
waiting / en espera
cancelled / cancelado
done / hecho
```

Operational interpretation:

```text
done/hecho:
    movement has been validated

ready/listo:
    operation is ready but not completed

waiting/en espera:
    operation may be waiting for stock availability or another dependency

cancelled/cancelado:
    operation was cancelled and may require review depending on scenario
```

These states should be reviewed operationally in Odoo when there are valuation, accounting, or stock differences.

The ETL must not automatically correct these records.

---

## Inventory and Valuation Considerations

Inventory and valuation differences may arise when:

```text
inventory movements are not completed
stock is insufficient
receipts are not validated
deliveries remain pending
manual valuation adjustments are made
stock and accounting reports are not aligned
```

The Inventory ETL helps expose data, but it does not replace operational correction processes.

Operational correction should happen in Odoo or through the proper business process.

---

## What Is Considered Closed

The following are considered closed for this Inventory phase:

```text
basic Odoo inventory extraction
scope-aware classification approach
dictionary-based lookup approach
snapshot and backlog architecture
controlled promotion architecture
not_found analysis pattern
bridge report pattern
inventory lifecycle support
documentation handoff to runbook
```

---

## What Remains Controlled

The following remain intentionally controlled and should not be fully automated without review:

```text
dictionary promotions
scope rule changes
classification heuristics
manual review decisions
historical-only product decisions
residual backlog closure
Odoo catalog cleanup
company source changes
```

---

## What Is Not Closed

The following are not considered closed by this document:

```text
production orchestration
automatic scheduling
Power BI final semantic model
accounting reconciliation automation
complete elimination of residual backlog
automatic product cleanup in Odoo
direct Odoo writeback
```

---

# Validation Queries

Run these queries to confirm the current Inventory baseline.

---

## 1. Snapshot row count

```sql
SELECT
    COUNT(*) AS total_snapshot_rows,
    COUNT(DISTINCT product_id) AS unique_products,
    COUNT(DISTINCT location_id) AS unique_locations
FROM odoo_inventory_snapshot;
```

---

## 2. Snapshot by mapping status

```sql
SELECT
    mapping_status,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT product_id) AS unique_products
FROM odoo_inventory_snapshot
GROUP BY mapping_status
ORDER BY total_rows DESC;
```

---

## 3. Backlog by bucket

```sql
SELECT
    backlog_bucket,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT product_id) AS unique_products
FROM odoo_inventory_backlog
GROUP BY backlog_bucket
ORDER BY total_rows DESC;
```

---

## 4. Backlog by scope

```sql
SELECT
    inventory_scope,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT product_id) AS unique_products
FROM odoo_inventory_backlog
GROUP BY inventory_scope
ORDER BY total_rows DESC;
```

---

## 5. Dictionary coverage

```sql
SELECT
    mapping_status,
    COUNT(*) AS total_mappings,
    COUNT(DISTINCT odoo_product_id) AS unique_odoo_products,
    COUNT(DISTINCT wansoft_code) AS unique_wansoft_codes
FROM inventory_mapping_dictionary
GROUP BY mapping_status
ORDER BY total_mappings DESC;
```

---

## 6. Residual unresolved products

```sql
SELECT
    product_id,
    product_name,
    inventory_scope,
    backlog_bucket,
    mapping_status,
    total_qty,
    total_value
FROM odoo_inventory_backlog
WHERE mapping_status IN ('not_found', 'pending_review')
ORDER BY total_value DESC
LIMIT 100;
```

---

## 7. Scope classification distribution

```sql
SELECT
    refined_scope,
    COUNT(*) AS total_products
FROM odoo_inventory_scope_classification
GROUP BY refined_scope
ORDER BY total_products DESC;
```

---

# Key Operational Scripts

## Inventory scope classification

```bash
python -m scripts.test_odoo_inventory_scope_classification
```

## Inventory ETL

```bash
python -m scripts.test_odoo_inventory_etl
```

## Dictionary lookup validation

```bash
python -m scripts.test_inventory_dictionary_lookup
```

## Dictionary application validation

```bash
python -m scripts.test_apply_inventory_dictionary
```

## Not found analyser

```bash
python -m scripts.test_inventory_not_found_analyzer
```

## Priority backlog

```bash
python -m scripts.test_inventory_not_found_priority_backlog
```

## Bridge reports

```bash
python -m scripts.test_inventory_not_found_p1_bridge
python -m scripts.test_inventory_not_found_p2_bridge
python -m scripts.test_inventory_not_found_residual_bridge
```

## Dictionary promotions

```bash
python -m scripts.test_promote_inventory_bridge_to_dictionary
python -m scripts.test_promote_inventory_not_found_p1_to_dictionary
python -m scripts.test_promote_inventory_not_found_p2_to_dictionary
python -m scripts.test_promote_inventory_not_found_residual_to_dictionary
```

---

# Recommended Future Work

Recommended next Inventory improvements:

```text
review residual not_found products by business impact
review pending_review products
continue controlled dictionary promotion
align inventory source governance with COMPANY_SOURCE usage
document production orchestration strategy
review Power BI consumption requirements
monitor inventory valuation issues separately from ETL mapping
```

---

# Current Status

This Inventory phase is considered closed at the current baseline.

Status:

```text
technically stable
functionally advanced
ready to support Purchases domain
residual backlog still visible
manual review still required
```

---

# Related Documentation

```text
docs/project-technical-guide.md
docs/inventory-runbook.md
docs/purchases-product-mapping-policy.md
docs/purchases-company-migration-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/wansoft-local-wsdl.md
```

---

# Recommended Commit

This document should be committed together with the rest of the documentation refresh.

Recommended final commit after all documentation updates:

```bash
git add README.md docs/

git commit -m "docs(project): add technical guide and domain documentation"

git push
```