"""
Odoo XML-RPC Connection (Core Infrastructure)
"""

import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()


def get_odoo_connection():
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB_NAME")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    return uid, models, db, password