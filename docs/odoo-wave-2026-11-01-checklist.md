# Odoo wave of 2026-11-01: Aeropuerto and Taquería Viaducto

Owner, 2026-10-12: **Aeropuerto and Taquería Viaducto start on Odoo on
Sunday 2026-11-01.** In Mexico they share one legal entity, and in Odoo they
are **branches** (child companies) of it. Parroquia and Exhibimex (Versalles)
are configured the same way but unused. Cancún and Playa del Carmen also have
configured branches, but (owner, 2026-10-12) Playa del Carmen closes next
year and will not be integrated in Odoo, and Cancún will run as a normal
company, not a branch.

Reminders so this is not forgotten: this checklist, "NOW / NEXT" in
`PROJECT_CONTEXT_REPORT.md`, a scheduled Claude session on Monday 2026-10-26,
and the nightly detector `scripts/check_odoo_company_activity.py` (inside the
stage "Odoo cutover validation"): from the first confirmed purchase or stock
move of a branch still configured as Wansoft, the night's log shows
`[AVISO] ... ya opera en Odoo ... pero el sistema la sigue tomando de Wansoft`.

## Odoo structure (read 2026-10-12)

| Legal entity (RFC) | Branch (res.company id) | Warehouse branch |
|---|---|---|
| FONDA ARGENTINA AEROPUERTO (FAA1005112F2), id 8 | Aeropuerto (32) | Aeropuerto, Wansoft 4959 |
| | Taquería Viaducto (33) | Taquería Viaducto, Wansoft 4962 |
| PERALTA Y LEON (PLE100312553), id 13 | Parroquia (28) | Taquería parroquia, 5321 |
| | Exhibimex (29) | Versalles, 5396 |
| LA PARRILLADA ORIGINAL DEL SUR (POS111123JA9), id 12 | Cancún (30) | Cancun, 6175 (will run as a normal company, not a branch) |
| | Playa del Carmen (31) | not mapped: Playa del Carmen closes next year, no Odoo integration |

On 2026-10-12 none of them had purchase orders, warehouses or stock moves.

## Done on 2026-10-12

- Name mapping: each branch name maps to its warehouse branch
  (`ODOO_COMPANY_SOURCE_KEY`); the three legal entities are
  `ODOO_HOLDING_COMPANIES` and map to no branch (before, FONDA ARGENTINA
  AEROPUERTO was mapped to Aeropuerto, which would have been ambiguous and
  could have made `odoo_cost_report.resolve_odoo_company_id` pick the legal
  entity instead of the branch). Aliases added in
  `scripts/build_dim_company_analytical.py`.
- Nightly detector of unconfigured Odoo activity (above).

## The week before (from Monday 2026-10-26)

1. **Odoo costs on a branch.** `extract/costs/odoo_cost_report.py` finds the
   cost-of-sales accounts with `account.account` `company_ids in [company]`.
   Branches share their legal entity's chart of accounts: check that the
   lookup works for company 32/33 (or use the parent's accounts filtered by
   the branch's journal items) before costs switch.
2. **Ask the owner** whether Odoo's warehouses for 32/33 exist by then, and
   whether the branches will keep capturing in Wansoft in parallel (the
   October wave did).
3. **Prepare, do not apply:**
   - a migration file `sql/migrations/cutover_06_november_wave.sql`:
     `odoo_company_migration_policy` rows for `Aeropuerto` and
     `Taquería Viaducto` (company names exactly as in Odoo, ids 32/33),
     `migrated_from_wansoft`, `operational_start_date = 2026-11-01`,
     active; and the relabel of their Wansoft canonical purchase history to
     `wansoft_history_before_odoo` (same as `cutover_05`; never the full
     delete-and-reload, which loses the history since 2021);
   - the code change: `COMPANY_SOURCE` -> `"odoo"` for both,
     `COSTS_AUTO_SWITCH_TO_ODOO` += both (costs stay on Wansoft until Odoo has
     their cost of sales), `ROLLOUT_COMPANY_EXPECTATIONS` in
     `scripts/validate_purchases_canonical_layer.py` (active, date-aware);
   - test the whole thing on dev with the purchases pipeline end to end.

## Done on 2026-10-28 (dev tested)

- Odoo read: the warehouses now exist (Aeropuerto 35 `Aerop`, Taquería
  Viaducto 36 `Taque`); still no purchase orders, stock moves, quants or
  journal entries for 32/33.
- **Odoo costs on a branch (item 1):** the lookup found 0 cost accounts for
  32/33: a branch has only its cash account; the chart of accounts is the
  parent's (8: 30 `expense_direct_cost` accounts).
  `odoo_cost_report.get_cost_accounts` now also searches the parent
  company's accounts; journal items are still filtered by the branch's
  `company_id`. Only the six branch companies have a parent, none of them on
  Odoo yet, so no current branch changes. To confirm with the first invoices
  after 11-01 that Odoo stamps the branch (not the parent) on the lines.
- `sql/migrations/cutover_06_november_wave.sql` written and applied on dev:
  2 policy rows (the accented name stored as bytes `C3AD`), 6,187 Wansoft
  canonical lines relabelled.
- Code flip: `COMPANY_SOURCE` -> `"odoo"` for both, both added to
  `COSTS_AUTO_SWITCH_TO_ODOO`, `ROLLOUT_COMPANY_EXPECTATIONS` entries.
  The cost switch rule on dev: both stay on Wansoft (expected).
- Daily stock (`scripts/build_analytics_inventory_stock_daily.py`):
  late-cutover guard (deletes Wansoft days from the Odoo start, relabels the
  history `wansoft_history_before_odoo`), and a bug found in the dev test:
  with the policy loaded before its start date the Wansoft series was built
  into the future (to 10-31); now capped at yesterday, in the build and in the
  validator. Tested on dev: start 11-01, a late cutover on 10-20, and back.

## Decision (owner, 2026-10-28): apply on Monday 2026-11-02

During the day of Monday 11-02 (not around 07:30): the owner runs
`cutover_06_november_wave.sql` in phpMyAdmin and the code flip is pushed the
same day, before the VM's 00:30 pull. The night of 11-02 -> 11-03 is the first
one configured. The night of 11-01 -> 11-02 still runs them as Wansoft: the
detector prints `[AVISO] ... ya opera en Odoo` if Odoo already has activity
(expected), and 11-01 may be stored as Wansoft. The next night repairs it
without manual reruns: the Wansoft canonical load reclassifies its window, the
movements reload their capture window, the Odoo side loads from the start
date, and the daily stock's late-cutover guard drops the Wansoft days from
11-01 and relabels the history (tested on dev). Costs stay on Wansoft anyway.

## Cutover (2026-11-01 is a Sunday)

The repository update runs at 00:30 and the cycle at 01:30. Either commit the
code change on Saturday 10-31 after the night's run (so the night of 10-31 to
11-01 still treats them as Wansoft and the night of 11-01 to 11-02 as Odoo),
and apply `cutover_06` on the VM on 11-01 during the day; or do both on
Monday 11-02 morning and re-run the purchases/analytics stages by hand
(runbook 9.3/9.4). Decide with the owner.

## After the cutover

- First nights: the purchases rollout check prints `[AVISO]` while a branch
  has no confirmed Odoo line yet (bug #38); that is expected.
- `python -m scripts.check_odoo_vs_warehouse` daily for the first week: only
  confirmed orders count (bug #42).
- Dictionary: still one approved mapping per Odoo product; the purchases ETL
  takes one and warns otherwise (bug #44). Never approve two rows of one Odoo
  product.
- T+7 (2026-11-08) and T+30 (2026-12-01) checkpoints.
- Costs switch by themselves (`costs_odoo_switch`; `[AVISO] ... cambió a
  costos de Odoo`); `costs_source_by_company` tells Central de Reportes.
- Unified inventory tables (`docs/analytics-inventory-unified-design.md`):
  their Wansoft movements before 11-01, Odoo after, parallel Wansoft capture
  flagged non-final.
- Update `docs/inventory-coverage-by-branch.md`, the data guides (branch
  crosswalk) and the README branch table.
- The detector must report 0 afterwards.
