# Inventory Runbook

## Purpose

This runbook explains how to operate, validate, and troubleshoot the Inventory domain ETL.

It is intended for day-to-day execution and technical validation of:

```text
Odoo inventory extraction
inventory scope classification
inventory dictionary lookup
inventory snapshot load
inventory backlog generation
inventory lifecycle analysis
bridge reports
controlled dictionary promotion
source governance alignment
```

This document is operational.

For architecture and design context, refer to:

```text
docs/project-technical-guide.md
docs/inventory-domain-closeout.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/wansoft-local-wsdl.md
```

---

## Inventory Domain Principles

The Inventory domain follows these principles:

```text
Odoo is read-only.
MySQL is the governance layer.
Inventory scope must be resolved before mapping.
Dictionary lookup must be controlled.
Backlogs must remain visible.
Promotions to dictionary must be reviewed.
Sales remain Wansoft.
Inventory source follows COMPANY_SOURCE.
```

The ETL must not update Odoo product records, inventory records, or catalog references.

---

## Source Governance

Inventory follows the company-level source governance defined in:

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

Current important rule:

```text
COMPANY_SOURCE is authoritative.
operational_start_date only applies when COMPANY_SOURCE = 'odoo'.
```

---

## Odoo Read-Only Rule

Odoo is treated as a read-only source.

The ETL must not:

```text
modify Odoo products
modify Odoo inventory quantities
modify Odoo locations
modify Odoo categories
modify Odoo references
create Odoo product aliases
write resolved mappings back to Odoo
```

All governance outputs should be stored in MySQL.

---

## MySQL Governance Role

MySQL stores the operational governance layer.

Main governance objects:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
bridge reports
promotion outputs
```

MySQL is where the project tracks:

```text
approved mappings
scope classification
mapping failures
dictionary candidates
historical product activity
manual review status
```

---

## Core Inventory Tables

### Main tables

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_scope_classification
odoo_inventory_snapshot
odoo_inventory_backlog
```

### Bridge and backlog-related tables

Depending on current branch state, the project may include bridge/backlog tables such as:

```text
inventory_not_found_priority_backlog
inventory_not_found_p1_bridge
inventory_not_found_p2_bridge
inventory_not_found_residual_bridge
inventory_bridge_report
```

These tables support controlled dictionary expansion.

---

## Inventory Scope Model

The Inventory domain does not treat all products as one universe.

Products are classified into scope buckets before mapping.

Final refined buckets:

```text
restaurantes
bodegon
empanadas
shared_cross_company
review_scope
operational_non_inventory
```

---

## Scope Meaning

### restaurantes

Products associated with the public-sales or restaurant sales universe.

These should not be blindly mapped as inventory candidates.

### bodegon

Products or product flows strongly associated with Bodegón.

### empanadas

Products or product flows strongly associated with Empanadas.

### shared_cross_company

Products used across operating companies and eligible for main inventory dictionary lookup.

### review_scope

Products that require manual review before deciding whether they belong in the main inventory universe.

### operational_non_inventory

Products that appear operational but should not be treated as core inventory mapping candidates.

---

## Current Inventory Inclusion Logic

The Inventory ETL currently applies dictionary lookup primarily to:

```text
shared_cross_company
```

The ETL sends these buckets to backlog or exclusion handling:

```text
scope_restaurantes_sales_reference
scope_bodegon
scope_bodegon_candidate
scope_empanadas
scope_empanadas_candidate
scope_review_scope
scope_operational_non_inventory
```

This prevents sales-reference products, provider-specific products, or operational non-inventory items from polluting the main dictionary.

---

## Current Baseline Status

At the current closeout state, the Inventory domain is considered technically stable and functionally advanced.

Validated baseline values:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

Interpretation:

```text
The inventory ETL is stable enough to support downstream work.
Residual unresolved products remain visible.
Dictionary expansion must continue through controlled review.
```

---

# Execution Order

Run the Inventory domain in this order.

---

## 1. Validate Odoo connection

If needed, validate that Odoo connectivity works through the existing Odoo database connection utilities.

Relevant module:

```text
core/database/odoo.py
```

Expected:

```text
Odoo credentials load correctly.
Odoo API connection works.
Odoo inventory extraction can read products and stock data.
```

---

## 2. Run inventory scope classification

```bash
python -m scripts.test_odoo_inventory_scope_classification
```

This validates or generates:

```text
odoo_inventory_scope_classification
```

Expected behaviour:

```text
products are classified into scope buckets
scope classification is saved to MySQL
unknown cases remain visible for review
```

---

## 3. Run inventory ETL

```bash
python -m scripts.test_odoo_inventory_etl
```

This loads:

```text
odoo_inventory_snapshot
odoo_inventory_backlog
```

Expected behaviour:

```text
Odoo inventory is extracted
inventory is consolidated by product/location
scope classification is merged
dictionary lookup is applied to eligible scope
snapshot rows are saved
unresolved rows are sent to backlog
```

---

## 4. Validate dictionary lookup

```bash
python -m scripts.test_inventory_dictionary_lookup
```

Expected behaviour:

```text
inventory_mapping_dictionary can be queried
approved mappings resolve correctly
unmapped products remain visible
```

---

## 5. Validate dictionary application

```bash
python -m scripts.test_apply_inventory_dictionary
```

Expected behaviour:

```text
dictionary matching applies only to eligible inventory scope
mapped products receive Wansoft reference metadata
unmapped products are not forced into a match
```

---

## 6. Run inventory not-found analyser

```bash
python -m scripts.test_inventory_not_found_analyzer
```

Expected behaviour:

```text
not_found backlog is analysed
candidate products are prioritised
diagnostic output is produced
```

---

## 7. Build priority backlog

```bash
python -m scripts.test_inventory_not_found_priority_backlog
```

Expected behaviour:

```text
high-impact unresolved products are identified
products are ranked for review based on operational relevance
```

---

## 8. Build bridge reports

Depending on the review phase, run:

```bash
python -m scripts.test_inventory_not_found_p1_bridge
python -m scripts.test_inventory_not_found_p2_bridge
python -m scripts.test_inventory_not_found_residual_bridge
```

Expected behaviour:

```text
bridge candidates are generated
candidate mappings remain reviewable before promotion
no automatic dictionary update occurs without promotion step
```

---

## 9. Promote approved bridge candidates

Promotion should be controlled.

Run only after manual review.

```bash
python -m scripts.test_promote_inventory_bridge_to_dictionary
python -m scripts.test_promote_inventory_not_found_p1_to_dictionary
python -m scripts.test_promote_inventory_not_found_p2_to_dictionary
python -m scripts.test_promote_inventory_not_found_residual_to_dictionary
```

Expected behaviour:

```text
approved candidates are inserted into inventory_mapping_dictionary
promotion source is traceable
mapping status is controlled
```

---

## 10. Rerun inventory ETL after promotion

After approved dictionary promotion:

```bash
python -m scripts.test_odoo_inventory_etl
```

Expected improvement:

```text
mapped inventory rows increase
not_found backlog decreases
pending_review remains visible if unresolved
```

---

# Validation Queries

Run these SQL checks after inventory ETL execution.

---

## 1. Snapshot row count

```sql
SELECT
    COUNT(*) AS total_snapshot_rows,
    COUN*(DISTINCT product_id) AS unique_pr*ducts,
    COUNT(DISTINCT location*id) AS unique_locations
FROM odoo_*nventory_snapshot;
```

Expected:
*```text
snapshot table should cont*in inventory rows
unique product a*d location counts should be reason*ble
```

---

## 2. Snapshot by ma*ping status

```sql
SELECT
    map*ing_status,
    COUNT(*) AS total_*ows,
    COUNT(DISTINCT product_id* AS unique_products
FROM odoo_inve*tory_snapshot
GROUP BY mapping_sta*us
ORDER BY total_rows DESC;
```

Use this to monitor how many products are mapped, pending, unresolved, or otherwise classified.

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

Use this to confirm that excluded scopes and unresolved items are being routed correctly.

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

Use this to validate that scope classification is controlling backlog routing.

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

Expected:

```text
approved mappings should be visible
pending or review mappings should remain controlled
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

Use this query to identify high-impact unresolved inventory products.

---

## 7. Validate scope classification

```sql
SELECT
    refined_scope,
    COUNT(*) AS total_products
FROM odoo_inve*tory_scope_classification
GROUP BY*refined_scope
ORDER BY total_produ*ts DESC;
```

Expected:

```text
p*oducts should be distributed acros* the refined scope model
shared_cr*ss_company should represent the ma*n dictionary-eligible universe
```*
---

# Operational Validation in *doo

Inventory behaviour in Odoo s*ould be reviewed carefully when th*re are accounting or valuation dif*erences.

In Odoo - Pridecta Inven*arios y Valoración-20260721_100357*Grabación de la reunión.mp4, the d*scussion explicitly referred to mo*itoring inventory operation states*such as ready/listo, waiting/en es*era, cancelled/cancelado and done/*echo because those states may indi*ate operational anomalies that aff*ct inventory and accounting alignm*nt. 【1-a65706】

Recommended operat*onal checks:

```text
Review inven*ory operations by state.
Investiga*e ready/listo records that were no* completed.
Investigate waiting/en*espera records caused by insuffici*nt stock.
Review cancelled/cancela*o operations for correction logic.*Confirm done/hecho movements repre*ent validated inventory movement.
*``

Do not correct production move*ents automatically from the ETL.

*orrections should be handled opera*ionally in Odoo or through the pro*er business process.

---

# Inven*ory, Receipts, and Locations Conte*t

Odoo inventory documentation in*ludes inventory configuration, inv*ntory reports, multiple warehouses*locations, replenishment rules, an* receipts. These topics are visibl* in manual_de_usuario.docx and man*al_de_usuario.pdf. 【2-39764c】【3-8918e0】

Relevant Odoo concepts for t*is runbook:

```text
inventory rep*rts
multiple warehouses and locati*ns
internal transfers
replenishmen* rules
receipts
stock movements
``*

The ETL should treat these Odoo *ecords as source data only.

---

* Backlog Types

## Scope backlog

*roducts excluded or separated beca*se of business scope:

```text
res*aurantes
bodegon
empanadas
review_*cope
operational_non_inventory
```*
These products should not be forc*d into the main inventory dictiona*y.

---

## Functional backlog

Pr*ducts that are eligible for mappin* but unresolved:

```text
not_foun*
pending_review
historical_only
``*

These products may require lifec*cle review, bridge reports, or man*al promotion.

---

# Dictionary P*omotion Policy

Dictionary promoti*n must be controlled.

Allowed pro*otion flow:

```text
not_found bac*log
→ prioritise
→ build bridge
→ *anual review
→ promote approved ca*didate
→ rerun inventory ETL
→ mea*ure impact
```

Not allowed:

```t*xt
automatic promotion without rev*ew
mapping by name only
mapping by*supplier only
mapping by scope alo*e
updating Odoo as part of ETL
```*
---

# Inventory Lifecycle Analys*s

The lifecycle analysis supports*decisions about whether products a*e active, dormant, historical, or *andidates for review.

Relevant ou*put:

```text
inventory_product_li*ecycle
```

Use lifecycle data to *upport decisions such as:

```text*historical-only product
active pro*uct
candidate for dictionary promo*ion
candidate for backlog closure
*``

---

# Relationship With Purch*ses

The Inventory domain provides*product governance for the Purchas*s domain.

Purchases product mappi*g uses:

```text
purchase.order.li*e.product_id
→ inventory_mapping_d*ctionary.odoo_product_id
→ wansoft*code
→ wansoft_product_name
→ wans*ft_department
```

Therefore:

```*ext
Inventory dictionary quality a*fects Purchases mapping quality.
`*`

The Purchases domain does not c*eate automatic aliases and relies *n approved dictionary mappings.

-*-

# Relationship With Sales

Sale* always remain Wansoft.

Inventory*must not assume that public-sale p*oducts belong to the same universe*as purchase/inventory products.

S*les-reference products should be t*eated carefully and routed through*scope-aware logic.

---

# Trouble*hooting

## Odoo connection fails
*Check:

```text
.env credentials
c*re/config/env_loader.py
core/datab*se/odoo.py
network access
Odoo URL*and database
```

---

## MySQL co*nection fails

Check:

```text
.en* credentials
core/database/mysql.p*
target database
user permissions
*etwork access
```

---

## Snapsho* is empty

Check:

```text
Odoo extraction returned data
scope classification exists
date or company filters are not too restrictive
target table was not truncated after failed load
```

---

## Backlog is unexpectedly high

Check:

```text
inventory_mapping_dictionary coverage
scope classification output
recent new Odoo products
missing Wansoft references
dictionary promotion status
```

---

## Products appear in wrong scope

Check:

```text
odoo_inventory_scope_classification
review_scope_refiner output
refined scope rules
manual overrides
```

---

## Products should map but remain not_found

Check:

```text
inventory_mapping_dictionary.odoo_product_id
mapping_status
wansoft_code
product lifecycle status
bridge candidate tables
```

---

## Sales-reference products are entering inventory mapping

Check:

```text
scope classification
restaurantes bucket
sales reference exclusion logic
INVENTORY_ETL_SCOPE_INCLUDE
INVENTORY_SCOPE_EXCLUDE
```

---

## Bodegón or Empanadas products are polluting shared inventory

Check:

```text
bodegon bucket
empanadas bucket
bodegon_candidate
empanadas_candidate
scope classifier rules
review scope output
```

---

# Environment Variables

Inventory-related `.env` examples:

```env
INVENTORY_ETL_SALES_REFERENCE_SCOPE=restaurantes
INVENTORY_ETL_SALES_REFERENCE_SOURCE=sales_reference
INVENTORY_ETL_SCOPE_INCLUDE=shared_cross_company
INVENTORY_ETL_SCOPE_BACKLOG=bodegon,empanadas,bodegon_candidate,empanadas_candidate,review_scope,operational_non_inventory
```

Inventory not-found analyser examples:

```env
INVENTORY_NOT_FOUND_BUCKET=not_found
INVENTORY_SCOPE_INCLUDE=shared_cross_company,review_scope
INVENTORY_SCOPE_EXCLUDE=bodegon,empanadas,restaurantes,operational_non_inventory
INVENTORY_NOT_FOUND_EXPORT=true
INVENTORY_NOT_FOUND_EXPORT_FILE=inventory_not_found_analysis.csv
```

---

# Recommended Execution Checklist

Use this checklist when running the Inventory domain.

```text
[ ] Confirm .env is loaded
[ ] Confirm Odoo connection
[ ] Confirm MySQL connection
[ ] Run inventory scope classification
[ ] Run inventory ETL
[ ] Validate snapshot row count
[ ] Validate mapping status distribution
[ ] Validate backlog distribution
[ ] Run not_found analyser if needed
[ ] Build bridge reports if needed
[ ] Review candidates manually
[ ] Promote approved candidates only
[ ] Rerun inventory ETL
[ ] Compare backlog reduction
[ ] Document findings
```

---

# Current Inventory Status

Current state:

```text
Inventory domain is technically stable.
Inventory dictionary governance is active.
Scope-aware ETL is active.
Residual unresolved products remain visible.
Manual review remains required for dictionary expansion.
```

Validated baseline:

```text
snapshot rows: 1660
residual functional not_found: 98 unique products
residual functional pending_review: 5 unique products
```

---

# Related Documentation

```text
docs/project-technical-guide.md
docs/inventory-domain-closeout.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-company-migration-policy.md
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