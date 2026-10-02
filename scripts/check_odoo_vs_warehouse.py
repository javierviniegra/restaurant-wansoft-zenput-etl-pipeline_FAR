"""Read-only cross-check of the nightly Odoo download against Odoo itself.

    python -m scripts.check_odoo_vs_warehouse [--from 2026-09-26] [--to 2026-10-01]

For every Odoo company and day it compares what Odoo holds right now with what
the last nightly download stored in the production warehouse:
  - confirmed purchase order lines (purchase.order.line, state purchase/done)
    vs odoo_purchase_order_line_snapshot, by order date: lines and subtotal;
  - validated receipts (stock.picking incoming, state done)
    vs odoo_purchase_receipt_snapshot, by date done: receipts.
The download keeps only what each company's migration policy allows
(odoo_company_migration_policy.operational_start_date, compared with the
order date for lines and the scheduled date for receipts, exactly as
extract/purchases/odoo_purchase_etl.py does; companies without an active
policy use PURCHASE_ETL_MIN_ORDER_DATE). Odoo records before that date are
counted apart as "excluidas" (by design, e.g. the parallel capture of the
branches migrated from Wansoft before 2026-10-01), never as differences.
Every other record present on only one side is looked up in Odoo: a record
created or changed after the download is labelled AFTER_DOWNLOAD (expected,
the next night picks it up); anything else is a real difference
(MISSING / EXTRA).

Days are Odoo's UTC dates, the same convention the snapshots store, so both
sides group identically (a sale-day in Mexico can straddle two UTC dates).
Connects to the production warehouse with WANSOFT_DB_* (never the *_DEV
variables), so it gives the same answer from the dev PC or the tasks VM.
Only SELECT statements and Odoo search_read/read calls are issued.
"""
import argparse
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

import mysql.connector

from core.config.companies import ODOO_INTERNAL_PROVIDER_COMPANIES
from core.database.odoo import get_odoo_connection  # also loads core/config/.env

PAGE = 2000


def production_connection():
    return mysql.connector.connect(
        host=os.getenv("WANSOFT_DB_HOST"),
        port=int(os.getenv("WANSOFT_DB_PORT") or 3306),
        user=os.getenv("WANSOFT_DB_USER"),
        password=os.getenv("WANSOFT_DB_PASSWORD"),
        database=os.getenv("WANSOFT_DB_NAME"),
    )


def odoo_search_read(conn, model, domain, fields):
    uid, models, db, password = conn
    rows, offset = [], 0
    while True:
        page = models.execute_kw(db, uid, password, model, "search_read", [domain],
                                 {"fields": fields, "limit": PAGE, "offset": offset, "order": "id"})
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def odoo_read(conn, model, ids, fields):
    """Current state of the given ids; deleted records are simply absent (read() would raise)."""
    uid, models, db, password = conn
    found = []
    for i in range(0, len(ids), PAGE):
        found.extend(models.execute_kw(db, uid, password, model, "search_read", [[["id", "in", ids[i:i + PAGE]]]],
                                       {"fields": fields, "context": {"active_test": False}}))
    return {r["id"]: r for r in found}


def m2o_name(value):
    return value[1] if isinstance(value, list) and len(value) > 1 else None


def m2o_id(value):
    return value[0] if isinstance(value, list) and value else None


def load_start_dates(cur):
    """{odoo company id: 'YYYY-MM-DD 00:00:00'} from the active migration policy, as the ETL reads it."""
    cur.execute("SELECT odoo_company_id, operational_start_date FROM odoo_company_migration_policy WHERE is_active = 1")
    return {int(cid): f"{start} 00:00:00" for cid, start in cur.fetchall() if start}


def split_by_policy(rows, filter_field, starts, fallback):
    """Keeps the Odoo rows the download would keep; returns (kept, excluded count per (company, day))."""
    kept, excluded = [], defaultdict(int)
    for r in rows:
        start = starts.get(m2o_id(r["company_id"]), fallback)
        value = str(r.get(filter_field) or "")[:19]
        if start and (not value or value < start):
            excluded[(m2o_name(r["company_id"]), r["_day"])] += 1
        else:
            kept.append(r)
    return kept, excluded


def as_dt(value):
    if not value:
        return None
    return value if isinstance(value, datetime) else datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")


def classify(only_ids, live_state, downloaded_at):
    """Splits ids present on one side only into AFTER_DOWNLOAD and real differences."""
    after, real = [], []
    for rid in only_ids:
        rec = live_state.get(rid)
        changed = as_dt(rec.get("write_date")) if rec else None
        (after if changed and downloaded_at and changed > downloaded_at else real).append(rid)
    return after, real


def compare(title, odoo_rows, wh_rows, excluded, key_label, live_state, downloaded_at, amount=False):
    """odoo_rows / wh_rows: {id: (company, day, amount)}; excluded: {(company, day): count} left out by policy."""
    print(f"\n{'=' * 86}\n{title}\n{'=' * 86}")
    print(f"Descarga en producción: {downloaded_at or 'sin datos'}")
    groups = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for rid, (comp, day, amt) in odoo_rows.items():
        g = groups[(comp, day)]; g[0] += 1; g[2] += amt
    for rid, (comp, day, amt) in wh_rows.items():
        g = groups[(comp, day)]; g[1] += 1; g[3] += amt
    for key in excluded:
        groups[key]

    header = f"{'empresa':<36}{'dia':<12}{'excl.':>6}{'odoo':>7}{'base':>7}"
    header += f"{'$ odoo':>14}{'$ base':>14}" if amount else ""
    print(header + "  estado")
    for (comp, day), (n_o, n_w, a_o, a_w) in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1])):
        same = n_o == n_w and (not amount or abs(a_o - a_w) < 0.01)
        n_x = excluded.get((comp, day), 0)
        line = f"{(comp or '?')[:35]:<36}{str(day):<12}{n_x:>6}{n_o:>7}{n_w:>7}"
        line += f"{a_o:>14,.2f}{a_w:>14,.2f}" if amount else ""
        status = "OK" if same else "DIFF"
        if same and n_o == 0:
            status = "EXCLUIDO (antes del arranque)"
        if comp in ODOO_INTERNAL_PROVIDER_COMPANIES:
            status += " [proveedor interno: no es sucursal, la capa de negocio no lo cuenta como comprador]"
        print(line + "  " + status)
    print(f"excl. = registros de Odoo anteriores a la fecha de arranque de la empresa: la descarga no los guarda a propósito "
          f"({sum(excluded.values())} en total).")

    only_odoo = sorted(set(odoo_rows) - set(wh_rows))
    only_wh = sorted(set(wh_rows) - set(odoo_rows))
    changed = [rid for rid in set(odoo_rows) & set(wh_rows)
               if odoo_rows[rid][1] != wh_rows[rid][1] or (amount and abs(odoo_rows[rid][2] - wh_rows[rid][2]) >= 0.01)]
    after_o, missing = classify(only_odoo, live_state, downloaded_at)
    after_w, extra = classify(only_wh, live_state, downloaded_at)
    after_c, changed_real = classify(changed, live_state, downloaded_at)

    print(f"\n{key_label} solo en Odoo: {len(only_odoo)} (después de la descarga: {len(after_o)}, MISSING: {len(missing)})")
    print(f"{key_label} solo en la base: {len(only_wh)} (cambiaron en Odoo después de la descarga: {len(after_w)}, EXTRA: {len(extra)})")
    print(f"{key_label} con fecha o monto distinto: {len(changed)} (después de la descarga: {len(after_c)}, reales: {len(changed_real)})")
    for label, ids in (("MISSING", missing), ("EXTRA", extra), ("CAMBIO", changed_real)):
        for rid in ids[:20]:
            src = odoo_rows.get(rid) or wh_rows.get(rid)
            rec = live_state.get(rid, {})
            print(f"  {label} id={rid} {src[0]} {src[1]} estado_odoo={rec.get('state', 'no existe')} modificado={rec.get('write_date')}")
        if len(ids) > 20:
            print(f"  ... y {len(ids) - 20} más")
    return len(missing) + len(extra) + len(changed_real)


def main(argv=None):
    yesterday = date.today() - timedelta(days=1)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="date_from", default=str(yesterday - timedelta(days=5)))
    parser.add_argument("--to", dest="date_to", default=str(yesterday))
    args = parser.parse_args(argv)
    start = f"{args.date_from} 00:00:00"
    end = f"{date.fromisoformat(args.date_to) + timedelta(days=1)} 00:00:00"
    print(f"Cotejo Odoo vs base de producción, {args.date_from} a {args.date_to} (fechas UTC de Odoo)")

    odoo = get_odoo_connection()
    db = production_connection()
    cur = db.cursor()
    starts = load_start_dates(cur)
    fallback = os.getenv("PURCHASE_ETL_MIN_ORDER_DATE", "").strip()
    fallback = f"{fallback[:10]} 00:00:00" if fallback else None
    problems = 0

    # 1) Confirmed purchase order lines (the download filters them by order date)
    live = odoo_search_read(odoo, "purchase.order.line",
                            [["state", "in", ["purchase", "done"]], ["date_order", ">=", start], ["date_order", "<", end]],
                            ["id", "company_id", "date_order", "price_subtotal", "state", "write_date"])
    for r in live:
        r["_day"] = str(r["date_order"])[:10]
    kept, excluded = split_by_policy(live, "date_order", starts, fallback)
    odoo_rows = {r["id"]: (m2o_name(r["company_id"]), r["_day"], float(r["price_subtotal"] or 0)) for r in kept}
    cur.execute("SELECT odoo_purchase_order_line_id, company_name, DATE(order_date), price_subtotal FROM odoo_purchase_order_line_snapshot "
                "WHERE order_date >= %s AND order_date < %s", (start, end))
    wh_rows = {int(r[0]): (r[1], str(r[2]), float(r[3] or 0)) for r in cur.fetchall()}
    cur.execute("SELECT MAX(etl_loaded_at) FROM odoo_purchase_order_line_snapshot")
    downloaded = cur.fetchone()[0]
    state = {r["id"]: r for r in live}
    missing_ids = [i for i in wh_rows if i not in state]
    state.update(odoo_read(odoo, "purchase.order.line", missing_ids, ["id", "state", "write_date"]))
    problems += compare("ÓRDENES DE COMPRA CONFIRMADAS (líneas, subtotal sin IVA)", odoo_rows, wh_rows, excluded, "Líneas",
                        state, downloaded, amount=True)

    # 2) Validated incoming receipts (grouped by date done; the download filters them by scheduled date)
    live = odoo_search_read(odoo, "stock.picking",
                            [["picking_type_code", "=", "incoming"], ["state", "=", "done"],
                             ["date_done", ">=", start], ["date_done", "<", end]],
                            ["id", "company_id", "date_done", "scheduled_date", "state", "write_date"])
    for r in live:
        r["_day"] = str(r["date_done"])[:10]
    kept, excluded = split_by_policy(live, "scheduled_date", starts, fallback)
    odoo_rows = {r["id"]: (m2o_name(r["company_id"]), r["_day"], 0.0) for r in kept}
    cur.execute("SELECT odoo_receipt_id, company_name, DATE(date_done) FROM odoo_purchase_receipt_snapshot "
                "WHERE state = 'done' AND picking_type_code = 'incoming' AND date_done >= %s AND date_done < %s", (start, end))
    wh_rows = {int(r[0]): (r[1], str(r[2]), 0.0) for r in cur.fetchall()}
    cur.execute("SELECT MAX(etl_loaded_at) FROM odoo_purchase_receipt_snapshot")
    downloaded = cur.fetchone()[0]
    state = {r["id"]: r for r in live}
    missing_ids = [i for i in wh_rows if i not in state]
    state.update(odoo_read(odoo, "stock.picking", missing_ids, ["id", "state", "write_date"]))
    problems += compare("RECEPCIONES VALIDADAS (entradas de mercancía)", odoo_rows, wh_rows, excluded, "Recepciones",
                        state, downloaded)

    # 3) Branches with an active policy and nothing confirmed or received in the period: show what Odoo does
    #    hold for them (drafts / RFQs are not purchases and are never downloaded)
    received = {m2o_id(r["company_id"]) for r in kept}
    confirmed = set()
    for r in odoo_search_read(odoo, "purchase.order", [["state", "in", ["purchase", "done"]],
                                                       ["date_order", ">=", start], ["date_order", "<", end]], ["company_id"]):
        confirmed.add(m2o_id(r["company_id"]))
    cur.execute("SELECT odoo_company_id, company_name, operational_start_date FROM odoo_company_migration_policy "
                "WHERE is_active = 1 ORDER BY company_name")
    quiet = [(int(cid), name, sd) for cid, name, sd in cur.fetchall()
             if name not in ODOO_INTERNAL_PROVIDER_COMPANIES and (int(cid) not in confirmed or int(cid) not in received)]
    if quiet:
        print(f"\n{'=' * 86}\nSUCURSALES SIN ÓRDENES CONFIRMADAS O SIN RECEPCIONES VALIDADAS EN EL PERIODO\n{'=' * 86}")
        for cid, name, sd in quiet:
            orders = odoo_search_read(odoo, "purchase.order", [["company_id", "=", cid], ["create_date", ">=", start]], ["state"])
            states = defaultdict(int)
            for o in orders:
                states[o["state"]] += 1
            print(f"  {name} (arranque {sd}): confirmadas={'sí' if cid in confirmed else 'NO'}, "
                  f"recepciones={'sí' if cid in received else 'NO'}; órdenes creadas en el periodo por estado: "
                  f"{dict(states) or 'ninguna'}")
        print("  draft = borrador, sent = solicitud de cotización enviada: no son compras hasta confirmarse (purchase/done).")

    db.close()
    print(f"\nRESULTADO: {'SIN DIFERENCIAS REALES' if problems == 0 else f'{problems} DIFERENCIAS REALES'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
