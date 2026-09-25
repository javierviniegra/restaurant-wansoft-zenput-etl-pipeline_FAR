"""Read-only preflight for a machine's .env: reports what is missing or unreachable, never prints secrets.

Usage (from the project root):  python -m scripts.check_env
Exits 1 if anything failed.
"""
import os
import sys
from pathlib import Path

import mysql.connector

from core.config.env_loader import load_environment

results = []


def check(ok, label, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))


def warn(label, detail=""):
    print(f"WARN  {label}" + (f"  ({detail})" if detail else ""))


def check_database(prefix, suffix):
    keys = [f"{prefix}_DB_{k}{suffix}" for k in ("HOST", "USER", "PASSWORD", "NAME")]
    missing = [k for k in keys if k != keys[2] and not os.getenv(k)]
    check(not missing, f"{prefix.title()} database settings present", ", ".join(missing))
    if missing:
        return
    host, user, password, name = (os.getenv(k) or "" for k in keys)
    if not password:
        warn(f"{keys[2]} is empty")
    try:
        conn = mysql.connector.connect(host=host, user=user, password=password, connection_timeout=8)
    except Exception as exc:
        check(False, f"{prefix.title()} database server accepts the credentials", f"{host}: {type(exc).__name__}")
        return
    check(True, f"{prefix.title()} database server accepts the credentials", host)
    cur = conn.cursor()
    cur.execute("SHOW DATABASES LIKE %s", (name,))
    if cur.fetchone():
        check(True, f"Database '{name}' exists")
    else:
        warn(f"Database '{name}' does not exist on that server yet")
    conn.close()


def main():
    load_environment()
    env = os.getenv("ENV", "prod").lower()
    suffix = "_DEV" if env == "dev" else ""
    print(f"ENV = {env}\n")

    check_database("WANSOFT", suffix)
    check_database("ZENPUT", suffix)

    odoo_keys = ["ODOO_URL", "ODOO_DB_NAME", "ODOO_USER", "ODOO_PASSWORD"]
    missing = [k for k in odoo_keys if not os.getenv(k)]
    check(not missing, "Odoo settings present", ", ".join(missing))
    if not missing:
        try:
            from core.database.odoo import get_odoo_connection
            uid = get_odoo_connection()[0]
            check(bool(uid), "Odoo accepts the credentials")
        except Exception as exc:
            check(False, "Odoo accepts the credentials", type(exc).__name__)

    check(bool(os.getenv("ZENPUT_API_TOKEN")), "Zenput API token present")

    from core.config.companies import CUENTAS_SUCURSALES
    empty = [str(sid) for sid, _, password in CUENTAS_SUCURSALES if not password]
    check(not empty, f"Wansoft passwords present for all {len(CUENTAS_SUCURSALES)} subsidiaries", "missing ids: " + ", ".join(empty))

    xml_key = "XML_DOWNLOAD_DIR_DEV" if env == "dev" else "XML_DOWNLOAD_DIR"
    xml_dir = os.getenv(xml_key)
    check(bool(xml_dir) and Path(xml_dir).is_dir(), f"{xml_key} points to an existing folder", xml_dir or "not set")

    for k in ("SALES_LOOKBACK_DAYS", "WANSOFT_LOOKBACK_DAYS", "PURCHASES_LOOKBACK_DAYS"):
        if not os.getenv(k):
            warn(f"{k} not set, the code default is used")

    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
