# Purchases Canonical Layer

## Purpose

This document describes the canonical purchase layer used to combine Wansoft and Odoo purchase data into a single BI-ready structure.

The canonical layer is designed to keep both systems traceable during the Odoo transition while avoiding duplicated or premature source replacement.

The core objective is:

```text
technical source snapshots
→ source governance
→ canonical purchase layer
→ BI / reporting / analysis
```

---

## Business Context

During the Odoo transition, purchases and inventory operations may exist in both Wansoft and Odoo.

However, not all Odoo activity should immediately replace Wansoft in final reporting. Some companies may still use Wansoft as the official source, while specific companies may already use Odoo as their official source.

Because of this, the project uses a controlled source selector:

```text
core/config/companies.py
```

The canonical purchase layer applies that source governance consistently.

---

## Source Systems

The canonical purchase layer currently supports:

```text
source_system = 'odoo'
source_system = 'wansoft'
```

Each source is loaded separately and remains traceable through:

```text
source_system
source_domain
company_source_key
final_purchase_source_status
```

---

## Canonical Tables

The canonical purchase layer is stored in four tables:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

These tables are final BI-ready structures, not raw extraction tables.

---

## Source Snapshots vs Canonical Tables

### Odoo technical snapshots

Odoo purchase data is first loaded into technical snapshot tables:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

These tables preserve the technical Odoo extraction and migration-policy metadata.

### Canonical purchase tables

The canonical layer receives only the rows that are allowed to feed final reporting.

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

The canonical layer should be consumed by Power BI and downstream analytics.

---

## Source Governance

The source selector is defined in:

```text
core/config/companies.py
```

The key configuration is:

```python
COMPANY_SOURCE = {
    "Acoxpa": "wansoft",
    "Aeropuerto": "wansoft",
    "Isabel La Católica": "wansoft",
    "Antenas": "odoo",
    "Taquería parroquia": "wansoft",
    "Vía Vallejo": "wansoft",
    "Viaducto": "wansoft",
    "Taquería Viaducto": "wansoft",
    "San Jeronimo": "wansoft",
    "Tepeyac": "wansoft",
    "Playa del Carmen": "wansoft",
    "Oceanía": "wansoft",
    "Cancun": "wansoft",
    "Napoles": "wansoft",
    "Metepec": "wansoft",
    "Versalles": "wansoft",
    "La Esquina Coyoacán": "wansoft",
    "CentroMyJ": "wansoft",
    "Puebla": "wansoft",
}
```

---

## Domain Source Rules

The project uses these source rules:

```text
sales      → always Wansoft
purchases  → COMPANY_SOURCE
inventory  → COMPANY_SOURCE
```

This means:

```text
Sales does not switch to Odoo.
Purchases switch by company according to COMPANY_SOURCE.
Inventory switches by company according to COMPANY_SOURCE.
```

---

## Operational Start Date Rule

The `operational_start_date` from `odoo_company_migration_policy` does not override `COMPANY_SOURCE`.

The correct rule is:

```text
COMPANY_SOURCE determines whether the company officially uses Odoo or Wansoft.
operational_start_date only applies when COMPANY_SOURCE = 'odoo'.
```

Example:

```text
Antenas:
    COMPANY_SOURCE = odoo
    Wansoft before operational_start_date is historical
    Odoo from operational_start_date onward is final

Oceanía:
    COMPANY_SOURCE = wansoft
    Odoo activity remains technical snapshot only
    Wansoft remains final source
```

---

## Odoo Company Mapping

Odoo company names are mapped to operational source keys.

Examples:

```text
FONDA ARGENTINA LAS ANTENAS -> Antenas
FONDA ARGENTINA ENCUENTRO OCEANIA -> Oceanía
FONDA ARGENTINA SAN JERONIMO -> San Jeronimo
FONDA ARGENTINA PUEBLA -> Puebla
FONDA ARGENTINA COYOACAN -> La Esquina Coyoacán
FONDA ARGENTINA MAQ -> Tepeyac
FONDA COSTA NERA -> Acoxpa
FONDA ARGENTINA -> Isabel La Católica
MARIO Y JULY -> CentroMyJ
```

---

## Wansoft Subsidiary Mapping

Wansoft company mapping is derived from:

```python
CUENTAS_SUCURSALES
```

The derived dictionary is:

```python
WANSOFT_SUBSIDIARY_SOURCE_KEY = {
    str(subsidiary_id): company_name
    for subsidiary_id, company_name, _password in CUENTAS_SUCURSALES
}
```

Examples:

```text
4960 -> Antenas
6175 -> Cancun
5320 -> Acoxpa
6560 -> Tepeyac
5943 -> Oceanía
12806 -> Puebla
```

This prevents maintaining two separate sources of truth for Wansoft subsidiary ids.

---

## Internal Provider Companies

Some Odoo companies exist because of intercompany or provider workflows, but they should not be treated as final operating branches.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

Rules:

```text
If company_name is an internal provider:
    exclude from final canonical branch-level facts

If vendor_name is an internal provider:
    keep the row if the buying company is a valid final company
```

Correct example:

```text
company_name = FONDA ARGENTINA LAS ANTENAS
vendor_name  = EL BODEGON DE FITO

Result:
    keep row
```

Incorrect example:

```text
company_name = EL BODEGON DE FITO

Result:
    exclude row from final branch-level canonical facts
```

---

## Odoo Canonical Load

Odoo canonical load is implemented in:

```text
extract/purchases/canonical_purchase_etl.py
```

Main entrypoint:

```python
run_canonical_purchase_odoo_etl()
```

The Odoo canonical load reads from:

```text
odoo_purchase_order_snapshot
odoo_purchase_order_line_snapshot
odoo_purchase_receipt_snapshot
odoo_purchase_receipt_move_snapshot
```

It applies company source governance and keeps only rows where:

```text
final_purchase_source_status = 'final_odoo_enabled'
```

For the current configuration, Odoo eligible rows belong to:

```text
company_source_key = Antenas
source_system = odoo
final_purchase_source_status = final_odoo_enabled
```

---

## Wansoft Canonical Load

Wansoft canonical load is implemented in:

```text
extract/purchases/canonical_purchase_etl.py
```

Main entrypoint:

```python
run_canonical_purchase_wansoft_etl()
```

The Wansoft source table is:

```text
getinputinventory_entrada
```

The source filter is:

```sql
WHERE TipoEntrada = 'Factura'
```

This table is treated as the reliable Wansoft purchase-like source because it represents inventory inputs related to invoices or supplier entries.

---

## Wansoft Date Fields

The load uses:

```text
FechaEntrada
```

as the operational purchase/input date.

The field:

```text
FechaReal
```

is preserved as the Wansoft upload or capture reference date when available.

---

## Wansoft Load Status Values

The Wansoft load classifies rows into source-status categories.

### final_wansoft_enabled

Used when the company remains a Wansoft final-source company.

```text
domain_source = wansoft
```

### wansoft_history_before_odoo

Used when the company is now Odoo-source, but the Wansoft row belongs to the historical period before the Odoo operational start date.

Example:

```text
Antenas Wansoft rows before 2026-06-01
```

### exclude_after_odoo_start

Used when the company is Odoo-source and the Wansoft row belongs to or after the Odoo operational start date.

These rows are not loaded to the canonical layer.

### unknown_source_review

Used when the company cannot be resolved to a known source key.

These rows are excluded from final load until mapping is corrected.

---

## Wansoft Technical Keys

Wansoft rows may contain invoice, provider and date values that are not safe as direct unique database keys because of:

```text
case-insensitive MySQL collation
trailing spaces
long natural keys
inconsistent invoice casing
duplicate invoice references
```

Therefore, Wansoft canonical technical keys use stable hashed identifiers.

### Order key

```text
source_order_id = wansoft_order:{company_key}:{fecha_key}:{hash}
```

Example shape:

```text
wansoft_order:acoxpa:2023-03-29:4f7c2a9b8d0e12aa
```

### Receipt key

```text
source_receipt_id = wansoft_receipt:{company_key}:{fecha_key}:{hash}
```

### Line key

```text
source_order_line_id = wansoft_line:{id}
```

If the row id is not available, a stable hash is used.

### Receipt movement key

```text
source_stock_move_id = wansoft_move:{id}
```

If the row id is not available, a stable hash is used.

Natural business values remain available in business columns such as:

```text
purchase_order_name
vendor_id
vendor_name
wansoft_code
wansoft_product_name
order_date
```

---

## Canonical Table Mapping

### Wansoft to canonical_purchase_order_snapshot

Wansoft does not provide a complete native historical purchase-order header equivalent to Odoo `purchase.order`.

Therefore, Wansoft order headers are derived from inventory invoice input documents.

| Wansoft field | Canonical field |
|---|---|
| Derived hash key | source_order_id |
| Factura | purchase_order_name |
| RFCProveedor or ClaveProveedor | vendor_id |
| NombreProveedor | vendor_name |
| subsidiary_name | company_id |
| company_source_key | company_source_key |
| FechaEntrada | order_date |
| FechaReal | approval_date |
| SUM(Cantidad * CostoUnitario) | amount_total |
| fixed value `wansoft` | source_system |

---

### Wansoft to canonical_purchase_order_line_snapshot

Each Wansoft `getinputinventory_entrada` row is treated as a purchase line.

| Wansoft field | Canonical field |
|---|---|
| id | source_order_line_id |
| Derived document key | source_order_id |
| Factura | purchase_order_name |
| RFCProveedor or ClaveProveedor | vendor_id |
| NombreProveedor | vendor_name |
| subsidiary_name | company_id |
| company_source_key | company_source_key |
| IdProducto | product_id |
| NombreProducto | product_name |
| CodigoProducto | wansoft_code |
| NombreProducto | wansoft_product_name |
| Departamento | wansoft_department |
| Cantidad | product_qty |
| Cantidad | qty_received |
| CostoUnitario | price_unit |
| Cantidad * CostoUnitario | price_total |
| FechaEntrada | order_date |

---

### Wansoft to canonical_purchase_receipt_snapshot

Derived receipt headers are created from the same Wansoft invoice/input document identity.

| Wansoft field | Canonical field |
|---|---|
| Derived receipt key | source_receipt_id |
| Factura | receipt_name |
| Derived order key | origin |
| RFCProveedor or ClaveProveedor | vendor_id |
| NombreProveedor | vendor_name |
| subsidiary_name | company_id |
| company_source_key | company_source_key |
| FechaEntrada | scheduled_date |
| FechaReal | date_done |
| fixed value `done` | state |

---

### Wansoft to canonical_purchase_receipt_move_snapshot

Each Wansoft `getinputinventory_entrada` row is also treated as a receipt movement.

| Wansoft field | Canonical field |
|---|---|
| id | source_stock_move_id |
| Factura | reference |
| Derived order key | origin |
| Derived receipt key | source_receipt_id |
| id or hash | source_order_line_id |
| IdProducto | product_id |
| NombreProducto | product_name |
| CodigoProducto | wansoft_code |
| NombreProducto | wansoft_product_name |
| Departamento | wansoft_department |
| Cantidad | product_uom_qty |
| Cantidad | quantity |
| IdUnidadDeMedida | product_uom_id |
| UnidadDeMedida | product_uom_name |
| FechaEntrada | move_date |
| FechaReal | date_deadline |

---

## Odoo Canonical Validation Results

The Odoo canonical load produced:

```text
orders_inserted: 282
lines_inserted: 1381
receipts_inserted: 268
receipt_moves_inserted: 1184
```

Current Odoo final status:

```text
source_system = odoo
company_source_key = Antenas
final_purchase_source_status = final_odoo_enabled
```

---

## Wansoft Canonical Validation Results

The Wansoft canonical load produced:

```text
orders_inserted: 145047
lines_inserted: 745344
receipts_inserted: 145047
receipt_moves_inserted: 745344
```

Wansoft source status summary:

```text
final_wansoft_enabled        693059
wansoft_history_before_odoo   52285
```

Antenas validation:

```text
Wansoft Antenas:
    min_order_date = 2021-09-04 14:19:30
    max_order_date = 2026-05-31 22:51:54
    total_lines = 52285

Odoo Antenas:
    min_order_date = 2026-06-01 16:10:54
    max_order_date = 2026-07-07 20:16:46
    total_lines = 1381
```

This confirms that Wansoft does not overlap the Odoo period for Antenas.

---

## Final Source Behaviour

The canonical layer now supports both systems:

```text
source_system = odoo
source_system = wansoft
```

Current behaviour:

```text
Antenas:
    Wansoft before Odoo operational start date
    Odoo from Odoo operational start date onward

All other configured Wansoft companies:
    Wansoft remains final source

Internal providers:
    excluded as company_name
    allowed as vendor_name
```

---

## Validation Queries

### 1. Source-system coexistence

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
    source_system,
    company_source_key;
```

---

### 2. Antenas source split

```sql
SELECT
    source_system,
    company_source_key,
    final_purchase_source_status,
    MIN(order_date) AS min_order_date,
    MAX(order_date) AS max_order_date,
    COUNT(*) AS total_lines,
    SUM(COALESCE(price_total, 0)) AS total_amount
FROM canonical_purchase_order_line_snapshot
WHERE company_source_key = 'Antenas'
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status
ORDER BY
    source_system,
    final_purchase_source_status;
```

---

### 3. Wansoft final-source companies

```sql
SELECT
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_lines,
    SUM(COALESCE(price_total, 0)) AS total_amount
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft'
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status
ORDER BY
    total_lines DESC;
```

---

### 4. Internal providers as vendors

```sql
SELECT
    source_system,
    vendor_name,
    company_name,
    company_source_key,
    COUNT(*) AS total_lines,
    SUM(COALESCE(price_total, 0)) AS total_amount
FROM canonical_purchase_order_line_snapshot
WHERE vendor_name IN (
    'EL BODEGON DE FITO',
    'LAS EMPANADAS DE MARIA EVA'
)
GROUP BY
    source_system,
    vendor_name,
    company_name,
    company_source_key
ORDER BY
    total_lines DESC;
```

---

### 5. Internal providers not as final companies

```sql
SELECT
    source_system,
    company_name,
    COUNT(*) AS total_lines
FROM canonical_purchase_order_line_snapshot
WHERE company_name IN (
    'EL BODEGON DE FITO',
    'LAS EMPANADAS DE MARIA EVA'
)
GROUP BY
    source_system,
    company_name;
```

Expected result:

```text
0 rows
```

---

### 6. Wansoft Antenas cutoff validation

```sql
SELECT
    source_system,
    company_source_key,
    final_purchase_source_status,
    MIN(order_date) AS min_order_date,
    MAX(order_date) AS max_order_date,
    COUNT(*) AS total_lines
FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft'
  AND company_source_key = 'Antenas'
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status;
```

Expected result:

```text
max_order_date < Odoo operational start date
```

---

## ETL Entrypoints

### Odoo canonical load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

Entrypoint:

```python
run_canonical_purchase_odoo_etl()
```

---

### Wansoft canonical load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

Entrypoint:

```python
run_canonical_purchase_wansoft_etl()
```

---

## Known Design Decisions

### 1. Wansoft purchase headers are derived

Wansoft does not provide the same historical purchase-order structure that Odoo provides.

Therefore, the canonical Wansoft purchase order table is derived from `getinputinventory_entrada` invoice input rows.

### 2. Wansoft uses hashed technical keys

Natural invoice keys are not used directly as database unique identifiers because of possible text inconsistencies and MySQL collation behaviour.

### 3. Odoo and Wansoft are loaded independently

Odoo rows and Wansoft rows are deleted and reloaded independently by `source_system`.

When Wansoft is reloaded:

```text
source_system = odoo
```

rows are preserved.

When Odoo is reloaded:

```text
source_system = wansoft
```

rows are preserved.

### 4. Internal providers are excluded only as final companies

Internal providers remain valid vendors.

They are excluded only when they appear as the buying or operating company.

### 5. Antenas is the first active Odoo purchase source

Current canonical logic validates:

```text
Antenas Wansoft history before 2026-06-01
Antenas Odoo final source from 2026-06-01
```

---

## Current Status

The canonical purchase layer is active and validated.

Completed:

```text
Odoo canonical load
Wansoft canonical load
COMPANY_SOURCE governance
Antenas source split
Internal provider handling
Wansoft technical key collision fix
Validation SQL
```

---

## Related Documentation

```text
docs/project-technical-guide.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/wansoft-local-wsdl.md
```

---

## Recommended Commit

```bash
git add docs/purchases-canonical-layer.md

git commit -m "docs(purchases): document canonical purchase layer"

git push
```