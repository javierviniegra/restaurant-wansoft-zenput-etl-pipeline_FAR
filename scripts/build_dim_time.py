"""
Build dim_time.

This script creates and refreshes the shared analytical calendar dimension used
by the unified MySQL analytical layer.

The table is deterministic:
- 1 row = 1 calendar date
- date_key = YYYYMMDD
- calendar_date is unique
- default range: 2020-01-01 to 2035-12-31

This script does not implement BI logic.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Dict, List

from core.database.mysql import get_db_connection


TABLE_NAME = "dim_time"

START_DATE = date(2020, 1, 1)
END_DATE = date(2035, 12, 31)


@dataclass
class TimeRow:
    date_key: int
    calendar_date: date

    year: int
    year_start_date: date
    year_end_date: date
    is_year_start: bool
    is_year_end: bool

    quarter_number: int
    quarter_name: str
    year_quarter: str
    quarter_start_date: date
    quarter_end_date: date
    is_quarter_start: bool
    is_quarter_end: bool

    month_number: int
    month_name: str
    month_short_name: str
    year_month_label: str
    month_start_date: date
    month_end_date: date
    is_month_start: bool
    is_month_end: bool

    week_of_year: int
    iso_week_of_year: int
    iso_year: int
    week_start_date: date
    week_end_date: date
    is_week_start: bool
    is_week_end: bool

    day_of_month: int
    day_of_year: int
    day_of_week_number: int
    day_of_week_name: str
    day_of_week_short_name: str
    is_weekend: bool


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def date_key_from_date(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def month_end(value: date) -> date:
    last_day = calendar.monthrange(value.year, value.month)[1]
    return date(value.year, value.month, last_day)


def quarter_start(value: date) -> date:
    quarter_number = ((value.month - 1) // 3) + 1
    start_month = ((quarter_number - 1) * 3) + 1
    return date(value.year, start_month, 1)


def quarter_end(value: date) -> date:
    quarter_number = ((value.month - 1) // 3) + 1
    end_month = quarter_number * 3
    last_day = calendar.monthrange(value.year, end_month)[1]
    return date(value.year, end_month, last_day)


def iso_week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def iso_week_end(value: date) -> date:
    return iso_week_start(value) + timedelta(days=6)


def build_time_row(value: date) -> TimeRow:
    iso = value.isocalendar()

    year_start = date(value.year, 1, 1)
    year_end = date(value.year, 12, 31)

    q_number = ((value.month - 1) // 3) + 1
    q_name = f"Q{q_number}"
    q_start = quarter_start(value)
    q_end = quarter_end(value)

    m_start = date(value.year, value.month, 1)
    m_end = month_end(value)

    w_start = iso_week_start(value)
    w_end = iso_week_end(value)

    day_of_week_number = value.weekday() + 1

    return TimeRow(
        date_key=date_key_from_date(value),
        calendar_date=value,

        year=value.year,
        year_start_date=year_start,
        year_end_date=year_end,
        is_year_start=value == year_start,
        is_year_end=value == year_end,

        quarter_number=q_number,
        quarter_name=q_name,
        year_quarter=f"{value.year}-{q_name}",
        quarter_start_date=q_start,
        quarter_end_date=q_end,
        is_quarter_start=value == q_start,
        is_quarter_end=value == q_end,

        month_number=value.month,
        month_name=calendar.month_name[value.month],
        month_short_name=calendar.month_abbr[value.month],
        year_month_label=value.strftime("%Y-%m"),
        month_start_date=m_start,
        month_end_date=m_end,
        is_month_start=value == m_start,
        is_month_end=value == m_end,

        week_of_year=int(value.strftime("%U")),
        iso_week_of_year=int(iso.week),
        iso_year=int(iso.year),
        week_start_date=w_start,
        week_end_date=w_end,
        is_week_start=value == w_start,
        is_week_end=value == w_end,

        day_of_month=value.day,
        day_of_year=int(value.strftime("%j")),
        day_of_week_number=day_of_week_number,
        day_of_week_name=calendar.day_name[value.weekday()],
        day_of_week_short_name=calendar.day_abbr[value.weekday()],
        is_weekend=day_of_week_number in (6, 7),
    )


def generate_rows(start_date: date, end_date: date) -> List:
    rows: List[TimeRow] = []

    current = start_date

    while current <= end_date:
        rows.append(build_time_row(current))
        current = current + timedelta(days=1)

    return rows


def create_table_if_missing(conn) -> None:
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        date_key INT NOT NULL PRIMARY KEY,
        calendar_date DATE NOT NULL,

        year SMALLINT NOT NULL,
        year_start_date DATE NOT NULL,
        year_end_date DATE NOT NULL,
        is_year_start BOOLEAN NOT NULL DEFAULT FALSE,
        is_year_end BOOLEAN NOT NULL DEFAULT FALSE,

        quarter_number TINYINT NOT NULL,
        quarter_name VARCHAR(10) NOT NULL,
        year_quarter VARCHAR(20) NOT NULL,
        quarter_start_date DATE NOT NULL,
        quarter_end_date DATE NOT NULL,
        is_quarter_start BOOLEAN NOT NULL DEFAULT FALSE,
        is_quarter_end BOOLEAN NOT NULL DEFAULT FALSE,

        month_number TINYINT NOT NULL,
        month_name VARCHAR(20) NOT NULL,
        month_short_name VARCHAR(10) NOT NULL,
        year_month_label VARCHAR(10) NOT NULL,
        month_start_date DATE NOT NULL,
        month_end_date DATE NOT NULL,
        is_month_start BOOLEAN NOT NULL DEFAULT FALSE,
        is_month_end BOOLEAN NOT NULL DEFAULT FALSE,

        week_of_year TINYINT NOT NULL,
        iso_week_of_year TINYINT NOT NULL,
        iso_year SMALLINT NOT NULL,
        week_start_date DATE NOT NULL,
        week_end_date DATE NOT NULL,
        is_week_start BOOLEAN NOT NULL DEFAULT FALSE,
        is_week_end BOOLEAN NOT NULL DEFAULT FALSE,

        day_of_month TINYINT NOT NULL,
        day_of_year SMALLINT NOT NULL,
        day_of_week_number TINYINT NOT NULL,
        day_of_week_name VARCHAR(20) NOT NULL,
        day_of_week_short_name VARCHAR(10) NOT NULL,
        is_weekend BOOLEAN NOT NULL DEFAULT FALSE,

        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_dim_time_calendar_date (calendar_date),
        KEY idx_dim_time_year_month (year_month_label),
        KEY idx_dim_time_year_quarter (year_quarter),
        KEY idx_dim_time_year_month_number (year, month_number),
        KEY idx_dim_time_iso_year_week (iso_year, iso_week_of_year),
        KEY idx_dim_time_weekend (is_weekend)
    )
    """
    cursor = conn.cursor()
    cursor.execute(ddl)
    conn.commit()
    cursor.close()


def insert_rows(conn, rows: List[TimeRow]) -> None:
    sql = f"""
    INSERT INTO {TABLE_NAME} (
        date_key,
        calendar_date,
        year,
        year_start_date,
        year_end_date,
        is_year_start,
        is_year_end,
        quarter_number,
        quarter_name,
        year_quarter,
        quarter_start_date,
        quarter_end_date,
        is_quarter_start,
        is_quarter_end,
        month_number,
        month_name,
        month_short_name,
        year_month_label,
        month_start_date,
        month_end_date,
        is_month_start,
        is_month_end,
        week_of_year,
        iso_week_of_year,
        iso_year,
        week_start_date,
        week_end_date,
        is_week_start,
        is_week_end,
        day_of_month,
        day_of_year,
        day_of_week_number,
        day_of_week_name,
        day_of_week_short_name,
        is_weekend
    )
    VALUES (
        %(date_key)s,
        %(calendar_date)s,
        %(year)s,
        %(year_start_date)s,
        %(year_end_date)s,
        %(is_year_start)s,
        %(is_year_end)s,
        %(quarter_number)s,
        %(quarter_name)s,
        %(year_quarter)s,
        %(quarter_start_date)s,
        %(quarter_end_date)s,
        %(is_quarter_start)s,
        %(is_quarter_end)s,
        %(month_number)s,
        %(month_name)s,
        %(month_short_name)s,
        %(year_month_label)s,
        %(month_start_date)s,
        %(month_end_date)s,
        %(is_month_start)s,
        %(is_month_end)s,
        %(week_of_year)s,
        %(iso_week_of_year)s,
        %(iso_year)s,
        %(week_start_date)s,
        %(week_end_date)s,
        %(is_week_start)s,
        %(is_week_end)s,
        %(day_of_month)s,
        %(day_of_year)s,
        %(day_of_week_number)s,
        %(day_of_week_name)s,
        %(day_of_week_short_name)s,
        %(is_weekend)s
    )
    """

    payload = []

    for row in rows:
        item = asdict(row)
        item["is_year_start"] = bool_to_int(row.is_year_start)
        item["is_year_end"] = bool_to_int(row.is_year_end)
        item["is_quarter_start"] = bool_to_int(row.is_quarter_start)
        item["is_quarter_end"] = bool_to_int(row.is_quarter_end)
        item["is_month_start"] = bool_to_int(row.is_month_start)
        item["is_month_end"] = bool_to_int(row.is_month_end)
        item["is_week_start"] = bool_to_int(row.is_week_start)
        item["is_week_end"] = bool_to_int(row.is_week_end)
        item["is_weekend"] = bool_to_int(row.is_weekend)
        payload.append(item)

    cursor = conn.cursor()

    # Deterministic rebuild. date_key is stable, so rebuilding is safe.
    cursor.execute(f"DELETE FROM {TABLE_NAME}")
    cursor.executemany(sql, payload)

    conn.commit()
    cursor.close()


def print_summary(rows: List[TimeRow]) -> None:
    print("=====================================================")
    print("DIM TIME BUILD SUMMARY")
    print("=====================================================")
    print(f"table: {TABLE_NAME}")
    print(f"start_date: {START_DATE}")
    print(f"end_date: {END_DATE}")
    print(f"total_rows_prepared: {len(rows)}")
    print(f"min_date_key: {rows[0].date_key if rows else None}")
    print(f"max_date_key: {rows[-1].date_key if rows else None}")
    print("=====================================================")


def main() -> int:
    print("=====================================================")
    print("DIM TIME BUILD START")
    print("=====================================================")

    conn = get_db_connection()

    try:
        create_table_if_missing(conn)
        rows = generate_rows(START_DATE, END_DATE)
        insert_rows(conn, rows)
        print_summary(rows)

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