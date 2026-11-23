"""
Remove the copies of a cash closing already loaded in getglobalcashclosing
(tukan's P77, owner 2026-11-23). The rule is in
extract/costs/cash_closing_copies.py; since then the loader does not insert
new copies.

Each copy is first saved, with the id of the corte it copies and when it was
removed, in getglobalcashclosing_removed_copies, then deleted. The first corte
of each group stays. A copy deleted within the loader's look-back window is
not inserted again: the loader skips it as a copy.

Dry run by default (counts and sales per year); --apply writes.

    python -m scripts.remove_cash_closing_copies
    python -m scripts.remove_cash_closing_copies --apply
"""
import argparse

from core.database.mysql import get_db_connection
from extract.costs.cash_closing_copies import COPIES_SQL

BACKUP = "getglobalcashclosing_removed_copies"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    args = parser.parse_args(argv)

    conn = get_db_connection(target="wansoft")
    cur = conn.cursor()
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_cash_copies")
    cur.execute(f"CREATE TEMPORARY TABLE tmp_cash_copies (PRIMARY KEY (copy_id)) AS {COPIES_SQL}")
    cur.execute("""SELECT YEAR(g.fecha_corte), COUNT(*), COUNT(DISTINCT t.original_id), SUM(g.total_ventas)
                   FROM tmp_cash_copies t JOIN getglobalcashclosing g ON g.id = t.copy_id
                   GROUP BY 1 ORDER BY 1""")
    rows = cur.fetchall()
    for y, n, groups, sales in rows:
        print(f"  {y}: {n} copies of {groups} cortes, {sales:,.2f} of repeated sales")
    total = sum(r[1] for r in rows)
    print(f"{total} copies in total")
    if not args.apply or not total:
        if not args.apply:
            print("Dry run: nothing written. Use --apply.")
        conn.close()
        return 0

    cur.execute(f"""CREATE TABLE IF NOT EXISTS {BACKUP} LIKE getglobalcashclosing""")
    for col, ddl in (("original_id", "INT NULL"), ("removed_at", "DATETIME NULL")):
        cur.execute("""SELECT COUNT(*) FROM information_schema.columns
                       WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s""", (BACKUP, col))
        if not cur.fetchone()[0]:
            cur.execute(f"ALTER TABLE {BACKUP} ADD COLUMN {col} {ddl}")
    cur.execute(f"""SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position) FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = 'getglobalcashclosing'""")
    cols = cur.fetchone()[0]
    cur.execute(f"""INSERT IGNORE INTO {BACKUP} ({cols}, original_id, removed_at)
                    SELECT {", ".join("g." + c for c in cols.split(","))}, t.original_id, NOW()
                    FROM tmp_cash_copies t JOIN getglobalcashclosing g ON g.id = t.copy_id""")
    saved = cur.rowcount
    cur.execute("DELETE g FROM getglobalcashclosing g JOIN tmp_cash_copies t ON t.copy_id = g.id")
    deleted = cur.rowcount
    conn.commit()
    print(f"Saved {saved} in {BACKUP}, deleted {deleted} from getglobalcashclosing")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
