"""Read-only nightly check: Odoo companies whose activity the warehouse is not configured to load.

    python -m scripts.check_odoo_company_activity [--days 7]

The owner's reminder for branch rollouts (2026-10-12): the next wave
(Aeropuerto and Taquería Viaducto, 2026-11-01) must not depend on someone
remembering to switch the configuration. For every Odoo company with
confirmed purchase orders or done stock moves in the last N days it prints
an [AVISO] when:
  - the company has no mapping to a branch (core/config/companies.py,
    ODOO_COMPANY_SOURCE_KEY) and is not an internal provider, a legal entity
    holding branches, or out of scope;
  - a legal entity holding branches records activity itself (it should be on
    its branches);
  - the branch is still on Wansoft in COMPANY_SOURCE (its Odoo activity is
    not loaded);
  - the branch is on Odoo but has no active row in
    odoo_company_migration_policy.
Accounting entries alone do not count (a company outside the group shares
the Odoo database and only posts entries). It never fails the cycle: it is
a reminder, run inside the stage "Odoo cutover validation". Checklist for a
new wave: docs/odoo-wave-2026-11-01-checklist.md.
"""
import argparse
from datetime import date, timedelta

from core.config.companies import (
    COMPANY_SOURCE,
    ODOO_HOLDING_COMPANIES,
    get_company_source_key,
    is_internal_provider_company,
    is_out_of_scope_company,
)
from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection


def active_policy_companies():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT company_name FROM odoo_company_migration_policy WHERE is_active = 1")
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def check(days=7):
    since = (date.today() - timedelta(days=days)).isoformat()
    uid, models, db, password = get_odoo_connection()
    policies = active_policy_companies()
    warnings = []
    for company in models.execute_kw(db, uid, password, "res.company", "search_read", [[]], {"fields": ["name"]}):
        name = company["name"]
        orders = models.execute_kw(db, uid, password, "purchase.order", "search_count",
                                   [[["company_id", "=", company["id"]], ["state", "in", ["purchase", "done"]], ["date_order", ">=", since]]])
        moves = models.execute_kw(db, uid, password, "stock.move", "search_count",
                                  [[["company_id", "=", company["id"]], ["state", "=", "done"], ["date", ">=", since]]])
        if not orders and not moves:
            continue
        activity = f"{orders} compras confirmadas y {moves} movimientos de inventario en {days} días"
        key = get_company_source_key(name)
        if is_out_of_scope_company(name) or is_internal_provider_company(name):
            continue
        if name in ODOO_HOLDING_COMPANIES:
            warnings.append(f"la razón social {name} registra actividad directamente ({activity}); debería estar en sus branches")
        elif key not in COMPANY_SOURCE:
            warnings.append(f"la compañía de Odoo '{name}' no tiene equivalencia con una sucursal ({activity}); "
                            f"agregarla a ODOO_COMPANY_SOURCE_KEY")
        elif COMPANY_SOURCE[key] != "odoo":
            warnings.append(f"{key} ('{name}') ya opera en Odoo ({activity}) pero el sistema la sigue tomando de Wansoft: "
                            f"¿arrancó? ver docs/odoo-wave-2026-11-01-checklist.md")
        elif name not in policies:
            warnings.append(f"{key} ('{name}') está en Odoo pero no tiene fila activa en odoo_company_migration_policy ({activity})")
    for line in warnings:
        print(f"[AVISO] {line}")
    print(f"Compañías de Odoo con actividad no configurada: {len(warnings)}")
    return warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)
    check(args.days)


if __name__ == "__main__":
    main()
