"""Reverts the bulk approvals of 2026-10-08 that left an Odoo product with two approved mappings (bug #44).

    python -m scripts.repair_duplicate_approved_mappings                     # dry run: list only
    python -m scripts.repair_duplicate_approved_mappings --apply --expect N  # write, only if N rows qualify

The first run of scripts/approve_exact_code_base_mappings.py approved every
encoding copy of a pair and did not check for an Odoo product proposed with
two Wansoft codes, so some Odoo products ended with two approved rows. The
purchases ETL merges the dictionary on the Odoo product id: every purchase
line of those products was duplicated and the nightly load of 2026-10-09
failed (the snapshot was left empty and the canonical layer froze).

Only rows approved by that bulk run (their notes carry its marker) are
touched, and only on Odoo products that now have more than one approved row:
  - all approved rows of the product share one Wansoft code: keep one (the
    clean name over a '??'-damaged copy, then the oldest), revert the other
    bulk-approved copies to 'pending_review';
  - the approved rows carry different codes (raw 1000- vs clean 2000- cuts):
    revert every bulk-approved row of that product to 'pending_review'; the
    owner decides which code is right.
Rows approved before 2026-10-08 are never changed. Uses the database ENV
points at: on the tasks VM that is production.
"""
import argparse
import sys
from collections import defaultdict

from core.database.mysql import get_db_connection

BULK_MARKER = "bulk-approved 2026-10-08"
NOTE = "reverted to pending 2026-10-09: second approved row of the same Odoo product (bug #44)"


def plan(rows):
    by_product = defaultdict(list)
    for r in rows:
        by_product[r["odoo_product_id"]].append(r)
    revert, keep = [], []
    for product_id, group in sorted(by_product.items()):
        if len(group) < 2 or not any(BULK_MARKER in (r["notes"] or "") for r in group):
            continue
        bulk = [r for r in group if BULK_MARKER in (r["notes"] or "")]
        if len({r["wansoft_code"] for r in group}) == 1:
            group.sort(key=lambda r: ("??" in (r["wansoft_product_name"] or ""), r["id"]))
            winner = group[0]
            keep.append(winner)
            revert += [r for r in bulk if r["id"] != winner["id"]]
        else:
            revert += bulk
    return revert, keep


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the reverts")
    parser.add_argument("--expect", type=int, help="with --apply: number of rows that must be reverted")
    args = parser.parse_args(argv)
    if args.apply and args.expect is None:
        parser.error("--apply needs --expect N (the count shown by the dry run)")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT DATABASE() AS db, @@hostname AS host")
    where = cur.fetchone()
    print(f"Database: {where['db']} on {where['host']}")
    cur.execute(
        """
        SELECT id, odoo_product_id, wansoft_code, wansoft_product_name, notes
        FROM inventory_mapping_dictionary
        WHERE mapping_status = 'approved' AND odoo_product_id IS NOT NULL
        """
    )
    revert, keep = plan(cur.fetchall())

    print(f"\nKept approved ({len(keep)}):")
    for r in keep:
        print(f"  id {r['id']:>5} odoo {r['odoo_product_id']} {r['wansoft_code']} {r['wansoft_product_name']}")
    print(f"\nRevert to pending_review ({len(revert)}):")
    for r in revert:
        print(f"  id {r['id']:>5} odoo {r['odoo_product_id']} {r['wansoft_code']} {r['wansoft_product_name']}")

    if not args.apply:
        print(f"\nDry run: nothing written. To apply: --apply --expect {len(revert)}")
        return 0
    if len(revert) != args.expect:
        print(f"\nNOT APPLIED: {len(revert)} rows qualify, --expect said {args.expect}")
        return 1

    ids = [r["id"] for r in revert]
    marks = ", ".join(["%s"] * len(ids))
    cur.execute(
        f"""
        UPDATE inventory_mapping_dictionary
        SET mapping_status = 'pending_review',
            notes = CONCAT_WS(' | ', NULLIF(notes, ''), %s),
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({marks}) AND mapping_status = 'approved'
        """,
        [NOTE, *ids],
    )
    if cur.rowcount != len(ids):
        conn.rollback()
        print(f"\nROLLBACK: updated {cur.rowcount} rows, expected {len(ids)}")
        return 1
    conn.commit()
    print(f"\nREVERTED {cur.rowcount} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
