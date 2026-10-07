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


SECTIONS = ("ventas", "cierres")


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
    conn.close()
    print(f"\nRESULTADO: {'TODO COINCIDE' if problems == 0 else f'{problems} DIFERENCIAS'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
