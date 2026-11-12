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

Owner, 2026-11-12 (tukan's P68): those 13, plus the 'pending_review'
duplicate of one of them, are rejected too (IN_USE_IDS). Each links an Odoo
menu item (5100-) to a Wansoft supply (1000-), e.g. "Bife de Chorizo 800 Grs"
to "Ate de Tejocote"; none has a 2026 Odoo purchase, and their stock moves
were already left out of analytics_inventory_movements
(EXCLUDED_DICTIONARY_IDS there). dim_product then shows the Odoo item and the
Wansoft supply as separate rows.

Dry run by default; --apply writes. Only rows still in the batch's allowed
statuses change.

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

IN_USE_IDS = [70, 120, 138, 144, 189, 233, 243, 262, 291, 346, 352, 353, 485, 1346]
IN_USE_NOTE = ("[2026-11-12] rejected by owner: the Odoo product is a menu item (5100-) linked to a "
               "Wansoft supply (1000-) only by the code suffix; no 2026 Odoo purchase.")

# (ids, note, statuses that may still change)
BATCHES = [
    (DICTIONARY_IDS, NOTE, ("approved",)),
    (IN_USE_IDS, IN_USE_NOTE, ("approved", "pending_review")),
]


def reject_batch(cur, ids, note, statuses, apply):
    marks = ",".join(["%s"] * len(ids))
    cur.execute(f"""
        SELECT id, odoo_product_id, odoo_product_name, wansoft_code, wansoft_product_name, mapping_status
        FROM inventory_mapping_dictionary WHERE id IN ({marks}) ORDER BY id
    """, ids)
    rows = cur.fetchall()
    pending = [r for r in rows if r[5] in statuses]
    print(f"{len(rows)} of {len(ids)} ids found; {len(pending)} still {'/'.join(statuses)}")
    for r in rows:
        if r[5] not in statuses:
            print(f"  skip id {r[0]} (status {r[5]})")
    if not apply or not pending:
        return 0
    status_marks = ",".join(["%s"] * len(statuses))
    cur.execute(f"""
        UPDATE inventory_mapping_dictionary
        SET mapping_status = 'rejected',
            notes = CONCAT_WS(' | ', NULLIF(notes, ''), %s),
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({",".join(["%s"] * len(pending))}) AND mapping_status IN ({status_marks})
    """, [note] + [r[0] for r in pending] + list(statuses))
    return cur.rowcount


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    args = parser.parse_args(argv)

    conn = get_db_connection()
    cur = conn.cursor()
    rejected = sum(reject_batch(cur, ids, note, statuses, args.apply) for ids, note, statuses in BATCHES)
    if not args.apply:
        print("Dry run: nothing written. Use --apply.")
    else:
        conn.commit()
        print(f"Rejected: {rejected}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
