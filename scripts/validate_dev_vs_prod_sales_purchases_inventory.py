"""
Ad-hoc validation: dev vs prod reconciliation for Sales, Purchases and
Inventory, across all 19 branches, for a fixed calendar date range.

Connects to both dev and prod explicitly (does not rely on the ENV
toggle in core/config/.env, so it is safe to run while other pipeline
processes are scheduled against whichever ENV value is currently set).

Read-only. Prints a per-branch comparison table for each domain.
"""

import os
import re
import sys
import unicodedata
from pathlib import Path
from decimal import Decimal

import mysql.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

env_path = ROOT / "core" / "config" / ".env"
load_dotenv(dotenv_path=env_path)

from core.config.companies import WANSOFT_SUBSIDIARY_SOURCE_KEY, COMPANY_SOURCE  # noqa: E402


# getexpenses_factura.Sucursal is a messy raw field: "Fonda Argentina - X"
# (sometimes with an en-dash, sometimes with mangled/double-encoded
# separators). scripts.build_dim_company_analytical.canonicalize_company_source_key
# does NOT clean this specific format (it is never fed this raw column in
# the real pipeline, only cleaner sources) -- confirmed by testing it
# directly against real getexpenses_factura values, which came back
# unchanged. This is a local normalizer for this validation script only.
_PURCHASE_BRANCH_ALIASES = {
    "taqueria viaducto": "Taquería Viaducto",
    "aeropuerto": "Aeropuerto",
    "taqueria parroquia": "Taquería parroquia",
    "san jeronimo": "San Jeronimo",
    "via vallejo": "Vía Vallejo",
    "viaducto": "Viaducto",
    "isabel la catolica": "Isabel La Católica",
    "isabel catolica": "Isabel La Católica",
    "tollocan": "Metepec",
    "cancun": "Cancun",
    "playa del carmen": "Playa del Carmen",
    "napoles": "Napoles",
    "antenas": "Antenas",
    "oceania": "Oceanía",
    "acoxpa": "Acoxpa",
    "taqueria exhibimex": "Versalles",
    "coyoacan": "La Esquina Coyoacán",
    "tepeyac": "Tepeyac",
    "la esquina coyoacan": "La Esquina Coyoacán",
    "centromyj": "CentroMyJ",
    "mario y july": "CentroMyJ",
    "puebla": "Puebla",
}


def _strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def normalize_purchase_branch(raw):
    if raw is None:
        return None
    s = re.sub(r"^Fonda Argentina\s*[-–—?]*\s*", "", raw.strip(), flags=re.IGNORECASE)
    key = _strip_accents(s).lower().strip()
    return _PURCHASE_BRANCH_ALIASES.get(key, s)


DATE_START = "2026-09-01"
DATE_END = "2026-09-14"  # inclusive


def connect(which: str):
    if which == "dev":
        return mysql.connector.connect(
            host=os.getenv("WANSOFT_DB_HOST_DEV"),
            user=os.getenv("WANSOFT_DB_USER_DEV"),
            password=os.getenv("WANSOFT_DB_PASSWORD_DEV"),
            database=os.getenv("WANSOFT_DB_NAME_DEV"),
        )
    return mysql.connector.connect(
        host=os.getenv("WANSOFT_DB_HOST"),
        user=os.getenv("WANSOFT_DB_USER"),
        password=os.getenv("WANSOFT_DB_PASSWORD"),
        database=os.getenv("WANSOFT_DB_NAME"),
    )


def fetch_sales(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT Sucursal AS branch,
               COUNT(*) AS n,
               SUM(CAST(Total AS DECIMAL(18,2))) AS total
        FROM getallordenesbyday_new_venta
        WHERE Fecha >= %s AND Fecha < DATE_ADD(%s, INTERVAL 1 DAY)
        GROUP BY Sucursal
        """,
        (f"{DATE_START}T00:00:00", f"{DATE_END}T00:00:00"),
    )
    rows = cur.fetchall()
    cur.close()
    return {r["branch"]: (r["n"], r["total"] or Decimal("0")) for r in rows}


def fetch_purchases(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT Sucursal AS branch,
               COUNT(*) AS n,
               SUM(CAST(Total AS DECIMAL(18,2))) AS total
        FROM getexpenses_factura
        WHERE FechaDeExpedicion >= %s AND FechaDeExpedicion < DATE_ADD(%s, INTERVAL 1 DAY)
        GROUP BY Sucursal
        """,
        (DATE_START, DATE_END),
    )
    rows = cur.fetchall()
    cur.close()
    out = {}
    for r in rows:
        canon = normalize_purchase_branch(r["branch"]) or r["branch"]
        n, total = out.get(canon, (0, Decimal("0")))
        out[canon] = (n + r["n"], total + (r["total"] or Decimal("0")))
    return out


def fetch_inventory(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT subsidiary_name AS sub_id,
               COUNT(*) AS n,
               SUM(Cantidad) AS qty
        FROM getoutgoinginventory_salida
        WHERE Fecha >= %s AND Fecha <= %s
        GROUP BY subsidiary_name
        """,
        (DATE_START, DATE_END),
    )
    rows = cur.fetchall()
    cur.close()
    out = {}
    for r in rows:
        branch = WANSOFT_SUBSIDIARY_SOURCE_KEY.get(str(r["sub_id"]), f"UNKNOWN({r['sub_id']})")
        out[branch] = (r["n"], r["qty"] or Decimal("0"))
    return out


def compare(title, dev_data, prod_data, all_branches, amount_label="total", qty_fmt="{:,.2f}"):
    print(f"\n=== {title} ({DATE_START} .. {DATE_END}) ===")
    header = f"{'branch':<24}{'dev_n':>8}{'prod_n':>8}{'dev_'+amount_label:>16}{'prod_'+amount_label:>16}{'diff':>14}"
    print(header)
    print("-" * len(header))
    mismatches = []
    for branch in sorted(all_branches):
        dn, dt = dev_data.get(branch, (0, Decimal("0")))
        pn, pt = prod_data.get(branch, (0, Decimal("0")))
        diff = dt - pt
        flag = ""
        if abs(diff) > Decimal("0.05") or dn != pn:
            flag = "  <-- DIFF"
            mismatches.append(branch)
        print(f"{branch:<24}{dn:>8}{pn:>8}{qty_fmt.format(dt):>16}{qty_fmt.format(pt):>16}{qty_fmt.format(diff):>14}{flag}")
    if mismatches:
        print(f"\n{len(mismatches)} branch(es) with a difference: {', '.join(mismatches)}")
    else:
        print("\nAll branches match exactly.")
    return mismatches


def main():
    print(f"Connecting to dev ({os.getenv('WANSOFT_DB_HOST_DEV')}) and prod ({os.getenv('WANSOFT_DB_HOST')})...")
    dev = connect("dev")
    prod = connect("prod")

    all_branches = set(COMPANY_SOURCE.keys())

    sales_dev = fetch_sales(dev)
    sales_prod = fetch_sales(prod)
    compare("SALES (getallordenesbyday_new_venta)", sales_dev, sales_prod, all_branches)

    purchases_dev = fetch_purchases(dev)
    purchases_prod = fetch_purchases(prod)
    wansoft_source_branches = {k for k, v in COMPANY_SOURCE.items() if v == "wansoft"}
    all_known = set(COMPANY_SOURCE.keys())
    unmapped_dev = {k: v for k, v in purchases_dev.items() if k not in all_known}
    unmapped_prod = {k: v for k, v in purchases_prod.items() if k not in all_known}
    if unmapped_dev or unmapped_prod:
        print("\nPurchases rows with a branch name that did not map to any known "
              "company_source_key (excluded from the comparison below):")
        for k, v in unmapped_dev.items():
            print(f"  dev : {k!r} -> n={v[0]} total={v[1]}")
        for k, v in unmapped_prod.items():
            print(f"  prod: {k!r} -> n={v[0]} total={v[1]}")
    compare(
        "PURCHASES (getexpenses_factura) -- Wansoft-source branches only; "
        "Odoo-source branches have no prod counterpart for this table",
        purchases_dev, purchases_prod, wansoft_source_branches,
    )

    inv_dev = fetch_inventory(dev)
    inv_prod = fetch_inventory(prod)
    compare(
        "INVENTORY (getoutgoinginventory_salida) -- Wansoft-source branches only; "
        "Odoo-source branches have no prod counterpart for this table",
        inv_dev, inv_prod, wansoft_source_branches, amount_label="qty",
    )

    odoo_source_branches = {k for k, v in COMPANY_SOURCE.items() if v == "odoo"}
    print(f"\nOdoo-source branches (Purchases + Inventory live only in dev's canonical/analytics "
          f"layer, no prod raw-table equivalent to diff against): {sorted(odoo_source_branches)}")

    dev.close()
    prod.close()


if __name__ == "__main__":
    raise SystemExit(main())
