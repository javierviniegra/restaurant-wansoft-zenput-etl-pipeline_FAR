"""
Odoo vendor bills and credit notes (expenses domain, block 3:
docs/analytics-expense-invoices-design.md).

Loads every vendor bill (account.move in_invoice) and vendor credit note
(in_refund) of the group's companies into two raw tables:

- odoo_vendor_bill_snapshot: one row per bill, any state (draft, posted,
  cancel), so a bill that is cancelled or reset to draft changes here too;
  the analytics table keeps only posted ones.
- odoo_vendor_bill_line_snapshot: its product lines (what was bought, on
  which account) and tax lines (IVA, withholdings). For goods lines the
  account is the clearing account "Goods Received - No Invoices", so each
  line also carries its product category's expense account, read with the
  bill company's context (company-dependent field, see
  extract/purchases/odoo_purchase_category_totals.py).

The whole history of every company is kept; the analytics table applies
each branch's start date (odoo_company_migration_policy), as purchases do.

Amounts are in the company currency and in EXPENSE SIGN: a bill is positive,
a credit note negative (amount = -amount_*_signed on the header; balance on
the lines, where IVA is positive and withholdings negative).

CFDI UUID: Odoo's l10n_mx_edi_cfdi_uuid is almost always empty; the team
types the UUID in `ref` (95-100% of posted bills). cfdi_uuid takes the EDI
field, else `ref` when it is UUID-shaped; cfdi_uuid_source says which. The
supplier's own folio is in payment_reference.

Incremental: the first run reads everything; later runs read the bills
written since the last load (minus a safety margin) plus every stored bill
that is not settled yet (payment_state not_paid / partial / in_payment), so
a bill paid later updates even if its write_date did not move. A bill's
lines are deleted and written again whenever the bill is read. --full reads
everything again and removes the bills that no longer exist in Odoo.

    python -m extract.expenses.odoo_vendor_bills            # incremental
    python -m extract.expenses.odoo_vendor_bills --full     # everything again

Read-only against Odoo.
"""
import argparse
import re
from datetime import datetime, timedelta

from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection
from extract.inventory.odoo_stock_moves import chunks, group_companies, m2o

BILLS = "odoo_vendor_bill_snapshot"
LINES = "odoo_vendor_bill_line_snapshot"
MOVE_TYPES = ["in_invoice", "in_refund"]
OPEN_PAYMENT_STATES = ("not_paid", "partial", "in_payment")
MARGIN_DAYS = 3
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

BILL_FIELDS = [
    "name", "move_type", "state", "payment_state", "company_id", "partner_id", "commercial_partner_id",
    "ref", "payment_reference", "l10n_mx_edi_cfdi_uuid", "invoice_date", "invoice_date_due", "date",
    "invoice_origin", "currency_id", "amount_untaxed_signed", "amount_tax_signed", "amount_total_signed",
    "amount_residual_signed", "invoice_payment_term_id", "reversed_entry_id", "matched_payment_ids",
    "write_date",
]
LINE_FIELDS = [
    "move_id", "company_id", "display_type", "account_id", "product_id", "name", "quantity",
    "price_unit", "price_subtotal", "balance", "tax_line_id",
]

DDL = [
    f"""
    CREATE TABLE IF NOT EXISTS {BILLS} (
        odoo_move_id INT NOT NULL PRIMARY KEY,
        odoo_company_id INT NOT NULL,
        odoo_company_name VARCHAR(255) NULL,
        company_source_key VARCHAR(100) NULL,
        move_type VARCHAR(20) NOT NULL,
        state VARCHAR(20) NOT NULL,
        payment_state VARCHAR(20) NULL,
        move_name VARCHAR(100) NULL,
        ref VARCHAR(255) NULL,
        payment_reference VARCHAR(255) NULL,
        cfdi_uuid CHAR(36) NULL,
        cfdi_uuid_source VARCHAR(20) NULL,
        invoice_date DATE NULL,
        invoice_date_due DATE NULL,
        accounting_date DATE NULL,
        odoo_partner_id INT NULL,
        partner_name VARCHAR(255) NULL,
        odoo_commercial_partner_id INT NULL,
        vendor_name VARCHAR(255) NULL,
        vendor_rfc VARCHAR(20) NULL,
        invoice_origin VARCHAR(500) NULL,
        currency VARCHAR(10) NULL,
        amount_untaxed DECIMAL(18,2) NULL,
        amount_tax DECIMAL(18,2) NULL,
        amount_total DECIMAL(18,2) NULL,
        amount_residual DECIMAL(18,2) NULL,
        payment_term VARCHAR(255) NULL,
        reversed_entry_id INT NULL,
        payment_count INT NOT NULL DEFAULT 0,
        last_payment_date DATE NULL,
        odoo_write_date DATETIME NULL,
        loaded_at DATETIME NOT NULL,
        KEY idx_bill_company_date (company_source_key, invoice_date),
        KEY idx_bill_state (state, payment_state),
        KEY idx_bill_uuid (cfdi_uuid),
        KEY idx_bill_partner (odoo_commercial_partner_id),
        KEY idx_bill_write (odoo_write_date)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {LINES} (
        odoo_line_id INT NOT NULL PRIMARY KEY,
        odoo_move_id INT NOT NULL,
        odoo_company_id INT NOT NULL,
        display_type VARCHAR(20) NOT NULL,
        odoo_account_id INT NULL,
        account_name VARCHAR(255) NULL,
        odoo_product_id INT NULL,
        product_name VARCHAR(500) NULL,
        odoo_category_id INT NULL,
        category_name VARCHAR(255) NULL,
        category_account_id INT NULL,
        category_account_name VARCHAR(255) NULL,
        line_label VARCHAR(1000) NULL,
        quantity DECIMAL(18,4) NULL,
        price_unit DECIMAL(18,6) NULL,
        price_subtotal DECIMAL(18,2) NULL,
        amount DECIMAL(18,2) NOT NULL,
        odoo_tax_id INT NULL,
        tax_name VARCHAR(255) NULL,
        tax_rate DECIMAL(10,4) NULL,
        tax_group VARCHAR(255) NULL,
        loaded_at DATETIME NOT NULL,
        KEY idx_line_move (odoo_move_id),
        KEY idx_line_account (odoo_account_id),
        KEY idx_line_category_account (category_account_id)
    )
    """,
]

BILL_COLUMNS = [
    "odoo_move_id", "odoo_company_id", "odoo_company_name", "company_source_key", "move_type", "state",
    "payment_state", "move_name", "ref", "payment_reference", "cfdi_uuid", "cfdi_uuid_source", "invoice_date",
    "invoice_date_due", "accounting_date", "odoo_partner_id", "partner_name", "odoo_commercial_partner_id",
    "vendor_name", "vendor_rfc", "invoice_origin", "currency", "amount_untaxed", "amount_tax", "amount_total",
    "amount_residual", "payment_term", "reversed_entry_id", "payment_count", "last_payment_date",
    "odoo_write_date", "loaded_at",
]
LINE_COLUMNS = [
    "odoo_line_id", "odoo_move_id", "odoo_company_id", "display_type", "odoo_account_id", "account_name",
    "odoo_product_id", "product_name", "odoo_category_id", "category_name", "category_account_id",
    "category_account_name", "line_label", "quantity", "price_unit", "price_subtotal", "amount", "odoo_tax_id",
    "tax_name", "tax_rate", "tax_group", "loaded_at",
]


class Odoo:
    def __init__(self):
        self.uid, self.models, self.db, self.password = get_odoo_connection()

    def __call__(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, *args, **kwargs)


def ensure_tables(conn):
    cur = conn.cursor()
    for ddl in DDL:
        cur.execute(ddl)
    conn.commit()
    cur.close()


def stored_state(conn):
    """Last write date and the ids of stored bills not settled yet."""
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(odoo_write_date) FROM {BILLS}")
    last = cur.fetchone()[0]
    cur.execute(f"SELECT odoo_move_id FROM {BILLS} WHERE state = 'posted' AND payment_state IN {OPEN_PAYMENT_STATES}")
    open_ids = {r[0] for r in cur.fetchall()}
    cur.close()
    return last, open_ids


def bill_ids_to_read(odoo, company_ids, since, open_ids):
    base = [["move_type", "in", MOVE_TYPES], ["company_id", "in", company_ids]]
    if since is None:
        return sorted(odoo("account.move", "search", [base], {"context": {"active_test": False}}))
    cutoff = since.strftime("%Y-%m-%d %H:%M:%S")
    ids = set(odoo("account.move", "search", [base + [["write_date", ">=", cutoff]]]))
    # Stored open bills are re-read even when unchanged: a payment does not
    # always move the bill's write_date. A bill deleted in Odoo is skipped by read.
    return sorted(ids | open_ids)


def resolve_uuid(bill):
    edi = (bill["l10n_mx_edi_cfdi_uuid"] or "").strip()
    if edi:
        return edi.upper(), "edi_field"
    ref = (bill["ref"] or "").strip()
    if UUID.match(ref):
        return ref.upper(), "ref"
    return None, None


def read_partners(odoo, bills):
    ids = sorted({m2o(b["commercial_partner_id"]) for b in bills if b["commercial_partner_id"]})
    partners = {}
    for part in chunks(ids):
        for p in odoo("res.partner", "read", [part], {"fields": ["name", "vat"], "context": {"active_test": False}}):
            partners[p["id"]] = p
    return partners


def read_payment_dates(odoo, bills):
    ids = sorted({pid for b in bills for pid in b["matched_payment_ids"]})
    dates = {}
    for part in chunks(ids):
        for p in odoo("account.payment", "read", [part], {"fields": ["date"]}):
            dates[p["id"]] = p["date"]
    return dates


def read_lines(odoo, move_ids):
    lines = []
    for part in chunks(move_ids):
        lines += odoo("account.move.line", "search_read",
                      [[["move_id", "in", part], ["display_type", "in", ["product", "tax"]]]], {"fields": LINE_FIELDS})
    return lines


def read_categories(odoo, lines, cache):
    """Product -> (category id, name, expense account) per company, cached across batches."""
    product_ids = sorted({m2o(l["product_id"]) for l in lines if l["product_id"]} - set(cache["products"]))
    for part in chunks(product_ids):
        for p in odoo("product.product", "read", [part], {"fields": ["categ_id"], "context": {"active_test": False}}):
            cache["products"][p["id"]] = p["categ_id"]
    needed = {(m2o(l["company_id"]), m2o(cache["products"][m2o(l["product_id"])]))
              for l in lines if l["product_id"] and cache["products"].get(m2o(l["product_id"]))}
    by_company = {}
    for company_id, categ_id in needed - set(cache["categories"]):
        by_company.setdefault(company_id, []).append(categ_id)
    for company_id, categ_ids in by_company.items():
        ctx = {"company_id": company_id, "allowed_company_ids": [company_id], "force_company": company_id}
        for c in odoo("product.category", "read", [categ_ids],
                      {"fields": ["complete_name", "property_account_expense_categ_id"], "context": ctx}):
            cache["categories"][(company_id, c["id"])] = c
    return cache


def read_taxes(odoo, lines, cache):
    ids = sorted({m2o(l["tax_line_id"]) for l in lines if l["tax_line_id"]} - set(cache["taxes"]))
    for part in chunks(ids):
        for t in odoo("account.tax", "read", [part], {"fields": ["name", "amount", "tax_group_id"],
                                                       "context": {"active_test": False}}):
            cache["taxes"][t["id"]] = t
    return cache


def expense_sign(value):
    return None if value is None else round(-value, 2)


def build_bill_rows(bills, companies, partners, payment_dates, loaded_at):
    rows = []
    for b in bills:
        company_id = m2o(b["company_id"])
        company_name, company_key = companies.get(company_id, (m2o(b["company_id"], 1), None))
        uuid, uuid_source = resolve_uuid(b)
        partner = partners.get(m2o(b["commercial_partner_id"]), {})
        paid_on = [payment_dates[p] for p in b["matched_payment_ids"] if payment_dates.get(p)]
        rows.append((
            b["id"], company_id, company_name, company_key, b["move_type"], b["state"], b["payment_state"],
            b["name"] or None, (b["ref"] or "").strip() or None, (b["payment_reference"] or "").strip() or None,
            uuid, uuid_source, b["invoice_date"] or None, b["invoice_date_due"] or None, b["date"] or None,
            m2o(b["partner_id"]), m2o(b["partner_id"], 1), m2o(b["commercial_partner_id"]), partner.get("name"),
            ((partner.get("vat") or "").strip().upper() or None), (b["invoice_origin"] or None),
            m2o(b["currency_id"], 1), expense_sign(b["amount_untaxed_signed"]), expense_sign(b["amount_tax_signed"]),
            expense_sign(b["amount_total_signed"]), expense_sign(b["amount_residual_signed"]),
            m2o(b["invoice_payment_term_id"], 1), m2o(b["reversed_entry_id"]), len(b["matched_payment_ids"]),
            max(paid_on) if paid_on else None, b["write_date"], loaded_at,
        ))
    return rows


def build_line_rows(lines, cache, loaded_at):
    rows = []
    for l in lines:
        company_id = m2o(l["company_id"])
        categ = cache["products"].get(m2o(l["product_id"])) if l["product_id"] else None
        category = cache["categories"].get((company_id, m2o(categ)), {}) if categ else {}
        cat_account = category.get("property_account_expense_categ_id")
        tax = cache["taxes"].get(m2o(l["tax_line_id"]), {}) if l["tax_line_id"] else {}
        rows.append((
            l["id"], m2o(l["move_id"]), company_id, l["display_type"], m2o(l["account_id"]), m2o(l["account_id"], 1),
            m2o(l["product_id"]), m2o(l["product_id"], 1), m2o(categ), category.get("complete_name"),
            m2o(cat_account), m2o(cat_account, 1), ((l["name"] or "")[:1000] or None),
            l["quantity"], l["price_unit"], l["price_subtotal"], round(l["balance"] or 0.0, 2),
            m2o(l["tax_line_id"]), tax.get("name"), tax.get("amount"), m2o(tax.get("tax_group_id"), 1), loaded_at,
        ))
    return rows


def upsert(cur, table, columns, key, rows):
    marks = ", ".join(["%s"] * len(columns))
    updates = ", ".join(f"{c} = VALUES({c})" for c in columns if c != key)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks}) ON DUPLICATE KEY UPDATE {updates}"
    for part in chunks(rows, 5000):
        cur.executemany(sql, part)


def save(conn, bill_rows, line_rows, move_ids):
    cur = conn.cursor()
    upsert(cur, BILLS, BILL_COLUMNS, "odoo_move_id", bill_rows)
    for part in chunks(move_ids, 5000):
        cur.execute(f"DELETE FROM {LINES} WHERE odoo_move_id IN ({', '.join(['%s'] * len(part))})", part)
    upsert(cur, LINES, LINE_COLUMNS, "odoo_line_id", line_rows)
    conn.commit()
    cur.close()


def remove_missing(conn, existing_in_odoo):
    """Full pass only: drop stored bills (and lines) that no longer exist in Odoo."""
    cur = conn.cursor()
    cur.execute(f"SELECT odoo_move_id FROM {BILLS}")
    gone = sorted({r[0] for r in cur.fetchall()} - set(existing_in_odoo))
    for part in chunks(gone, 5000):
        marks = ", ".join(["%s"] * len(part))
        cur.execute(f"DELETE FROM {LINES} WHERE odoo_move_id IN ({marks})", part)
        cur.execute(f"DELETE FROM {BILLS} WHERE odoo_move_id IN ({marks})", part)
    conn.commit()
    cur.close()
    return len(gone)


def run(full=False):
    loaded_at = datetime.now().replace(microsecond=0)
    odoo = Odoo()
    companies, skipped = group_companies(odoo.models, odoo.db, odoo.uid, odoo.password)

    conn = get_db_connection()
    try:
        ensure_tables(conn)
        last, open_ids = stored_state(conn)
        since = None if (full or last is None) else last - timedelta(days=MARGIN_DAYS)
        print(f"Odoo vendor bills: {'full load' if since is None else f'changed since {since}'}; "
              f"{len(companies)} companies of the group (skipped: {', '.join(sorted(skipped))})")
        ids = bill_ids_to_read(odoo, sorted(companies), since, open_ids)
        print(f"  bills to read: {len(ids)}" + ("" if since is None else f" (incl. {len(open_ids)} stored open bills)"))

        cache = {"products": {}, "categories": {}, "taxes": {}}
        total_bills = total_lines = 0
        for part in chunks(ids, 2000):
            bills = odoo("account.move", "read", [part], {"fields": BILL_FIELDS})
            present = [b["id"] for b in bills]
            lines = read_lines(odoo, present)
            read_categories(odoo, lines, cache)
            read_taxes(odoo, lines, cache)
            bill_rows = build_bill_rows(bills, companies, read_partners(odoo, bills), read_payment_dates(odoo, bills),
                                        loaded_at)
            save(conn, bill_rows, build_line_rows(lines, cache, loaded_at), present)
            total_bills += len(bill_rows)
            total_lines += len(lines)
            print(f"  saved {total_bills} of {len(ids)} bills ({total_lines} lines)")
        removed = remove_missing(conn, ids) if since is None else 0
    finally:
        conn.close()

    print(f"Odoo vendor bills loaded: {total_bills} bills, {total_lines} lines"
          + (f"; {removed} stored bills no longer in Odoo removed" if since is None else ""))
    return total_bills


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true", help="read every bill again and drop those deleted in Odoo")
    args = parser.parse_args(argv)
    run(full=args.full)


if __name__ == "__main__":
    main()
