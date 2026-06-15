import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def load_inventory_scope_classification() -> pd.DataFrame:
    """
    Carga la clasificación refinada de scope desde MySQL.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        odoo_product_id,
        inventory_scope,
        scope_source,
        scope_status,
        refined_inventory_scope,
        refined_scope_source,
        refined_scope_status
    FROM odoo_inventory_scope_classification
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df