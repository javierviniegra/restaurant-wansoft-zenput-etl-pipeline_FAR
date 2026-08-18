"""
Validate dim_time.

Validation goals:
- table exists
- row count matches configured date range
- min/max dates match configured date range
- date_key is unique
- calendar_date is unique
- date_key matches YYYYMMDD
- weekend flags are correct
- month boundary flags are correct
- quarter boundary flags are correct
- year boundary flags are correct
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import pandas as pd

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_time"

START_DATE = date(2020, 1, 1)
END_DATE = date(2035, 12, 31)


def expected_row_count() -> int:
    return (END_DATE - START_DATE).days + 1


def query_df(conn, query: str, params: tuple | None = None) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)


def validation_result(name: str, status: str, details: Any = None) -> Dict[str, Any]:
    return {
        "validation": name,
        "status": status,
        "details": details,
    }


def table_exists(conn) -> bool:
    query = """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    df = query_df(conn, query, (TABLE_NAME,))
    return bool(df.iloc[0]["total"] > 0)


def validate_table_exists(conn) -> Dict[str, Any]:
    exists = table_exists(conn)

    return validation_result(
        "dim_time_exists",
        "PASS" if exists else "FAIL",
        {"table_name": TABLE_NAME, "exists": exists},
    )


def validate_row_count(conn) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(*) AS total_rows
        FROM {TABLE_NAME}
    """
    df = query_df(conn, query)

    actual = int(df.iloc[0]["total_rows"])
    expected = expected_row_count()

    return validation_result(
        "dim_time_row_count",
        "PASS" if actual == expected else "FAIL",
        {
            "actual_rows": actual,
            "expected_rows": expected,
        },
    )


def validate_min_max_dates(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            MIN(calendar_date) AS min_date,
            MAX(calendar_date) AS max_date
        FROM {TABLE_NAME}
    """
    df = query_df(conn, query)

    min_date = str(df.iloc[0]["min_date"])
    max_date = str(df.iloc[0]["max_date"])

    expected_min = START_DATE.isoformat()
    expected_max = END_DATE.isoformat()

    status = "PASS" if min_date == expected_min and max_date == expected_max else "FAIL"

    return validation_result(
        "dim_time_min_max_dates",
        status,
        {
            "min_date": min_date,
            "expected_min": expected_min,
            "max_date": max_date,
            "expected_max": expected_max,
        },
    )


def validate_unique_date_key(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            COUNT(*) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY date_key
        HAVING COUNT(*) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "date_key_unique",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_unique_calendar_date(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            calendar_date,
            COUNT(*) AS total_rows
        FROM {TABLE_NAME}
        GROUP BY calendar_date
        HAVING COUNT(*) > 1
    """
    df = query_df(conn, query)

    return validation_result(
        "calendar_date_unique",
        "PASS" if df.empty else "FAIL",
        df.to_dict("records"),
    )


def validate_no_null_calendar_date(conn) -> Dict[str, Any]:
    query = f"""
        SELECT COUNT(*) AS bad_rows
        FROM {TABLE_NAME}
        WHERE calendar_date IS NULL
    """
    df = query_df(conn, query)
    bad_rows = int(df.iloc[0]["bad_rows"])

    return validation_result(
        "calendar_date_not_null",
        "PASS" if bad_rows == 0 else "FAIL",
        {"bad_rows": bad_rows},
    )


def validate_date_key_format(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            calendar_date
        FROM {TABLE_NAME}
        WHERE date_key <> CAST(DATE_FORMAT(calendar_date, '%Y%m%d') AS UNSIGNED)
    """
    df = query_df(conn, query)

    return validation_result(
        "date_key_matches_calendar_date",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_weekend_flags(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            calendar_date,
            day_of_week_number,
            is_weekend
        FROM {TABLE_NAME}
        WHERE (day_of_week_number IN (6, 7) AND is_weekend = FALSE)
           OR (day_of_week_number NOT IN (6, 7) AND is_weekend = TRUE)
    """
    df = query_df(conn, query)

    return validation_result(
        "weekend_flags_valid",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_month_boundary_flags(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            calendar_date,
            is_month_start,
            is_month_end
        FROM {TABLE_NAME}
        WHERE (DAY(calendar_date) = 1 AND is_month_start = FALSE)
           OR (DAY(calendar_date) <> 1 AND is_month_start = TRUE)
           OR (calendar_date = LAST_DAY(calendar_date) AND is_month_end = FALSE)
           OR (calendar_date <> LAST_DAY(calendar_date) AND is_month_end = TRUE)
    """
    df = query_df(conn, query)

    return validation_result(
        "month_boundary_flags_valid",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_quarter_boundary_flags(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            calendar_date,
            quarter_number,
            quarter_start_date,
            quarter_end_date,
            is_quarter_start,
            is_quarter_end
        FROM {TABLE_NAME}
        WHERE (calendar_date = quarter_start_date AND is_quarter_start = FALSE)
           OR (calendar_date <> quarter_start_date AND is_quarter_start = TRUE)
           OR (calendar_date = quarter_end_date AND is_quarter_end = FALSE)
           OR (calendar_date <> quarter_end_date AND is_quarter_end = TRUE)
    """
    df = query_df(conn, query)

    return validation_result(
        "quarter_boundary_flags_valid",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_year_boundary_flags(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            calendar_date,
            year_start_date,
            year_end_date,
            is_year_start,
            is_year_end
        FROM {TABLE_NAME}
        WHERE (calendar_date = year_start_date AND is_year_start = FALSE)
           OR (calendar_date <> year_start_date AND is_year_start = TRUE)
           OR (calendar_date = year_end_date AND is_year_end = FALSE)
           OR (calendar_date <> year_end_date AND is_year_end = TRUE)
    """
    df = query_df(conn, query)

    return validation_result(
        "year_boundary_flags_valid",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def validate_iso_week_fields(conn) -> Dict[str, Any]:
    query = f"""
        SELECT
            date_key,
            calendar_date,
            iso_year,
            iso_week_of_year
        FROM {TABLE_NAME}
        WHERE iso_year IS NULL
           OR iso_week_of_year IS NULL
           OR iso_week_of_year < 1
           OR iso_week_of_year > 53
    """
    df = query_df(conn, query)

    return validation_result(
        "iso_week_fields_valid",
        "PASS" if df.empty else "FAIL",
        df.head(20).to_dict("records"),
    )


def print_result(result: Dict[str, Any]) -> None:
    print(f"{result['validation']}: {result['status']}")

    details = result.get("details")

    if details not in (None, [], {}):
        print(details)


def main() -> int:
    print("=====================================================")
    print("DIM TIME VALIDATION START")
    print("=====================================================")

    conn = get_db_connection()
    results: List[Dict[str, Any]] = []

    try:
        exists_result = validate_table_exists(conn)
        results.append(exists_result)

        if exists_result["status"] == "PASS":
            results.extend(
                [
                    validate_row_count(conn),
                    validate_min_max_dates(conn),
                    validate_unique_date_key(conn),
                    validate_unique_calendar_date(conn),
                    validate_no_null_calendar_date(conn),
                    validate_date_key_format(conn),
                    validate_weekend_flags(conn),
                    validate_month_boundary_flags(conn),
                    validate_quarter_boundary_flags(conn),
                    validate_year_boundary_flags(conn),
                    validate_iso_week_fields(conn),
                ]
            )

        print()
        print("-----------------------------------------------------")
        print("VALIDATION DETAILS")
        print("-----------------------------------------------------")

        for result in results:
            print_result(result)

        total = len(results)
        passed = sum(1 for r in results if r["status"] == "PASS")
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