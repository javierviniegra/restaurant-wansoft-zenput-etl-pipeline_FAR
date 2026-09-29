"""Read-only comparison of the shadow run (test databases) against production.

Run on the tasks VM, whose .env points at the _prueba databases:
    python -m scripts.compare_shadow_run [--days 6]

For each table it compares, per day and branch, row counts and amounts between
the live database and its _prueba copy, only for days both sides have loaded.
Branches that buy on Odoo are expected to have no Wansoft invoices, entries or
butchery rows in the test copy after their Odoo start date; those gaps are
labelled EXPECTED, not DIFF (also when the test copy has fewer rows: the
restored backup still held some). Cost rows the new pipeline takes from Odoo
(extract/costs/cost_routing.py) while the legacy tasks still store Wansoft's
cost, or zero, are labelled ODOO_COST. Only SELECT statements are issued.
"""
import argparse
import os
import sys
import unicodedata
from datetime import date, timedelta

from core.database.mysql import get_mysql_connection
from core.config.companies import COMPANY_SOURCE, WANSOFT_SUBSIDIARY_SOURCE_KEY
from extract.costs.cost_routing import costs_source, load_costs_odoo_start_dates

ODOO_KEYS = {k for k, v in COMPANY_SOURCE.items() if v == "odoo"}
# Words that identify the Odoo-sourced branches inside Wansoft's long names.
ODOO_NAME_HINTS = ("acoxpa", "antenas", "tepeyac", "oceania", "coyoacan", "puebla", "centro mario")


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return text


def branch_label(value):
    """Returns (label, is_odoo_branch) for a short key, a Wansoft id or a long name."""
    key = WANSOFT_SUBSIDIARY_SOURCE_KEY.get(str(value), value)
    if key in ODOO_KEYS:
        return key, True
    return str(key), any(h in norm(key) for h in ODOO_NAME_HINTS)


# name, database kind, table, branch expression, date expression, amount expression, odoo gap expected
CHECKS = [
    ("Ventas (tickets)", "wansoft", "getallordenesbyday_new_venta", "Sucursal", "DATE(Fecha)", "CAST(Total AS DECIMAL(14,2))", False),
    ("Ventas (pagos)", "wansoft", "getallordenesbyday_new_pago", "Sucursal", "DATE(Fecha)", "CAST(Total AS DECIMAL(14,2))", False),
    ("Cierre de caja", "wansoft", "getglobalcashclosing", "subsidiary_id", "DATE(fecha_corte)", "total_ventas", False),
    ("Costo mensual", "wansoft", "costeomensual", "subsidiary_id", "DATE(created_at)", "CostoTotal", "cost"),
    ("Costo semanal", "wansoft", "costeomensual_semanapyq", "subsidiary_id", "DATE(created_at)", "CostoTotal", "cost"),
    ("Costo por dia", "wansoft", "gettotalcostbydate", "subsidiary_id", "DATE(created_at)", "CostoTotalVenta", "cost"),
    ("Tablajeria", "wansoft", "gettablajeriareport", "subsidiary_id", "InputDate", "totalCostOfGeneratedProduct", True),
    ("Facturas", "wansoft", "getexpenses_factura", "Sucursal", "DATE(LEFT(FechaDeExpedicion,10))", "CAST(Subtotal AS DECIMAL(14,2))", True),
    ("Entradas", "wansoft", "getinputinventory_entrada", "subsidiary_name", "DATE(FechaEntrada)", "Cantidad*CostoUnitario", True),
    ("Zenput checklists", "zenput", "submissions", "location_name", "DATE(date_submitted)", "1", False),
    ("Zenput tareas", "zenput", "zenput_tasks", "account_name", "DATE(date_created)", "1", False),
]


def fetch(cur, schema, table, branch, day, amount, since):
    cur.execute(
        f"SELECT {branch}, {day}, COUNT(*), ROUND(SUM({amount}), 2) FROM `{schema}`.`{table}` "
        f"WHERE {day} >= %s GROUP BY 1, 2", (since,))
    return {(str(b), d): (n, float(v or 0)) for b, d, n, v in cur.fetchall() if d is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=6, help="days back to compare (default 6)")
    args = parser.parse_args()
    since = date.today() - timedelta(days=args.days)

    schemas = {"wansoft": os.getenv("WANSOFT_DB_NAME", ""), "zenput": os.getenv("ZENPUT_DB_NAME", "")}
    for kind, test in schemas.items():
        if not test.endswith("_prueba"):
            sys.exit(f"Refusing to run: {kind.upper()}_DB_NAME is '{test}', not a _prueba database.")

    conns = {kind: get_mysql_connection(kind) for kind in schemas}
    start_dates = load_costs_odoo_start_dates()
    total_diff = 0
    for name, kind, table, branch, day, amount, odoo_gap in CHECKS:
        cur = conns[kind].cursor()
        prod = fetch(cur, kind, table, branch, day, amount, since)
        test = fetch(cur, schemas[kind], table, branch, day, amount, since)
        last_common = min(max((d for _, d in prod), default=since), max((d for _, d in test), default=since))
        same = expected = odoo_cost = 0
        diffs = []
        for key in sorted(set(prod) | set(test)):
            if key[1] > last_common:
                continue
            p, t = prod.get(key, (0, 0.0)), test.get(key, (0, 0.0))
            if p[0] == t[0] and abs(p[1] - t[1]) < 0.01:
                same += 1
                continue
            label, is_odoo = branch_label(key[0])
            if odoo_gap is True and is_odoo and t[0] <= p[0]:
                expected += 1
                continue
            if odoo_gap == "cost" and t[0] and costs_source(label, key[1], start_dates) == "odoo":
                odoo_cost += 1
                continue
            diffs.append((label, key[1], p, t))
        total_diff += len(diffs)
        extra = f", {odoo_cost} ODOO_COST" if odoo_cost else ""
        print(f"\n== {name} ({table}) through {last_common}: {same} same, {expected} expected (Odoo branch){extra}, {len(diffs)} DIFF")
        for label, d, p, t in diffs[:60]:
            pct = f"{(t[1] - p[1]) / p[1] * 100:+.2f}%" if p[1] else "n/a"
            print(f"   DIFF {d} {label[:32]:32s} prod {p[0]:>6} ${p[1]:>14,.2f} | prueba {t[0]:>6} ${t[1]:>14,.2f} | {pct}")
        if len(diffs) > 60:
            print(f"   ... {len(diffs) - 60} more")
    print(f"\nTotal DIFF groups: {total_diff}")


if __name__ == "__main__":
    main()
