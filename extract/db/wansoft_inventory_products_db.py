import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def get_wansoft_inventory_products_from_db():
    """
    Obtiene catálogo de productos de inventory desde Wansoft
    usando getstockinventory_inventario.
    """

    conn = get_db_connection(target="wansoft")

    query = """
    SELECT DISTINCT
        CodigoProducto,
        Producto,
        UnidadDeMedida,
        Departamento,
        CodigoDepartamento
    FROM getstockinventory_inventario
    WHERE CodigoProducto IS NOT NULL
      AND CodigoProducto <> ''
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df
