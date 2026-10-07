"""Read-only reconciliation of the production warehouse against its live sources.

    python -m scripts.reconcile_sources [--from 2026-09-30] [--to 2026-10-06] [--only ventas,cierres]

One section per domain; each compares, per branch and day, what the warehouse
holds with what the source system says right now, and prints OK / DIFF lines
plus a summary. Exit code 1 when any section finds a real difference.

Sections (built step by step, 2026-10-07):
  ventas   tickets (getallordenesbyday_new_venta) vs Wansoft's cash closings of
           the day (GetGlobalCashClosing_Xml). Wansoft can return several
           closings for one operating day: the day matches when the tickets
           equal the SUM of the closings (several shifts) or the LARGEST one (a
           full-day close that includes an earlier partial one: Puebla
           2026-09-29; Isabel, San Jerónimo and Vía Vallejo 2026-09-30). Same
           rule as the Sales Candado since 2026-10-07.
  cierres  each closing Wansoft returns vs the getglobalcashclosing row with the
           same (branch, fecha_corte): present, same total and order count.
  compras  branches still on Wansoft (COMPANY_SOURCE): every invoice Wansoft
           returns for the day (GetExpenses_Xml) must be in getexpenses_factura
           with the same subtotal, and every inventory entry
           (GetInputInventory_Xml) in getinputinventory_entrada with the same
           quantity and unit cost (matched by their Wansoft ids).
  costos   each branch's daily cost vs its live source per
           costs_source_by_company (Wansoft GetTotalCostByDate or Odoo's cost of
           sales), plus the duplicate/continuity check of the accumulated
           tables for Odoo-costed branches. Differences inside the nightly cost
           window are usually the source recalculating after last night's load
           (fixed by the next night); they are listed apart.

Connects to the production warehouse with WANSOFT_DB_* (never *_DEV), so it
gives the same answer from the dev PC or the tasks VM. Only SELECT statements
and read calls to the sources are issued.
"""
import argparse
import html
import os
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import mysql.connector

from core.database.odoo import get_odoo_connection  # noqa: F401  -- loads core/config/.env first
from core.config.companies import CUENTAS_SUCURSALES
from core.clients.wansoft_client import get_wansoft_client

TOLERANCE = 0.01


def production_connection():
    return mysql.connector.connect(
        host=os.getenv("WANSOFT_DB_HOST"), port=int(os.getenv("WANSOFT_DB_PORT") or 3306),
        user=os.getenv("WANSOFT_DB_USER"), password=os.getenv("WANSOFT_DB_PASSWORD"),
        database=os.getenv("WANSOFT_DB_NAME"),
    )


def days(first, last):
    d = first
    while d <= last:
        yield d
        d += timedelta(days=1)


def wansoft_closings(client, sid, pwd, day):
    """[(fecha_corte 'YYYY-MM-DD HH:MM:SS', total, orders)] Wansoft returns for this operating day, or None on error."""
    try:
        raw = client.service.GetGlobalCashClosing_Xml(sid, pwd, day.strftime("%Y-%m-%d"))
        root = ET.fromstring(html.unescape(raw))
    except Exception as exc:  # noqa: BLE001 -- reported as a source error, never hides a difference
        print(f"    [ERROR Wansoft] {sid} {day}: {exc}")
        return None
    out = []
    for corte in root.findall(".//Corte"):
        ventas = corte.find("Ventas")
        info = corte.find("InformacionOperativa")
        total = float((ventas.attrib.get("Total") if ventas is not None else "0").replace(",", "") or 0)
        orders = int(float(info.attrib.get("NoDeOrdenes", "0") or 0)) if info is not None else 0
        out.append((corte.attrib.get("Fecha", "").replace("T", " ")[:19], total, orders))
    return out


def section_ventas_cierres(conn, client, first, last, do_ventas, do_cierres):
    cur = conn.cursor()
    problems = 0
    unverified = [0]
    stats = {"ventas_ok": 0, "ventas_parcial": 0, "ventas_diff": 0, "sin_cierre": 0,
             "cierres_ok": 0, "cierres_diff": 0, "cierres_faltan": 0}
    for sid, key, _ in CUENTAS_SUCURSALES:
        # Read the password at call time: CUENTAS_SUCURSALES may have been built before .env was loaded.
        pwd = os.getenv(f"WANSOFT_PWD_{sid}")
        for day in days(first, last):
            closings = wansoft_closings(client, sid, pwd, day)
            if closings is None:
                problems += 1
                continue
            if do_ventas:
                cur.execute("SELECT SUM(CAST(Total AS DECIMAL(14,2))), COUNT(*) FROM getallordenesbyday_new_venta "
                            "WHERE Sucursal = %s AND CAST(Fecha AS DATE) = %s", (key, day))
                total, tickets = cur.fetchone()
                total = float(total or 0)
                totals = [t for _, t, _ in closings]
                if not closings:
                    stats["sin_cierre"] += 1
                    if total:
                        unverified[0] += 1
                        print(f"  SIN CIERRE  {key:<20} {day}: tickets ${total:,.2f} ({tickets}); Wansoft todavía no devuelve corte")
                elif abs(sum(totals) - total) < TOLERANCE:
                    stats["ventas_ok"] += 1
                elif abs(max(totals) - total) < TOLERANCE:
                    stats["ventas_parcial"] += 1
                    print(f"  OK (corte mayor de {len(totals)}) {key:<20} {day}: tickets ${total:,.2f}; cortes {totals}")
                else:
                    stats["ventas_diff"] += 1
                    problems += 1
                    print(f"  DIFF ventas {key:<20} {day}: tickets ${total:,.2f} ({tickets}) vs cortes {totals}")
            if do_cierres:
                for fecha_corte, total, orders in closings:
                    cur.execute("SELECT total_ventas, no_ordenes FROM getglobalcashclosing WHERE subsidiary_id = %s "
                                "AND fecha_corte = %s", (int(sid), fecha_corte))
                    row = cur.fetchone()
                    if row is None:
                        stats["cierres_faltan"] += 1
                        problems += 1
                        print(f"  FALTA cierre {key:<20} {fecha_corte}: Wansoft ${total:,.2f} ({orders} órdenes)")
                    elif abs(float(row[0] or 0) - total) >= TOLERANCE or int(row[1] or 0) != orders:
                        stats["cierres_diff"] += 1
                        problems += 1
                        print(f"  DIFF cierre  {key:<20} {fecha_corte}: base ${float(row[0] or 0):,.2f} ({row[1]}) "
                              f"vs Wansoft ${total:,.2f} ({orders})")
                    else:
                        stats["cierres_ok"] += 1
    if do_ventas:
        print(f"\nVENTAS: {stats['ventas_ok']} sucursal-día iguales a la suma de cortes, {stats['ventas_parcial']} iguales al "
              f"corte mayor de varios, {stats['ventas_diff']} distintos, {stats['sin_cierre']} sin corte todavía")
    if do_cierres:
        print(f"CIERRES: {stats['cierres_ok']} iguales, {stats['cierres_diff']} distintos, {stats['cierres_faltan']} faltan en la base")
    if unverified[0]:
        print(f"[AVISO] {unverified[0]} sucursal-día con ventas no se pudieron verificar (Wansoft no devolvió corte)")
    return problems + unverified[0]


def _wansoft_docs(client, method, sid, pwd, day, tag):
    try:
        raw = getattr(client.service, method)(subsidiaryId=sid, pwdWebService=pwd, operationdate=day.strftime("%Y-%m-%d"))
        return ET.fromstring(raw).findall(f".//{tag}") if raw else []
    except Exception as exc:  # noqa: BLE001
        print(f"    [ERROR Wansoft {method}] {sid} {day}: {exc}")
        return None


def _num(value):
    try:
        return float(str(value or "0").replace(",", ""))
    except ValueError:
        return 0.0


def section_compras(conn, client, first, last):
    from core.config.companies import COMPANY_SOURCE
    cur = conn.cursor()
    problems = 0
    stats = {"facturas_ok": 0, "facturas_diff": 0, "facturas_faltan": 0, "entradas_ok": 0, "entradas_diff": 0, "entradas_faltan": 0}
    for sid, key, _ in CUENTAS_SUCURSALES:
        if COMPANY_SOURCE.get(key, "wansoft") != "wansoft":
            continue
        pwd = os.getenv(f"WANSOFT_PWD_{sid}")
        for day in days(first, last):
            facturas = _wansoft_docs(client, "GetExpenses_Xml", sid, pwd, day, "Factura")
            if facturas is None:
                problems += 1
            else:
                for f in facturas:
                    doc = f.attrib.get("IdDocumento")
                    # Wansoft's IdDocumento is a global id; getexpenses_factura stores the branch's long name.
                    cur.execute("SELECT Subtotal FROM getexpenses_factura WHERE IdDocumento = %s", (doc,))
                    rows = cur.fetchall()
                    if not rows:
                        stats["facturas_faltan"] += 1; problems += 1
                        print(f"  FALTA factura {key:<20} {day}: IdDocumento {doc} ${_num(f.attrib.get('Subtotal')):,.2f} "
                              f"{f.attrib.get('NombreProveedor')}")
                    elif all(abs(_num(r[0]) - _num(f.attrib.get("Subtotal"))) >= TOLERANCE for r in rows):
                        stats["facturas_diff"] += 1; problems += 1
                        print(f"  DIFF factura  {key:<20} {day}: IdDocumento {doc} base {rows[0][0]} vs Wansoft {f.attrib.get('Subtotal')}")
                    else:
                        stats["facturas_ok"] += 1
            entradas = _wansoft_docs(client, "GetInputInventory_Xml", sid, pwd, day, "Entrada")
            if entradas is None:
                problems += 1
                continue
            for e in entradas:
                eid = e.attrib.get("IdEntrada")
                cur.execute("SELECT Cantidad, CostoUnitario FROM getinputinventory_entrada WHERE IdEntrada = %s AND subsidiary_name = %s",
                            (eid, sid))
                found = cur.fetchall()
                row = found[0] if found else None
                if row is None:
                    stats["entradas_faltan"] += 1; problems += 1
                    print(f"  FALTA entrada {key:<20} {day}: IdEntrada {eid} {e.attrib.get('NombreProducto')}")
                elif abs(float(row[0]) - _num(e.attrib.get("Cantidad"))) >= TOLERANCE or abs(float(row[1]) - _num(e.attrib.get("CostoUnitario"))) >= TOLERANCE:
                    stats["entradas_diff"] += 1; problems += 1
                    print(f"  DIFF entrada  {key:<20} {day}: IdEntrada {eid} base {row[0]} x {row[1]} vs Wansoft "
                          f"{e.attrib.get('Cantidad')} x {e.attrib.get('CostoUnitario')}")
                else:
                    stats["entradas_ok"] += 1
    print(f"\nFACTURAS (sucursales en Wansoft): {stats['facturas_ok']} iguales, {stats['facturas_diff']} distintas, {stats['facturas_faltan']} faltan")
    print(f"ENTRADAS (sucursales en Wansoft): {stats['entradas_ok']} iguales, {stats['entradas_diff']} distintas, {stats['entradas_faltan']} faltan")
    return problems


def section_costos(conn, client, first, last):
    from core.config.lookback import COSTS_LOOKBACK_DAYS
    from core.database.odoo import get_odoo_connection as _odoo
    from extract.costs.cost_switch import check_cost_continuity
    from extract.costs.odoo_cost_report import get_daily_cost
    cur = conn.cursor()
    cur.execute("SELECT company_source_key, wansoft_subsidiary_id, odoo_company_id, odoo_cost_start_date, reason FROM costs_source_by_company")
    routing = cur.fetchall()
    names = {sid: name for sid, name in ((int(s), None) for s, _, _ in CUENTAS_SUCURSALES)}
    cur.execute("SELECT DISTINCT subsidiary_id, subsidiary_name FROM gettotalcostbydate WHERE created_at >= %s", (first - timedelta(days=40),))
    names.update({int(s): n for s, n in cur.fetchall()})
    window_start = date.today() - timedelta(days=COSTS_LOOKBACK_DAYS)
    odoo = None
    problems = 0
    stats = {"ok": 0, "recalculo": 0, "diff": 0, "sin_dato": 0}
    for key, sid, oid, start, reason in routing:
        pwd = os.getenv(f"WANSOFT_PWD_{sid}")
        live_odoo = {}
        if start is not None:
            odoo = odoo or _odoo()
            uid, m, db, pw = odoo
            live_odoo = {date.fromisoformat(str(r.fecha)[:10]): float(r.CostoTotal)
                         for r in get_daily_cost(m, uid, db, pw, oid, str(first), str(last)).itertuples()}
        for day in days(first, last):
            cur.execute("SELECT CostoTotalVenta FROM gettotalcostbydate WHERE subsidiary_id = %s AND DATE(created_at) = %s", (sid, day))
            row = cur.fetchone()
            stored = float(row[0]) if row else None
            if start is not None and day >= start:
                live, source = live_odoo.get(day), "Odoo"
            else:
                source = "Wansoft"
                try:
                    raw = client.service.GetTotalCostByDate(subsidiaryName=names.get(sid), pwdWebService=pwd, operationdate=str(day))
                    nodes = ET.fromstring(raw).findall(".//CostosTotalesDeVenta") if raw else []
                    live = _num(nodes[0].attrib.get("Total")) if nodes else None
                except Exception as exc:  # noqa: BLE001
                    print(f"    [ERROR Wansoft GetTotalCostByDate] {key} {day}: {exc}")
                    problems += 1
                    continue
            if live is None and stored is None:
                stats["sin_dato"] += 1
                continue
            if live is not None and stored is not None and abs(live - stored) < TOLERANCE:
                stats["ok"] += 1
            elif day >= window_start:
                stats["recalculo"] += 1
                print(f"  RECALCULO {key:<20} {day} ({source}): base {stored or 0:,.2f} vs fuente ahora {live or 0:,.2f} "
                      f"(la fuente cambió después de la carga; la próxima noche lo actualiza)")
            else:
                stats["diff"] += 1; problems += 1
                print(f"  DIFF costo {key:<20} {day} ({source}): base {stored or 0:,.2f} vs fuente {live or 0:,.2f} (fuera de la ventana)")
        if start is not None:
            for p in check_cost_continuity(conn, sid, start, last, from_day=first):
                problems += 1
                print(f"  CONTINUIDAD {key}: {p}")
    print(f"\nCOSTOS: {stats['ok']} sucursal-día iguales a la fuente, {stats['recalculo']} recalculados por la fuente después "
          f"de la carga (dentro de la ventana, se corrigen solos), {stats['diff']} distintos fuera de la ventana, {stats['sin_dato']} sin dato")
    return problems


def section_zenput(first, last):
    """Every Zenput checklist submitted and every task created in the period must be in the zenput database."""
    import requests
    headers = {"accept": "application/json", "X-API-TOKEN": os.getenv("ZENPUT_API_TOKEN")}
    zconn = mysql.connector.connect(host=os.getenv("ZENPUT_DB_HOST"), user=os.getenv("ZENPUT_DB_USER"),
                                    password=os.getenv("ZENPUT_DB_PASSWORD"), database=os.getenv("ZENPUT_DB_NAME"))
    zcur = zconn.cursor()
    lo, hi = str(first), str(last + timedelta(days=1))
    problems = 0

    def in_db(table, column, ids):
        if not ids:
            return set()
        found = set()
        ids = list(ids)
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            zcur.execute(f"SELECT {column} FROM {table} WHERE {column} IN ({','.join(['%s'] * len(chunk))})", chunk)
            found |= {str(r[0]) for r in zcur.fetchall()}
        return found

    # Checklists, per form template (the nightly loader reads the first 20 templates)
    templates = requests.get("https://www.zenput.com/api/v1/forms/list_templates/?start=0&limit=100",
                             headers=headers, timeout=120).json().get("results", [])
    if len(templates) > 20:
        problems += 1
        print(f"  AVISO: Zenput tiene {len(templates)} formularios y la carga nocturna solo pide los primeros 20")
    api_subs = {}
    for t in templates:
        url = f"https://www.zenput.com/api/v3/submissions?form_template_id={t.get('id')}"
        while url:
            data = requests.get(url, headers=headers, timeout=120).json()
            for s in data.get("data", []):
                when = str((s.get("smetadata") or {}).get("date_submitted") or "")[:10]
                if lo <= when < hi:
                    api_subs[str(s.get("id"))] = (t.get("title"), when)
            url = (data.get("meta") or {}).get("next")
    missing = set(api_subs) - in_db("submissions", "submission_id", api_subs)
    for sid in sorted(missing):
        problems += 1
        print(f"  FALTA checklist {sid}: {api_subs[sid][0]} {api_subs[sid][1]}")
    print(f"\nCHECKLISTS: {len(api_subs)} enviados en el periodo según Zenput, {len(api_subs) - len(missing)} en la base, {len(missing)} faltan")

    # Tasks created in the period
    api_tasks, start = {}, 0
    while True:
        resp = requests.get("https://www.zenput.com/api/v1/tasks/list_tasks", headers=headers,
                            params={"limit": 100, "start": start}, timeout=120)
        if resp.status_code == 429:
            import time
            time.sleep(60)
            continue
        page = resp.json().get("results", [])
        for t in page:
            created = t.get("date_created")
            if isinstance(created, dict) and "$date" in created:  # tasks API: {'$date': epoch milliseconds, UTC}
                from datetime import datetime, timezone
                when = datetime.fromtimestamp(created["$date"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            else:
                when = str(created or "")[:10]
            if lo <= when < hi:
                api_tasks[str(t.get("id"))] = (t.get("title"), when)
        if len(page) < 100:
            break
        start += 100
    missing = set(api_tasks) - in_db("zenput_tasks", "task_id", api_tasks)
    for tid in sorted(missing):
        problems += 1
        print(f"  FALTA tarea {tid}: {api_tasks[tid][0]} {api_tasks[tid][1]}")
    print(f"TAREAS: {len(api_tasks)} creadas en el periodo según Zenput, {len(api_tasks) - len(missing)} en la base, {len(missing)} faltan")
    zconn.close()
    return problems


def section_negocio(conn, first, last):
    """Business purchase layer vs the canonical layer it is built from, and the daily aggregate vs the lines."""
    cur = conn.cursor()
    problems = 0
    month_lo = first.replace(day=1)
    cur.execute("""SELECT company_source_key, DATE_FORMAT(order_date, '%Y-%m'), COUNT(*), ROUND(SUM(price_subtotal), 2)
                   FROM canonical_purchase_order_line_snapshot WHERE order_date >= %s AND order_date < %s GROUP BY 1, 2""",
                (month_lo, last + timedelta(days=1)))
    canon = {(k, m): (n, float(s or 0)) for k, m, n, s in cur.fetchall()}
    cur.execute("""SELECT company_source_key, DATE_FORMAT(order_date, '%Y-%m'), COUNT(*), ROUND(SUM(price_subtotal), 2)
                   FROM analytics_purchase_order_lines WHERE order_date >= %s AND order_date < %s GROUP BY 1, 2""",
                (month_lo, last + timedelta(days=1)))
    anal = {(k, m): (n, float(s or 0)) for k, m, n, s in cur.fetchall()}
    for key in sorted(set(canon) | set(anal), key=lambda x: (x[0] or "", x[1])):
        c, a = canon.get(key, (0, 0.0)), anal.get(key, (0, 0.0))
        if c[0] != a[0] or abs(c[1] - a[1]) >= TOLERANCE:
            problems += 1
            print(f"  DIFF negocio {key[0]} {key[1]}: canónica {c[0]} líneas ${c[1]:,.2f} vs negocio {a[0]} ${a[1]:,.2f}")
    print(f"\nCANÓNICA vs NEGOCIO (líneas de compra, desde {month_lo}): {len(set(canon) | set(anal))} sucursal-mes revisados, "
          f"{problems} distintos")

    cur.execute("""SELECT l.company_source_key, DATE(l.order_date), ROUND(SUM(l.price_total), 2)
                   FROM analytics_purchase_order_lines l WHERE l.include_in_business_views = 1
                   AND l.order_date >= %s AND l.order_date < %s GROUP BY 1, 2""", (first, last + timedelta(days=1)))
    lines = {(k, str(d)): float(s or 0) for k, d, s in cur.fetchall()}
    daily_problems = 0
    cur.execute("""SELECT company_source_key, DATE(order_date), ROUND(SUM(business_price_total_total), 2)
                   FROM analytics_purchase_daily_company_product WHERE order_date >= %s AND order_date < %s
                   GROUP BY 1, 2""", (first, last + timedelta(days=1)))
    daily = {(k, str(d)): float(s or 0) for k, d, s in cur.fetchall()}
    for key in sorted(set(lines) | set(daily)):
        if abs(lines.get(key, 0) - daily.get(key, 0)) >= 1.0:
            daily_problems += 1
            print(f"  DIFF diario {key[0]} {key[1]}: líneas de negocio ${lines.get(key, 0):,.2f} vs tabla diaria ${daily.get(key, 0):,.2f}")
    print(f"TABLA DIARIA vs LÍNEAS DE NEGOCIO ({first}..{last}): {len(set(lines) | set(daily))} sucursal-día, {daily_problems} distintos")
    problems += daily_problems

    cur.execute("""SELECT COALESCE(exclude_reason, '(sin motivo)'), COUNT(*), ROUND(SUM(price_subtotal), 2)
                   FROM analytics_purchase_order_lines WHERE include_in_business_views = 0
                   AND order_date >= %s AND order_date < %s GROUP BY 1 ORDER BY 2 DESC""", (first, last + timedelta(days=1)))
    print(f"Líneas fuera de la vista de negocio en el periodo, por motivo:")
    for reason, n, s in cur.fetchall():
        print(f"    {reason}: {n} líneas, ${float(s or 0):,.2f}")
    return problems


SECTIONS = ("ventas", "cierres", "compras", "costos", "zenput", "negocio")


def main(argv=None):
    yesterday = date.today() - timedelta(days=1)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="date_from", default=str(yesterday - timedelta(days=6)))
    parser.add_argument("--to", dest="date_to", default=str(yesterday))
    parser.add_argument("--only", help=f"comma-separated sections: {', '.join(SECTIONS)}")
    args = parser.parse_args(argv)
    first, last = date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    only = {s.strip() for s in args.only.split(",")} if args.only else set(SECTIONS)
    print(f"Conciliación contra las fuentes, {first} a {last} (solo lectura)")

    conn = production_connection()
    problems = 0
    if only & {"ventas", "cierres"}:
        print(f"\n{'=' * 80}\nVENTAS Y CIERRES DE CAJA vs Wansoft\n{'=' * 80}")
        problems += section_ventas_cierres(conn, get_wansoft_client(), first, last, "ventas" in only, "cierres" in only)
    if "compras" in only:
        print(f"\n{'=' * 80}\nCOMPRAS DE SUCURSALES EN WANSOFT (facturas y entradas) vs Wansoft\n{'=' * 80}")
        problems += section_compras(conn, get_wansoft_client(), first, last)
        print("(Las compras de sucursales en Odoo se cotejan con scripts/check_odoo_vs_warehouse.py)")
    if "costos" in only:
        print(f"\n{'=' * 80}\nCOSTOS vs su fuente (costs_source_by_company)\n{'=' * 80}")
        problems += section_costos(conn, get_wansoft_client(), first, last)
    if "zenput" in only:
        print(f"\n{'=' * 80}\nZENPUT (checklists y tareas) vs API de Zenput\n{'=' * 80}")
        problems += section_zenput(first, last)
    if "negocio" in only:
        print(f"\n{'=' * 80}\nCAPA DE NEGOCIO vs CAPA CANÓNICA (compras)\n{'=' * 80}")
        problems += section_negocio(conn, first, last)
    conn.close()
    print(f"\nRESULTADO: {'TODO COINCIDE' if problems == 0 else f'{problems} DIFERENCIAS'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
