# Purchases Product Mapping Policy

## Purpose

This document defines how product mapping should work in the Purchases domain during the Odoo/Wansoft transition.

The goal is to keep product governance explicit, controlled, and traceable without creating automatic product aliases that could incorrectly merge different products.

---

## Business Context

During the Odoo transition, there are two relevant scenarios:

1. Existing companies migrated from Wansoft to Odoo
2. New Odoo branches that may create or use new products directly in Odoo

A new product created in Odoo may later appear in purchase activity from other companies. However, product names may differ between Odoo and Wansoft, or even between Odoo companies.

Because of this, the pipeline must avoid assuming that two products are equivalent only because their names are similar.

---

## Core Decision

The project will **not** create an automatic product alias dictionary at this stage.

This means the pipeline will not automatically infer that:

```text
Odoo Product A = Odoo Product B = Wansoft Product X
```

based only on product name similarity.

---

## Mapping Rule

### Case 1: Product has a Wansoft reference/code

If a new Odoo product has a valid Wansoft reference or can be explicitly mapped through the approved inventory dictionary, then it may be linked to the Wansoft product governance layer.

Expected flow:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
```

If the product exists in:

```text
inventory_mapping_dictionary
```

with:

```text
mapping_status = approved
```

then the purchase line can be considered mapped.

---

### Case 2: Product does not have a Wansoft reference/code

If a new Odoo product does not have a Wansoft reference or an approved mapping, it must be treated as a new product.

Expected behavior:

```text
product_mapping_found = 0
purchase_mapping_bucket = unmapped_inventory_candidate
```

The product should remain in the purchase inventory mapping backlog for review.

It should not be automatically mapped to another product based only on name similarity.

---

## Why Automatic Aliases Are Not Used

Automatic aliases can create risks such as:

- mapping two different products as if they were the same
- mixing costs from non-equivalent products
- polluting inventory valuation
- hiding catalog duplication issues
- incorrectly linking products across companies
- creating operational confusion between purchasing, inventory, and sales

For example, these products may look similar but should not be automatically treated as equivalent:

```text
Rib Eye
Rib Eye CAB
Rib Eye Lipon
Rib Eye (Bife de Chorizo)
Short Rib
Back Rib
```

They may differ by:

- supplier
- cut/specification
- unit of measure
- packaging
- purchasing use
- inventory use
- sales/use in recipes
- cost behavior

Because of this, similarity alone is not enough.

---

## Approved Mapping Source

The approved source for product mapping remains:

```text
inventory_mapping_dictionary
```

This dictionary is the controlled governance layer for linking Odoo products to Wansoft product references.

---

## Purchases Mapping Flow

The Purchases ETL should resolve product mapping in this order:

```text
1. Read purchase.order.line.product_id
2. Check inventory_mapping_dictionary
3. If approved mapping exists:
       mark line as mapped_inventory
4. If no approved mapping exists:
       classify the line by operational scope
5. If classified as inventory_candidate:
       send to odoo_purchase_inventory_mapping_backlog
```

---

## Backlog Treatment

Products without an approved mapping are reviewed through:

```text
odoo_purchase_inventory_mapping_backlog
```

This backlog is deduplicated by:

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
```

This allows manual review based on business impact.

---

## Expected Buckets

Purchase lines may be classified into:

```text
mapped_inventory
inventory_candidate
sales_reference_candidate
bodegon_candidate
empanadas_candidate
operational_non_inventory_candidate
empty_line
manual_review
```

Only this bucket is considered a candidate for inventory dictionary review:

```text
inventory_candidate
```

---

## Policy For New Odoo Products

When a new Odoo product appears:

### If it has an approved Wansoft mapping

It can be used normally in the pipeline as a mapped product.

### If it does not have an approved Wansoft mapping

It should be considered a new product and remain in backlog.

No automatic alias should be created.

---

## Policy For Products With Different Names

If a product has a different name but the same explicit Wansoft reference/code, it may be mapped through the dictionary.

If it has a different name and no explicit Wansoft reference/code, it should not be automatically matched.

The product should stay in backlog until reviewed.

---

## No Alias Dictionary Decision

The following table will **not** be created at this stage:

```text
inventory_product_alias_dictionary
```

Reason:

```text
Product equivalence should be governed by explicit references and approved dictionary mappings, not inferred name similarity.
```

This decision can be revisited later if the business requires alias governance, but it is intentionally excluded from the current baseline.

---

## Practical Example

### Valid mapped scenario

```text
Odoo product:
Rib Eye (Bife de Chorizo)

Approved dictionary:
odoo_product_id → wansoft_code

Result:
mapped_inventory
```

---

### New product scenario

```text
Odoo product:
Rib Eye Special New Branch

No approved dictionary row
No explicit Wansoft reference

Result:
unmapped_inventory_candidate
```

The product stays in:

```text
odoo_purchase_inventory_mapping_backlog
```

until reviewed.

---

## ETL Responsibility

The ETL is responsible for:

```text
1. Detecting whether a product has an approved mapping
2. Classifying unmapped product lines
3. Sending inventory candidates to backlog
4. Avoiding automatic alias creation
```

The ETL should not:

```text
1. Infer product equivalence only by name
2. Create automatic aliases
3. Promote products automatically to the dictionary
4. Modify Odoo product records
```

---

## Governance Principle

The project follows this principle:

```text
Explicit reference beats name similarity.
```

A product should only be considered mapped if there is a trusted reference or an approved dictionary row.

---

## Related Tables

```text
inventory_mapping_dictionary
odoo_purchase_order_line_snapshot
odoo_purchase_inventory_mapping_backlog
odoo_inventory_scope_classification
```

---

## Related Documentation

```text
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
```

---

## Current Status

This policy is active for the Purchases domain.

No automatic product alias table will be implemented at this stage.

Unmapped inventory candidates will continue to be reviewed through:

```text
odoo_purchase_inventory_mapping_backlog
```

---

## Next Step

Continue with the purchase inventory backlog review flow.

Recommended next step:

```text
Analyze odoo_purchase_inventory_mapping_backlog against inventory scope and decide which products should be promoted to inventory_mapping_dictionary.
```