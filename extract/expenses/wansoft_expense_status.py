"""
Current status of Wansoft supplier invoices (expenses domain, block 4:
docs/analytics-expense-invoices-design.md).

getexpenses_factura is loaded by legacy getExpenses.py, which only re-reads
invoices issued in the last WANSOFT_LOOKBACK_DAYS: an invoice marked paid (or
rejected) later keeps its old Estatus forever. On 2026-10-20 on dev, 158
Nápoles and 1,112 Aeropuerto invoices stored as "Por pagar" were already
"Pagada" in Wansoft.

GetPendingExpenses_Xml is NOT a list of unpaid invoices: it returns every
document whose download was never acknowledged (UpdateExpensesDownloadStatus
is never called, on purpose), i.e. about three years of invoices of the
branch (from mid-2023), each with its CURRENT Estatus and TotalDeudor. This
script stores that live status in wansoft_expense_live_status, one row per
IdDocumento (Wansoft's global document id), for every subsidiary in
CUENTAS_SUCURSALES. The key is IdDocumento + subsidiary (on 2026-10-20 no
document was listed by two subsidiaries; the key just makes it safe).
getexpenses_factura is not touched; the analytics table takes the live status
when there is one and the stored one otherwise.

Read-only against Wansoft. NEVER call MarkExpenseAsPaid_* or
UpdateExpensesDownloadStatus_*: they write to Wansoft (the second one would
also empty this list).

    python -m extract.expenses.wansoft_expense_status
    python -m extract.expenses.wansoft_expense_status --only Aeropuerto
"""
import argparse
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime

from core.clients.wansoft_client import get_wansoft_client
from core.config.env_loader import load_environment
from core.config.companies import CUENTAS_SUCURSALES
from core.database.mysql import get_db_connection

TABLE = "wansoft_expense_live_status"

DDL = f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        id_documento VARCHAR(32) NOT NULL,
        subsidiary_id INT NOT NULL,
        company_source_key VARCHAR(100) NOT NULL,
        estatus VARCHAR(50) NULL,
        total_deudor DECIMAL(18,4) NULL,
        subtotal DECIMAL(18,4) NULL,
        total DECIMAL(18,4) NULL,
        fecha_de_expedicion DATE NULL,
        cuenta VARCHAR(255) NULL,
        subcuenta VARCHAR(255) NULL,
        tipo_de_egreso VARCHAR(100) NULL,
        uuid VARCHAR(64) NULL,
        first_seen_at DATETIME NOT NULL,
        last_seen_at DATETIME NOT NULL,
        PRIMARY KEY (id_documento, subsidiary_id),
        KEY idx_live_status_company (company_source_key, estatus),
        KEY idx_live_status_seen (last_seen_at)
    )
"""

COLUMNS = ["id_documento", "subsidiary_id", "company_source_key", "estatus", "total_deudor", "subtotal", "total",
           "fecha_de_expedicion", "cuenta", "subcuenta", "tipo_de_egreso", "uuid", "first_seen_at", "last_seen_at"]


def number(value):
    try:
        return float((value or "").replace(",", ""))
    except ValueError:
        return None


def day(value):
    return (value or "")[:10] or None


def text(value):
    return (value or "").strip() or None


def rows_from_xml(xml_text, subsidiary_id, company_key, seen_at):
    rows = []
    for f in ET.fromstring(xml_text).iter("Factura"):
        a = f.attrib
        if not a.get("IdDocumento"):
            continue
        rows.append((a["IdDocumento"], subsidiary_id, company_key, text(a.get("Estatus")), number(a.get("TotalDeudor")),
                     number(a.get("Subtotal")), number(a.get("Total")), day(a.get("FechaDeExpedicion")),
                     text(a.get("Cuenta")), text(a.get("Subcuenta")), text(a.get("TipoDeEgreso")), text(a.get("UUID")),
                     seen_at, seen_at))
    return rows


def save(conn, rows):
    marks = ", ".join(["%s"] * len(COLUMNS))
    # first_seen_at keeps its original value; everything else is the latest reading.
    updates = ", ".join(f"{c} = VALUES({c})" for c in COLUMNS if c not in ("id_documento", "subsidiary_id", "first_seen_at"))
    sql = f"INSERT INTO {TABLE} ({', '.join(COLUMNS)}) VALUES ({marks}) ON DUPLICATE KEY UPDATE {updates}"
    cur = conn.cursor()
    for i in range(0, len(rows), 5000):
        cur.executemany(sql, rows[i:i + 5000])
    conn.commit()
    cur.close()


def run(only=None):
    load_environment()
    seen_at = datetime.now().replace(microsecond=0)
    client = get_wansoft_client()
    conn = get_db_connection()
    failed = []
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        conn.commit()
        cur.close()
        # CUENTAS_SUCURSALES reads the passwords when companies.py is imported, possibly
        # before the .env is loaded; read them again here.
        for subsidiary_id, company_key, _ in CUENTAS_SUCURSALES:
            if only and company_key not in only:
                continue
            started = time.time()
            try:
                password = os.getenv(f"WANSOFT_PWD_{subsidiary_id}")
                if not password:
                    raise RuntimeError(f"WANSOFT_PWD_{subsidiary_id} is not set")
                xml_text = client.service.GetPendingExpenses_Xml(subsidiaryId=int(subsidiary_id),
                                                                 pwdWebService=password)
                if not xml_text:
                    raise RuntimeError("empty response")
                rows = rows_from_xml(xml_text, int(subsidiary_id), company_key, seen_at)
                save(conn, rows)
            except Exception as exc:  # one branch failing must not stop the others
                failed.append(company_key)
                print(f"  [ERROR] {company_key} ({subsidiary_id}): {type(exc).__name__}: {exc}")
                continue
            print(f"  {company_key}: {len(rows)} invoices ({time.time() - started:.0f}s)")
    finally:
        conn.close()
    print(f"Wansoft live invoice status done; failed: {', '.join(failed) or 'none'}")
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="branch keys as in CUENTAS_SUCURSALES (e.g. Aeropuerto Napoles)")
    args = parser.parse_args(argv)
    return run(only=args.only)


if __name__ == "__main__":
    raise SystemExit(main())
