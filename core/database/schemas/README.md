# Database Schemas

## Wansoft
- Source: Wansoft ERP extraction
- Tables for: sales, inventory, cost, etc.

## Zenput
- Source: Zenput API / MySQL
- Tables for: tasks, forms, audits

---

## Usage

Run scripts to initialize local development:
mysql -u user -p dbname < wansoft.sql
mysql -u user -p dbname < zenput.sql