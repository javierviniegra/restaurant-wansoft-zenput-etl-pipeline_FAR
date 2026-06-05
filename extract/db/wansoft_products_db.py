import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def get_wansoft_products_from_db():
    """
    Obtiene catálogo de productos desde Wansoft usando la tabla
    getstockinventory_inventario como primera fuente base.
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