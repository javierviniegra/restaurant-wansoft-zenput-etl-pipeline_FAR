import pandas as pd
from core.database.mysql import get_mysql_connection as get_db_connection
from analysis.product_replacement_detector import detect_replacements


def sql_safe(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def save_product_replacements():
    df = detect_replacements(threshold=92)

    if df.empty:
        print("No hay reemplazos para guardar.")
        return

    conn = get_db_connection(target="wansoft")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO product_replacement_candidates (
        product_name_a,
        product_name_b,
        base_name,
        presentation_a,
        presentation_b,
        replacement_score,
        replacement_reason,
        recommended_lifecycle_a,
        recommended_lifecycle_b,
        review_status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for _, row in df.iterrows():
        rows.append(tuple(sql_safe(row[col]) for col in [
            "product_name_a",
            "product_name_b",
            "base_name",
            "presentation_a",
            "presentation_b",
            "replacement_score",
            "replacement_reason",
            "recommended_lifecycle_a",
            "recommended_lifecycle_b",
            "review_status"
        ]))

    cursor.executemany(insert_sql, rows)
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Insertados {len(rows)} reemplazos potenciales en product_replacement_candidates.")