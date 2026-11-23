"""
Take the removed cash-closing copies out of costeoMensual's CostoDeCortesías
and CostoDeCancelaciones (tukan's P77, owner 2026-11-23).

Since 2026-09-17 descargarCostoWansoft.py fills those two columns with the
month-to-date sum of getglobalcashclosing, so the copies removed by
scripts/remove_cash_closing_copies.py were counted in them. Rows inside the
costs look-back window are recomputed by the nightly run; older ones keep the
inflated value. This script fixes only the rows whose stored value is exactly
the clean month-to-date sum plus the removed copies' sum (both columns), and
writes the clean sum. No other row or column changes.

Dry run by default; --apply writes.

    python -m scripts.fix_costs_cash_closing_copies
    python -m scripts.fix_costs_cash_closing_copies --apply
"""
import argparse

from core.database.mysql import get_db_connection

MTD = """(SELECT SUM(g.{a} + g.{b}) FROM {table} g
          WHERE g.subsidiary_id = m.subsidiary_id
            AND g.fecha_corte >= DATE_FORMAT(m.created_at, '%Y-%m-01')
            AND g.fecha_corte <= CONCAT(DATE(m.created_at), ' 23:59:59'))"""

ROWS_SQL = f"""
    SELECT m.id, m.subsidiary_name, DATE(m.created_at), m.`CostoDeCortesías`, m.CostoDeCancelaciones,
           {MTD.format(a="cortesias_en_cuentas", b="cortesias_en_platillos", table="getglobalcashclosing")},
           {MTD.format(a="cancelaciones_en_cuentas", b="cancelaciones_en_platillos", table="getglobalcashclosing")},
           {MTD.format(a="cortesias_en_cuentas", b="cortesias_en_platillos", table="getglobalcashclosing_removed_copies")},
           {MTD.format(a="cancelaciones_en_cuentas", b="cancelaciones_en_platillos", table="getglobalcashclosing_removed_copies")}
    FROM costeoMensual m
    WHERE m.created_at >= '2026-09-01'
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    args = parser.parse_args(argv)

    conn = get_db_connection(target="wansoft")
    cur = conn.cursor()
    cur.execute(ROWS_SQL)
    f = lambda x: float(x or 0)
    fix = []
    for rid, name, day, cort, canc, cort_ok, canc_ok, cort_cp, canc_cp in cur.fetchall():
        if not (f(cort_cp) or f(canc_cp)):
            continue
        if f(cort) == f(cort_ok) and f(canc) == f(canc_ok):
            continue
        if abs(f(cort) - f(cort_ok) - f(cort_cp)) <= 0.01 and abs(f(canc) - f(canc_ok) - f(canc_cp)) <= 0.01:
            fix.append((rid, name, day, f(cort), f(cort_ok), f(canc), f(canc_ok)))
    print(f"{len(fix)} costeoMensual rows include removed copies")
    months = {}
    for r in fix:
        months[(r[1], r[2].strftime("%Y-%m"))] = r
    for (name, month), r in sorted(months.items()):
        print(f"  {name} {month}, last row {r[2]}: cortesias {r[3]:,.2f} -> {r[4]:,.2f}, "
              f"cancelaciones {r[5]:,.2f} -> {r[6]:,.2f}")
    if not args.apply or not fix:
        if not args.apply:
            print("Dry run: nothing written. Use --apply.")
        conn.close()
        return 0
    cur.executemany("UPDATE costeoMensual SET `CostoDeCortesías` = %s, CostoDeCancelaciones = %s WHERE id = %s",
                    [(str(r[4]), str(r[6]), r[0]) for r in fix])
    conn.commit()
    print(f"Updated {len(fix)} rows")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
