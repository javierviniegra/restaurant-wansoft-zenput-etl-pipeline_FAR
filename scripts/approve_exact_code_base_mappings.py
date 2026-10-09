"""Bulk-approves the weekly job's safest product mappings (owner, 2026-10-08, "A").

    python -m scripts.approve_exact_code_base_mappings                     # dry run: list only
    python -m scripts.approve_exact_code_base_mappings --apply --expect N  # write, only if N rows qualify

The weekly product-mapping job (pipelines/jobs/product_mapping_backlog_job.py)
proposes links between a Wansoft product code and its Odoo product and leaves
them 'pending_review' in inventory_mapping_dictionary. A row qualifies for
bulk approval when ALL of these hold:
  - mapping_status = 'pending_review' and mapping_source =
    'weekly_auto_match:exact_code_base' (same code base on both sides);
  - similarity_score >= 99 and an Odoo product id is present;
  - the Wansoft and Odoo names are identical once accents, case, spaces and
    punctuation are ignored (the '??' encoding damage is ignored too: it hits
    both names alike);
  - no conflict: the Wansoft code has no approved row already (on 2026-10-08,
    spirits approved against an older Odoo product: the owner decides which
    one is current), the Odoo product is not approved for another Wansoft code
    (meat cuts: raw vs clean), and the code is not proposed for two different
    Odoo products.
  - the Odoo product is not proposed for two different Wansoft codes (raw
    1000- vs clean/"Orden" 2000- cuts: the owner decides).
At most ONE row is approved per Odoo product (bug #44, 2026-10-09): the
purchases ETL merges the dictionary on the Odoo product id, so two approved
rows of one product duplicated its purchase lines and the load failed. Of
the copies of a pair that differ only by the '??' encoding damage, the one
with the clean name is approved and the others stay pending. (The first run,
on 2026-10-08, approved every copy; the 2026-10-09 repair reverted them.)

Approval feeds the canonical purchase enrichment and the inventory mapping on
the next night. It never changes what counts in the business purchase views.
Uses the database ENV points at: on the tasks VM that is production.
"""
import argparse
import re
import sys
import unicodedata
from collections import defaultdict

from core.database.mysql import get_db_connection

SOURCE = "weekly_auto_match:exact_code_base"
NOTE = "bulk-approved 2026-10-08 (owner): exact_code_base, identical names, no conflict"


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def classify(rows):
    approved = [r for r in rows if r["mapping_status"] == "approved"]
    approved_codes = {r["wansoft_code"] for r in approved}
    approved_odoo_code = defaultdict(set)
    for r in approved:
        if r["odoo_product_id"] is not None:
            approved_odoo_code[r["odoo_product_id"]].add(r["wansoft_code"])

    approved_odoo = {r["odoo_product_id"] for r in approved if r["odoo_product_id"] is not None}
    pending = [r for r in rows if r["mapping_status"] == "pending_review" and r["mapping_source"] == SOURCE]
    odoo_by_code = defaultdict(set)
    code_by_odoo = defaultdict(set)
    for r in pending:
        odoo_by_code[r["wansoft_code"]].add(r["odoo_product_id"])
        code_by_odoo[r["odoo_product_id"]].add(r["wansoft_code"])
    # Clean name first, then oldest: the first copy of each Odoo product wins.
    pending.sort(key=lambda r: ("??" in (r["wansoft_product_name"] or ""), r["id"]))
    chosen_odoo = set()

    qualify, skipped = [], []
    for r in pending:
        if r["odoo_product_id"] is None or (r["similarity_score"] or 0) < 99:
            reason = "no Odoo product or similarity < 99"
        elif norm(r["wansoft_product_name"]) != norm(r["odoo_product_name"]):
            reason = "names differ"
        elif r["wansoft_code"] in approved_codes:
            reason = "Wansoft code already approved"
        elif approved_odoo_code.get(r["odoo_product_id"], set()) - {r["wansoft_code"]}:
            reason = "Odoo product approved for another code"
        elif len(odoo_by_code[r["wansoft_code"]]) > 1:
            reason = "code proposed for two Odoo products"
        elif len(code_by_odoo[r["odoo_product_id"]]) > 1:
            reason = "Odoo product proposed for two codes"
        elif r["odoo_product_id"] in approved_odoo:
            reason = "Odoo product already approved"
        elif r["odoo_product_id"] in chosen_odoo:
            reason = "copy of a pair already chosen (one row per Odoo product)"
        else:
            chosen_odoo.add(r["odoo_product_id"])
            qualify.append(r)
            continue
        skipped.append((reason, r))
    return qualify, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the approvals")
    parser.add_argument("--expect", type=int, help="with --apply: number of rows that must qualify")
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
        SELECT id, wansoft_code, wansoft_product_name, odoo_product_id, odoo_product_name,
               mapping_source, mapping_status, similarity_score
        FROM inventory_mapping_dictionary
        """
    )
    qualify, skipped = classify(cur.fetchall())

    print(f"\nSkipped ({len(skipped)}):")
    for reason, r in sorted(skipped, key=lambda x: (x[0], x[1]["wansoft_code"])):
        print(f"  [{reason}] id {r['id']} {r['wansoft_code']} {r['wansoft_product_name']} -> odoo {r['odoo_product_id']}")
    print(f"\nQualify ({len(qualify)}):")
    for r in sorted(qualify, key=lambda x: x["wansoft_code"]):
        print(f"  id {r['id']:>5} {r['wansoft_code']:24} {str(r['wansoft_product_name'])[:40]:40} -> odoo {r['odoo_product_id']}")

    if not args.apply:
        print(f"\nDry run: nothing written. To apply: --apply --expect {len(qualify)}")
        return 0
    if len(qualify) != args.expect:
        print(f"\nNOT APPLIED: {len(qualify)} rows qualify, --expect said {args.expect}")
        return 1

    ids = [r["id"] for r in qualify]
    marks = ", ".join(["%s"] * len(ids))
    cur.execute(
        f"""
        UPDATE inventory_mapping_dictionary
        SET mapping_status = 'approved',
            notes = CONCAT_WS(' | ', NULLIF(notes, ''), %s),
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({marks}) AND mapping_status = 'pending_review'
        """,
        [NOTE, *ids],
    )
    if cur.rowcount != len(ids):
        conn.rollback()
        print(f"\nROLLBACK: updated {cur.rowcount} rows, expected {len(ids)}")
        return 1
    conn.commit()
    print(f"\nAPPROVED {cur.rowcount} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
