"""Remove stale duplicate Wansoft invoices and make IdDocumento unique in getexpenses_factura.

    python -m scripts.dedupe_getexpenses_factura            # dry run (default)
    python -m scripts.dedupe_getexpenses_factura --apply

IdDocumento is Wansoft's global document id and the only usable identifier of
getexpenses_factura (`id` is always 0, Factura_Id / Egresos_Id are never
filled, UUID is empty in 56% of rows; tukanmx asked on 2026-10-20). It was
unique except for 90 Coyoacán invoices of 2026-01-28..02-09 stored twice: once
under the branch's old name "La Esquina Coyoacán" and once under the current
"Fonda Argentina - Coyoacan" (the name getExpenses.py writes). The old-name
rows are stale: the current-name copies match Wansoft's live status in all 90
cases (wansoft_expense_live_status), while 18 old-name copies still say
"Por pagar" for invoices Wansoft has rejected, and 31 carry an older folio.

--apply, in one run:
  1. copies the stale rows to getexpenses_factura_dedupe_backup_20261020;
  2. deletes them (only when the current-name copy of the same IdDocumento
     exists);
  3. stops if any IdDocumento is still duplicated, otherwise adds the unique
     key uq_getexpenses_factura_iddocumento (IdDocumento).
Running it again does nothing (no stale rows, key already there). The ALTER
gives up after 60 s if a long query holds the table (on dev an orphan query
made it wait 10 minutes); then run --apply again.

After this, legacy getExpenses.py (which looks rows up by IdDocumento +
Sucursal) gets an error for a day if Wansoft ever returned an existing
IdDocumento under another branch name: that day is logged as failed and the
others continue. On 2026-10-20 no document was listed by two subsidiaries.

Writes to the database the .env points at: on the tasks VM that is production.
"""
import argparse

from core.database.mysql import get_db_connection

TABLE = "getexpenses_factura"
BACKUP = "getexpenses_factura_dedupe_backup_20261020"
UNIQUE_KEY = "uq_getexpenses_factura_iddocumento"
LOCK_WAIT_SECONDS = 60
# Old branch name -> name getExpenses.py writes today.
STALE_BRANCH_NAMES = {"La Esquina Coyoacán": "Fonda Argentina - Coyoacan"}

STALE_ROWS = f"""
    FROM {TABLE} s
    WHERE s.Sucursal = %s
      AND EXISTS (SELECT 1 FROM {TABLE} c WHERE c.IdDocumento = s.IdDocumento AND c.Sucursal = %s)
"""


def duplicated_documents(cur):
    cur.execute(f"SELECT IdDocumento, COUNT(*) FROM {TABLE} GROUP BY IdDocumento HAVING COUNT(*) > 1")
    return cur.fetchall()


def has_unique_key(cur):
    cur.execute(f"SHOW INDEX FROM {TABLE} WHERE Key_name = %s", (UNIQUE_KEY,))
    return bool(cur.fetchall())


def main(apply=False):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT @@hostname, DATABASE()")
        host, database = cur.fetchone()
        print(f"Database: {database} on {host}")

        stale = {}
        for old, current in STALE_BRANCH_NAMES.items():
            cur.execute(f"SELECT s.IdDocumento, s.Estatus, s.Folio {STALE_ROWS}", (old, current))
            stale[old] = cur.fetchall()
            print(f"Stale rows under '{old}' with a copy under '{current}': {len(stale[old])}")
        dups = duplicated_documents(cur)
        print(f"Duplicated IdDocumento now: {len(dups)}; unique key present: {has_unique_key(cur)}")

        if not apply:
            print("Dry run: nothing written. Use --apply to back up, delete and add the unique key.")
            return 0

        deleted = 0
        for old, current in STALE_BRANCH_NAMES.items():
            ids = [row[0] for row in stale[old]]
            if not ids:
                continue
            # MariaDB cannot DELETE from a table that a subquery of the same statement
            # reads, so the ids found above are used; backup and delete commit together.
            marks = ", ".join(["%s"] * len(ids))
            cur.execute(f"CREATE TABLE IF NOT EXISTS {BACKUP} LIKE {TABLE}")
            cur.execute(f"SELECT IdDocumento FROM {BACKUP} WHERE Sucursal = %s", (old,))
            backed_up = {row[0] for row in cur.fetchall()}
            to_copy = [i for i in ids if i not in backed_up]
            if to_copy:
                cur.execute(f"INSERT INTO {BACKUP} SELECT * FROM {TABLE} WHERE Sucursal = %s AND IdDocumento IN "
                            f"({', '.join(['%s'] * len(to_copy))})", [old] + to_copy)
            cur.execute(f"DELETE FROM {TABLE} WHERE Sucursal = %s AND IdDocumento IN ({marks})", [old] + ids)
            deleted += cur.rowcount
        conn.commit()
        print(f"Deleted {deleted} stale rows (copied first to {BACKUP})")

        dups = duplicated_documents(cur)
        if dups:
            print(f"[ERROR] {len(dups)} IdDocumento still duplicated, unique key NOT added: {dups[:10]}")
            return 1
        if has_unique_key(cur):
            print(f"Unique key {UNIQUE_KEY} already present")
        else:
            # An ALTER waiting for a metadata lock (any long query on the table)
            # also blocks every new read of it; give up after a minute instead.
            cur.execute(f"SET SESSION lock_wait_timeout = {LOCK_WAIT_SECONDS}")
            try:
                cur.execute(f"ALTER TABLE {TABLE} ADD UNIQUE KEY {UNIQUE_KEY} (IdDocumento)")
            except Exception as exc:
                print(f"[ERROR] unique key NOT added ({exc}); the stale rows are already deleted. "
                      f"Check SHOW PROCESSLIST for long queries on {TABLE} and run --apply again.")
                return 1
            print(f"Unique key {UNIQUE_KEY} added")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="back up, delete the stale rows and add the unique key")
    raise SystemExit(main(parser.parse_args().apply))
