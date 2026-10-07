"""
Stage "Compras por clasificar (cada 5 días)" (owner, 2026-10-07).

Under the owner's option 1, purchase lines whose vendor or product is not
classified in the catalogs still count in the business views, flagged in
analytics_purchase_order_lines.catalog_status:
  proveedor_sin_catalogo, producto_sin_catalogo,
  proveedor_y_producto_sin_catalogo, producto_por_clasificar.
The catalogs are rebuilt every night (vendors become catalogued by
themselves), but a product needs a person to confirm its classification
(the product mapping dictionary, see the weekly mapping job). This stage
keeps that work visible, every 5 days:

1. rewrites the table purchase_catalog_review_backlog: one row per pending
   vendor/product and branch, with lines, amount, first and last purchase
   date and days pending;
2. writes the same list as CSV under reports/purchase_catalog_review/
   (gitignored: business data, the repository is public);
3. prints [AVISO] lines when the unclassified share of this month's business
   purchases exceeds MAX_SHARE, or something has been pending more than
   MAX_DAYS days. It never fails the cycle: this is catalog work, not a load
   error.
"""
import csv
import os
from datetime import date
from pathlib import Path

from core.database.mysql import get_db_connection

MAX_SHARE = float(os.getenv("PURCHASE_CATALOG_MAX_SHARE", "0.02"))
MAX_DAYS = int(os.getenv("PURCHASE_CATALOG_MAX_DAYS", "15"))
EVERY_DAYS = 5
PROJECT_DIR = Path(__file__).resolve().parents[2]

BACKLOG_DDL = """
    CREATE TABLE IF NOT EXISTS purchase_catalog_review_backlog (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        catalog_status VARCHAR(50) NOT NULL,
        company_source_key VARCHAR(255) NULL,
        source_system VARCHAR(50) NULL,
        vendor_name VARCHAR(255) NULL,
        product_id VARCHAR(100) NULL,
        product_name VARCHAR(255) NULL,
        wansoft_code VARCHAR(100) NULL,
        line_count INT NOT NULL,
        amount_subtotal DECIMAL(18,2) NOT NULL,
        first_order_date DATE NULL,
        last_order_date DATE NULL,
        days_pending INT NULL,
        generated_at DATETIME NOT NULL,
        KEY idx_backlog_status (catalog_status),
        KEY idx_backlog_company (company_source_key)
    )
"""

BACKLOG_QUERY = """
    SELECT catalog_status, company_source_key, source_system,
           CASE WHEN catalog_status LIKE 'proveedor%%' THEN vendor_name END AS vendor_name,
           CASE WHEN catalog_status LIKE '%%producto%%' THEN product_id END AS product_id,
           CASE WHEN catalog_status LIKE '%%producto%%' THEN product_name END AS product_name,
           CASE WHEN catalog_status LIKE '%%producto%%' THEN wansoft_code END AS wansoft_code,
           COUNT(*) AS line_count, ROUND(SUM(price_subtotal), 2) AS amount_subtotal,
           DATE(MIN(order_date)) AS first_order_date, DATE(MAX(order_date)) AS last_order_date
    FROM analytics_purchase_order_lines
    WHERE include_in_business_views = 1
      AND catalog_status IS NOT NULL AND catalog_status <> 'catalogado'
      AND order_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    GROUP BY 1, 2, 3, 4, 5, 6, 7
    ORDER BY amount_subtotal DESC
"""


def is_due(today=None):
    """True one day out of EVERY_DAYS (fixed calendar rhythm, independent of when the cycle last ran)."""
    today = today or date.today()
    return today.toordinal() % EVERY_DAYS == 0


def run_purchase_catalog_review_job():
    today = date.today()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(BACKLOG_DDL)
        cur.execute(BACKLOG_QUERY)
        rows = cur.fetchall()
        cur.execute("DELETE FROM purchase_catalog_review_backlog")
        out = []
        for (status, company, source, vendor, pid, pname, code, n, amount, first, last) in rows:
            days_pending = (today - first).days if first else None
            out.append((status, company, source, vendor, pid, pname, code, int(n), float(amount or 0), first, last, days_pending))
        cur.executemany(
            "INSERT INTO purchase_catalog_review_backlog (catalog_status, company_source_key, source_system, vendor_name, "
            "product_id, product_name, wansoft_code, line_count, amount_subtotal, first_order_date, last_order_date, "
            "days_pending, generated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())", out)
        conn.commit()

        # Share of this month's business purchases that is not classified yet
        cur.execute("""SELECT ROUND(SUM(price_subtotal), 2),
                              ROUND(SUM(CASE WHEN catalog_status <> 'catalogado' THEN price_subtotal ELSE 0 END), 2)
                       FROM analytics_purchase_order_lines
                       WHERE include_in_business_views = 1 AND order_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')""")
        total, pending = (float(v or 0) for v in cur.fetchone())
    finally:
        conn.close()

    folder = PROJECT_DIR / "reports" / "purchase_catalog_review"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"compras_por_clasificar_{today:%Y%m%d}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["estado_catalogo", "sucursal", "origen", "proveedor", "product_id", "producto", "codigo_wansoft",
                    "lineas", "importe_sin_iva", "primera_compra", "ultima_compra", "dias_pendiente"])
        w.writerows(out)

    by_status = {}
    for r in out:
        by_status.setdefault(r[0], [0, 0.0])
        by_status[r[0]][0] += r[7]
        by_status[r[0]][1] += r[8]
    print(f"Compras por clasificar (últimos 90 días): {len(out)} renglones -> {path}")
    for status, (n, amount) in sorted(by_status.items(), key=lambda kv: -kv[1][1]):
        print(f"  {status}: {n} líneas, ${amount:,.2f}")
    share = pending / total if total else 0.0
    print(f"Este mes: ${pending:,.2f} sin clasificar de ${total:,.2f} de compras de negocio ({share * 100:.1f}%)")
    if share > MAX_SHARE:
        print(f"[AVISO] Compras sin clasificar este mes: {share * 100:.1f}% (límite {MAX_SHARE * 100:.0f}%). "
              f"Revisar {path.name} y clasificar en el diccionario de mapeo de productos.")
    old = [r for r in out if r[11] is not None and r[11] > MAX_DAYS]
    if old:
        print(f"[AVISO] {len(old)} renglones llevan más de {MAX_DAYS} días sin clasificar; los de mayor importe:")
        for r in sorted(old, key=lambda r: -r[8])[:10]:
            print(f"    {r[0]} | {r[1]} | {r[3] or ''}{r[5] or ''} | ${r[8]:,.2f} | {r[11]} días")
