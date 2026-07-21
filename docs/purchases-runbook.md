# Purchases Runbook

## Purpose

This runbook explains how to operate, validate, and troubleshoot the Purchases domain ETL.

It is intended for day-to-day execution and technical validation of:

```text
Odoo purchase snapshots
Odoo purchase receipts
Odoo purchase receipt moves
purchase product mapping
purchase inventory backlog
company source governance
canonical purchase layer
Wansoft canonical purchase load
```

This document is operational. For architecture and design, refer to:

```text
docs/project-technical-guide.md
docs/purchases-canonical-layer.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
```

---

## Current Purchases Architecture

The Purchases domain is built in layers:

```text
Odoo extraction
    ↓
Odoo purchase snapshots
    ↓
product mapping and classification
    ↓
purchase inventory mapping backlog
    ↓
Odoo canonical purchase load

Wansoft getinputinventory_entrada
    ↓
TipoEntrada = 'Factura'
    ↓
Wansoft subsidiary mapping
    ↓
COMPANY_SOURCE governance
    ↓
Wansoft canonical purchase load

Odoo + Wansoft
    ↓
canonical_purchase_* tables
```

---

## Source Governance Rules

Purchases follow company-level source governance from:

```text
core/config/companies.py
```

Main rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

For Purchases:

```text
If COMPANY_SOURCE = 'odoo':
    Odoo is the final source from operational_start_date onward.
    Wansoft is preserved only before operational_start_date.

If COMPANY_SOURCE = 'wansoft':
    Wansoft remains the final source.

If company_name is an internal provider:
    exclude from final branch-level facts.

If vendor_name is an internal provider:
    keep the row if the buying company is final-eligible.
```

---

## Current Internal Providers

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

These companies may appear as vendors, but they should not appear as final operating companies.

---

## Current Validated Source Split

Current validated behaviour:

```text
Antenas:
    Wansoft historical purchases before 2026-06-01
    Odoo final purchases from 2026-06-01 onward

Other Wansoft companies:
    Wansoft remains the final purchase source
```

---

# Execution Order

Run the Purchases domain in this order.

---

## 1. Validate company source governance

```bash
python -m scripts.test_company_source_governance
```

Expected checks:

```text
Antenas:
    sales      -> wansoft
    purchases  -> odoo
    inventory  -> odoo

FONDA ARGENTINA MAQ:
    source_key -> Tepeyac

FONDA COSTA NERA:
    source_key -> Acoxpa

EL BODEGON DE FITO:
    purchases  -> internal_provider
    inventory  -> internal_provider
    include_final -> False

LAS EMPANADAS DE MARIA EVA:
    purchases  -> internal_provider
    inventory  -> internal_provider
    include_final -> False
```

---

## 2. Run Odoo purchase order and line ETL

```bash
python -m scripts.test_odoo_purchase_etl
```

This loads:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
```

Expected behaviour:

```text
purchase.order extracted
purchase.order.line extracted
company migration policy applied
purchase line classification applied
product mapping applied
```

---

## 3. Run Odoo purchase receipt ETL

```bash
python -m scripts.test_odoo_purchase_receipt_etl
```

This loads:

```text
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

Expected behaviour:

```text
stock.picking incoming extracted
stock.move receipt movements extracted
company migration policy applied
receipt and movement snapshots saved
```

---

## 4. Build purchase inventory mapping backlog

```bash
python -m scripts.test_purchase_inventory_mapping_backlog
```

This loads:

```text
odoo_purchase_inventory_mapping_backlog
```

Expected behaviour:

```text
unmapped inventory candidates are grouped by product
new products without explicit reference remain in backlog
no automatic aliases are created
```

Current validated rule:

```text
Explicit reference beats name similarity.
```

---

## 5. Validate purchase backlog product references

```bash
python -m scripts.test_purchase_backlog_product_reference_report
```

Expected output:

```text
REFERENCE SUMMARY
SAMPLE WITH REFERENCE
SAMPLE WITHOUT REFERENCE
```

Current validated result:

```text
new_product_no_reference = 233 products
has_reference_candidate = 0 products
```

Interpretation:

```text
Products without explicit Odoo/Wansoft reference are treated as new products.
They remain in backlog.
They are not automatically matched by similar name.
```

---

## 6. Validate company source eligibility for Odoo purchases

```bash
python -m scripts.test_purchase_company_source_eligibility
```

Expected output:

```text
COMPANY SOURCE ELIGIBILITY SUMMARY
FINAL ODOO SAMPLE: ORDERS
FINAL ODOO SAMPLE: LINES
FINAL ODOO SAMPLE: RECEIPTS
FINAL ODOO SAMPLE: RECEIPT_MOVES
```

Expected statuses:

```text
FONDA ARGENTINA LAS ANTENAS:
    final_odoo_enabled

EL BODEGON DE FITO:
    exclude_internal_provider

LAS EMPANADAS DE MARIA EVA:
    exclude_internal_provider

FONDA COSTA NERA:
    wansoft_only

FONDA ARGENTINA MAQ:
    wansoft_only
```

---

## 7. Run Odoo canonical purchase load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

This loads Odoo-eligible rows into:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

Expected current validated counts:

```text
orders_inserted: 282
lines_inserted: 1381
receipts_inserted: 268
receipt_moves_inserted: 1184
```

Expected source status:

```text
source_system = odoo
company_source_key = Antenas
final_purchase_source_status = final_odoo_enabled
```

---

## 8. Validate Wansoft subsidiary mapping

```bash
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
```

This validates mapping from:

```text
getinputinventory_entrada.subsidiary_name
```

to:

```text
company_source_key
```

through:

```text
WANSOFT_SUBSIDIARY_SOURCE_KEY
```

which is derived from:

```text
CUENTAS_SUCURSALES
```

Expected validated mappings:

```text
4960 -> Antenas
6175 -> Cancun
5320 -> Acoxpa
6560 -> Tepeyac
5943 -> Oceanía
12806 -> Puebla
```

Expected status:

```text
No relevant missing_subsidiary_mapping rows.
```

---

## 9. Run Wansoft canonical purchase load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

This reads:

```text
getinputinventory_entrada
```

using:

```sql
WHERE TipoEntrada = 'Factura'
```

and loads Wansoft rows into:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

Expected current validated counts:

```text
orders_inserted: 145047
lines_inserted: 745344
receipts_inserted: 145047
receipt_moves_inserted: 745344
```

Expected status summary:

```text
final_wansoft_enabled        693059
wansoft_history_before_odoo   52285
```

---

# Canonical Validation Queries

Run these queries after Odoo and Wansoft canonical loads.

---

## 1. Source-system coexistence

```sql
SELECT
    'orders' AS canonical_table,
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_rows
FROM canonical_purchase_order_snapshot
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status

UNION ALL

SELECT
    'lines' AS canonical_table,
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_rows
FROM canonical_purchase_order_line_snapshot
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status

UNION ALL

SELECT
    'receipts' AS canonical_table,
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_rows
FROM canonical_purchase_receipt_snapshot
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status

UNION ALL

SELECT
    'receipt_moves' AS canonical_table,
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_rows
FROM canonical_purchase_receipt_move_snapshot
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status
ORDER BY
    canonical_table,
