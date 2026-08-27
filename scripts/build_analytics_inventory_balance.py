"""
Build analytics_inventory_balance.

Unifies the current inventory balance per company + product across Wansoft
(entradas - salidas) and Odoo (direct stock snapshot), hiding which system
produced the number, following the same coexistence pattern already used
for Purchases.

Main rules (see docs/inventory-wansoft-odoo-balance-unification-design.md):
- Wansoft side is only computed for companies where COMPANY_SOURCE == "wansoft".
- Odoo side is read directly from the already-governed analytics_inventory_snapshot
  (company_mapping_status = 'final_odoo_enabled'); no new extraction.
- Balance window is full history since each subsidiary's Inventario inicial,
  not a rolling window.
- TipoEntrada = 'Orden de compra a proveedor' is excluded (not physical stock yet).
- TipoSalida IN ('Error de captura', 'Factura de egresos rechazada') is excluded
  (not real movements).
- TipoEntrada = 'Transferencia' and TipoSalida = 'Transferencia' are both
  excluded: Wansoft does not reliably expose a matching outgoing leg for
  intra-subsidiary transfers, so summing only the entrada side would inflate
  the balance.
- wansoft_code is CodigoProducto verbatim; do not join dim_product for the
  Wansoft side, it has duplicate wansoft_code rows and would fan out the sums.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from core.database.mysql import get_db_connection
from core.config.companies import WANSOFT_SUBSIDIARY_SOURCE_KEY, COMPANY_SOURCE


TARGET_TABLE = "analytics_inventory_balance"
ENTRADA_TABLE = "getinputinventory_entrada"
SALIDA_TABLE = "getOutgoingInventory_Salida"
SNAPSHOT_TABLE = "analytics_inventory_snapshot"
BATCH_SIZE = 5000

ENTRADA_EXCLUDED_TYPES = ("Orden de compra a proveedor", "Transferencia")
SALIDA_EXCLUDED_TYPES = ("Error de captura", "Factura de egresos rechazada", "Transferencia")

WANSOFT_FINAL_SUBSIDIARY_IDS = [
    subsidiary_id
    for subsidiary_id, company_name in WANSOFT_SUBSIDIARY_SOURCE_KEY.items()
    if COMPANY_SOURCE.get(company_name) == "wansoft"
]


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (table_name,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row["total"] > 0)


def recreate_table(conn: Any) -> None:
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE}")

    ddl = f"""
    CREATE TABLE {TARGET_TABLE} (
        inventory_balance_key BIGINT AUTO_INCREMENT PRIMARY KEY,

        company_source_key VARCHAR(255) NOT NULL,
        source_system VARCHAR(20) NOT NULL,

        wansoft_code VARCHAR(255) NOT NULL,
        product_name VARCHAR(500) NULL,

        current_balance_qty DECIMAL(18,4) NOT NULL DEFAULT 0,

        source_row_count BIGINT NOT NULL DEFAULT 0,
        entrada_qty DECIMAL(18,4) NULL,
        salida_qty DECIMAL(18,4) NULL,

        final_inventory_source_status VARCHAR(100) NOT NULL,
        include_in_business_views BOOLEAN NOT NULL DEFAULT TRUE,
        exclude_reason VARCHAR(500) NULL,

        refreshed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_inventory_balance (company_source_key, wansoft_code, source_system),
        KEY idx_inventory_balance_company (company_source_key),
        KEY idx_inventory_balance_code (wansoft_code),
        KEY idx_inventory_balance_business_views (include_in_business_views)
    )
    """

    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def fetch_wansoft_entrada(conn: Any) -> pd.DataFrame:
    placeholders = ",".join(["%s"] * len(WANSOFT_FINAL_SUBSIDIARY_IDS))
    query = f"""
        SELECT
            subsidiary_name,
            CodigoProducto,
            MAX(NombreProducto) AS product_name,
            SUM(Cantidad) AS entrada_qty,
            COUNT(1) AS entrada_rows
        FROM {ENTRADA_TABLE}
        WHERE subsidiary_name IN ({placeholders})
          AND TipoEntrada NOT IN ({",".join(["%s"] * len(ENTRADA_EXCLUDED_TYPES))})
          AND CodigoProducto IS NOT NULL AND CodigoProducto <> ''
        GROUP BY subsidiary_name, CodigoProducto
    """
    params = tuple(WANSOFT_FINAL_SUBSIDIARY_IDS) + ENTRADA_EXCLUDED_TYPES
    return pd.read_sql(query, conn, params=params)


def fetch_wansoft_salida(conn: Any) -> pd.DataFrame:
    placeholders = ",".join(["%s"] * len(WANSOFT_FINAL_SUBSIDIARY_IDS))
    query = f"""
        SELECT
            subsidiary_name,
            CodigoProducto,
            SUM(Cantidad) AS salida_qty,
            COUNT(1) AS salida_rows
        FROM {SALIDA_TABLE}
        WHERE subsidiary_name IN ({placeholders})
          AND TipoSalida NOT IN ({",".join(["%s"] * len(SALIDA_EXCLUDED_TYPES))})
          AND CodigoProducto IS NOT NULL AND CodigoProducto <> ''
        GROUP BY subsidiary_name, CodigoProducto
    """
    params = tuple(WANSOFT_FINAL_SUBSIDIARY_IDS) + SALIDA_EXCLUDED_TYPES
    return pd.read_sql(query, conn, params=params)


def build_wansoft_side(conn: Any) -> pd.DataFrame:
    df_entrada = fetch_wansoft_entrada(conn)
    df_salida = fetch_wansoft_salida(conn)

    df = pd.merge(
        df_entrada,
        df_salida,
        on=["subsidiary_name", "CodigoProducto"],
        how="outer",
    )

    df["entrada_qty"] = df["entrada_qty"].fillna(0)
    df["salida_qty"] = df["salida_qty"].fillna(0)
    df["entrada_rows"] = df["entrada_rows"].fillna(0)
    df["salida_rows"] = df["salida_rows"].fillna(0)

    df["company_source_key"] = df["subsidiary_name"].map(WANSOFT_SUBSIDIARY_SOURCE_KEY)
    df["wansoft_code"] = df["CodigoProducto"]
    df["current_balance_qty"] = df["entrada_qty"] - df["salida_qty"]
    df["source_row_count"] = df["entrada_rows"] + df["salida_rows"]
    df["source_system"] = "wansoft"
    df["final_inventory_source_status"] = "final_wansoft_enabled"
    df["include_in_business_views"] = True
    df["exclude_reason"] = None

    return df[[
        "company_source_key", "source_system", "wansoft_code", "product_name",
        "current_balance_qty", "source_row_count", "entrada_qty", "salida_qty",
        "final_inventory_source_status", "include_in_business_views", "exclude_reason",
    ]]


def build_odoo_side(conn: Any) -> pd.DataFrame:
    query = f"""
        SELECT
            company_source_key,
            wansoft_code,
            MAX(wansoft_product_name) AS product_name,
            SUM(stock_qty) AS current_balance_qty,
            COUNT(1) AS source_row_count
        FROM {SNAPSHOT_TABLE}
        WHERE company_mapping_status = 'final_odoo_enabled'
          AND include_in_business_views = TRUE
          AND wansoft_code IS NOT NULL AND wansoft_code <> ''
        GROUP BY company_source_key, wansoft_code
    """
    df = pd.read_sql(query, conn)

    df["source_system"] = "odoo"
    df["entrada_qty"] = np.nan
    df["salida_qty"] = np.nan
    df["final_inventory_source_status"] = "final_odoo_enabled"
    df["include_in_business_views"] = True
    df["exclude_reason"] = None

    return df[[
        "company_source_key", "source_system", "wansoft_code", "product_name",
        "current_balance_qty", "source_row_count", "entrada_qty", "salida_qty",
        "final_inventory_source_status", "include_in_business_views", "exclude_reason",
    ]]


def count_odoo_rows_missing_wansoft_code(conn: Any) -> int:
    query = f"""
        SELECT COUNT(1) AS total
        FROM {SNAPSHOT_TABLE}
        WHERE company_mapping_status = 'final_odoo_enabled'
          AND include_in_business_views = TRUE
          AND (wansoft_code IS NULL OR wansoft_code = '')
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    return int(row["total"]) if row else 0


def load_rows(conn: Any, df: pd.DataFrame) -> None:
    if df.empty:
        return

    sql = f"""
        INSERT INTO {TARGET_TABLE} (
            company_source_key,
            source_system,
            wansoft_code,
            product_name,
            current_balance_qty,
            source_row_count,
            entrada_qty,
            salida_qty,
            final_inventory_source_status,
            include_in_business_views,
            exclude_reason
        ) VALUES (
            %(company_source_key)s,
            %(source_system)s,
            %(wansoft_code)s,
            %(product_name)s,
            %(current_balance_qty)s,
            %(source_row_count)s,
            %(entrada_qty)s,
            %(salida_qty)s,
            %(final_inventory_source_status)s,
            %(include_in_business_views)s,
            %(exclude_reason)s
        )
    """

    df_clean = df.astype(object).where(df.notna(), None)
    df_clean = df_clean.replace({np.nan: None})
    rows = df_clean.to_dict(orient="records")

    cursor = conn.cursor()
    for index in range(0, len(rows), BATCH_SIZE):
        batch = rows[index:index + BATCH_SIZE]
        cursor.executemany(sql, batch)
        conn.commit()
    cursor.close()


def get_summary(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT
            source_system,
            final_inventory_source_status,
            COUNT(1) AS total_rows,
            COALESCE(SUM(current_balance_qty), 0) AS total_balance_qty
        FROM {TARGET_TABLE}
        GROUP BY source_system, final_inventory_source_status
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return {"by_source_system": rows}


def print_summary(summary: Dict[str, Any], odoo_rows_missing_wansoft_code: int) -> None:
    print("=====================================================")
    print("ANALYTICS INVENTORY BALANCE BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TARGET_TABLE}")
    print(f"wansoft_final_subsidiary_count: {len(WANSOFT_FINAL_SUBSIDIARY_IDS)}")
    for row in summary["by_source_system"]:
        print(
            f"{row['source_system']} ({row['final_inventory_source_status']}): "
            f"rows={row['total_rows']} total_balance_qty={row['total_balance_qty']}"
        )
    print(f"odoo_rows_dropped_missing_wansoft_code: {odoo_rows_missing_wansoft_code}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY BALANCE BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        if not table_exists(conn, ENTRADA_TABLE) or not table_exists(conn, SALIDA_TABLE):
            raise RuntimeError("Required source tables do not exist (entrada/salida)")

        if not table_exists(conn, SNAPSHOT_TABLE):
            raise RuntimeError(f"Required source table does not exist: {SNAPSHOT_TABLE}")

        df_wansoft = build_wansoft_side(conn)
        df_odoo = build_odoo_side(conn)
        odoo_rows_missing_wansoft_code = count_odoo_rows_missing_wansoft_code(conn)

        df_final = pd.concat([df_wansoft, df_odoo], ignore_index=True)

        recreate_table(conn)
        load_rows(conn, df_final)

        summary = get_summary(conn)
        print_summary(summary, odoo_rows_missing_wansoft_code)

        print("BUILD RESULT: COMPLETED")
        return 0

    except Exception as exc:
        print("BUILD RESULT: FAILED")
        print(f"error: {exc}")
        return 1

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
