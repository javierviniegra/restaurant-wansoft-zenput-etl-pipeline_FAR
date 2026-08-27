"""
Validate analytics_inventory_balance.

Validation goals:
- table exists
- grain is unique: (company_source_key, wansoft_code, source_system)
- Wansoft-side total reconciles against a fresh recomputation from
  getinputinventory_entrada / getOutgoingInventory_Salida with the same
  exclusion filters as the build
- Odoo-side total reconciles against analytics_inventory_snapshot
- every row is source_system in ('wansoft', 'odoo')
- every wansoft-side row's company_source_key is actually COMPANY_SOURCE == "wansoft"
  (no Antenas/Coyoacán leakage from historical rows in the raw tables)
- every odoo-side row's final_inventory_source_status is 'final_odoo_enabled'
- distributions by source_system and company are available
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.mysql import get_db_connection
from core.config.companies import COMPANY_SOURCE, WANSOFT_SUBSIDIARY_SOURCE_KEY


TARGET_TABLE = "analytics_inventory_balance"
ENTRADA_TABLE = "getinputinventory_entrada"
SALIDA_TABLE = "getOutgoingInventory_Salida"
SNAPSHOT_TABLE = "analytics_inventory_snapshot"
AMOUNT_TOLERANCE_RATE = Decimal("0.0001")

ENTRADA_EXCLUDED_TYPES = ("Orden de compra a proveedor", "Transferencia")
SALIDA_EXCLUDED_TYPES = ("Error de captura", "Factura de egresos rechazada", "Transferencia")


def query_df(conn: Any, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def table_exists(conn: Any, table_name: str) -> bool:
    query = """
        SELECT COUNT(1) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (table_name,))
    return bool(df.iloc[0]["total"] > 0)


def validate_table_exists(conn: Any) -> Dict[str, Any]:
    exists = table_exists(conn, TARGET_TABLE)
    return validation_result(
        "analytics_inventory_balance_exists",
        "PASS" if exists else "FAIL",
        {"table_name": TARGET_TABLE, "exists": exists},
    )


def validate_grain_unique(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT company_source_key, wansoft_code, source_system, COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
        GROUP BY company_source_key, wansoft_code, source_system
        HAVING COUNT(1) > 1
    """
    df = query_df(conn, query)
    return validation_result(
        "grain_unique",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_wansoft_balance_reconciles(conn: Any) -> Dict[str, Any]:
    entrada_placeholders = ",".join(["%s"] * len(ENTRADA_EXCLUDED_TYPES))
    salida_placeholders = ",".join(["%s"] * len(SALIDA_EXCLUDED_TYPES))

    # Recompute directly from source: sum entrada/salida for exactly the
    # subsidiary ids present in the wansoft side of the target table, then
    # compare the fresh total against what's stored.
    subsidiary_ids_df = query_df(
        conn,
        f"""
            SELECT DISTINCT company_source_key
            FROM {TARGET_TABLE}
            WHERE source_system = 'wansoft'
        """,
    )
    wansoft_companies = set(subsidiary_ids_df["company_source_key"].tolist())

    subsidiary_ids = [
        subsidiary_id
        for subsidiary_id, company_name in WANSOFT_SUBSIDIARY_SOURCE_KEY.items()
        if company_name in wansoft_companies
    ]

    if not subsidiary_ids:
        return validation_result(
            "wansoft_balance_reconciles",
            "FAIL",
            {"reason": "no wansoft-side rows found in target table"},
        )

    sub_placeholders = ",".join(["%s"] * len(subsidiary_ids))

    fresh_query = f"""
        SELECT
            (SELECT COALESCE(SUM(Cantidad), 0) FROM {ENTRADA_TABLE}
             WHERE subsidiary_name IN ({sub_placeholders})
               AND TipoEntrada NOT IN ({entrada_placeholders})
               AND CodigoProducto IS NOT NULL AND CodigoProducto <> '') AS fresh_entrada_total,
            (SELECT COALESCE(SUM(Cantidad), 0) FROM {SALIDA_TABLE}
             WHERE subsidiary_name IN ({sub_placeholders})
               AND TipoSalida NOT IN ({salida_placeholders})
               AND CodigoProducto IS NOT NULL AND CodigoProducto <> '') AS fresh_salida_total
    """
    params = (
        tuple(subsidiary_ids) + ENTRADA_EXCLUDED_TYPES
        + tuple(subsidiary_ids) + SALIDA_EXCLUDED_TYPES
    )
    fresh_df = query_df(conn, fresh_query, params)
    fresh_row = fresh_df.iloc[0]
    fresh_total = Decimal(str(fresh_row["fresh_entrada_total"])) - Decimal(str(fresh_row["fresh_salida_total"]))

    stored_df = query_df(
        conn,
        f"SELECT COALESCE(SUM(current_balance_qty), 0) AS stored_total FROM {TARGET_TABLE} WHERE source_system = 'wansoft'",
    )
    stored_total = Decimal(str(stored_df.iloc[0]["stored_total"]))

    difference = abs(fresh_total - stored_total)
    tolerance = max(fresh_total.copy_abs(), Decimal("1")) * AMOUNT_TOLERANCE_RATE

    return validation_result(
        "wansoft_balance_reconciles",
        "PASS" if difference <= tolerance else "FAIL",
        {
            "fresh_total": str(fresh_total),
            "stored_total": str(stored_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_odoo_balance_reconciles(conn: Any) -> Dict[str, Any]:
    fresh_query = f"""
        SELECT COALESCE(SUM(stock_qty), 0) AS fresh_total
        FROM {SNAPSHOT_TABLE}
        WHERE company_mapping_status = 'final_odoo_enabled'
          AND include_in_business_views = TRUE
          AND wansoft_code IS NOT NULL AND wansoft_code <> ''
    """
    fresh_df = query_df(conn, fresh_query)
    fresh_total = Decimal(str(fresh_df.iloc[0]["fresh_total"]))

    stored_df = query_df(
        conn,
        f"SELECT COALESCE(SUM(current_balance_qty), 0) AS stored_total FROM {TARGET_TABLE} WHERE source_system = 'odoo'",
    )
    stored_total = Decimal(str(stored_df.iloc[0]["stored_total"]))

    difference = abs(fresh_total - stored_total)
    tolerance = max(fresh_total.copy_abs(), Decimal("1")) * AMOUNT_TOLERANCE_RATE

    return validation_result(
        "odoo_balance_reconciles",
        "PASS" if difference <= tolerance else "FAIL",
        {
            "fresh_total": str(fresh_total),
            "stored_total": str(stored_total),
            "difference": str(difference),
            "tolerance": str(tolerance),
        },
    )


def validate_only_expected_source_systems(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT DISTINCT source_system FROM {TARGET_TABLE}
        WHERE source_system NOT IN ('wansoft', 'odoo')
    """
    df = query_df(conn, query)
    return validation_result(
        "only_expected_source_systems",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_only_wansoft_final_companies_on_wansoft_side(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT DISTINCT company_source_key
        FROM {TARGET_TABLE}
        WHERE source_system = 'wansoft'
    """
    df = query_df(conn, query)
    offenders = [
        company
        for company in df["company_source_key"].tolist()
        if COMPANY_SOURCE.get(company) != "wansoft"
    ]
    return validation_result(
        "only_wansoft_final_companies_on_wansoft_side",
        "PASS" if not offenders else "FAIL",
        {"offending_companies": offenders},
    )


def validate_only_odoo_final_status_on_odoo_side(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(1) AS total
        FROM {TARGET_TABLE}
        WHERE source_system = 'odoo'
          AND final_inventory_source_status <> 'final_odoo_enabled'
    """
    df = query_df(conn, query)
    total = int(df.iloc[0]["total"])
    return validation_result(
        "only_odoo_final_status_on_odoo_side",
        "PASS" if total == 0 else "FAIL",
        {"offending_rows": total},
    )


def validate_source_system_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT source_system, COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
        GROUP BY source_system
    """
    df = query_df(conn, query)
    rows = df.to_dict(orient="records")
    return validation_result(
        "source_system_distribution_available",
        "PASS" if rows else "FAIL",
        rows,
    )


def validate_company_distribution(conn: Any) -> Dict[str, Any]:
    query = f"""
        SELECT company_source_key, source_system, COUNT(1) AS total_rows
        FROM {TARGET_TABLE}
        GROUP BY company_source_key, source_system
        ORDER BY company_source_key, source_system
    """
    df = query_df(conn, query)
    rows = df.to_dict(orient="records")
    return validation_result(
        "company_distribution_available",
        "PASS" if rows else "FAIL",
        rows,
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")
    details = result.get("details")
    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("ANALYTICS INVENTORY BALANCE VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        exists_result = validate_table_exists(conn)
        results.append(exists_result)

        if exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_grain_unique(conn),
                    validate_wansoft_balance_reconciles(conn),
                    validate_odoo_balance_reconciles(conn),
                    validate_only_expected_source_systems(conn),
                    validate_only_wansoft_final_companies_on_wansoft_side(conn),
                    validate_only_odoo_final_status_on_odoo_side(conn),
                    validate_source_system_distribution(conn),
                    validate_company_distribution(conn),
                ]
            )

        print()
        print("-----------------------------------------------------")
        print("VALIDATION DETAILS")
        print("-----------------------------------------------------")

        for result in results:
            print_result(result)

        total = len(results)
        passed = sum(1 for result in results if result["status"] == "PASS")
        failed = total - passed

        print()
        print("-----------------------------------------------------")
        print("SUMMARY COUNTS")
        print("-----------------------------------------------------")
        print(f"total_validations: {total}")
        print(f"passed: {passed}")
        print(f"failed: {failed}")

        if failed == 0:
            print()
            print("VALIDATION RESULT: PASSED")
            return 0

        print()
        print("VALIDATION RESULT: FAILED")
        print("Failed validations:")
        for result in results:
            if result["status"] != "PASS":
                print(f"- {result['validation']}")
        return 1

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
