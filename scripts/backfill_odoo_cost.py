"""
Backfill historical Odoo cost-of-sale data into gettotalcostbydate and
costeomensual_semanapyq, for every company currently configured as
COMPANY_SOURCE == "odoo" (dynamic, no hardcoded branch list).

getTotalCostByDate.py / getCostReport_SemanaPyQ.py already cover the last
31 days daily. This script fills the gap before that rolling window, from
each company's actual earliest posted cost-of-sale line in Odoo (queried
live, not assumed) up to 32 days ago. Safe to re-run: uses the same
compare-then-update/insert pattern as the two legacy scripts, so it never
duplicates a row.

Usage: python -m scripts.backfill_odoo_cost
"""

import sys
from datetime import datetime, timedelta

import pandas as pd

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from core.database.mysql import get_db_connection
from core.database.odoo import get_odoo_connection
from core.config.companies import COMPANY_SOURCE, WANSOFT_SUBSIDIARY_SOURCE_KEY
from extract.costs.odoo_cost_report import resolve_odoo_company_id, get_earliest_cost_date, get_daily_cost


CUTOFF_DATE = (datetime.now() - timedelta(days=32)).strftime("%Y-%m-%d")

SUBSIDIARY_ID_BY_KEY = {key: int(sid) for sid, key in WANSOFT_SUBSIDIARY_SOURCE_KEY.items()}


def get_operational_start_date(cursor, odoo_company_id):
    """
    Governance floor: never backfill Odoo cost data from before the
    company's operational_start_date. Without this, this script pulled
    from Odoo's earliest posted cost-of-sale line unconditionally, which
    can predate the real migration cutover (test/setup entries, or Odoo
    simply having older accounting history than the company's actual
    Wansoft-to-Odoo switch) and created real Wansoft/Odoo overlap in
    costeomensual_semanapyq. Confirmed 2026-08-31 on Antenas/Acoxpa/
    Oceanía/Tepeyac -- 4 dates with both a stale Wansoft row and an
    Odoo row for the same day, the Odoo row from data that predated
    operational_start_date.
    """
    cursor.execute(
        "SELECT operational_start_date FROM odoo_company_migration_policy WHERE odoo_company_id = %s AND is_active = 1",
        (odoo_company_id,),
    )
    row = cursor.fetchone()
    return row[0].strftime("%Y-%m-%d") if row else None


def get_known_subsidiary_name(cursor, subsidiary_id):
    cursor.execute(
        "SELECT subsidiary_name FROM gettotalcostbydate WHERE subsidiary_id = %s LIMIT 1",
        (subsidiary_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def backfill_gettotalcostbydate(cursor, subsidiary_id, subsidiary_name, df_daily):
    inserted = updated = unchanged = 0
    for _, row in df_daily.iterrows():
        lafecha = row["fecha"]
        total_costo = float(row["CostoTotal"])
        mes_ano = datetime.strptime(lafecha, "%Y-%m-%d").strftime("%m-%Y")

        cursor.execute(
            "SELECT id, CostoTotalVenta FROM gettotalcostbydate WHERE subsidiary_id = %s AND CAST(created_at as date) = %s",
            (subsidiary_id, lafecha),
        )
        existing = cursor.fetchone()

        if existing:
            _, total_db = existing
            if abs(total_costo - float(total_db)) > 0.01:
                cursor.execute(
                    "UPDATE gettotalcostbydate SET CostoTotalVenta = %s, mes_ano = %s WHERE subsidiary_id = %s AND DATE(created_at) = %s",
                    (total_costo, mes_ano, subsidiary_id, lafecha),
                )
                updated += 1
            else:
                unchanged += 1
        else:
            cursor.execute(
                "INSERT INTO gettotalcostbydate (subsidiary_id, subsidiary_name, CostoTotalVenta, mes_ano, created_at) VALUES (%s, %s, %s, %s, %s)",
                (subsidiary_id, subsidiary_name, total_costo, mes_ano, lafecha),
            )
            inserted += 1

    return inserted, updated, unchanged


def backfill_costeomensual_semanapyq(cursor, subsidiary_id, subsidiary_name, df_daily):
    df = df_daily.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    df["iso_year"] = df["fecha_dt"].dt.isocalendar().year
    df["iso_week"] = df["fecha_dt"].dt.isocalendar().week
    df = df.sort_values("fecha_dt")
    df["CostoTotal_wtd"] = df.groupby(["iso_year", "iso_week"])["CostoTotal"].cumsum()
    df["CostoDeProductosVendidos_wtd"] = df.groupby(["iso_year", "iso_week"])["CostoDeProductosVendidos"].cumsum()
    df["CostoDeMerma_wtd"] = df.groupby(["iso_year", "iso_week"])["CostoDeMerma"].cumsum()

    inserted = updated = unchanged = 0
    for _, row in df.iterrows():
        lafecha = row["fecha"]
        # costeomensual_semanapyq stores created_at = real_date + 1 day on
        # its Wansoft side (legacy/wansoft/automaticos/getCostReport_
        # SemanaPyQ.py); mirror that offset here so backfilled Odoo rows
        # land on the same created_at date as Wansoft rows for the same
        # real-world day. gettotalcostbydate (the other table this script
        # backfills) has no such offset -- see backfill_gettotalcostbydate
        # above, unaffected.
        fecha_created_at = (row["fecha_dt"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        mes_ano = row["fecha_dt"].strftime("%m-%Y")
        total_costo = float(row["CostoTotal_wtd"])
        total_productos_costo = float(row["CostoDeProductosVendidos_wtd"])
        costo_merma = float(row["CostoDeMerma_wtd"])

        cursor.execute(
            "SELECT id, CostoTotal, CostoDeProductosVendidos FROM costeomensual_semanapyq WHERE subsidiary_id = %s AND DATE(created_at) = %s",
            (subsidiary_id, fecha_created_at),
        )
        existing = cursor.fetchone()

        if existing:
            _, total_db, productos_db = existing
            if (abs(total_costo - float(total_db)) > 0.01) or (abs(total_productos_costo - float(productos_db)) > 0.01):
                cursor.execute(
                    """
                    UPDATE costeomensual_semanapyq
                    SET subsidiary_name = %s, CostoTotal = %s, CostoDeProductosVendidos = %s, CostoDeMerma = %s, mes_ano = %s
                    WHERE DATE(created_at) = %s AND subsidiary_id = %s
                    """,
                    (subsidiary_name, total_costo, total_productos_costo, costo_merma, mes_ano, fecha_created_at, subsidiary_id),
                )
                updated += 1
            else:
                unchanged += 1
        else:
            cursor.execute(
                """
                INSERT INTO costeomensual_semanapyq
                    (subsidiary_id, subsidiary_name, CostoTotal, CostoDeProductosVendidos, CostoDeMerma, mes_ano, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (subsidiary_id, subsidiary_name, total_costo, total_productos_costo, costo_merma, mes_ano, fecha_created_at),
            )
            inserted += 1

    return inserted, updated, unchanged


def main():
    odoo_keys = sorted(key for key, source in COMPANY_SOURCE.items() if source == "odoo")
    print(f"Sucursales COMPANY_SOURCE=='odoo': {odoo_keys}")

    db_connection = get_db_connection(target="wansoft")
    cursor = db_connection.cursor()
    odoo_uid, odoo_models, odoo_db, odoo_password = get_odoo_connection()

    for key in odoo_keys:
        subsidiary_id = SUBSIDIARY_ID_BY_KEY.get(key)
        if subsidiary_id is None:
            print(f"[SKIP] {key}: no aparece en WANSOFT_SUBSIDIARY_SOURCE_KEY, no se puede resolver subsidiary_id")
            continue

        subsidiary_name = get_known_subsidiary_name(cursor, subsidiary_id)
        if subsidiary_name is None:
            print(f"[SKIP] {key} (id {subsidiary_id}): sin fila previa en gettotalcostbydate; correr primero getTotalCostByDate.py")
            continue

        odoo_company_id = resolve_odoo_company_id(odoo_models, odoo_uid, odoo_db, odoo_password, key)
        if odoo_company_id is None:
            print(f"[SKIP] {key}: no se pudo resolver company_id de Odoo")
            continue

        earliest_date = get_earliest_cost_date(odoo_models, odoo_uid, odoo_db, odoo_password, odoo_company_id)
        if earliest_date is None:
            print(f"[SKIP] {key}: sin lineas de costo posted en Odoo")
            continue

        operational_start_date = get_operational_start_date(cursor, odoo_company_id)
        if operational_start_date and operational_start_date > earliest_date:
            print(
                f"[GOVERNANCE] {key}: earliest Odoo line ({earliest_date}) predates "
                f"operational_start_date ({operational_start_date}) -- clamping to "
                f"operational_start_date, Wansoft stays authoritative before it."
            )
            earliest_date = operational_start_date

        if earliest_date >= CUTOFF_DATE:
            print(f"[OK] {key}: earliest_date={earliest_date} ya cubierto por la ventana diaria de 31 dias, nada que rellenar")
            continue

        print(f"[BACKFILL] {key} (id {subsidiary_id}, odoo_company_id {odoo_company_id}): {earliest_date} -> {CUTOFF_DATE}")
        df_daily = get_daily_cost(odoo_models, odoo_uid, odoo_db, odoo_password, odoo_company_id, earliest_date, CUTOFF_DATE)

        if df_daily.empty:
            print(f"[OK] {key}: sin filas en el rango, nada que insertar")
            continue

        i1, u1, s1 = backfill_gettotalcostbydate(cursor, subsidiary_id, subsidiary_name, df_daily)
        db_connection.commit()
        i2, u2, s2 = backfill_costeomensual_semanapyq(cursor, subsidiary_id, subsidiary_name, df_daily)
        db_connection.commit()

        print(f"[DONE] {key}: gettotalcostbydate insertados={i1} actualizados={u1} sin_cambio={s1} | "
              f"costeomensual_semanapyq insertados={i2} actualizados={u2} sin_cambio={s2}")

    cursor.close()
    db_connection.close()


if __name__ == "__main__":
    main()
