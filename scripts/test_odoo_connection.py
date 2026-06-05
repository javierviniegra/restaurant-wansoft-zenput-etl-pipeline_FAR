# scripts/test_odoo_connection.py

from core.database.odoo import get_odoo_connection

def test():
    uid, models, db, password = get_odoo_connection()

    print("UID:", uid)
    print("Connection OK ✅")

if __name__ == "__main__":
    test()
