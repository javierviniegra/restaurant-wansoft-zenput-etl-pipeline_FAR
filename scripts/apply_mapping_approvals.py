"""
Approve the Odoo -> Wansoft product equivalences the owner reviewed by hand
(seeds/odoo_wansoft_mapping_approvals.csv; first batch: tukan's P71,
2026-11-20, 106 pairs; P72-P74, 2026-11-23: Baileys, Tallarines, Azucar Glass, Jarabe de Jamaica, Arugula).

For each (odoo_product_id, wansoft_code) of the seed, in
inventory_mapping_dictionary (domain 'inventory'):
- a row with that pair is set to 'approved' (whatever its status);
- with none, a new 'approved' row is inserted with the current Odoo name
  (odoo_stock_move_snapshot) and the Wansoft name/department (dim_product);
  when another Odoo product already holds that name with that Wansoft code
  (the unique key is domain + odoo_product_name + wansoft_code), the name
  gets " (Odoo <id>)" appended;
- any other row of the same Odoo product that is approved or pending is set
  to 'rejected': one approved Wansoft code per Odoo product, or the purchases
  ETL duplicates its lines (bug #44) and analytics_odoo_product_code leaves
  the product out.
One Wansoft code may have several Odoo products (e.g. three Chandon Spritz).
The nightly movements build then publishes them in analytics_odoo_product_code.

seeds/odoo_wansoft_mapping_rejections.csv (same columns) lists pairs the
owner said are NOT the same product, with no correct code to give instead
(tukan's P76, 2026-11-23: Jugo de Mango 355 Ml is not the 250 Ml one): any
approved or pending row with that pair is set to 'rejected'. Pairs, not row
ids, because ids differ between dev and prod. A pair in both seeds is an error.

Dry run by default; --apply writes.

    python -m scripts.apply_mapping_approvals
    python -m scripts.apply_mapping_approvals --apply
"""
import argparse
import csv
import unicodedata
from pathlib import Path

from core.database.mysql import get_db_connection

SEED = Path(__file__).resolve().parents[1] / "seeds" / "odoo_wansoft_mapping_approvals.csv"
REJECT_SEED = SEED.with_name("odoo_wansoft_mapping_rejections.csv")
SOURCE = "owner_review"


def key(name, code):
    """The unique key as the table's utf8mb4_general_ci collation compares it: no case, no accents, no trailing spaces."""
    fold = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().rstrip()
    return fold(name), fold(code)


def load_seed(path=SEED):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [dict(r, odoo_product_id=int(r["odoo_product_id"])) for r in csv.DictReader(f)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    args = parser.parse_args(argv)

    seed = load_seed()
    conn = get_db_connection()
    cur = conn.cursor()
    ids = sorted({s["odoo_product_id"] for s in seed})
    marks = ",".join(["%s"] * len(ids))
    cur.execute(f"""SELECT id, odoo_product_id, wansoft_code, mapping_status FROM inventory_mapping_dictionary
                    WHERE domain = 'inventory' AND odoo_product_id IN ({marks})""", ids)
    existing = cur.fetchall()
    cur.execute(f"""SELECT odoo_product_id, MAX(product_display_name) FROM odoo_stock_move_snapshot
                    WHERE odoo_product_id IN ({marks}) GROUP BY odoo_product_id""", ids)
    odoo_names = dict(cur.fetchall())
    cur.execute(f"""SELECT CAST(odoo_product_id AS DECIMAL(20,0)), MAX(odoo_product_name), MAX(odoo_category)
                    FROM dim_product WHERE CAST(NULLIF(odoo_product_id, '') AS DECIMAL(20,0)) IN ({marks})
                    GROUP BY 1""", ids)
    dim_odoo = {int(r[0]): (r[1], r[2]) for r in cur.fetchall()}
    codes = sorted({s["wansoft_code"] for s in seed})
    cur.execute(f"""SELECT wansoft_code, MAX(wansoft_product_name), MAX(wansoft_department) FROM dim_product
                    WHERE wansoft_code IN ({",".join(["%s"] * len(codes))}) GROUP BY wansoft_code""", codes)
    dim_wansoft = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    cur.execute("SELECT odoo_product_name, wansoft_code FROM inventory_mapping_dictionary WHERE domain = 'inventory'")
    taken_keys = {key(n, w) for n, w in cur.fetchall()}

    approve, insert, reject = [], [], []
    for s in seed:
        oid, code = s["odoo_product_id"], s["wansoft_code"]
        note = f"[{s['decided_on']}] {s['decided_by']}: {s['note']}"
        rows = [r for r in existing if r[1] == oid]
        same = [r for r in rows if r[2] == code]
        if same:
            approve += [(r[0], note) for r in same if r[3] != "approved"]
        else:
            name = odoo_names.get(oid) or dim_odoo.get(oid, (None, None))[0] or f"Odoo {oid}"
            if key(name, code) in taken_keys:
                name = f"{name} (Odoo {oid})"
            taken_keys.add(key(name, code))
            wname, wdept = dim_wansoft.get(code, (None, None))
            insert.append((oid, name, dim_odoo.get(oid, (None, None))[1], code, wname, wdept, note))
        reject += [(r[0], f"[{s['decided_on']}] {s['decided_by']}: rejected, Odoo {oid} is {code}")
                   for r in rows if r[2] != code and r[3] in ("approved", "pending_review")]

    print(f"{len(seed)} pairs in the seed: {len(approve)} rows to approve, {len(insert)} to insert, "
          f"{len(reject)} other rows of the same Odoo products to reject")

    not_same = load_seed(REJECT_SEED)
    both = {(s["odoo_product_id"], s["wansoft_code"]) for s in seed} & \
           {(s["odoo_product_id"], s["wansoft_code"]) for s in not_same}
    if both:
        raise SystemExit(f"pairs in both the approvals and the rejections seed: {sorted(both)}")
    n_before = len(reject)
    for s in not_same:
        cur.execute("""SELECT id FROM inventory_mapping_dictionary WHERE domain = 'inventory'
                       AND odoo_product_id = %s AND wansoft_code = %s
                       AND mapping_status IN ('approved', 'pending_review')""",
                    (s["odoo_product_id"], s["wansoft_code"]))
        reject += [(r[0], f"[{s['decided_on']}] {s['decided_by']}: rejected, {s['note']}") for r in cur.fetchall()]
    print(f"{len(not_same)} pairs in the rejections seed: {len(reject) - n_before} rows to reject")
    for i in insert[:5]:
        print("  insert", i[:6])
    if not args.apply:
        print("Dry run: nothing written. Use --apply.")
        conn.close()
        return 0
    for rid, note in approve:
        cur.execute("""UPDATE inventory_mapping_dictionary SET mapping_status = 'approved',
                       notes = CONCAT_WS(' | ', NULLIF(notes, ''), %s) WHERE id = %s""", (note, rid))
    for rid, note in reject:
        cur.execute("""UPDATE inventory_mapping_dictionary SET mapping_status = 'rejected',
                       notes = CONCAT_WS(' | ', NULLIF(notes, ''), %s) WHERE id = %s""", (note, rid))
    cur.executemany("""INSERT INTO inventory_mapping_dictionary
                       (domain, odoo_product_id, odoo_product_name, odoo_category_name, wansoft_code,
                        wansoft_product_name, wansoft_department, mapping_source, mapping_status, notes)
                       VALUES ('inventory', %s, %s, %s, %s, %s, %s, %s, 'approved', %s)""",
                    [(i[0], i[1], i[2], i[3], i[4], i[5], SOURCE, i[6]) for i in insert])
    conn.commit()
    print(f"Approved {len(approve)}, inserted {len(insert)}, rejected {len(reject)}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
