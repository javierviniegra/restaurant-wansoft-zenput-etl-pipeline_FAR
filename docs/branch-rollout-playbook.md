# Branch Rollout Playbook

## Purpose

This document defines the controlled process for rolling out a branch from Wansoft to Odoo in the data warehouse project.

The purpose is to make each rollout reproducible, auditable, and safe.

This playbook applies to:

```text
Purchases
Inventory
Company source governance
Odoo purchase snapshots
Wansoft historical purchases
Canonical purchase tables
Pipeline validation
Rollout company pattern checks
```

This document does not replace the operational Odoo go-live checklist.

It documents the data platform steps required to make a branch behave correctly in the canonical analytical layer.

---

## Core Rollout Principle

The project uses this source governance rule:

```text
Sales      -> always Wansoft
Purchases  -> COMPANY_SOURCE
Inventory  -> COMPANY_SOURCE
```

This means:

```text
Sales never switch to Odoo in this project.
Purchases switch by company according to COMPANY_SOURCE.
Inventory switches by company according to COMPANY_SOURCE.
```

The authoritative selector is:

```text
core/config/companies.py
```

The key dictionary is:

```python
COMPANY_SOURCE
```

---

## Standard Rollout Patterns

There are two supported rollout patterns:

```text
migrated_from_wansoft
new_odoo_branch
```

---

## Pattern 1: migrated_from_wansoft

Use this pattern when the branch already had historical operations in Wansoft and later starts operating in Odoo.

Expected canonical behaviour:

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

for the migrated branch.

Reference branch:

```text
Antenas
```

Current migrated rollout examples:

```text
Antenas
La Esquina Coyoacán
```

Business interpretation:

```text
Wansoft remains valid history.
Odoo becomes the final source from the operational start date.
The canonical layer must not double-count Odoo and Wansoft after the start date.
```

---

## Pattern 2: new_odoo_branch

Use this pattern when the branch starts as an Odoo branch and should not be treated as a Wansoft historical migration.

Expected canonical behaviour:

```text
Odoo:
    final_odoo_enabled
```

Not allowed after activation:

```text
wansoft / final_wansoft_enabled
```

for the new Odoo branch.

Current new branch example:

```text
CentroMyJ
```

Future new branch example:

```text
Puebla
```

Puebla may be documented as future rollout with:

```text
active = False
```

until the rollout is officially activated.

---

## Current Rollout Rule for Fondas

Current rollout rule:

```text
All migrated Fonda branches should replicate the Antenas pattern.
```

Meaning:

```text
Wansoft history before operational_start_date.
Odoo final source from operational_start_date onward.
```

Current exception:

```text
CentroMyJ
```

CentroMyJ is treated as:

```text
new_odoo_branch
```

Puebla is currently handled as:

```text
future new_odoo_branch
active = False
```

until the official rollout is activated.

---

## Important Concept: operational_start_date

The `operational_start_date` does not decide whether a company uses Odoo.

The correct hierarchy is:

```text
1. COMPANY_SOURCE decides whether the branch is Odoo or Wansoft.
2. operational_start_date applies only when COMPANY_SOURCE = 'odoo'.
3. .env dates are fallback values only.
```

Example:

```text
If COMPANY_SOURCE = 'wansoft':
    operational_start_date does not make the branch Odoo.

If COMPANY_SOURCE = 'odoo':
    operational_start_date defines the valid Odoo start date.
```

---

## Files That Must Be Updated During Rollout

A rollout should update all relevant governance files.

### 1. Python source governance

```text
core/config/companies.py
```

Update:

```python
COMPANY_SOURCE
```

and confirm company mapping dictionaries resolve the branch correctly.

---

### 2. Seed SQL

```text
sql/seeds/seed_odoo_company_migration_policy.sql
```

This keeps the rollout reproducible when creating or rebuilding the policy table.

---

### 3. Maintenance SQL

```text
sql/maintenance/update_odoo_company_migration_policy.sql
```

This is the controlled script used to update an existing environment.

---

### 4. MySQL policy table

```text
odoo_company_migration_policy
```

This must reflect the same policy as the SQL files.

Manual updates through phpMyAdmin are allowed for local testing, but the final SQL must also be versioned.

---

### 5. Rollout validator expectations

```text
scripts/validate_purchases_canonical_layer.py
```

Update:

```python
ROLLOUT_COMPANY_EXPECTATIONS
```

when a branch becomes part of the active rollout validation.

---

## Rollout Configuration: migrated_from_wansoft

Use this configuration for a migrated branch.

Example:

```text
La Esquina Coyoacán
```

### COMPANY_SOURCE

In:

```text
core/config/companies.py
```

set:

```python
"La Esquina Coyoacán": "odoo"
```

### Migration policy

In:

```text
odoo_company_migration_policy
```

expected values:

```text
company_source_key = La Esquina Coyoacán
company_name = FONDA ARGENTINA COYOACAN
company_migration_type = migrated_from_wansoft
history_source = wansoft
include_odoo_history = 0
operational_start_date = official Odoo start date
is_active = 1
```

### Expected canonical output

```text
source_system = odoo
final_purchase_source_status = final_odoo_enabled

source_system = wansoft
final_purchase_source_status = wansoft_history_before_odoo
```

---

## Rollout Configuration: new_odoo_branch

Use this configuration for a branch that starts directly as Odoo.

Example:

```text
CentroMyJ
```

### COMPANY_SOURCE

In:

```text
core/config/companies.py
```

set:

```python
"CentroMyJ": "odoo"
```

### Migration policy

In:

```text
odoo_company_migration_policy
```

expected values:

```text
company_source_key = CentroMyJ
company_name = MARIO Y JULY
company_migration_type = new_odoo_branch
history_source = odoo
include_odoo_history = 1
operational_start_date = official Odoo start date
is_active = 1
```

### Expected canonical output

```text
source_system = odoo
final_purchase_source_status = final_odoo_enabled
```

Not expected after activation:

```text
source_system = wansoft
final_purchase_source_status = final_wansoft_enabled
```

---

## Future Rollout Configuration

A future branch may be documented before activation.

Example:

```text
Puebla
```

In:

```text
scripts/validate_purchases_canonical_layer.py
```

use:

```python
{
    "company_source_key": "Puebla",
    "rollout_type": "new_odoo_branch",
    "active": False,
    "description": "Future Odoo rollout branch. Documented but not enforced yet.",
}
```

Meaning:

```text
Puebla is listed in the rollout plan.
Puebla does not fail current validation.
Puebla becomes enforced only when active = True.
```

When Puebla becomes active, change:

```python
"active": False
```

to:

```python
"active": True
```

and rerun the validation.

---

## SQL Template: migrated_from_wansoft

Use this pattern in both:

```text
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
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
    36,
    'FONDA ARGENTINA COYOACAN',
    'migrated_from_wansoft',
    'wansoft',
    0,
    '2026-06-01',
    1,
    'Migrated branch. Should follow Antenas pattern: Wansoft history before cutoff, Odoo final after cutoff.'
)
ON DUPLICATE KEY UPDATE
    company_migration_type = VALUES(company_migration_type),
    history_source = VALUES(history_source),
    include_odoo_history = VALUES(include_odoo_history),
    operational_start_date = VALUES(operational_start_date),
    is_active = VALUES(is_active),
    notes = VALUES(notes);
```

Important:

```text
Use the official Odoo company id.
Use the official operational_start_date.
Do not infer the official date from min_order_date unless that has been confirmed operationally.
```

---

## SQL Template: new_odoo_branch

Use this pattern for a new Odoo branch.

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
    35,
    'MARIO Y JULY',
    'new_odoo_branch',
    'odoo',
    1,
    '2026-06-01',
    1,
    'New Odoo branch. Odoo is the historical and final source.'
)
ON DUPLICATE KEY UPDATE
    company_migration_type = VALUES(company_migration_type),
    history_source = VALUES(history_source),
    include_odoo_history = VALUES(include_odoo_history),
    operational_start_date = VALUES(operational_start_date),
    is_active = VALUES(is_active),
    notes = VALUES(notes);
```

---

## Local Testing Workflow

Use this workflow before committing rollout changes.

---

### Step 1: Create a test branch

```bash
git checkout -b test/rollout-branch-name
```

---

### Step 2: Update source governance

Edit:

```text
core/config/companies.py
```

Set the branch source:

```python
"Branch Source Key": "odoo"
```

---

### Step 3: Update SQL files

Update:

```text
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
```

---

### Step 4: Apply policy in MySQL

Apply the maintenance SQL in MySQL.

If testing manually in phpMyAdmin, make sure the same change is also present in the SQL files.

---

### Step 5: Validate policy table

```sql
SELECT
    odoo_company_id,
    company_name,
    company_migration_type,
    history_source,
    include_odoo_history,
    operational_start_date,
    is_active
FROM odoo_company_migration_policy
WHERE company_name IN (
    'FONDA ARGENTINA COYOACAN',
    'MARIO Y JULY',
    'FONDA ARGENTINA PUEBLA'
);
```

---

### Step 6: Validate company source governance

```bash
python -m scripts.test_company_source_governance
```

Expected for migrated branches:

```text
domain=purchases source=odoo
domain=inventory source=odoo
domain=sales source=wansoft
```

Expected for internal providers:

```text
domain=purchases source=internal_provider
include_final=False
```

---

### Step 7: Rebuild Odoo canonical layer

Run:

```bash
python -m scripts.test_odoo_purchase_etl
python -m scripts.test_odoo_purchase_receipt_etl
python -m scripts.test_purchase_company_source_eligibility
python -m scripts.test_canonical_purchase_odoo_etl
```

---

### Step 8: Rebuild Wansoft canonical layer

If `COMPANY_SOURCE` changed for a branch that has Wansoft history, rebuild the Wansoft canonical layer.

Recommended controlled cleanup:

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
```

Do not use `DROP TABLE` for normal rollout testing.

Use source-specific `DELETE` and reload instead.

---

### Step 9: Validate rollout pattern

Run:

```bash
python -m scripts.validate_purchases_canonical_layer
```

Expected:

```text
rollout_company_patterns: PASS
VALIDATION RESULT: PASSED
```

---

### Step 10: Run full purchases pipeline

After individual validation passes:

```bash
python -m scripts.run_purchases_pipeline
```

Expected:

```text
PIPELINE RESULT: COMPLETED
```

---

## Rollout Validation Query

Use this SQL to review a branch manually:

```sql
SELECT
    source_system,
    company_source_key,
    final_purchase_source_status,
    COUNT(*) AS total_lines,
    MIN(order_da*e) AS min_order_date,
    MAX(orde*_date) AS max_order_date
FROM cano*ical_purchase_order_line_snapshot
*HERE company_source_key IN (
    '*ntenas',
    'La Esquina Coyoacán'*
    'CentroMyJ',
    'Puebla'
)
G*OUP BY
    source_system,
    comp*ny_source_key,
    final_purchase_*ource_status
ORDER BY
    company_*ource_key,
    source_system,
    *inal_purchase_source_status;
```

*xpected examples:

```text
Antenas*
    odoo / final_odoo_enabled
   *wansoft / wansoft_history_before_o*oo

La Esquina Coyoacán:
    odoo * final_odoo_enabled
    wansoft / *ansoft_history_before_odoo

Centro*yJ:
    odoo / final_odoo_enabled
*Puebla:
    ignored while active =*False
    enforced once active = T*ue
```

---

## How to Interpret m*n_order_date

The field:

```text
*IN(order_date)
```

shows the firs* actual order available in the can*nical table.

It does not necessar*ly equal:

```text
operational_sta*t_date
```

Example:

```text
oper*tional_start_date = 2026-06-01
fir*t actual Odoo order = 2026-06-02
`*`

In this case, the validation ca* still be correct.

The policy dat* allows Odoo rows from the start d*te onward, but it does not create *ows for days with no transactions.*
---

## Avoiding Common Rollout M*stakes

### Mistake 1: Updating My*QL but not SQL files

Problem:

``*text
Local environment works, but *hange is not reproducible.
```

Co*rect action:

```text
Update MySQL*for testing.
Also update seed and *aintenance SQL.
```

---

### Mist*ke 2: Updating seed SQL but not ex*sting MySQL table

Problem:

```te*t
The current environment still us*s old values.
```

Correct action:*
```text
Run the maintenance SQL o* update the table.
```

---

### M*stake 3: Changing policy but not r*building Wansoft canonical

Proble*:

```text
Wansoft rows still show*final_wansoft_enabled after rollou*.
```

Correct action:

```text
Re*oad source_system = 'wansoft' cano*ical rows.
```

---

### Mistake 4* Using DROP TABLE

Problem:

```te*t
May remove schema, indexes, constraints, or metadata.
```

Correct action:

```text
Use source-specific DELETE and reload.
```

---

### Mistake 5: Activating future rollout validation too early

Problem:

```text
Validation fails for a branch that is not live yet.
```

Correct action:

```text
Keep active = False until official rollout activation.
```

---

## Puebla Future Activation Checklist

When Puebla becomes active:

```text
[ ] Confirm official operational_start_date
[ ] Confirm whether Puebla remains new_odoo_branch
[ ] Set COMPANY_SOURCE["Puebla"] = "odoo"
[ ] Update seed SQL
[ ] Update maintenance SQL
[ ] Apply policy in MySQL
[ ] Set Puebla active = True in ROLLOUT_COMPANY_EXPECTATIONS
[ ] Run company source governance test
[ ] Run Odoo purchase ETL
[ ] Run Odoo receipt ETL
[ ] Run Odoo canonical ETL
[ ] Reload Wansoft canonical if needed
[ ] Run validate_purchases_canonical_layer.py
[ ] Confirm rollout_company_patterns = PASS
[ ] Run full purchases pipeline
```

---

## Current Validated Rollout State

Validated:

```text
Antenas:
    migrated_from_wansoft
    active = True
    pattern = PASS

La Esquina Coyoacán:
    migrated_from_wansoft
    active = True
    pattern = PASS

CentroMyJ:
    new_odoo_branch
    active = True
    pattern = PASS

Puebla:
    new_odoo_branch
    active = False
    skipped by validation
```

---

## Related Files

```text
core/config/companies.py
sql/seeds/seed_odoo_company_migration_policy.sql
sql/maintenance/update_odoo_company_migration_policy.sql
scripts/test_company_source_governance.py
scripts/test_purchase_company_source_eligibility.py
scripts/test_canonical_purchase_odoo_etl.py
scripts/test_canonical_purchase_wansoft_etl.py
scripts/validate_purchases_canonical_layer.py
scripts/run_purchases_pipeline.py
```

---

## Related Documentation

```text
README.md
docs/project-technical-guide.md
docs/project-status-and-todo.md
docs/production-orchestration-plan.md
docs/pipeline-logging-and-run-interpretation.md
docs/purchases-company-migration-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
```

---

## Current Status

Current status:

```text
Rollout pattern validation is implemented.
Antenas pattern is validated.
La Esquina Coyoacán pattern is validated.
CentroMyJ new branch pattern is validated.
Puebla is documented as inactive future rollout.
```

---

## Recommended Commit

This document should be committed as part of the Section 13 documentation update.

Recommended commit when Section 13 is closed:

```bash
git add README.md docs/ scripts/ sql/ core/

git commit -m "docs(project): document branch rollout playbook and pipeline logging"

git push
```