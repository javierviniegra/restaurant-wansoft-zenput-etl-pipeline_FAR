# Purchases Company Migration Policy

## Purpose

This document defines the company-level source governance policy for the Purchases domain during the Wansoft to Odoo transition.

The purpose of this policy is to prevent premature replacement of Wansoft data with Odoo data while preserving historical continuity and source traceability.

The policy applies to:

```text
Purchases
Inventory
Canonical purchase tables
Odoo purchase snapshots
Wansoft purchase-like inputs
```

This policy does not apply to Sales because Sales always remains Wansoft.

---

## Core Principle

The authoritative source selector is:

```text
core/config/companies.py
```

The key configuration is:

```python
COMPANY_SOURCE
```

Main rule:

```text
COMPANY_SOURCE determines the official source system by operating company.
```

`operational_start_date` does not decide whether a company uses Odoo or Wansoft.

`operational_start_date` only applies after `COMPANY_SOURCE` marks the company as Odoo.

---

## Domain Source Rules

The project uses the following source rules:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

Meaning:

```text
Sales does not switch to Odoo.
Purchases switch by company according to COMPANY_SOURCE.
Inventory switches by company according to COMPANY_SOURCE.
```

---

## Source Governance Hierarchy

The source selection hierarchy is:

```text
1. COMPANY_SOURCE
2. odoo_company_migration_policy.operational_start_date
3. .env fallback dates
```

### 1. COMPANY_SOURCE

`COMPANY_SOURCE` is the authoritative source selector.

Example:

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

If a company is marked as:

```text
wansoft
```

then Wansoft remains the official final source for Purchases and Inventory.

If a company is marked as:

```text
odoo
```

then Odoo becomes the official final source for Purchases and Inventory from the configured operational start date.

---

### 2. operational_start_date

`operational_start_date` defines the valid Odoo start date for companies that are already configured as Odoo-source.

Correct interpretation:

```text
If COMPANY_SOURCE = 'odoo':
    operational_start_date defines when Odoo becomes final.

If COMPANY_SOURCE = 'wansoft':
    operational_start_date does not switch the company to Odoo.
```

---

### 3. .env fallback

`.env` date parameters are fallback values only.

Examples:

```env
PURCHASE_ETL_MIN_ORDER_DATE=2026-06-01
PURCHASE_ETL_MIN_RECEIPT_DATE=2026-06-01
```

These values should not override company-specific governance.

---

## Current Source Status

Current validated company source behaviour:

```text
Antenas:
    Purchases -> Odoo
    Inventory -> Odoo
    Sales -> Wansoft

All other configured companies:
    Purchases -> Wansoft
    Inventory -> Wansoft
    Sales -> Wansoft
```

---

## Antenas Source Split

Antenas is currently the active Odoo-source company for Purchases.

Validated behaviour:

```text
Antenas Wansoft:
    historical purchases before 2026-06-01

Antenas Odoo:
    final purchases from 2026-06-01 onward
```

Validated canonical ranges:

```text
Wansoft Antenas max_order_date: 2026-05-31 22:51:54
Odoo Antenas min_order_date: 2026-06-01 16:10:54
```

This confirms:

```text
Wansoft does not invade the Odoo period for Antenas.
Odoo does not replace Wansoft history before the operational start date.
```

---

## Company Migration Policy Table

The company migration policy is stored in:

```text
odoo_company_migration_policy
```

This table stores metadata such as:

```text
company_name
company_migration_type
history_source
include_odoo_history
operational_start_date
is_active
```

The policy table is used to determine valid date boundaries, not to override `COMPANY_SOURCE`.

---

## Company Migration Types

### migrated_from_wansoft

Used for companies that had historical operations in Wansoft and later begin operating in Odoo.

Expected behaviour:

```text
Wansoft remains historical source.
Odoo starts at operational_start_date.
```

Typical configuration:

```text
company_migration_type = migrated_from_wansoft
history_source = wansoft
include_odoo_history = 0
```

---

### new_odoo_branch

Used for companies that start directly in Odoo.

Expected behaviour:

```text
Odoo is the source from operational_start_date.
```

Typical configuration:

```text
company_migration_type = new_odoo_branch
history_source = odoo
include_odoo_history = 1
```

---

## Odoo Company Name Mapping

Odoo company names are mapped to operational company keys used by `COMPANY_SOURCE`.

Validated mappings:

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

Important corrections:

```text
FONDA ARGENTINA MAQ -> Tepeyac
FONDA COSTA NERA -> Acoxpa
```

---

## Wansoft Subsidiary Mapping

Wansoft subsidiary mapping is derived from:

```python
CUENTAS_SUCURSALES
```

The derived mapping is:

```python
WANSOFT_SUBSIDIARY_SOURCE_KEY = {
    str(subsidiary_id): company_name
    for subsidiary_id, company_name, _password in CUENTAS_SUCURSALES
}
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

This avoids maintaining a second manual mapping dictionary.

---

## Internal Provider Companies

Some Odoo companies exist for intercompany/provider workflows but should not be treated as final operating branches.

Current internal provider companies:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

These companies may exist in Odoo because they participate in intercompany or provider flows.

However, for Grupo Fonda Argentina canonical BI facts:

```text
They are not final operating branches.
They are treated as internal providers.
```

---

## Internal Provider Rules

### Rule 1: Exclude as company_name

If an internal provider appears as the buying or operating company:

```text
company_name = EL BODEGON DE FITO
company_name = LAS EMPANADAS DE MARIA EVA
```

then the row is excluded from final branch-level canonical facts.

---

### Rule 2: Keep as vendor_name

If an internal provider appears as the supplier/vendor:

```text
vendor_name = EL BODEGON DE FITO
vendor_name = LAS EMPANADAS DE MARIA EVA
```

then the row is kept if the buying company is a valid final company.

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
vendor_name  = external supplier

Result:
    exclude row from final branch-level canonical facts
```

---

## Purchases Canonical Source Status

The canonical purchase layer uses `final_purchase_source_status` to explain why a row is included or excluded.

### final_odoo_enabled

Used when:

```text
source_system = odoo
company source = odoo
company is final-eligible
```

Current example:

```text
Antenas Odoo purchases from 2026-06-01 onward.
```

---

### final_wansoft_enabled

Used when:

```text
source_system = wansoft
company source = wansoft
company is final-eligible
```

Current example:

```text
Acoxpa
Aeropuerto
Isabel La Católica
Oceanía
Tepeyac
Puebla
Cancun
```

---

### wansoft_history_before_odoo

Used when:

```text
source_system = wansoft
company source = odoo
row date is before operational_start_date
```

Current example:

```text
Antenas Wansoft purchases before 2026-06-01.
```

---

### exclude_after_odoo_start

Used when:

```text
source_system = wansoft
company source = odoo
row date is greater than or equal to operational_start_date
```

These rows are excluded from final canonical purchases.

---

### exclude_internal_provider

Used when:

```text
company_name is an internal provider company
```

These rows are excluded from final branch-level canonical facts.

---

### unknown_source_review

Used when:

```text
company could not be resolved to a known source key
```

These rows should not be loaded to final canonical facts until mapping is corrected.

---

## Purchases Canonical Behaviour

The Purchases canonical layer supports:

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

Current validated behaviour:

```text
Antenas:
    Wansoft historical purchases before Odoo operational start date
    Odoo final purchases from Odoo operational start date onward

Other Wansoft companies:
    Wansoft remains the final purchase source

Internal providers:
    excluded as company_name
    allowed as vendor_name
```

---

## Current Validated Counts

### Odoo canonical load

```text
orders_inserted: 282
lines_inserted: 1381
receipts_inserted: 268
receipt_moves_inserted: 1184
```

### Wansoft canonical load

```text
orders_inserted: 145047
lines_inserted: 745344
receipts_inserted: 145047
receipt_moves_inserted: 745344
```

### Wansoft status summary

```text
final_wansoft_enabled        693059
wansoft_history_before_odoo   52285
```

---

## Validation Queries

### 1. Validate Antenas source split

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

Expected:

```text
odoo     Antenas    final_odoo_enabled
wansoft  Antenas    wansoft_history_before_odoo
```

---

### 2. Validate Wansoft final-source companies

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
ORDER BY total_lines DESC;
```

Expected:

```text
Companies configured as Wansoft should appear as final_wansoft_enabled.
Antenas may appear only as wansoft_history_before_odoo.
```

---

### 3. Validate internal providers as vendors

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
ORDER BY total_lines DESC;
```

Expected:

```text
Rows may appear.
```

Reason:

```text
Internal providers are valid vendors.
```

---

### 4. Validate internal providers are not final companies

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

Expected:

```text
0 rows
```

---

## ETL Entrypoints

### Company source governance

```bash
python -m scripts.test_company_source_governance
```

### Odoo source eligibility

```bash
python -m scripts.test_purchase_company_source_eligibility
```

### Odoo canonical purchase load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

### Wansoft subsidiary mapping report

```bash
python -m scripts.test_wansoft_purchase_subsidiary_mapping_report
```

### Wansoft canonical purchase load

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

---

## Files Related to This Policy

```text
core/config/companies.py
wansoft.sql
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
docs/purchases-company-migration-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
```

---

## Known Design Decisions

### 1. COMPANY_SOURCE is authoritative

The source system is not inferred from available data.

Even if Odoo contains records for a company, those rows do not become final unless `COMPANY_SOURCE` marks the company as Odoo.

---

### 2. operational_start_date does not switch companies

`operational_start_date` only defines the valid Odoo starting date for companies already configured as Odoo-source.

---

### 3. Sales always remain Wansoft

Sales does not follow `COMPANY_SOURCE`.

Sales remains Wansoft even when Purchases or Inventory use Odoo for a company.

---

### 4. Internal providers are excluded only as companies

Bodegón and Empanadas are not final operating branches.

They may remain valid vendors.

---

### 5. Wansoft historical data is preserved

When a company switches to Odoo, Wansoft data before the operational start date remains historical and valid.

---

## Current Status

This policy is active.

Validated:

```text
COMPANY_SOURCE governance
Antenas Odoo source
Antenas Wansoft history before Odoo
Wansoft final-source companies
internal providers as vendors
internal providers excluded as companies
canonical purchase layer source split
```

---

## Related Documentation

```text
docs/project-technical-guide.md
docs/purchases-canonical-layer.md
docs/purchases-product-mapping-policy.md
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