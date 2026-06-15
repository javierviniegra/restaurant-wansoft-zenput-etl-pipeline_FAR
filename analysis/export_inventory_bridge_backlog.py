import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def export_inventory_bridge_backlog():
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        odoo_product_name,
        odoo_category_name,
        raw_classification,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        wansoft_lifecycle_candidate,
        similarity_score,
        suggested_action
    FROM inventory_bridge_report
    ORDER BY
        FIELD(
            suggested_action,
            'assign_default_code',
            'review_before_assigning_code',
            'historical_with_remaining_stock_review',
            'keep_as_historical'
        ),
        similarity_score DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No hay bridge report para exportar.")
        return

    file_name = "inventory_bridge_backlog.csv"
    df.to_csv(file_name, index=False, encoding="utf-8-sig")

    print(f"Archivo exportado: {file_name}")
    print(f"Total registros: {len(df)}")


if __name__ == "__main__":
    export_inventory_bridge_backlog()