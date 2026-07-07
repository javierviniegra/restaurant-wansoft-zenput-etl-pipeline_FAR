# Purchases Company Migration Policy

## Purpose

The `odoo_company_migration_policy` table controls from which date each Odoo company should be included in the Purchases ETL pipeline.

This is required because the Odoo transition contains two different company scenarios:

1. Companies migrated from Wansoft to Odoo
2. New branches that start directly in Odoo

The policy prevents historical Odoo data from being mixed incorrectly with Wansoft historical data.

---

## Business Context

During the Odoo transition, not all companies should be treated the same way.

Some companies already have operational history in Wansoft. For those companies, Wansoft remains the historical source, and Odoo should only be used from the approved operational start date.

Other companies are new branches that begin operations directly in Odoo. For those companies, Odoo is the valid historical source from their operational start date.

This policy allows the ETL to apply the correct cutoff date per company instead of relying only on a global date from `.env`.

---

## Business Rule

### Migrated companies

For companies migrated from Wansoft to Odoo:

- Historical source remains Wansoft
- Odoo data should only be included from the approved operational start date
- Odoo pre-cutoff history is excluded from the analytical pipeline

Configuration:

```text
company_migration_type = migrated_from_wansoft
history_source = wansoft
include_odoo_history = 0
```

---

### New Odoo branches

For new branches that start operations directly in Odoo:

- Historical source is Odoo
- Odoo data is included from the branch operational start date

Configuration:

```text
company_migration_type = new_odoo_branch
history_source = odoo
include_odoo_history = 1
```

---

## Table

```text
odoo_company_migration_policy
```

---

## Main Columns

| Column | Purpose |
|---|---|
| `odoo_company_id` | Odoo company ID |
| `company_name` | Odoo company name |
| `company_migration_type` | Defines whether the company migrated from Wansoft or is a new Odoo branch |
| `history_source` | Defines the official historical data source |
| `include_odoo_history` | Indicates whether Odoo historical data should be included |
| `operational_start_date` | First valid date for ETL inclusion |
| `is_active` | Enables or disables the policy |
| `notes` | Operational or governance notes |

---

## Accepted Values

### `company_migration_type`

```text
migrated_from_wansoft
new_odoo_branch
```

### `history_source`

```text
wansoft
odoo
```

### `include_odoo_history`

```text
0 = Do not include Odoo history before operational_start_date
1 = Include Odoo history from operational_start_date
```

---

## Repository Files

### Schema

```text
wansoft.sql
```

Contains only the table structure:

```sql
CREATE TABLE IF NOT EXISTS odoo_company_migration_policy (...)
```

The schema should only include structural definitions such as:

```sql
CREATE TABLE
ALTER TABLE
ADD COLUMN
ADD KEY
```

---

### Seed

```text
sql/seeds/seed_odoo_company_migration_policy.sql
```

Contains the initial controlled configuration for companies currently detected in the purchases snapshot.

This file can be used to seed the initial policy in a test or production environment after review.

---

### Maintenance / Overrides

```text
sql/maintenance/update_odoo_company_migration_policy.sql
```

Contains controlled examples for safe updates, such as:

- marking a company as a new Odoo branch
- changing an operational start date
- disabling a company policy
- inserting a new company policy

This file should not be executed blindly in production. Copy and execute only the required block for the approved change.

---

## Important Rule

The schema should contain only structure.

The following belongs in schema:

```sql
CREATE TABLE ...
ALTER TABLE ...
ADD COLUMN ...
ADD KEY ...
```

The following does **not** belong in schema:

```sql
UPDATE ...
CASE WHEN ...
runtime classification logic
manual business transformations
```

Runtime logic belongs in ETL code.

Configuration seed and approved changes belong in versioned SQL seed or maintenance files.

---

## ETL Behaviour

The Purchases ETL should filter purchase orders and purchase order lines using this policy.

Expected logic:

```text
If company exists in odoo_company_migration_policy and is_active = 1:
    use operational_start_date from the company policy

If company does not exist in policy:
    use PURCHASE_ETL_MIN_ORDER_DATE from .env as fallback
```

This allows each company to have its own cutoff date.

---

## Current Fallback Configuration

The global fallback value is configured in `.env`:

```env
PURCHASE_ETL_MIN_ORDER_DATE=2026-06-01
PURCHASE_ETL_MIN_RECEIPT_DATE=2026-06-01
```

This fallback is only used when a company does not exist in `odoo_company_migration_policy` or has no active policy.

---

## Recommended Workflow

### 1. Add a migrated company

Use this configuration:

```text
company_migration_type = migrated_from_wansoft
history_source = wansoft
include_odoo_history = 0
```

Example:

```sql
INSERT INTO odoo_company_migration_policy (
    odoo_company_id,
    company_name,
    company_migration_type,
    history_source,
    include_odoo_history,
    operational_start_date,
    is_active,
    notes
)
VALUES (
    999,
    'COMPANY NAME',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-01',
    1,
    'Migrated from Wansoft. Odoo data included only from approved operational start date.'
)
ON DUPLICATE KEY UPDATE
    company_name = VALUES(company_name),
    company_migration_type = VALUES(company_migration_type),
    history_source = VALUES(history_source),
    include_odoo_history = VALUES(include_odoo_history),
    operational_start_date = VALUES(operational_start_date),
    is_active = VALUES(is_active),
    notes = VALUES(notes);
```

---

### 2. Add a new Odoo branch

Use this configuration:

```text
company_migration_type = new_odoo_branch
history_source = odoo
include_odoo_history = 1
```

Example:

```sql
INSERT INTO odoo_company_migration_policy (
    odoo_company_id,
    company_name,
    company_migration_type,
    history_source,
    include_odoo_history,
    operational_start_date,
    is_active,
    notes
)
VALUES (
    999,
    'NEW COMPANY NAME',
    'new_odoo_branch',
    'odoo',
    1,
    '2026-07-07',
    1,
    'New Odoo branch. Odoo history included from operational start date.'
)
ON DUPLICATE KEY UPDATE
    company_name = VALUES(company_name),
    company_migration_type = VALUES(company_migration_type),
    history_source = VALUES(history_source),
    include_odoo_history = VALUES(include_odoo_history),
    operational_start_date = VALUES(operational_start_date),
    is_active = VALUES(is_active),
    notes = VALUES(notes);
```

---

### 3. Update an existing company

Use the maintenance file:

```text
sql/maintenance/update_odoo_company_migration_policy.sql
```

Recommended process:

```text
1. Open the maintenance SQL file
2. Copy only the required block
3. Adjust company name, type, history source and date
4. Execute the block in MySQL
5. Run the validation query
6. Commit the approved change if the SQL file was updated
```

---

## Validation Query

Use this query after seeding or updating the policy:

```sql
SELECT
    odoo_company_id,
    company_name,
    company_migration_type,
    history_source,
    include_odoo_history,
    operational_start_date,
    is_active,
    notes
FROM odoo_company_migration_policy
ORDER BY company_name;
```

---

## Current Initial Policy

The initial policy was seeded from the current purchase snapshot.

Current companies detected in the purchase snapshot include:

```text
EL BODEGON DE FITO
FONDA ARGENTINA
FONDA ARGENTINA COYOACAN
FONDA ARGENTINA ENCUENTRO OCEANIA
FONDA ARGENTINA LAS ANTENAS
FONDA ARGENTINA MAQ
FONDA ARGENTINA PUEBLA
FONDA ARGENTINA SAN JERONIMO
FONDA COSTA NERA
LAS EMPANADAS DE MARIA EVA
MARIO Y JULY
```

All companies were initially seeded as:

```text
company_migration_type = migrated_from_wansoft
history_source = wansoft
include_odoo_history = 0
```

Before production usage, each company should be reviewed and confirmed as either:

```text
migrated_from_wansoft
new_odoo_branch
```

---

## Example Maintenance Cases

### Mark a company as a new Odoo branch

```sql
UPDATE odoo_company_migration_policy
SET
    company_migration_type = 'new_odoo_branch',
    history_source = 'odoo',
    include_odoo_history = 1,
    operational_start_date = '2026-07-07',
    notes = 'New Odoo branch. Odoo history included from operational start date.'
WHERE company_name = 'FONDA ARGENTINA ENCUENTRO OCEANIA';
```

---

### Adjust operational start date

```sql
UPDATE odoo_company_migration_policy
SET
    operational_start_date = '2026-06-01',
    notes = 'Migrated from Wansoft. Odoo included only from approved operational date.'
WHERE company_name = 'FONDA ARGENTINA MAQ';
```

---

### Disable a company policy

```sql
UPDATE odoo_company_migration_policy
SET
    is_active = 0,
    notes = 'Policy disabled. Company excluded from migration-aware ETL.'
WHERE company_name = 'COMPANY NAME';
```

---

## How This Policy Affects Purchases ETL

The Purchases ETL should apply the policy to:

```text
purchase.order
purchase.order.line
stock.picking
stock.move
```

The same company cutoff logic should later be applied to:

- purchase order headers
- purchase order lines
- purchase receipts
- receipt moves

---

## Relationship With Inventory Domain

The Purchases domain uses the inventory dictionary for product alignment.

Purchase lines are enriched through:

```text
purchase.order.line.product_id
→ inventory_mapping_dictionary.odoo_product_id
→ wansoft_code
→ wansoft_product_name
→ wansoft_department
```

This allows purchase activity in Odoo to remain analytically aligned with Wansoft product codes during the transition.

---

## Current Status

The company migration policy table has been created.

The initial policy seed has been generated from the current purchases snapshot.

The next implementation step is:

```text
Integrate odoo_company_migration_policy into the Purchases ETL.
```

---

## Next Step

Implement company-specific filtering in:

```text
extract/purchases/odoo_purchase_etl.py
```

Expected result:

```text
Purchases ETL no longer relies only on PURCHASE_ETL_MIN_ORDER_DATE.
Each company uses its configured operational_start_date.
```