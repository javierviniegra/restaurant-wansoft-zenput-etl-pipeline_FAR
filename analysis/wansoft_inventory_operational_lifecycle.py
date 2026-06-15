import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


RELEVANT_ACTIVITY_TYPES = [
    "Factura",
    "Transferencia",
    "Ajuste de inventario",
    "Producto procesado",
    "Inventario inicial"
]


def get_latest_stock_snapshot():
    """
    Devuelve stock actual por CodigoProducto usando la última Fecha disponible
    en getstockinventory_inventario.

    IMPORTANTE:
    Se fuerza una sola fila por CodigoProducto.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    WITH latest_dates AS (
        SELECT
            CodigoProducto,
            MAX(Fecha) AS max_fecha
        FROM getstockinventory_inventario
        WHERE CodigoProducto IS NOT NULL
          AND CodigoProducto <> ''
        GROUP BY CodigoProducto
    )
    SELECT
        i.CodigoProducto,
        MAX(i.Producto) AS Producto,
        MAX(i.Departamento) AS Departamento,
        MAX(i.CodigoDepartamento) AS CodigoDepartamento,
        MAX(i.UnidadDeMedida) AS UnidadDeMedida,
        MAX(i.Fecha) AS latest_stock_date,
        SUM(COALESCE(i.Disponibilidad, 0)) AS current_stock_qty
    FROM getstockinventory_inventario i
    INNER JOIN latest_dates l
        ON i.CodigoProducto = l.CodigoProducto
       AND i.Fecha = l.max_fecha
    GROUP BY i.CodigoProducto
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def get_last_operational_activity():
    conn = get_db_connection(target="wansoft")

    query_fechareal = f"""
    SELECT
        CodigoProducto,
        MAX(FechaReal) AS last_activity_date
    FROM getinputinventory_entrada
    WHERE TipoEntrada IN ({",".join(["%s"] * len(RELEVANT_ACTIVITY_TYPES))})
      AND CodigoProducto IS NOT NULL
      AND CodigoProducto <> ''
    GROUP BY CodigoProducto
    """

    query_fecha = f"""
    SELECT
        CodigoProducto,
        MAX(Fecha) AS last_activity_date
    FROM getinputinventory_entrada
    WHERE TipoEntrada IN ({",".join(["%s"] * len(RELEVANT_ACTIVITY_TYPES))})
      AND CodigoProducto IS NOT NULL
      AND CodigoProducto <> ''
    GROUP BY CodigoProducto
    """

    try:
        df = pd.read_sql(query_fechareal, conn, params=RELEVANT_ACTIVITY_TYPES)
    except Exception:
        df = pd.read_sql(query_fecha, conn, params=RELEVANT_ACTIVITY_TYPES)

    conn.close()
    return df


def classify_operational_lifecycle(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    out["last_activity_date"] = pd.to_datetime(out["last_activity_date"], errors="coerce")
    out["latest_stock_date"] = pd.to_datetime(out["latest_stock_date"], errors="coerce")
    out["current_stock_qty"] = pd.to_numeric(out["current_stock_qty"], errors="coerce").fillna(0)

    today = pd.Timestamp.today().normalize()
    out["days_since_last_activity"] = (today - out["last_activity_date"]).dt.days

    def lifecycle_rule(row):
        days = row["days_since_last_activity"]
        stock = row["current_stock_qty"]

        if pd.isna(days):
            return "never_operated"

        if days <= 180:
            return "active_operational"

        if 181 <= days <= 730:
            return "dormant_operational"

        if days > 730 and stock <= 0:
            return "historical_candidate"

        if days > 730 and stock > 0:
            return "historical_with_stock_review"

        return "review"

    out["lifecycle_candidate"] = out.apply(lifecycle_rule, axis=1)
    return out


def build_wansoft_inventory_operational_lifecycle():
    df_stock = get_latest_stock_snapshot()
    df_activity = get_last_operational_activity()

    if df_stock.empty:
        return pd.DataFrame()

    df = df_stock.merge(df_activity, on="CodigoProducto", how="left")
    df = classify_operational_lifecycle(df)
    return df


def summarize_wansoft_inventory_operational_lifecycle(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["lifecycle_candidate", "count", "pct"])

    total = len(df)
    summary = df["lifecycle_candidate"].value_counts().reset_index()
    summary.columns = ["lifecycle_candidate", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)
    return summary