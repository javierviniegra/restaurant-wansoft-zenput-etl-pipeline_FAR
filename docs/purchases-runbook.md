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
pipeline JSON logging
branch rollout validation
```

This document is operational.

For architecture and design context, refer to:

```text
docs/project-technical-guide.md
docs/purchases-canonical-layer.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
```

---

## Current Status

The Purchases domain now has a controlled orchestration pipeline.

Implemented:

```text
scripts/run_purchases_pipeline.py
scripts/test_run_purchases_pipeline.py
scripts/validate_purchases_canonical_layer.py
```

Current status:

```text
dry-run validated
real pipeline execution validated
canonical validation integrated as required final step
JSON run logging implemented
rollout company pattern validation implemented
```

Current pipeline result expectation:

```text
PIPELINE RESULT: COMPLETED
```

---

## Purchases Architecture

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
    ↓
canonical validation
    ↓
JSON pipeline log
```

---

## Source Governance Rules

Purchases follow company-level source governance from:

```text
core/config/companies.py
```

Main source rules:

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

La Esquina Coyoacán:
    Wansoft historical purchases before operational_start_date
    Odoo final purchases from operational_start_date onward

CentroMyJ:
    Odoo final purchases as new Odoo branch

Other Wansoft companies:
    Wansoft remains the final purchase source
```

---

# Recommended Execution Method

The recommended way to run the Purchases domain is now:

```bash
python -m scripts.run_purchases_pipeline
```

This executes the full controlled pipeline.

Before running the real pipeline, always validate the orchestration structure with:

```bash
python -m scripts.run_purchases_pipeline --dry-run
```

---

# Purchases Pipeline Execution Order

The current pipeline executes these steps:

```text
01. Company source governance
02. Odoo purchase order and line ETL
03. Odoo purchase receipt ETL
04. Purchase inventory mapping backlog
05. Purchase backlog product reference report
06. Purchase company source eligibility
07. Odoo canonical purchase load
08. Wansoft purchase subsidiary mapping report
09. Wansoft canonical purchase load
10. Purchases canonical layer validation
```

Modules executed:

```text
01. scripts.test_company_source_governance
02. scripts.test_odoo_purchase_etl
03. scripts.test_odoo_purchase_receipt_etl
04. scripts.test_purchase_inventory_mapping_backlog
05. scripts.test_purchase_backlog_product_reference_report
06. scripts.test_purchase_company_source_eligibility
07. scripts.test_canonical_purchase_odoo_etl
08. scripts.test_wansoft_purchase_subsidiary_mapping_report
09. scripts.test_canonical_purchase_wansoft_etl
10. scripts.validate_purchases_canonical_layer
```

---

## Dry Run

Run:

```bash
python -m scripts.run_purchases_pipeline --dry-run
```

Expected result:

```text
total_steps: 10
success: 0
dry_run: 10
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

A dry run does not execute ETLs.

It only validates:

```text
pipeline structure
step order
required or optional flags
summary generation
JSON log generation
```

---

## Real Pipeline Run

Run:

```bash
python -m scripts.run_purchases_pipeline
```

Expected result:

```text
total_steps: 10
success: 10
dry_run: 0
failed_or_error: 0
required_failed_or_error: 0

PIPELINE RESULT: COMPLETED
```

If any required step fails, the pipeline should stop and return a failed result.

---

# Pipeline Logging

The Purchases pipeline generates a local JSON log for every execution.

Log folder:

```text
logs/purchases_pipeline_runs/
```

Example:

```text
logs/purchases_pipeline_runs/20260722_120853_27ea21c9-9a4c-4abb-82b8-2334d06c422a.json
```

Each log includes:

```text
run_id
pipeline_name
status
dry_run
started_at
finished_at
duration_seconds
total_steps
success
dry_run_steps
failed_or_error
required_failed_or_error
step-level results
return codes
error messages
```

The logs are local execution artefacts.

They should not be committed.

Recommended `.gitignore` entry:

```gitignore
# Pipeline run logs
logs/
```

For detailed log interpretation, refer to:

```text
docs/pipeline-logging-and-run-interpretation.md
```

---

# How to Read a Successful Run

A successful real run should show:

```text
PIPELINE RESULT: COMPLETED
required_failed_or_error: 0
failed_or_error: 0
```

The JSON log should show:

```text
status = COMPLETED
dry_run = false
required_failed_or_error = 0
```

Step statuses should show:

```text
SUCCESS
```

for all required steps.

---

# How to Identify the Slowest Step

In the console summary or JSON log, review:

```text
duration_seconds
```

The slowest current step is usually:

```text
09. Wansoft canonical purchase load
```

Module:

```text
scripts.test_canonical_purchase_wansoft_etl
```

Future performance work should review:

```text
incremental Wansoft refresh
batch insert strategy
index review
date filters
historical reload separation
```

Do not change business logic only to reduce runtime.

---

# Manual Execution Order

If the full pipeline is not needed, run the individual steps in this order.

---

## 1. Validate Company Source Governance

```bash
python -m scripts.test_company_source_governance
```

Expected checks:

```text
Antenas:
    sales      -> wansoft
    purchases  -> odoo
    inventory  -> odoo

La Esquina Coyoacán:
    sales      -> wansoft
    purchases  -> odoo
    inventory  -> odoo

CentroMyJ:
    sales      -> wansoft
    purchases  -> odoo
    inventory  -> odoo

Internal providers:
    purchases  -> internal_provider
    inventory  -> internal_provider
    include_final -> False
```

---

## 2. Run Odoo Purchase Order and Line ETL

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

## 3. Run Odoo Purchase Receipt ETL

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

## 4. Build Purchase Inventory Mapping Backlog

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

---

## 5. Validate Purchase Backlog Product References

```bash
python -m scripts.test_purchase_backlog_product_reference_report
```

Expected output:

```text
REFERENCE SUMMARY
SAMPLE WITH REFERENCE
SAMPLE WITHOUT REFERENCE
```

Interpretation:

```text
Products without explicit Odoo/Wansoft reference are treated as new products.
They remain in backlog.
They are not automatically matched by similar name.
```

---

## 6. Validate Company Source Eligibility for Odoo Purchases

```bash
python -m scripts.test_purchase_company_source_eligibility
```

Expected statuses:

```text
final_odoo_enabled
wansoft_only
exclude_internal_provider
```

Only rows marked as:

```text
final_odoo_enabled
```

are loaded into the Odoo canonical layer.

---

## 7. Run Odoo Canonical Purchase Load

```bash
python -m scripts.test_canonical_purchase_odoo_etl
```

This loads eligible Odoo rows into:

```text
canonical_purchase_order_snapshot
canonical_purchase_order_line_snapshot
canonical_purchase_receipt_snapshot
canonical_purchase_receipt_move_snapshot
```

Expected source status:

```text
source_system = odoo
final_purchase_source_status = final_odoo_enabled
```

---

## 8. Validate Wansoft Subsidiary Mapping

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

---

## 9. Run Wansoft Canonical Purchase Load

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

Expected Wansoft statuses:

```text
final_wansoft_enabled
wansoft_history_before_odoo
```

---

## 10. Run Canonical Validation

```bash
python -m scripts.validate_purchases_canonical_layer
```

Expected result:

```text
VALIDATION RESULT: PASSED
```

The full pipeline should not be considered successful unless this validation passes.

---

# Canonical Validation Checks

The final validator checks:

```text
source-system coexistence
Antenas source split
Wansoft final-source companies
internal providers as vendors
internal providers not as final companies
canonical product mapping distribution
canonical table counts
rollout company patterns
```

Current validation count:

```text
total_validations: 8
```

Expected result:

```text
passed: 8
failed: 0
VALIDATION RESULT: PASSED
```

---

# Rollout Company Pattern Validation

The Purchases canonical validator includes rollout-specific expectations.

Current rollout types:

```text
migrated_from_wansoft
new_odoo_branch
```

---

## migrated_from_wansoft

Expected pattern:

```text
Odoo:
    final_odoo_enabled from operational_start_date onward

Wansoft:
    wansoft_history_before_odoo before operational_start_date
```

Not allowed after activation:

```text
wansoft / final_wansoft_enabled
```

Current active examples:

```text
Antenas
La Esquina Coyoacán
```

---

## new_odoo_branch

Expected pattern:

```text
Odoo:
    final_odoo_enabled
```

Not allowed after activation:

```text
wansoft / final_wansoft_enabled
```

Current active example:

```text
CentroMyJ
```

Current inactive future example:

```text
Puebla
```

---

## Active vs Inactive Rollout Expectations

Rollout expectations may be configured as:

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

Current expected behaviour:

```text
Puebla:
    rollout_type = new_odoo_branch
    active = False
    skipped by validation until official activation
```

---

# Rollout Validation Query

Use this SQL to review rollout behaviour manually:

```sql
SELECT
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_lines,
    MIN(order_date) AS min_order_date,
    MAX(order_date) AS max_order_date
FROM canonical_purchase_order_line_snapshot
WHERE company_source_key IN (
    'Antenas',
    'La Esquina Coyoacán',
    'CentroMyJ',
    'Puebla'
)
GROUP BY
    source_system,
    company_source_key,
    final_purchase_source_status
ORDER BY
    company_source_key,
    source_system,
    final_purchase_source_status;
```

Expected:

```text
Antenas:
    odoo / final_odoo_enabled
    wansoft / wansoft_history_before_odoo

La Esquina Coyoacán:
    odoo / final_odoo_enabled
    wansoft / wansoft_history_before_odoo

CentroMyJ:
    odoo / final_odoo_enabled

Puebla:
    ignored while active = False
    enforced once active = True
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

Odoo canonical refresh should affect only:

```text
source_system = 'odoo'
```

Expected behaviour:

```text
Odoo canonical rows are rebuilt.
Wansoft canonical rows remain untouched.
```

---

## Wansoft Refresh

Rules:

```text
Delete only source_system = 'wansoft'
Reload eligible Wansoft rows
Preserve source_system = 'odoo'
```

Wansoft canonical refresh should affect only:

```text
source_system = 'wansoft'
```

Expected behaviour:

```text
Wansoft canonical rows are rebuilt.
Odoo canonical rows remain untouched.
```

---

## Controlled Wansoft Cleanup for Rollout Testing

For rollout testing or source-governance corrections, use source-specific cleanup.

Do not use `DROP TABLE` for normal rollout testing.

Use:

```sql
DELETE FROM canonical_purchase_order_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_receipt_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_receipt_move_snapshot
WHERE source_system = 'wansoft';
```

Then reload Wansoft canonical rows:

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
```

Then validate:

```bash
python -m scripts.validate_purchases_canonical_layer
```

Expected result:

```text
VALIDATION RESULT: PASSED
```

---

## Why DROP TABLE Should Be Avoided

Avoid:

```sql
DROP TABLE canonical_purchase_order_snapshot;
DROP TABLE canonical_purchase_order_line_snapshot;
DROP TABLE canonical_purchase_receipt_snapshot;
DROP TABLE canonical_purchase_receipt_move_snapshot;
```

Reason:

```text
DROP TABLE may remove schema, indexes, constraints, metadata, or grants.
Source-specific DELETE preserves the table structure.
```

Use `DROP TABLE` only for controlled schema rebuilds, not for regular ETL reloads or rollout validation.

---

# Troubleshooting

## Pandas SQLAlchemy Warning

You may see warnings like:

```text
pandas only supports SQLAlchemy connectable...
```

This warning does not block the ETL.

Current status:

```text
Safe to ignore during development.
Optional cleanup later: migrate read_sql connections to SQLAlchemy engines.
```

The warning means Pandas recommends using SQLAlchemy connections for `read_sql`.

It does not mean the ETL failed.

---

## Wansoft Rows Remain `final_wansoft_enabled` After Rollout

If a migrated branch still appears as:

```text
source_system = wansoft
final_purchase_source_status = final_wansoft_enabled
```

after it should behave like Antenas, check:

```text
COMPANY_SOURCE
company_source_key spelling and accents
odoo_company_migration_policy
seed SQL
maintenance SQL
whether Wansoft canonical rows were reloaded
```

Correct migrated branch pattern:

```text
source_system = odoo
final_purchase_source_status = final_odoo_enabled

source_system = wansoft
final_purchase_source_status = wansoft_history_before_odoo
```

If policy was changed, reload:

```text
source_system = wansoft
```

canonical rows.

Recommended controlled reload:

```sql
DELETE FROM canonical_purchase_order_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_order_line_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_receipt_snapshot
WHERE source_system = 'wansoft';

DELETE FROM canonical_purchase_receipt_move_snapshot
WHERE source_system = 'wansoft';
```

Then run:

```bash
python -m scripts.test_canonical_purchase_wansoft_etl
python -m scripts.validate_purchases_canonical_layer
```

---

## `min_order_date` Does Not Match `operational_start_date`

This is not automatically an error.

Reason:

```text
MIN(order_date) shows the first actual order present in the canonical table.
operational_start_date defines when Odoo is allowed to become final.
```

Example:

```text
operational_start_date = 2026-06-01
first actual Odoo order = 2026-06-02
```

This can still be valid.

The policy date allows Odoo rows from the start date onward, but it does not create rows for days with no transactions.

---

## Internal Providers Appear as Vendors

This is allowed.

Internal providers:

```text
EL BODEGON DE FITO
LAS EMPANADAS DE MARIA EVA
```

They may appear as:

```text
vendor_name
```

They should not appear as final:

```text
company_name
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

---

## Internal Providers Appear as Final Companies

This is not allowed.

Incorrect example:

```text
company_name = EL BODEGON DE FITO
```

If this happens, review:

```text
company mapping
internal provider list
canonical exclusion logic
```

The validator should fail:

```text
internal_providers_not_as_companies
```

---

## Rollout Validation Fails for a Future Branch

If a branch is not active yet, keep it as:

```python
"active": False
```

in:

```text
ROLLOUT_COMPANY_EXPECTATIONS
```

Once the branch becomes active, change it to:

```python
"active": True
```

and rerun:

```bash
python -m scripts.validate_purchases_canonical_layer
```

Expected after activation:

```text
rollout_company_patterns: PASS
VALIDATION RESULT: PASSED
```

---

## Rollout Validation Fails for a Migrated Branch

For a migrated branch, expected pattern is:

```text
Odoo:
    final_odoo_enabled from operational_start_date onward

Wansoft:
    wansoft_history_before_odoo before operational_start_date
```

If the branch shows:

```text
wansoft / final_wansoft_enabled
```

then check:

```text
COMPANY_SOURCE
odoo_company_migration_policy
seed SQL
maintenance SQL
canonical Wansoft reload
company_source_key spelling and accents
```

Reference migrated branch pattern:

```text
Antenas
```

Current migrated rollout examples:

```text
Antenas
La Esquina Coyoacán
```

---

## Rollout Validation Fails for a New Odoo Branch

For a new Odoo branch, expected pattern is:

```text
Odoo:
    final_odoo_enabled
```

Not expected after activation:

```text
wansoft / final_wansoft_enabled
```

Current active new branch example:

```text
CentroMyJ
```

Current inactive future branch example:

```text
Puebla
```

If Puebla is not active yet, it should remain:

```python
"active": False
```

---

# Recommended Execution Checklist

Use this checklist when running the Purchases domain.

```text
[ ] Confirm .env is loaded
[ ] Confirm MySQL connection
[ ] Confirm Odoo connection
[ ] Confirm Wansoft credentials and local WSDL setup
[ ] Confirm COMPANY_SOURCE before rollout
[ ] Confirm odoo_company_migration_policy before rollout
[ ] Confirm seed SQL and maintenance SQL are aligned
[ ] Confirm logs/ is ignored by Git
[ ] Run pipeline dry-run
[ ] Run real pipeline
[ ] Confirm pipeline summary
[ ] Confirm JSON log file was generated
[ ] Confirm final validation passed
[ ] Review slowest step
[ ] Review rollout_company_patterns
[ ] Keep logs out of Git
```

---

# Current Purchases Pipeline Status

Current state:

```text
Purchases pipeline is implemented.
Purchases pipeline dry-run works.
Purchases pipeline real execution works.
Canonical validation is integrated as required.
JSON logging is implemented.
Rollout validation is implemented.
Branch rollout playbook is documented.
Pipeline log interpretation is documented.
```

Current known pending work:

```text
Wansoft canonical performance optimisation
database-level run logging
database-level validation persistence
Inventory pipeline equivalent
Puebla future rollout activation
```

---

# Current Validated Rollout State

Current active rollout validations:

```text
Antenas:
    rollout_type = migrated_from_wansoft
    active = True
    pattern = PASS

La Esquina Coyoacán:
    rollout_type = migrated_from_wansoft
    active = True
    pattern = PASS

CentroMyJ:
    rollout_type = new_odoo_branch
    active = True
    pattern = PASS
```

Current inactive future rollout:

```text
Puebla:
    rollout_type = new_odoo_branch
    active = False
    skipped by validation
```

---

# Related Documentation

```text
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/branch-rollout-playbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/inventory-runbook.md
docs/wansoft-local-wsdl.md
```

---

# Related Files

```text
scripts/run_purchases_pipeline.py
scripts/test_run_purchases_pipeline.py
scripts/validate_purchases_canonical_layer.py
scripts/test_company_source_governance.py
scripts/test_purchase_company_source_eligibility.py
scripts/test_canonical_purchase_odoo_etl.py
scripts/test_canonical_purchase_wansoft_etl.py
core/config/companies.py
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
```

---

# Recommended Commit

This document should be committed as part of the Section 13 documentation update.

Recommended commit when Section 13 is closed:

```bash
git add README.md docs/ scripts/ sql/ core/

git commit -m "docs(project): update purchases runbook for pipeline orchestration and rollout validation"

git push
```