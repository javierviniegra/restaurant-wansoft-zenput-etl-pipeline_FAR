"""Build analytics_expense_invoices: every supplier invoice of every branch, Wansoft and Odoo, by Cuenta.

    python -m scripts.build_analytics_expense_invoices

Expenses domain, block 5 (docs/analytics-expense-invoices-design.md). One table
that replicates getexpenses_factura (every supplier invoice classified by
Wansoft's TipoDeEgreso / Cuenta / Subcuenta) for all branches, whatever system
they buy in. Rebuilt in full on each run into a new table that then replaces
the old one (readers never see it empty).

Sources:
- Wansoft: getexpenses_factura, with the current Estatus from
  wansoft_expense_live_status when Wansoft still lists the invoice (block 4).
  One row per invoice, Cuenta / Subcuenta as captured in Wansoft.
- Odoo: odoo_vendor_bill_snapshot + odoo_vendor_bill_line_snapshot (block 3),
  posted and cancelled bills and credit notes (drafts are not documents yet).
  Each product line is classified through expense_account_mapping /
  expense_vendor_rule (block 2); a bill becomes one row per bucket
  (tipo / cuenta / subcuenta, or exclusion), with its taxes spread over the
  buckets in proportion to their subtotal. Credit notes are negative.

Routing (as purchases): a branch with an active odoo_company_migration_policy
row takes Wansoft invoices issued before its operational_start_date and Odoo
bills from that date on; a branch born on Odoo (include_odoo_history = 1)
takes all its Odoo bills, opening investment included; every other branch is
Wansoft only. Rows of the other
system's period are kept with include_in_business_views = 0 and an
exclude_reason, like Wansoft "Rechazada", cancelled Odoo bills, advance lines,
internal-provider companies and a branch's documents after it left the group
(BRANCH_LAST_GROUP_DAY: Taquería San Fernando after 2025-02-28). Business figures: include_in_business_views = 1.

Ids: expense_document_id = '<source_system>:<document id>' (Wansoft
IdDocumento, Odoo account.move id) identifies the invoice; expense_row_key is
unique per row (an Odoo bill can have several Cuenta rows).

uuid_document_count: how many included documents carry the same CFDI UUID
(NULL when only one). Wansoft has the same CFDI captured twice (sometimes in two
branches) or a mistyped UUID; on dev 213 UUIDs on 436 Wansoft invoices, about
1.23 MDP of same-amount repeats over the whole history. They are kept as in the
source (the owner's Power BI counts them too) and flagged here.
"""
import hashlib
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from core.config.companies import BRANCH_LAST_GROUP_DAY, get_company_source_key
from core.database.mysql import get_db_connection

TABLE = "analytics_expense_invoices"
STAGING = f"{TABLE}_new"
OLD = f"{TABLE}_old"
CENT = Decimal("0.01")
ZERO = Decimal("0")
GOODS_WITHOUT_PRODUCT = ("Costo de producción", "Costo operativo", "Costo de alimentos")  # owner, block 1 F

# getexpenses_factura.Sucursal (the long name getExpenses.py writes) -> company_source_key.
# Compared on letters and digits only, so accents and the historical encoding
# damage of production ('Canc??n', 'Ocean??a') resolve to the same branch.
WANSOFT_BRANCH_NAMES = {
    "Fonda Argentina - Acoxpa": "Acoxpa",
    "Fonda Argentina - Aeropuerto": "Aeropuerto",
    "Fonda Argentina - Antenas": "Antenas",
    "Fonda Argentina - Cancún": "Cancun",
    "Fonda Argentina - Coyoacan": "La Esquina Coyoacán",
    "La Esquina Coyoacán": "La Esquina Coyoacán",
    "Fonda Argentina - Isabel La Católica": "Isabel La Católica",
    "Fonda Argentina - Nápoles": "Napoles",
    "Fonda Argentina - Oceanía": "Oceanía",
    "Fonda Argentina - Playa del Carmen": "Playa del Carmen",
    "Fonda Argentina - Taquería Exhibimex": "Versalles",
    "Fonda Argentina - Taqueria San Fernando": "Taqueria San Fernando",  # closed (Wansoft 7697)
    "Fonda Argentina - Taqueria Viaducto": "Taquería Viaducto",
    "Fonda Argentina - Tepeyac": "Tepeyac",
    "Fonda Argentina - Tollocan": "Metepec",
    "Fonda Argentina - Viaducto": "Viaducto",
    "Fonda Argentina – San Jerónimo": "San Jeronimo",
    "Fonda Argentina – Taquería Parroquía": "Taquería parroquia",
    "Fonda Argentina – Vía Vallejo": "Vía Vallejo",
    "Fonda Argentina - Centro Mario y July": "CentroMyJ",
    "Fonda Argentina - Puebla": "Puebla",
}

ODOO_STATUS = {"paid": "Pagada", "in_payment": "En pago", "partial": "Pago parcial", "not_paid": "Por pagar",
               "reversed": "Revertida"}

COLUMNS = [
    ("expense_row_key", "CHAR(32) NOT NULL PRIMARY KEY"),
    ("expense_document_id", "VARCHAR(40) NOT NULL"),
    ("source_system", "VARCHAR(10) NOT NULL"),
    ("source_document_id", "VARCHAR(32) NOT NULL"),
    ("document_type", "VARCHAR(20) NOT NULL"),
    ("company_source_key", "VARCHAR(100) NULL"),
    ("source_company_name", "VARCHAR(255) NULL"),
    ("invoice_date", "DATE NULL"),
    ("due_date", "DATE NULL"),
    ("folio", "VARCHAR(255) NULL"),
    ("uuid", "VARCHAR(64) NULL"),
    ("uuid_document_count", "INT NULL"),
    ("vendor_name", "VARCHAR(255) NULL"),
    ("vendor_rfc", "VARCHAR(20) NULL"),
    ("vendor_key", "VARCHAR(50) NULL"),
    ("tipo_de_egreso", "VARCHAR(100) NULL"),
    ("cuenta", "VARCHAR(255) NULL"),
    ("subcuenta", "VARCHAR(255) NULL"),
    ("is_costo_operativo", "TINYINT(1) NOT NULL"),
    ("classification_status", "VARCHAR(30) NOT NULL"),
    ("source_account_name", "VARCHAR(500) NULL"),
    ("subtotal", "DECIMAL(18,2) NOT NULL"),
    ("discount", "DECIMAL(18,2) NOT NULL"),
    ("iva", "DECIMAL(18,2) NOT NULL"),
    ("ieps", "DECIMAL(18,2) NULL"),
    ("retentions", "DECIMAL(18,2) NOT NULL"),
    ("total", "DECIMAL(18,2) NOT NULL"),
    ("status", "VARCHAR(30) NULL"),
    ("source_status", "VARCHAR(50) NULL"),
    ("status_from_live", "TINYINT(1) NOT NULL"),
    ("payment_date", "DATE NULL"),
    ("payment_terms", "VARCHAR(255) NULL"),
    ("purchase_order_ref", "VARCHAR(500) NULL"),
    ("include_in_business_views", "TINYINT(1) NOT NULL"),
    ("exclude_reason", "VARCHAR(50) NULL"),
    ("built_at", "DATETIME NOT NULL"),
]
NAMES = [c for c, _ in COLUMNS]
DDL = f"""
    CREATE TABLE {STAGING} (
        {', '.join(f'{c} {t}' for c, t in COLUMNS)},
        KEY idx_expense_document (expense_document_id),
        KEY idx_expense_company_date (company_source_key, invoice_date),
        KEY idx_expense_cuenta (cuenta, subcuenta),
        KEY idx_expense_business (include_in_business_views, invoice_date)
    )
"""


def letters(value):
    return re.sub(r"[^A-Za-z0-9]", "", value or "").lower()


BRANCH_BY_LETTERS = {letters(k): v for k, v in WANSOFT_BRANCH_NAMES.items()}


def dec(value):
    text = (str(value) if value is not None else "").replace(",", "").strip()
    try:
        return Decimal(text) if text else ZERO
    except ArithmeticError:
        return ZERO


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = (value or "").strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date() if text else None
    except ValueError:
        return None


def blank(value):
    text = (value or "").strip() if isinstance(value, str) else value
    return text or None


def row_key(*parts):
    return hashlib.md5("|".join("" if p is None else str(p) for p in parts).encode("utf-8")).hexdigest()


def fetch(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def start_dates(cur):
    """company_source_key -> (Odoo operational start date, take all Odoo history) for active policies.

    Branches born on Odoo (Puebla, CentroMyJ: include_odoo_history = 1) never
    were on Wansoft, so their bills before the opening (the opening investment)
    are kept too (owner, 2026-10-20); migrated branches start at the date.
    """
    starts = {}
    for name, start, all_history in fetch(cur, """
            SELECT company_name, operational_start_date, include_odoo_history
            FROM odoo_company_migration_policy WHERE is_active = 1"""):
        key = get_company_source_key(name)
        if key:
            starts[key] = (start, bool(all_history))
    return starts


def wansoft_rows(cur, starts, built_at):
    live = {doc: (status, subsidiary) for doc, status, subsidiary in
            fetch(cur, "SELECT id_documento, estatus, subsidiary_id FROM wansoft_expense_live_status")}
    rows, unknown = [], defaultdict(int)
    for (doc, sucursal, folio, rfc, vendor, vendor_key, subtotal, iva, ieps, total, issued, expires, terms, cuenta,
         subcuenta, estatus, tipo, uuid, po_folio, discount, retentions) in fetch(cur, """
            SELECT IdDocumento, Sucursal, Folio, RFCProveedor, NombreProveedor, ClaveProveedor, Subtotal, IVA, IEPS,
                   Total, FechaDeExpedicion, FechaDeExpiracion, TerminosDePago, Cuenta, Subcuenta, Estatus,
                   TipoDeEgreso, UUID, FolioOrdenCompra, Discount, Retentions
            FROM getexpenses_factura"""):
        key = BRANCH_BY_LETTERS.get(letters(sucursal))
        if key is None:
            unknown[sucursal] += 1
        invoice_date = as_date(issued)
        live_status = live.get(doc, (None, None))[0]
        status = blank(live_status) or blank(estatus)
        cuenta, subcuenta, tipo = blank(cuenta), blank(subcuenta), blank(tipo)
        start = starts.get(key, (None, False))[0]
        last_day = BRANCH_LAST_GROUP_DAY.get(key)
        if status == "Rechazada":
            reason = "rejected"
        elif last_day and (invoice_date is None or invoice_date > last_day):
            reason = "branch_left_group"
        elif start and invoice_date and invoice_date >= start:
            reason = "after_odoo_start"
        else:
            reason = None
        rows.append((
            row_key("wansoft", doc), f"wansoft:{doc}", "wansoft", doc, "invoice", key, sucursal, invoice_date,
            as_date(expires), blank(folio), blank(uuid), blank(vendor), blank((rfc or "").upper()), blank(vendor_key),
            tipo, cuenta, subcuenta, int(cuenta == "Costo operativo"), "source" if cuenta else "empty_cuenta", cuenta,
            dec(subtotal), dec(discount), dec(iva), dec(ieps), dec(retentions), dec(total), status, blank(estatus),
            int(live_status is not None), None, blank(terms), blank(po_folio), int(reason is None), reason, built_at,
        ))
    return rows, dict(unknown)


def classify_lines(cur):
    """odoo_move_id -> list of (bucket, amount, source account name) for its product lines."""
    accounts = {r[0]: r[1:] for r in fetch(cur, """
        SELECT odoo_account_id, mapping_status, tipo_de_egreso, cuenta, subcuenta, exclude_reason
        FROM expense_account_mapping""")}
    vendors = {r[0]: r[1:] for r in fetch(cur, """
        SELECT odoo_partner_id, rule_status, tipo_de_egreso, cuenta, subcuenta FROM expense_vendor_rule""")}
    partner_of = dict(fetch(cur, f"SELECT odoo_move_id, odoo_commercial_partner_id FROM odoo_vendor_bill_snapshot"))
    lines = defaultdict(list)
    for move_id, account_id, account_name, category_account_id, category_account_name, product_id, amount in fetch(cur, """
            SELECT odoo_move_id, odoo_account_id, account_name, category_account_id, category_account_name,
                   odoo_product_id, amount
            FROM odoo_vendor_bill_line_snapshot WHERE display_type = 'product'"""):
        mapping = accounts.get(account_id)
        source_name = account_name
        if mapping and mapping[0] == "product_category":
            if category_account_id is None:
                bucket = (*GOODS_WITHOUT_PRODUCT, "goods_without_product", None)
                lines[move_id].append((bucket, amount, source_name))
                continue
            mapping = accounts.get(category_account_id)
            source_name = category_account_name
        if mapping is None:
            bucket = (None, None, None, "unmapped_account", None)
        else:
            status, tipo, cuenta, subcuenta, exclude = mapping
            if status == "approved":
                bucket = (tipo, cuenta, subcuenta, "account_mapping", None)
            elif status == "excluded":
                bucket = (None, None, None, "excluded", exclude or "excluded_account")
            elif status == "vendor_rule":
                rule = vendors.get(partner_of.get(move_id))
                bucket = ((rule[1], rule[2], rule[3], "vendor_rule", None) if rule and rule[0] == "approved"
                          else (None, None, None, "unclassified", None))
            else:  # unclassified, pending_review
                bucket = (None, None, None, "unclassified", None)
        lines[move_id].append((bucket, amount, source_name))
    return lines


def tax_totals(cur):
    """odoo_move_id -> (iva, ieps, retentions as a positive withheld amount), expense sign."""
    taxes = defaultdict(lambda: [ZERO, ZERO, ZERO])
    for move_id, amount, rate, group in fetch(cur, """
            SELECT odoo_move_id, amount, tax_rate, tax_group FROM odoo_vendor_bill_line_snapshot
            WHERE display_type = 'tax'"""):
        t = taxes[move_id]
        if rate is not None and rate < 0:
            t[2] -= amount
        elif "IEPS" in (group or "").upper():
            t[1] += amount
        else:
            t[0] += amount
    return taxes


def spread(total, weights):
    """Split total over weights proportionally, to the cent, remainder on the largest weight."""
    base = sum(weights)
    if not weights:
        return []
    if base == 0:
        parts = [ZERO] * len(weights)
        parts[0] = total
        return parts
    parts = [(total * w / base).quantize(CENT, ROUND_HALF_UP) for w in weights]
    biggest = max(range(len(weights)), key=lambda i: abs(weights[i]))
    parts[biggest] += total - sum(parts)
    return parts


def odoo_rows(cur, starts, built_at):
    lines = classify_lines(cur)
    taxes = tax_totals(cur)
    rows = []
    for (move_id, company_name, key, move_type, state, payment_state, ref, payment_reference, uuid, invoice_date,
         due_date, accounting_date, vendor_name, vendor_rfc, partner_id, origin, untaxed, payment_term,
         last_payment) in fetch(cur, """
            SELECT odoo_move_id, odoo_company_name, company_source_key, move_type, state, payment_state, ref,
                   payment_reference, cfdi_uuid, invoice_date, invoice_date_due, accounting_date, vendor_name,
                   vendor_rfc, odoo_commercial_partner_id, invoice_origin, amount_untaxed, payment_term,
                   last_payment_date
            FROM odoo_vendor_bill_snapshot WHERE state IN ('posted', 'cancel')"""):
        doc_date = invoice_date or accounting_date
        start, all_history = starts.get(key, (None, False))
        last_day = BRANCH_LAST_GROUP_DAY.get(key)
        if key is None:
            bill_reason = "internal_provider_or_holding"
        elif last_day and (doc_date is None or doc_date > last_day):
            bill_reason = "branch_left_group"
        elif state == "cancel":
            bill_reason = "cancelled"
        elif not start:
            bill_reason = "branch_on_wansoft"
        elif not all_history and (doc_date is None or doc_date < start):
            bill_reason = "before_odoo_start"
        else:
            bill_reason = None
        status = "Cancelada" if state == "cancel" else ODOO_STATUS.get(payment_state, payment_state)

        buckets = defaultdict(lambda: [ZERO, set()])
        for bucket, amount, source_name in lines.get(move_id, []):
            buckets[bucket][0] += Decimal(amount)
            if source_name:
                buckets[bucket][1].add(source_name)
        if not buckets:  # a bill with no product line (only taxes, or empty)
            buckets[(None, None, None, "no_lines", None)] = [ZERO, set()]
        order = sorted(buckets, key=lambda b: tuple("" if x is None else x for x in b))
        subtotals = [buckets[b][0] for b in order]
        iva, ieps, retentions = taxes.get(move_id, (ZERO, ZERO, ZERO))
        iva_parts, ieps_parts, ret_parts = (spread(iva, subtotals), spread(ieps, subtotals),
                                            spread(retentions, subtotals))
        for i, bucket in enumerate(order):
            tipo, cuenta, subcuenta, classification, line_reason = bucket
            reason = bill_reason or line_reason
            subtotal = subtotals[i].quantize(CENT, ROUND_HALF_UP)
            rows.append((
                row_key("odoo", move_id, *bucket), f"odoo:{move_id}", "odoo", str(move_id),
                "credit_note" if move_type == "in_refund" else "invoice", key, company_name, doc_date, due_date,
                payment_reference, uuid, vendor_name, vendor_rfc, str(partner_id) if partner_id else None,
                tipo, cuenta, subcuenta, int(cuenta == "Costo operativo"), classification,
                "; ".join(sorted(buckets[bucket][1]))[:500] or None,
                subtotal, ZERO, iva_parts[i], ieps_parts[i], ret_parts[i],
                subtotal + iva_parts[i] + ieps_parts[i] - ret_parts[i],
                status, f"{state}/{payment_state}", 0, last_payment, payment_term, origin,
                int(reason is None), reason, built_at,
            ))
    return rows


def flag_shared_uuids(rows):
    """Insert uuid_document_count, counted over the included rows (documents, not rows)."""
    built = [c for c in NAMES if c != "uuid_document_count"]  # the tuples do not carry it yet
    i_uuid, i_doc, i_inc = (built.index(c) for c in ("uuid", "expense_document_id", "include_in_business_views"))
    i_count = NAMES.index("uuid_document_count")
    documents = defaultdict(set)
    for r in rows:
        if r[i_inc] and r[i_uuid]:
            documents[r[i_uuid].upper()].add(r[i_doc])
    out = []
    for r in rows:
        n = len(documents.get((r[i_uuid] or "").upper(), ())) if r[i_inc] else 0
        out.append(r[:i_count] + (n if n > 1 else None,) + r[i_count:])
    return out


def main():
    built_at = datetime.now().replace(microsecond=0)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        starts = start_dates(cur)
        w_rows, unknown = wansoft_rows(cur, starts, built_at)
        if unknown:
            raise SystemExit(f"[ERROR] getexpenses_factura.Sucursal without a branch in WANSOFT_BRANCH_NAMES: {unknown}")
        o_rows = odoo_rows(cur, starts, built_at)
        rows = flag_shared_uuids(w_rows + o_rows)

        cur.execute(f"DROP TABLE IF EXISTS {STAGING}")
        cur.execute(DDL)
        sql = f"INSERT INTO {STAGING} ({', '.join(NAMES)}) VALUES ({', '.join(['%s'] * len(NAMES))})"
        for i in range(0, len(rows), 5000):
            cur.executemany(sql, rows[i:i + 5000])
        conn.commit()
        cur.execute(f"DROP TABLE IF EXISTS {OLD}")
        if fetch(cur, "SHOW TABLES LIKE %s", (TABLE,)):
            cur.execute(f"RENAME TABLE {TABLE} TO {OLD}, {STAGING} TO {TABLE}")
            cur.execute(f"DROP TABLE {OLD}")
        else:
            cur.execute(f"RENAME TABLE {STAGING} TO {TABLE}")

        print(f"{TABLE}: {len(rows)} rows (Wansoft {len(w_rows)}, Odoo {len(o_rows)}); "
              f"Odoo start dates: {', '.join(f'{k} {s}' + (' (all history)' if a else '') for k, (s, a) in sorted(starts.items()))}")
        for source, included, reason, n, amount in fetch(cur, f"""
                SELECT source_system, include_in_business_views, COALESCE(exclude_reason, '-'), COUNT(*), SUM(subtotal)
                FROM {TABLE} GROUP BY 1, 2, 3 ORDER BY 1, 2 DESC, 4 DESC"""):
            print(f"  {source:<8} include={included} {reason:<28} {n:>8} rows {amount:>18,.2f}")
        # Business rows the classification could not place: a new Odoo account
        # (not in expense_account_mapping), a "Por clasificar" decision or a vendor
        # of "Other overheads" without a rule. A reminder, never a failure.
        for key, status, account, n, amount in fetch(cur, f"""
                SELECT COALESCE(company_source_key, '-'), classification_status, COALESCE(source_account_name, '-'),
                       COUNT(*), SUM(subtotal)
                FROM {TABLE}
                WHERE include_in_business_views = 1
                  AND classification_status IN ('unmapped_account', 'unclassified', 'no_lines')
                  AND invoice_date >= CURDATE() - INTERVAL 60 DAY
                GROUP BY 1, 2, 3 ORDER BY ABS(SUM(subtotal)) DESC LIMIT 15"""):
            print(f"[AVISO] gastos sin clasificar (últimos 60 días): {key} | {status} | {account} | "
                  f"{n} renglones | {amount:,.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
