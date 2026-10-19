"""
Send branches back from Odoo costs to Wansoft costs (owner, 2026-10-19).

Isabel La Católica and Vía Vallejo were switched to Odoo costs on 2026-10-01
by the old two-consecutive-days rule (nights of 2026-10-18 and 10-19), but
Odoo had invoiced only their first days of October: the days without Odoo
invoices kept Wansoft's numbers and October mixed both systems. The owner
chose to send them back to Wansoft; the new rule (extract/costs/cost_switch.py)
switches a branch only after a complete month is invoiced in Odoo.

For each branch: deletes its row from costs_odoo_switch, recomputes its three
cost tables from Wansoft from the day before the old switch date through
yesterday (the same child run the nightly stage uses after a switch), and
republishes costs_source_by_company.

Dry run by default; --apply writes. Runs against the database ENV points at.

    python -m scripts.revert_cost_switch --branches "Isabel La Católica,Vía Vallejo"
    python -m scripts.revert_cost_switch --branches "Isabel La Católica,Vía Vallejo" --apply
"""
import argparse
import sys

from core.database.mysql import get_db_connection
from extract.costs.cost_routing import publish_costs_source_table
from extract.costs.cost_switch import load_switch_dates
from pipelines.jobs.costs_switch_job import _backfill


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--branches", required=True, help="comma-separated short keys")
    parser.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # the child run's log has characters cp1252 cannot print
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    branches = [b.strip() for b in args.branches.split(",") if b.strip()]

    conn = get_db_connection()
    try:
        switches = load_switch_dates(conn)
        found = {b: switches[b] for b in branches if b in switches}
        for b in branches:
            print(f"{b}: " + (f"en costos de Odoo desde {found[b]}" if b in found else "no tiene cambio registrado"))
        if not found:
            print("Nada que regresar.")
            return 0
        since = min(found.values())
        if not args.apply:
            print(f"Dry run: se borrarían {len(found)} cambios y se recalcularían sus costos desde Wansoft "
                  f"a partir de {since}. Usa --apply.")
            return 0
        cur = conn.cursor()
        cur.execute(f"DELETE FROM costs_odoo_switch WHERE company_source_key IN ({','.join(['%s'] * len(found))})",
                    list(found))
        conn.commit()
        print(f"Cambios borrados: {cur.rowcount}")
        _backfill(found.keys(), since)
        for key, sid, oid, start, reason in publish_costs_source_table(conn):
            if key in found:
                print(f"[costs_source_by_company] {key}: {reason}" + (f" desde {start}" if start else ""))
        print("Listo: costos de Wansoft.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
