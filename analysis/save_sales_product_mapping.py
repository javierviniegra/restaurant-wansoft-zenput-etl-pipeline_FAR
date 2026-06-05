import math
import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.build_sales_product_mapping import build_sales_product_mapping


def deduplicate_sales_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplica el mapping antes de insertar.
    Mantiene una sola fila por combinación lógica.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    out = out.drop_duplicates(
        subset=["domain", "wansoft_code", "odoo_code", "match_type"],
        keep="first"
    )

    return out


def sql_safe(value):
    """
    Convierte valores problemáticos a tipos aceptables por MySQL.
    """
    # pandas / numpy nulls
    if pd.isna(value):
        return None

    # float nan explícito
    if isinstance(value, float) and math.isnan(value):
        return None

    # strings vacíos
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        return value

    # bool -> int opcional
    if isinstance(value, bool):
        return int(value)

    return value


def save_sales_product_mapping(include_fuzzy: bool = True):
    """
    Persiste el mapping del dominio sales en MySQL.
    - exact_code -> approved
    - odoo_no_code -> pending
    - fuzzy_name -> suggested (opcional)
    """

    df_mapping = build_sales_product_mapping(threshold=95)

    if df_mapping is None or df_mapping.empty:
        print("No hay registros para guardar.")
        return

    if not include_fuzzy:
        df_mapping = df_mapping[df_mapping["match_type"] != "fuzzy_name"].copy()

    df_mapping = deduplicate_sales_mapping(df_mapping)

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO product_catalog_mapping (
        source_system,
        domain,
        wansoft_code,
        odoo_code,
        canonical_code,
        canonical_name,
        match_type,
        confidence_score,
        status,
        notes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df_mapping.iterrows():
        rows.append((
            sql_safe(row.get("source_system")),
            sql_safe(row.get("domain")),
            sql_safe(row.get("wansoft_code")),
            sql_safe(row.get("odoo_code")),
            sql_safe(row.get("canonical_code")),
            sql_safe(row.get("canonical_name")),
            sql_safe(row.get("match_type")),
            sql_safe(row.get("confidence_score")),
            sql_safe(row.get("status")),
            sql_safe(row.get("notes")),
        ))

    # Debug opcional: detectar si algo sigue mal antes de insertar
    bad_rows = []
    for i, r in enumerate(rows):
        if any(isinstance(x, float) and math.isnan(x) for x in r):
            bad_rows.append((i, r))

    if bad_rows:
        print("Se detectaron filas con NaN antes de insertar:")
        for idx, r in bad_rows[:10]:
            print(idx, r)
        raise ValueError("Todavía hay NaN en rows. Revisar build_product_mapping().")

    cursor.executemany(insert_sql, rows)
    conn.commit()

    print(f"Insertados {len(rows)} registros en product_catalog_mapping.")


    cursor.close()
    conn.close()