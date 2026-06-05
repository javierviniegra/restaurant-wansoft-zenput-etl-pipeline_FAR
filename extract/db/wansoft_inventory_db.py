import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def get_wansoft_inventory_from_db():
    """
    Lee la tabla principal de inventario snapshot en Wansoft.
    Respeta ENV=dev/prod según mysql.py.
    """

    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        id,
        Sucursal,
        Fecha,
        IdProducto,
        CodigoProducto,
        Producto,
        IdDepartamento,
        CodigoDepartamento,
        Departamento,
        IdUnidadDeMedida,
        UnidadDeMedida,
        Disponibilidad,
        Balance,
        Critico
    FROM getstockinventory_inventario
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df