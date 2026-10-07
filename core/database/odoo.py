"""
Odoo XML-RPC Connection (Core Infrastructure)
"""

import xmlrpc.client
import os
from dotenv import load_dotenv

from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / "core" / "config" / ".env"
load_dotenv(dotenv_path=env_path)


# xmlrpc.client has no timeout: a call Odoo never answers would hang the
# nightly cycle forever (see core/clients/wansoft_client.py, 2026-10-07).
ODOO_TIMEOUT_SECONDS = int(os.getenv("ODOO_TIMEOUT_SECONDS", "600"))


class _TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class _TimeoutSafeTransport(xmlrpc.client.SafeTransport):
    def __init__(self, timeout, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


def _proxy(endpoint):
    transport_class = _TimeoutSafeTransport if endpoint.startswith("https") else _TimeoutTransport
    return xmlrpc.client.ServerProxy(endpoint, transport=transport_class(ODOO_TIMEOUT_SECONDS))


def get_odoo_connection():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB_NAME")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")

    common = _proxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})

    models = _proxy(f"{url}/xmlrpc/2/object")

    return uid, models, db, password