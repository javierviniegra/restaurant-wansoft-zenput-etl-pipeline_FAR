import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection


def get_latest_stock_snapshot():
    """
    Devuelve stock actual por CodigoProducto usando la última Fecha disponible
    en getstockinventory_inventario.
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
        i.Producto,
        i.Departamento,
        i.CodigoDepartamento,
        i.UnidadDeMedida,
        MAX(i.Fecha) AS latest_stock_date,
        SUM(i.Disponibilidad) AS current_stock_qty
    FROM getstockinventory_inventario i
    INNER JOIN latest_dates l
        ON i.CodigoProducto = l.CodigoProducto
       AND i.Fecha = l.max_fecha
    GROUP BY
        i.CodigoProducto,
        i.Producto,
        i.Departamento,
        i.CodigoDepartamento,
        i.UnidadDeMedida
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def get_last_purchase_dates():
    """
    Devuelve la última fecha de compra por factura en Wansoft.
    Usa getinputinventory_entrada y prioriza FechaReal si existe.
    """

    conn = get_db_connection(target="wansoft")

    # Intento 1: con FechaReal
    query_fechareal = """
    SELECT
        CodigoProducto,
        MAX(FechaReal) AS last_purchase_date
    FROM getinputinventory_entrada
    WHERE TipoEntrada = 'Factura'
      AND CodigoProducto IS NOT NULL
      AND CodigoProducto <> ''
    GROUP BY CodigoProducto
    """

    # Fallback: con Fecha
    query_fecha = """
    SELECT
        CodigoProducto,
        MAX(Fecha) AS last_purchase_date
    FROM getinputinventory_entrada
    WHERE TipoEntrada = 'Factura'
      AND CodigoProducto IS NOT NULL
      AND CodigoProducto <> ''
    GROUP BY CodigoProducto
    """

    try:
        df = pd.read_sql(query_fechareal, conn)
    except Exception:
        df = pd.read_sql(query_fecha, conn)

    conn.close()

    return df


def classify_inventory_lifecycle(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica productos de inventory por ciclo de vida según última compra y stock actual.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    out["last_purchase_date"] = pd.to_datetime(out["last_purchase_date"], errors="coerce")
    out["latest_stock_date"] = pd.to_datetime(out["latest_stock_date"], errors="coerce")
    out["current_stock_qty"] = pd.to_numeric(out["current_stock_qty"], errors="coerce").fillna(0)

    # referencia temporal: hoy
    today = pd.Timestamp.today().normalize()

    out["days_since_last_purchase"] = (today - out["last_purchase_date"]).dt.days

    def lifecycle_rule(row):
        days = row["days_since_last_purchase"]
        stock = row["current_stock_qty"]

        # nunca comprado
        if pd.isna(days):
            return "never_purchased"

        # activo
        if days <= 180:
            return "active_procurement"

        # dormido
        if 181 <= days <= 730:
            return "dormant"

        # > 730 días
        if days > 730 and stock <= 0:
            return "historical_candidate"

        if days > 730 and stock > 0:
            return "historical_with_stock_review"

        return "review"

    out["lifecycle_candidate"] = out.apply(lifecycle_rule, axis=1)

    return out


def build_wansoft_inventory_lifecycle_candidates() -> pd.DataFrame:
    """
    Construye dataset consolidado:
    - stock actual
    - última compra
    - clasificación lifecycle
    """

    df_stock = get_latest_stock_snapshot()
    df_purchase = get_last_purchase_dates()

    if df_stock.empty:
        return pd.DataFrame()

    df = df_stock.merge(
        df_purchase,
        on="CodigoProducto",
        how="left"
    )

    df = classify_inventory_lifecycle(df)

    return df


def summarize_wansoft_inventory_lifecycle(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resumen por lifecycle_candidate.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["lifecycle_candidate", "count", "pct"])

    total = len(df)

    summary = (
        df["lifecycle_candidate"]
        .value_counts()
        .reset_index()
    )
    summary.columns = ["lifecycle_candidate", "count"]
    summary["pct"] = (summary["count"] / total * 100).round(2)

    return summary
