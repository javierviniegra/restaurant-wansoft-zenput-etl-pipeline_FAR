"""Seed the expense classification tables from the owner's decisions.

    python -m scripts.seed_expense_mappings            # dry run (default)
    python -m scripts.seed_expense_mappings --apply

Expenses domain, block 2 (docs/analytics-expense-invoices-design.md). Two
governed tables decide how every Odoo vendor-bill line is classified into
Wansoft's Cuenta / Subcuenta / TipoDeEgreso:

- expense_account_mapping: one row per Odoo account. Odoo has one account per
  company (Carnes is 16 accounts with 16 ids) and the same code can carry a
  different name in another company, so the key is the account id. The owner
  decided by account name (seeds/expense_account_mapping_seed.csv); this
  script expands each name to the matching account of every branch company in
  ODOO_COMPANY_SOURCE_KEY, so branches that start later (Aeropuerto, Taquería
  Viaducto) are covered from day 1.
- expense_vendor_rule: one row per Odoo vendor, used for lines on accounts
  whose mapping_status is 'vendor_rule' ("Other overheads": bills captured
  without product or real account). Seed: seeds/expense_vendor_rule_seed.csv.

mapping_status / rule_status:
  approved          classified with cuenta / subcuenta / tipo_de_egreso
  product_category  goods clearing account: classify each line through its
                    product category's expense account (company context)
  vendor_rule       classify through expense_vendor_rule
  excluded          left out of the table (exclude_reason, e.g. advance)
  unclassified      the owner decided it stays "Por clasificar"
  pending_review    added automatically, waiting for the owner

A re-run never overwrites a human decision: it inserts new rows and only
updates rows still in pending_review. When the owner CHANGES a decision, it is
edited in the seed file and applied once with --update-decided, which rewrites
the existing rows that differ from the seed (first used 2026-10-26: La Cava de
James from unclassified to Costo de bebidas). Read-only against Odoo.
"""
import argparse
import csv
import xmlrpc.client
from collections import Counter
from pathlib import Path

from core.config.companies import ODOO_COMPANY_SOURCE_KEY
from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_SEED = ROOT / "seeds" / "expense_account_mapping_seed.csv"
VENDOR_SEED = ROOT / "seeds" / "expense_vendor_rule_seed.csv"

ACCOUNT_STATUSES = {"approved", "product_category", "vendor_rule", "excluded", "unclassified", "pending_review"}
VENDOR_STATUSES = {"approved", "unclassified", "pending_review"}

DDL = [
    """
    CREATE TABLE IF NOT EXISTS expense_account_mapping (
        id INT AUTO_INCREMENT PRIMARY KEY,
        odoo_account_id BIGINT NOT NULL,
        odoo_company_id BIGINT NOT NULL,
        odoo_company_name VARCHAR(255) NOT NULL,
        company_source_key VARCHAR(100) NULL,
        odoo_account_code VARCHAR(64) NULL,
        odoo_account_name VARCHAR(255) NOT NULL,
        odoo_account_type VARCHAR(50) NULL,
        mapping_status VARCHAR(30) NOT NULL,
        tipo_de_egreso VARCHAR(100) NULL,
        cuenta VARCHAR(255) NULL,
        subcuenta VARCHAR(255) NULL,
        exclude_reason VARCHAR(100) NULL,
        mapping_method VARCHAR(50) NOT NULL,
        decision_note VARCHAR(500) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_expense_account_mapping_account (odoo_account_id),
        KEY idx_expense_account_mapping_company (odoo_company_id),
        KEY idx_expense_account_mapping_status (mapping_status)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS expense_vendor_rule (
        id INT AUTO_INCREMENT PRIMARY KEY,
        odoo_partner_id BIGINT NOT NULL,
        vendor_name VARCHAR(255) NOT NULL,
        vendor_rfc VARCHAR(20) NULL,
        rule_status VARCHAR(30) NOT NULL,
        rule_source VARCHAR(50) NOT NULL,
        tipo_de_egreso VARCHAR(100) NULL,
        cuenta VARCHAR(255) NULL,
        subcuenta VARCHAR(255) NULL,
        evidence VARCHAR(255) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_expense_vendor_rule_partner (odoo_partner_id),
        KEY idx_expense_vendor_rule_rfc (vendor_rfc),
        KEY idx_expense_vendor_rule_status (rule_status)
    )
    """,
]

ACCOUNT_COLUMNS = ["odoo_account_id", "odoo_company_id", "odoo_company_name", "company_source_key",
                   "odoo_account_code", "odoo_account_name", "odoo_account_type", "mapping_status",
                   "tipo_de_egreso", "cuenta", "subcuenta", "exclude_reason", "mapping_method", "decision_note"]
VENDOR_COLUMNS = ["odoo_partner_id", "vendor_name", "vendor_rfc", "rule_status", "rule_source",
                  "tipo_de_egreso", "cuenta", "subcuenta", "evidence"]


def read_seed(path, status_field, valid):
    with open(path, encoding="utf-8") as f:
        rows = [{k: (v.strip() or None) for k, v in r.items()} for r in csv.DictReader(f)]
    for r in rows:
        if r[status_field] not in valid:
            raise ValueError(f"{path.name}: invalid {status_field} {r[status_field]!r}")
        if r[status_field] == "approved" and not (r["cuenta"] and r["subcuenta"] and r["tipo_de_egreso"]):
            raise ValueError(f"{path.name}: approved row without cuenta/subcuenta/tipo_de_egreso: {r}")
    return rows


def odoo_branch_accounts():
    """Every account of the chart used by each branch company in ODOO_COMPANY_SOURCE_KEY.

    An Odoo branch (Aeropuerto, Taquería Viaducto: children of FONDA ARGENTINA
    AEROPUERTO) has no chart of its own: it posts to its root company's
    accounts. So accounts are read once per root company, with its context
    (the code is company-dependent). company_source_key is set only when the
    root itself is a mapped branch; a shared holding chart gets NULL, and the
    branch comes from each bill's company instead.
    """
    uid, models, db, password = get_odoo_connection()
    x = lambda *a, **k: models.execute_kw(db, uid, password, *a, **k)
    companies = x("res.company", "search_read", [[["name", "in", list(ODOO_COMPANY_SOURCE_KEY)]]],
                  {"fields": ["name", "root_id"]})
    roots = {c["root_id"][0]: c["root_id"][1] for c in companies}
    accounts, skipped = [], []
    for root_id, root_name in roots.items():
        ctx = {"allowed_company_ids": [root_id], "active_test": False}
        try:
            found = x("account.account", "search_read", [[["company_ids", "in", [root_id]]]],
                      {"fields": ["name", "code", "account_type"], "context": ctx})
        except xmlrpc.client.Fault as exc:
            # The API user is not allowed in every configured company (e.g. branches
            # not started yet); those are reported and seeded on a later run.
            skipped.append(f"{root_name} ({exc.faultString})")
            continue
        for a in found:
            accounts.append({"odoo_account_id": a["id"], "odoo_company_id": root_id,
                             "odoo_company_name": root_name,
                             "company_source_key": ODOO_COMPANY_SOURCE_KEY.get(root_name),
                             "odoo_account_code": a["code"] or None, "odoo_account_name": a["name"].strip(),
                             "odoo_account_type": a["account_type"]})
    return accounts, len(roots), skipped


def upsert(cur, table, key, columns, rows, status_field, update_decided=False):
    """Insert new rows; update existing ones only while they are still pending_review,
    or, with update_decided, whenever the seed (a decision the owner changed) differs."""
    cur.execute(f"SELECT {key}, {status_field} FROM {table}")
    existing = dict(cur.fetchall())
    inserted = updated = kept = 0
    for r in rows:
        values = [r.get(c) for c in columns]
        if r[key] not in existing:
            cur.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})", values)
            inserted += 1
        elif update_decided or (existing[r[key]] == "pending_review" and r[status_field] != "pending_review"):
            sets = ", ".join(f"{c} = %s" for c in columns if c != key)
            cur.execute(f"UPDATE {table} SET {sets} WHERE {key} = %s", [r.get(c) for c in columns if c != key] + [r[key]])
            # rowcount counts only rows whose values actually changed
            updated += cur.rowcount
            kept += 1 - cur.rowcount
        else:
            kept += 1
    return inserted, updated, kept


def main(apply=False, update_decided=False):
    account_seed = read_seed(ACCOUNT_SEED, "mapping_status", ACCOUNT_STATUSES)
    vendor_seed = read_seed(VENDOR_SEED, "rule_status", VENDOR_STATUSES)
    decisions = {r["odoo_account_name"]: r for r in account_seed}

    accounts, n_companies, skipped = odoo_branch_accounts()
    rows, matched_names = [], set()
    for a in accounts:
        d = decisions.get(a["odoo_account_name"])
        if not d:
            continue
        matched_names.add(a["odoo_account_name"])
        rows.append({**a, "mapping_status": d["mapping_status"], "tipo_de_egreso": d["tipo_de_egreso"],
                     "cuenta": d["cuenta"], "subcuenta": d["subcuenta"], "exclude_reason": d["exclude_reason"],
                     "mapping_method": "owner_decision_by_name", "decision_note": d["decision_note"]})
    vendors = [{**v, "odoo_partner_id": int(v["odoo_partner_id"])} for v in vendor_seed]

    print(f"Odoo: {n_companies} charts of accounts (branch companies and their roots), {len(accounts)} accounts; "
          f"{len(rows)} accounts match {len(matched_names)} of {len(decisions)} decided names")
    for s in skipped:
        print(f"  [AVISO] company not readable by the Odoo API user, skipped: {s}")
    for name in sorted(set(decisions) - matched_names):
        print(f"  [AVISO] no branch account named {name!r}")
    print("  by status:", dict(Counter(r["mapping_status"] for r in rows)))
    print("  by company:", dict(Counter(r["company_source_key"] for r in rows)))
    print(f"Vendor rules: {len(vendors)} ({dict(Counter(v['rule_status'] for v in vendors))})")

    if not apply:
        print("Dry run: nothing written. Use --apply to create and fill the tables.")
        return
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for ddl in DDL:
            cur.execute(ddl)
        a = upsert(cur, "expense_account_mapping", "odoo_account_id", ACCOUNT_COLUMNS, rows, "mapping_status",
                   update_decided)
        v = upsert(cur, "expense_vendor_rule", "odoo_partner_id", VENDOR_COLUMNS, vendors, "rule_status", update_decided)
        conn.commit()
    finally:
        conn.close()
    how = "changed by the seed" if update_decided else "updated from pending_review"
    print(f"expense_account_mapping: {a[0]} inserted, {a[1]} {how}, {a[2]} kept")
    print(f"expense_vendor_rule: {v[0]} inserted, {v[1]} {how}, {v[2]} kept")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="create the tables and write the rows")
    parser.add_argument("--update-decided", action="store_true",
                        help="also rewrite existing rows that differ from the seed: only after the owner changed a "
                             "decision in the seed files (never in the nightly run)")
    args = parser.parse_args()
    main(args.apply, args.update_decided)
