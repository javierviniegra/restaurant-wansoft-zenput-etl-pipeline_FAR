import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def get_wansoft_sales_products_from_db():
    """
    Catálogo de productos de venta / platillos desde Wansoft.
    Usa getallordenesbyday_new_detalleventa.
    """

    conn = get_db_connection(target="wansoft")

    query = """
      SELECT DISTINCT
          CodigoPlatillo,
          Platillo,
          CodigoGrupo,
          Grupo,
          CodigoTipoGrupo,
          TipoGrupo
      FROM getallordenesbyday_new_detalleventa
      WHERE CodigoPlatillo IS NOT NULL
        AND CodigoPlatillo <> ''
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df