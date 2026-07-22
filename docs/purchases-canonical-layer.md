# Purchases Canonical Layer

## Purpose

This document describes the canonical Purchases layer for the Wansoft + Odoo Data Warehouse and ETL Pipeline project.

The purpose of the canonical layer is to provide final BI-ready Purchases tables that can safely combine Odoo and Wansoft data while preserving source traceability.

This document explains:

```text
canonical purchase tables
source_system strategy
source_domain strategy
COMPANY_SOURCE governance
Odoo canonical load
Wansoft canonical load
rollout company patterns
internal provider handling
Antenas source split
La Esquina Coyoacán rollout validation
CentroMyJ new branch validation
Puebla future rollout handling
Wansoft technical keys
validation queries
pipeline validation
```

---

## Core Principle

The canonical Purchases layer must answer:

```text
Which system is the final source for this purchase row?
```

The answer is controlled by:

```text
core/config/companies.py
COMPANY_SOURCE
odoo_company_migration_policy
source_system
final_purchase_source_status
```

Main source governance rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

---

## Canonical Tables

The canonical Purchases layer contains these tables:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

These tables are final analytical tables, not raw source tables.

They combine:

```text
Odoo final purchase data
Wansoft final purchase data
Wansoft historical purchase data before Odoo rollout
```

---

## Source Systems

The canonical Purchases layer supports:

```text
source_system = odoo
source_system = wansoft
```

Meaning:

```text
odoo:
    Row came from Odoo purchase, receipt, or stock movement snapshots.

wansoft:
    Row came from persisted Wansoft purchase-like inventory input data.
```

---

## Source Domain

The canonical Purchases layer uses:

```text
source_domain = purchases
```

This allows future canonical layers to use the same source-system strategy across other domains such as:

```text
inventory
sales
```

---

## Main Governance Fields

Canonical purchase tables include fields such as:

```text
source_system
source_domain
company_source_key
final_purchase_source_status
company_name
vendor_name
order_date
product_mapping_status
product_mapping_source
purchase_mapping_bucket
```

---

## final_purchase_source_status

The field:

```text
final_purchase_source_status
```

explains why a row is included in the canonical layer and how it should be interpreted.

Current expected values:

```text
final_odoo_enabled
final_wansoft_enabled
wansoft_history_before_odoo
exclude_internal_provider
exclude_after_odoo_start
unknown_source_review
```

---

## Status Meaning

### final_odoo_enabled

Used when:

```text
source_system = odoo
COMPANY_SOURCE = odoo
company is final-eligible
row is on or after operational_start_date
```

Example:

```text
Antenas Odoo purchases from 2026-06-01 onward.
La Esquina Coyoacán Odoo purchases from operational_start_date onward.
CentroMyJ Odoo purchases as a new Odoo branch.
```

---

### final_wansoft_enabled

Used when:

```text
source_system = wansoft
COMPANY_SOURCE = wansoft
company is final-eligible
```

Example:

```text
Acoxpa
Aeropuerto
Isabel La Católica
Oceanía
Tepeyac
Cancun
Metepec
Napoles
San Jeronimo
```

---

### wansoft_history_before_odoo

Used when:

```text
source_system = wansoft
COMPANY_SOURCE = odoo
row date is before operational_start_date
```

Example:

```text
Antenas Wansoft purchases before 2026-06-01.
La Esquina Coyoacán Wansoft purchases before its operational_start_date.
```

This status preserves historical Wansoft data without allowing Wansoft to remain the final source after the Odoo rollout.

---

### exclude_after_odoo_start

Used when:

```text
source_system = wansoft
COMPANY_SOURCE = odoo
row date is greater than or equal to operational_start_date
```

These rows should not be loaded into final canonical facts.

---

### exclude_internal_provider

Used when:

```text
company_name is an internal provider company
```

These rows are excluded from final branch-level facts.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

---

### unknown_source_review

Used when:

```text
company_source_key cannot be resolved
```

Rows with this status should not be treated as final until mapping is corrected.

---

# Odoo Canonical Load

## Entrypoint

Run:

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

Function:

```python
run_canonical_purchase_odoo_etl()
```

---

## Source Tables

Odoo canonical Purchases are loaded from:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

---

## Odoo Eligibility

Odoo rows are eligible when:

```text
COMPANY_SOURCE = odoo
include_final_company = True
final_purchase_source_status = final_odoo_enabled
```

Current active Odoo final companies:

```text
Antenas
La Esquina Coyoacán
CentroMyJ
```

---

## Current Odoo Canonical Counts

Current validated Odoo canonical counts after rollout validation:

```text
canonical_purchase_order_snapshot:
    source_system = odoo
    total_rows = 882

canonical_purchase_order_line_snapshot:
    source_system = odoo
    total_rows = 4771

canonical_purchase_receipt_snapshot:
    source_system = odoo
    total_rows = 876

canonical_purchase_receipt_move_snapshot:
    source_system = odoo
    total_rows = 4763
```

These counts include active Odoo rollout companies such as:

```text
Antenas
La Esquina Coyoacán
CentroMyJ
```

---

# Wansoft Canonical Load

## Entrypoint

Run:

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

Function:

```python
run_canonical_purchase_wansoft_etl()
```

---

## Source Table

Wansoft canonical Purchases are loaded from:

```text
getinputinventory_entrada
```

Filtering rule:

```sql
WHERE TipoEntrada = 'Factura'
```

---

## Relevant Wansoft Fields

Main Wansoft fields include:

```text
id
subsidiary_name
IdEntrada
CodigoProducto
NombreProducto
Departamento
UnidadDeMedida
Cantidad
CostoUnitario
FechaEntrada
Factura
FechaFactura
RFCProveedor
ClaveProveedor
NombreProveedor
FechaReal
```

---

## Wansoft Eligibility

Wansoft rows are eligible as final when:

```text
COMPANY_SOURCE = wansoft
include_final_company = True
```

Wansoft rows are eligible as historical when:

```text
COMPANY_SOURCE = odoo
row date is before operational_start_date
```

Wansoft rows are not final after Odoo rollout for migrated branches.

---

## Current Wansoft Canonical Counts

Current validated Wansoft canonical counts after rollout validation:

```text
canonical_purchase_order_snapshot:
    source_system = wansoft
    total_rows = 145015

canonical_purchase_order_line_snapshot:
    source_system = wansoft
    total_rows = 745161

canonical_purchase_receipt_snapshot:
    source_system = wansoft
    total_rows = 145015

canonical_purchase_receipt_move_snapshot:
    source_system = wansoft
    total_rows = 745161
```

---

## Current Wansoft Final Status Summary

Current validated Wansoft status distribution:

```text
final_wansoft_enabled        690000
wansoft_history_before_odoo   55161
```

Interpretation:

```text
Most Wansoft rows remain final for Wansoft-source companies.
Rows from migrated Odoo-source companies before their cutoff remain as Wansoft history.
```

---

# Current Canonical Table Counts

Current validated canonical table counts:

```text
canonical_purchase_order_snapshot:
    odoo:      882
    wansoft: 145015

canonical_purchase_order_line_snapshot:
    odoo:      4771
    wansoft: 745161

canonical_purchase_receipt_snapshot:
    odoo:      876
    wansoft: 145015

canonical_purchase_receipt_move_snapshot:
    odoo:      4763
    wansoft: 745161
```

These counts were validated through:

```bash
python -m scripts.validate_purchases_canonical_layer
```

Expected validation result:

```text
VALIDATION RESULT: PASSED
```

---

# Rollout Company Pattern Validation

The canonical validation layer now includes rollout-specific expectations.

Implemented in:

```text
scripts/validate_purchases_canonical_layer.py
```

Constant:

```python
ROLLOUT_COMPANY_EXPECTATIONS
```

Current validation name:

```text
rollout_company_patterns
```

---

## Supported Rollout Types

Current rollout types:

```text
migrated_from_wansoft
new_odoo_branch
```

---

## migrated_from_wansoft

Use this pattern when the branch previously operated in Wansoft and later starts operating in Odoo.

Expected canonical pattern:

```text
source_system = odoo
final_purchase_source_status = final_odoo_enabled

source_system = wansoft
final_purchase_source_status = wansoft_history_before_odoo
```

Not allowed after activation:

```text
source_system = wansoft
final_purchase_source_status = final_wansoft_enabled
```

Current validated migrated branches:

```text
Antenas
La Esquina Coyoacán
```

---

## new_odoo_branch

Use this pattern when the branch starts directly as an Odoo branch.

Expected canonical pattern:

```text
source_system = odoo
final_purchase_source_status = final_odoo_enabled
```

Not allowed after activation:

```text
source_system = wansoft
final_purchase_source_status = final_wansoft_enabled
```

Current validated new Odoo branch:

```text
CentroMyJ
```

Current future inactive rollout:

```text
Puebla
```

---

## Active and Inactive Rollout Expectations

Each rollout expectation may use:

```text
active = True
active = False
```

Meaning:

```text
active = True:
    validation is enforced and can fail the pipeline.

active = False:
    rollout is documented as future work but does not fail current validation.
```

Current rollout expectation state:

```text
Antenas:
    rollout_type = migrated_from_wansoft
    active = True

La Esquina Coyoacán:
    rollout_type = migrated_from_wansoft
    active = True

CentroMyJ:
    rollout_type = new_odoo_branch
    active = True

Puebla:
    rollout_type = new_odoo_branch
    active = False
```

---

## Current Validated Rollout Output

Current validated rollout output:

```text
Antenas:
    odoo    -> final_odoo_enabled
    wansoft -> wansoft_history_before_odoo

La Esquina Coyoacán:
    odoo    -> final_odoo_enabled
    wansoft -> wansoft_history_before_odoo

CentroMyJ:
    odoo    -> final_odoo_enabled

Puebla:
    skipped because active = False
```

---

# Branch-Specific Current State

## Antenas

Current status:

```text
migration pattern = migrated_from_wansoft
rollout active = True
canonical validation = PASS
```

Expected canonical behaviour:

```text
Odoo:
    final_odoo_enabled from 2026-06-01 onward

Wansoft:
    wansoft_history_before_odoo before 2026-06-01
```

Current validated output:

```text
source_system = odoo
company_source_key = Antenas
final_purchase_source_status = final_odoo_enabled

source_system = wansoft
company_source_key = Antenas
final_purchase_source_status = wansoft_history_before_odoo
```

---

## La Esquina Coyoacán

Current status:

```text
migration pattern = migrated_from_wansoft
rollout active = True
canonical validation = PASS
```

Expected canonical behaviour:

```text
Odoo:
    final_odoo_enabled from operational_start_date onward

Wansoft:
    wansoft_history_before_odoo before operational_start_date
```

Current validated output:

```text
source_system = odoo
company_source_key = La Esquina Coyoacán
final_purchase_source_status = final_odoo_enabled

source_system = wansoft
company_source_key = La Esquina Coyoacán
final_purchase_source_status = wansoft_history_before_odoo
```

Important note:

```text
If min_order_date does not match operational_start_date, this is not automatically an error.
MIN(order_date) shows the first actual order present in the canonical table.
```

---

## CentroMyJ

Current status:

```text
migration pattern = new_odoo_branch
rollout active = True
canonical validation = PASS
```

Expected canonical behaviour:

```text
Odoo:
    final_odoo_enabled
```

Current validated output:

```text
source_system = odoo
company_source_key = CentroMyJ
final_purchase_source_status = final_odoo_enabled
```

---

## Puebla

Current status:

```text
migration pattern = new_odoo_branch
rollout active = False
canonical validation = skipped
```

Puebla is documented as a future rollout.

Current expected behaviour:

```text
Puebla does not fail validation while active = False.
```

When Puebla becomes active:

```text
Change active = False to active = True.
Update COMPANY_SOURCE.
Update seed SQL.
Update maintenance SQL.
Apply policy in MySQL.
Run validation.
```

Expected future canonical behaviour:

```text
source_system = odoo
company_source_key = Puebla
final_purchase_source_status = final_odoo_enabled
```

Not allowed after activation:

```text
source_system = wansoft
company_source_key = Puebla
final_purchase_source_status = final_wansoft_enabled
```

---

# Product Mapping Behaviour

## Odoo Product Mapping

Odoo purchase lines are enriched through:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

Odoo rows depend on controlled dictionary mapping.

The project does not create automatic product aliases.

Key rule:

```text
Explicit reference beats name similarity.
```

---

## Wansoft Product Mapping

Wansoft rows already contain native Wansoft product identifiers.

For Wansoft canonical rows:

```text
product_mapping_status = native_wansoft
product_mapping_source = getinputinventory_entrada
purchase_mapping_bucket = mapped_wansoft_native
```

---

## Current Mapping Distribution

Current validated mapping distribution includes:

```text
Odoo mapped rows through p1_bridge
Odoo mapped rows through p2_bridge
Odoo mapped rows through residual_bridge
Odoo unmapped inventory candidates
Odoo unmapped Bodegón candidates
Odoo unmapped Empanadas candidates
Odoo unmapped sales references
Odoo empty lines
Wansoft native rows
```

Current Wansoft mapping status:

```text
source_system = wansoft
product_mapping_status = native_wansoft
product_mapping_source = getinputinventory_entrada
purchase_mapping_bucket = mapped_wansoft_native
```

---

# Internal Provider Handling

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Rules:

```text
If company_name is an internal provider:
    exclude from final canonical branch-level facts.

If vendor_name is an internal provider:
    keep the row if the buying company is final-eligible.
```

Correct example:

```text
company_name = FONDA ARGENTINA LAS ANTENAS
vendor_name  = EL BODEGON DE FITO
```

Expected result:

```text
Keep row.
```

Incorrect example:

```text
company_name = EL BODEGON DE FITO
```

Expected result:

```text
Exclude row from final branch-level canonical facts.
```

Validator check:

```text
internal_providers_as_vendors
internal_providers_not_as_companies
```

---

# Wansoft Technical Key Strategy

Wansoft natural invoice keys are not used directly as unique canonical IDs because of:

```text
case-insensitive MySQL collation
trailing spaces
long natural keys
inconsistent invoice casing
duplicate invoice references
```

Instead, stable hashed technical keys are used.

Examples:

```text
source_order_id = wansoft_order:{company_key}:{fecha_key}:{hash}
source_receipt_id = wansoft_receipt:{company_key}:{fecha_key}:{hash}
source_order_line_id = wansoft_line:{id}
source_stock_move_id = wansoft_move:{id}
```

Natural values remain available in business columns such as:

```text
purchase_order_name
vendor_id
vendor_name
wansoft_code
wansoft_product_name
order_date
```

---

# Source-System Reload Strategy

Canonical purchase tables should be refreshed by `source_system`.

This allows the project to reload one source without deleting validated data from the other source.

---

## Odoo Refresh

Rules:

```text
Delete only source_system = 'odoo'
Reload eligible Odoo rows
Preserve source_system = 'wansoft'
```

