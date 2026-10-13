"""
Reject 69 approved Odoo -> Wansoft mappings whose Odoo product is another
product and was never used (owner, 2026-10-13).

Found while building analytics_inventory_movements: 106 approved mappings
carry an Odoo product id whose Odoo name today differs from the dictionary.
24 are the same product renamed (kept). 82 point at a different product,
almost always an Odoo menu item (families 5100-/5200-) matched to a Wansoft
supply (1000-) only because the rest of the code coincides, or historical
ids from an earlier Odoo database (e.g. 3213 "Back Rib" is today "Te Bombay
Chai"). Review: reports/inventory_mapping_review/revision_mapeos_odoo_wansoft_20261013.xlsx.

These 69 of the 82 have no Odoo stock move, ever, and no confirmed Odoo
purchase in 2026: the link is wrong and unused. They become 'rejected', the
terminal status the weekly mapping job never touches
(analysis/save_product_mapping.py) and approve_exact_code_base_mappings.py
never re-approves. The Wansoft product itself is untouched (62 of these
Wansoft codes are in use in 2026). The other 13 (in use) wait for the
owner's review.

Dry run by default; --apply writes. Only rows still 'approved' change.

    python -m scripts.reject_mismapped_unused_mappings
    python -m scripts.reject_mismapped_unused_mappings --apply
"""
import argparse

from core.database.mysql import get_db_connection

DICTIONARY_IDS = [
    17, 19, 20, 28, 29, 31, 33, 34, 35, 45, 57, 58, 71, 81, 82, 84, 92, 102, 118, 123,
    125, 126, 135, 155, 173, 207, 219, 256, 259, 293, 344, 345, 347, 348, 349, 350, 351,
    354, 355, 357, 361, 362, 363, 364, 365, 388, 389, 394, 404, 405, 416, 418, 426, 448,
    469, 472, 476, 477, 482, 483, 484, 486, 487, 490, 491, 494, 497, 500, 1347,
]
NOTE = ("[2026-10-13] rejected by owner: the Odoo product id is another product "
        "(name mismatch) and has no Odoo stock move or 2026 purchase.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    args = parser.parse_args(argv)

    conn = get_db_connection()
    cur = conn.cursor()
    marks = ",".join(["%s"] * len(DICTIONARY_IDS))
    cur.execute(f"""
        SELECT id, odoo_product_id, odoo_product_name, wansoft_code, wansoft_product_name, mapping_status
        FROM inventory_mapping_dictionary WHERE id IN ({marks}) ORDER BY id
    """, DICTIONARY_IDS)
    rows = cur.fetchall()
    approved = [r for r in rows if r[5] == "approved"]
    print(f"{len(rows)} of {len(DICTIONARY_IDS)} ids found; {len(approved)} still approved")
    for r in rows:
        if r[5] != "approved":
            print(f"  skip id {r[0]} (status {r[5]})")
    if not args.apply:
        print("Dry run: nothing written. Use --apply.")
        return 0
    if approved:
        cur.execute(f"""
            UPDATE inventory_mapping_dictionary
            SET mapping_status = 'rejected',
                notes = CONCAT_WS(' | ', NULLIF(notes, ''), %s),
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({",".join(["%s"] * len(approved))}) AND mapping_status = 'approved'
        """, [NOTE] + [r[0] for r in approved])
        conn.commit()
        print(f"Rejected: {cur.rowcount}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
