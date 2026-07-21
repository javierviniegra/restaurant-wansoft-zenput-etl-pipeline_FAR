# Purchases Product Mapping Policy

## Purpose

This document defines the product mapping policy for the Purchases domain during the Wansoft and Odoo transition.

The purpose of this policy is to prevent unsafe product equivalence assumptions while keeping purchase analytics aligned with the existing Wansoft product governance model.

The policy applies to:

```text
Odoo purchase order lines
Odoo purchase receipts and receipt moves
Wansoft purchase-like inventory inputs
purchase inventory mapping backlog
canonical purchase order lines
canonical purchase receipt moves
```

The policy is based on one main principle:

```text
Explicit reference beats name similarity.
```

---

## Core Decision

The project does not create automatic product aliases between Odoo and Wansoft.

This means the ETL does not automatically assume that two products are equivalent only because they have similar names.

The project intentionally avoids a generic alias table such as:

```text
inventory_product_alias_dictionary
```

at this stage.

---

## Why Automatic Aliases Are Not Used

Automatic aliases are risky because product names may look similar while representing different operational realities.

Examples:

```text
Rib Eye
Rib Eye CAB
Rib Eye Lipon
Rib Eye (Bife de Chorizo)
Short Rib
Back Rib
```

These products may differ by:

```text
supplier
cut or specification
unit of measure
packaging
purchase usage
inventory usage
recipe usage
cost behaviour
```

Because of this, name similarity is not enough to determine product equivalence.

---

## Product Governance Source of Truth

The approved product mapping source remains:

```text
inventory_mapping_dictionary
```

This dictionary links Odoo products to Wansoft product references in a controlled way.

The expected relationship is:

```text
Odoo product
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

Only approved mappings should be used for canonical purchase enrichment.

---

## Approved Mapping Rule

A purchase line is mapped only when there is an approved row in:

```text
inventory_mapping_dictionary
```

Expected conditions:

```text
inventory_mapping_dictionary.odoo_product_id = purchase product_id
mapping_status = approved
```

When this condition is met:

```text
product_mapping_found = 1
product_mapping_status = approved
product_mapping_source = inventory_mapping_dictionary
purchase_mapping_bucket = mapped_inventory
```

---

## New Product Rule

If a new Odoo product does not have an explicit Wansoft reference or an approved dictionary mapping, it is treated as a new product.

Expected behaviour:

```text
product_mapping_found = 0
purchase_mapping_bucket = unmapped_inventory_candidate
```

The product should remain in:

```text
odoo_purchase_inventory_mapping_backlog
```

until manually reviewed.

The ETL must not automatically map it by similar name.

---

## Explicit Reference Rule

If a new Odoo product has an explicit Wansoft reference, it may be mapped through the approved dictionary flow.

Expected flow:

```text
Odoo product has Wansoft reference/code
→ reviewed against Wansoft product governance
→ added to inventory_mapping_dictionary if approved
→ future purchase lines are mapped
```

No direct automatic promotion should occur without review.

---

## No Name Similarity Mapping

The ETL must not map products using:

```text
similar product names
partial string matching
fuzzy matching
manual assumptions inside code
supplier similarity
category similarity alone
```

This avoids hidden equivalence errors.

Incorrect example:

```text
Odoo Product: Rib Eye Special New Branch
Wansoft Product: Rib Eye

Decision:
    Do not map by name similarity.
```

Correct behaviour:

```text
Keep as unmapped_inventory_candidate until reviewed.
```

---

## Purchase Product Mapping Flow

The Purchases ETL should resolve product mapping in this order:

```text
1. Read purchase.order.line.product_id
2. Check inventory_mapping_dictionary
3. If approved mapping exists:
       mark as mapped_inventory
4. If no approved mapping exists:
       classify by product and operational scope
5. If product is an inventory candidate:
       send to odoo_purchase_inventory_mapping_backlog
6. Do not create an automatic alias
```

---

## Odoo Purchase Lines

Odoo purchase lines are loaded into:

```text
odoo_purchase_order_line_snapshot
```

Product mapping fields include:

```text
product_mapping_found
product_mapping_status
product_mapping_source
wansoft_code
wansoft_product_name
wansoft_department
purchase_product_scope
purchase_mapping_bucket
purchase_classification_source
extracted_product_code
```

Mapped purchase lines can later flow into:

```text
canonical_purchase_order_line_snapshot
```

with the corresponding Wansoft product metadata.

---

## Odoo Receipts and Receipt Moves

Odoo receipt moves are loaded into:

```text
odoo_purchase_receipt_move_snapshot
```

Receipt movements may be enriched with purchase-line mapping when linked to:

```text
odoo_purchase_order_line_id
```

The canonical receipt move table is:

```text
canonical_purchase_receipt_move_snapshot
```

Product mapping fields may include:

```text
wansoft_code
wansoft_product_name
wansoft_department
```

These fields should come from approved dictionary governance or purchase-line enrichment, not from alias guessing.

---

## Wansoft Product Mapping Behaviour

Wansoft purchase-like data is loaded from:

```text
getinputinventory_entrada
```

using:

```sql
WHERE TipoEntrada = 'Factura'
```

Wansoft rows already contain native Wansoft product identifiers.

Relevant fields include:

```text
IdProducto
CodigoProducto
NombreProducto
Departamento
UnidadDeMedida
Cantidad
CostoUnitario
FechaEntrada
Factura
RFCProveedor
NombreProveedor
```

For Wansoft canonical purchase rows:

```text
product_mapping_found = 1
product_mapping_status = native_wansoft
product_mapping_source = getinputinventory_entrada
purchase_mapping_bucket = mapped_wansoft_native
```

This is because Wansoft rows are already expressed in Wansoft product terms.

---

## Canonical Purchase Layer Mapping Behaviour

The canonical purchase layer supports both:

```text
source_system = odoo
source_system = wansoft
```

Canonical purchase tables:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

For Odoo rows:

```text
product mapping depends on inventory_mapping_dictionary
```

For Wansoft rows:

```text
product mapping is native Wansoft mapping
```

This allows both systems to coexist while preserving product traceability.

---

## Purchase Mapping Buckets

Recommended mapping buckets:

```text
mapped_inventory
unmapped_inventory_candidate
mapped_wansoft_native
sales_reference_candidate
bodegon_candidate
empanadas_candidate
operational_non_inventory_candidate
empty_line
manual_review
```

### mapped_inventory

Odoo purchase product has an approved dictionary mapping.

### unmapped_inventory_candidate

Odoo purchase product appears to be an inventory product but has no approved mapping.

### mapped_wansoft_native

Wansoft purchase row already contains native Wansoft product identifiers.

### sales_reference_candidate

The product may be related to sales or public-sale catalogue references.

### bodegon_candidate

The product may belong to a Bodegón-related operational universe but still requires controlled review.

### empanadas_candidate

The product may belong to an Empanadas-related operational universe but still requires controlled review.

### operational_non_inventory_candidate

The product appears operational but not suitable for main inventory dictionary mapping.

### empty_line

The line has no product, quantity, or amount and should not be treated as a product mapping candidate.

### manual_review

The product or line has insufficient or unusual information and needs manual review.

---

## Backlog Policy

Products without approved mapping are reviewed through:

```text
odoo_purchase_inventory_mapping_backlog
```

The backlog is deduplicated by:

```text
product_id
```

and includes operational metrics such as:

```text
total_lines
unique_vendors
unique_companies
total_qty
total_received
total_amount
first_order_date
last_order_date
suggested_action
backlog_status
```

This allows review by business impact.

---

## Backlog Reference Validation

The project validates whether products in the purchase backlog have usable Odoo references.

Current validated result:

```text
new_product_no_reference = 233 products
has_reference_candidate = 0 products
```

Interpretation:

```text
No backlog product had a usable Odoo default_code reference.
All 233 products remain new-product or review candidates.
```

This supports the policy:

```text
No automatic alias.
No name-similarity mapping.
Keep unresolved products in backlog.
```

---

## Reference Normalisation

Odoo may return empty references as:

```text
False
"False"
"false"
None
NaN
""
"null"
```

These values are not valid references.

The ETL should normalise these values to:

```text
None
```

A valid reference must be a non-empty, meaningful code.

---

## Product Reference Examples

### Valid mapping candidate

```text
Odoo product:
    Rib Eye (Bife de Chorizo)

Approved dictionary:
    odoo_product_id -> wansoft_code

Result:
    mapped_inventory
```

---

### New product without reference

```text
Odoo product:
    Rib Eye Special New Branch

No approved dictionary row.
No explicit Wansoft reference.

Result:
    unmapped_inventory_candidate
```

The product remains in:

```text
odoo_purchase_inventory_mapping_backlog
```

---

### Wansoft native product

```text
Wansoft row:
    CodigoProducto = 5200-101-100-001
    NombreProducto = Empanada de Carne

Result:
    mapped_wansoft_native
```

---

## Internal Provider Companies

The following companies are internal providers, not final operating companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

This policy affects company inclusion, not product mapping by itself.

Correct rule:

```text
Exclude internal providers when they appear as company_name.
Keep them when they appear as vendor_name and the buying company is final-eligible.
```

Example kept:

```text
company_name = FONDA ARGENTINA LAS ANTENAS
vendor_name  = EL BODEGON DE FITO
```

Example excluded:

```text
company_name = EL BODEGON DE FITO
vendor_name  = external supplier
```

Product mapping still follows the same rules:

```text
explicit reference
approved dictionary
native Wansoft code
or backlog
```

---

## Source System Differences

### Odoo rows

Odoo purchase rows require mapping because Odoo product IDs may not be directly equivalent to Wansoft product codes.

Mapping source:

```text
inventory_mapping_dictionary
```

### Wansoft rows

Wansoft purchase rows already contain Wansoft product identifiers.

Mapping source:

```text
getinputinventory_entrada
```

Canonical source status:

```text
mapped_wansoft_native
```

---

## ETL Responsibilities

The Purchases ETL is responsible for:

```text
extracting purchase lines
classifying line type
applying company source governance
checking approved dictionary mapping
identifying unmapped inventory candidates
building purchase inventory backlog
loading canonical product metadata
avoiding automatic alias creation
```

The ETL must not:

```text
infer product equivalence by name
create automatic aliases
promote products automatically to the dictionary
modify Odoo product records
overwrite Wansoft product governance
```

---

## Manual Review Responsibilities

Manual or controlled review is required when:

```text
a product has no approved mapping
a product has no usable Odoo reference
a product appears in multiple operational scopes
a product has unusually high purchase amount
a product appears across several vendors or companies
a product may be operational rather than inventory
```

Review outcomes may include:

```text
approve dictionary mapping
keep in backlog
mark as operational non-inventory
mark as sales reference candidate
request product reference cleanup
```

---

## Dictionary Promotion Rule

A product may be promoted to:

```text
inventory_mapping_dictionary
```

only when the reviewer confirms the relationship between:

```text
Odoo product
Wansoft product code
Wansoft product name
Department
Operational usage
```

Promotion should be controlled and auditable.

---

## What Is Not Allowed

The following are not allowed in the current baseline:

```text
automatic alias dictionary
fuzzy matching as final mapping
mapping by product name only
mapping by supplier only
mapping by category only
automatic promotion from backlog to dictionary
direct ETL updates into Odoo product records
```

---

## Related Tables

```text
inventory_mapping_dictionary
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_move_snapshot
odoo_purchase_inventory_mapping_backlog
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_move_snapshot
getinputinventory_entrada
```

---

## Related ETL Entrypoints

### Purchase ETL

```bash
python -m scripts.test_odoo_purchase_etl
```

### Purchase receipt ETL

```bash
python -m scripts.test_odoo_purchase_receipt_etl
```

### Purchase inventory mapping backlog

```bash
python -m scripts.test_purchase_inventory_mapping_backlog
```

### Backlog product reference report

```bash
python -m scripts.test_purchase_backlog_product_reference_report
```

### Odoo canonical purchase load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

### Wansoft canonical purchase load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

---

## Validation Queries

### 1. Validate unmapped Odoo purchase products

```sql
SELECT
    purchase_mapping_bucket,
    COUNT(*) AS total_lines,
    COUNT(DISTINCT product_id) AS unique_products,
    SUM(COALESCE(price_total, 0)) AS total_amount
FROM odoo_purchase_order_line_snapshot
GROUP BY purchase_mapping_bucket
ORDER BY total_amount DESC;
```

---

### 2. Validate purchase inventory mapping backlog

```sql
SELECT
    backlog_status,
    suggested_action,
    COUNT(*) AS unique_products,
    SUM(COALESCE(total_lines, 0)) AS total_lines,
    SUM(COALESCE(total_amount, 0)) AS total_amount
FROM odoo_purchase_inventory_mapping_backlog
GROUP BY
    backlog_status,
    suggested_action
ORDER BY total_amount DESC;
```

---

### 3. Validate canonical Odoo mapped products

```sql
SELECT
    product_mapping_status,
    product_mapping_source,
    purchase_mapping_bucket,
    COUNT(*) AS total_lines,
    COUNT(DISTINCT product_id) AS unique_products,
    SUM(COALESCE(price_total, 0)) AS total_amount
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'odoo'
GROUP BY
    product_mapping_status,
    product_mapping_source,
    purchase_mapping_bucket
ORDER BY total_amount DESC;
```

---

### 4. Validate Wansoft native mapping

```sql
SELECT
    product_mapping_status,
    product_mapping_source,
    purchase_mapping_bucket,
    COUNT(*) AS total_lines,
    COUNT(DISTINCT wansoft_code) AS unique_wansoft_codes,
    SUM(COALESCE(price_total, 0)) AS total_amount
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft'
GROUP BY
    product_mapping_status,
    product_mapping_source,
    purchase_mapping_bucket
ORDER BY total_amount DESC;
```

---

### 5. Validate backlog candidates by amount

```sql
SELECT
    product_id,
    product_name,
    total_lines,
    unique_vendors,
    unique_companies,
    total_qty,
    total_received,
    total_amount,
    first_order_date,
    last_order_date,
    suggested_action,
    backlog_status
FROM odoo_purchase_inventory_mapping_backlog
WHERE backlog_status = 'open'
ORDER BY total_amount DESC
LIMIT 100;
```

---

## Current Validated Status

Current validated product mapping status:

```text
No automatic aliases are used.
Odoo unresolved products remain in backlog.
Odoo backlog products without references are treated as new products.
Wansoft canonical rows use native Wansoft product codes.
Canonical purchase layer preserves mapping source and source_system.
```

Current validated reference report:

```text
new_product_no_reference = 233 products
has_reference_candidate = 0 products
```

---

## Known Design Decisions

### 1. No automatic alias table

The project intentionally does not create:

```text
inventory_product_alias_dictionary
```

at this stage.

### 2. Dictionary remains authoritative

Approved mapping must come from:

```text
inventory_mapping_dictionary
```

### 3. Product names are not enough

Similar names do not prove equivalence.

### 4. Wansoft native rows remain Wansoft-native

Wansoft rows are already expressed in Wansoft product terms.

### 5. Odoo product cleanup is separate from ETL

If Odoo references are missing or incorrect, the ETL should not patch Odoo.

The issue should remain visible through backlog and governance workflows.

---

## Current Status

This policy is active.

Validated:

```text
purchase product mapping through inventory_mapping_dictionary
no automatic product aliases
backlog for unmapped Odoo purchase inventory candidates
Odoo reference normalisation
Wansoft native product mapping
canonical purchase source traceability
```

---

## Related Documentation

```text
docs/project-technical-guide.md
docs/purchases-company-migration-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/wansoft-local-wsdl.md
```

---

## Recommended Commit

This document should be committed together with the rest of the documentation refresh.

Recommended final commit after all documentation updates:

```bash
git add README.md docs/

git commit -m "docs(project): add technical guide and domain documentation"

git push
```