"""
Inventory Extraction Module (Odoo)

Extracts current stock levels from Odoo PostgreSQL database.
"""

import pandas as pd
from extract.odoo.connection import get_odoo_connection


def extract_inventory():
    print("Running Odoo inventory extraction...")

    conn = get_odoo_connection()

    query = """
    SELECT
        sq.product_id,
        pt.name AS product_name,
        sq.quantity AS qty_available,
        sl.complete_name AS location
    FROM stock_quant sq
    LEFT JOIN product_product pp ON sq.product_id = pp.id
    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
    LEFT JOIN stock_location sl ON sq.location_id = sl.id
    WHERE sq.quantity != 0
    """

    df = pd.read_sql(query, conn)

    print(f"Records extracted: {len(df)}")

    conn.close()

    return df