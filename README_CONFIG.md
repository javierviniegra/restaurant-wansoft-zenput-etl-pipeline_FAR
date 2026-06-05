# Odoo Catalog Maintenance (Pre-ETL)

## Overview

This module performs catalog maintenance before running ETL jobs from Odoo into MySQL.

It ensures:
- Odoo products without integration codes are classified
- Non-sale products are excluded from the sales domain
- Product lifecycle is preserved (active vs historical)
- Presentation changes (e.g. 750 ml → 700 ml) are detected
- Replacement candidates are stored and reviewed

---

## Execution Flow

1. Extract Odoo products
2. Classify products without integration code
3. Detect product replacements (presentation changes)
4. Update lifecycle classification
5. Generate review datasets
6. Run ETL to MySQL

---

## Development Setup

Set environment variable:

ENV=dev

Run:

python -m scripts.run_odoo_catalog_maintenance

---

## Production Setup

Set environment variable:

ENV=prod

### Backup before first execution

CREATE TABLE backup_product_catalog_mapping AS
SELECT * FROM product_catalog_mapping;

CREATE TABLE backup_product_product AS
SELECT * FROM product_product;

---

### Run catalog maintenance

python -m scripts.run_odoo_catalog_maintenance

---

### After maintenance

Review the following:

- product_replacement_candidates
- product_catalog_mapping
- Odoo products without integration code

Only after validation should the production ETL run.

---

## Lifecycle Rules

- active: current product used for sales
- historical: old versions (e.g. previous presentations)
- replaced: detected via presentation change
- obsolete: no longer used

---

## Key Principle

Wansoft defines what is sold.  
Odoo reflects and supports inventory and accounting.

---

## Notes

- Replacement detection DOES NOT merge products
- Historical products are preserved
- Cleaning only modifies sale_ok flag, not deletes data
- This process should be executed periodically before ETL