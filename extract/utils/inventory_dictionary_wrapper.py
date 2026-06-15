import pandas as pd
from extract.utils.inventory_dictionary_lookup import load_inventory_mapping_dictionary


def apply_inventory_dictionary(
    df_odoo_inventory: pd.DataFrame,
    product_name_col: str = "product_name",
    odoo_product_id_col: str = "odoo_product_id",
    allow_pending: bool = False,
    allow_historical: bool = False
) -> pd.DataFrame:
    """
    Aplica el diccionario de inventory a un DataFrame del ETL de Odoo.

    Añade columnas:
    - mapping_found
    - lookup_method
    - mapping_status
    - usable_for_etl
    - wansoft_code
    - wansoft_product_name
    - wansoft_department
    - lifecycle_candidate
    - similarity_score
    - mapping_notes
    """

    if df_odoo_inventory is None or df_odoo_inventory.empty:
        return pd.DataFrame()

    df = df_odoo_inventory.copy()

    lookup_engine = load_inventory_mapping_dictionary()

    results = []

    for _, row in df.iterrows():
        product_name = row.get(product_name_col)
        odoo_product_id = row.get(odoo_product_id_col)

        match = lookup_engine.lookup(
            odoo_product_name=product_name,
            odoo_product_id=odoo_product_id,
            allow_pending=allow_pending,
            allow_historical=allow_historical
        )

        results.append(match)

    df_lookup = pd.DataFrame(results)

    df["mapping_found"] = df_lookup["found"]
    df["lookup_method"] = df_lookup["lookup_method"]
    df["mapping_status"] = df_lookup["mapping_status"]
    df["usable_for_etl"] = df_lookup["usable_for_etl"]
    df["wansoft_code"] = df_lookup["wansoft_code"]
    df["wansoft_product_name"] = df_lookup["wansoft_product_name"]
    df["wansoft_department"] = df_lookup["wansoft_department"]
    df["lifecycle_candidate"] = df_lookup["lifecycle_candidate"]
    df["similarity_score"] = df_lookup["similarity_score"]
    df["mapping_notes"] = df_lookup["notes"]

    return df


def summarize_inventory_dictionary_application(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resumen rápido del resultado del wrapper.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["metric", "value"])

    total = len(df)
    found = int(df["mapping_found"].fillna(False).sum())
    usable = int(df["usable_for_etl"].fillna(False).sum())
    not_found = total - found
    not_usable = total - usable

    summary = pd.DataFrame([
        {"metric": "total_rows", "value": total},
        {"metric": "mapping_found", "value": found},
        {"metric": "mapping_not_found", "value": not_found},
        {"metric": "usable_for_etl", "value": usable},
        {"metric": "not_usable_for_etl", "value": not_usable},
    ])

    return summary


def split_inventory_dictionary_result(df: pd.DataFrame) -> dict:
    """
    Devuelve particiones útiles para el ETL.
    """
    if df is None or df.empty:
        return {
            "approved_rows": pd.DataFrame(),
            "pending_rows": pd.DataFrame(),
            "historical_rows": pd.DataFrame(),
            "not_found_rows": pd.DataFrame()
        }

    approved_rows = df[df["mapping_status"] == "approved"].copy()
    pending_rows = df[df["mapping_status"] == "pending_review"].copy()
    historical_rows = df[df["mapping_status"] == "historical_only"].copy()
    not_found_rows = df[df["mapping_found"] == False].copy()

    return {
        "approved_rows": approved_rows,
        "pending_rows": pending_rows,
        "historical_rows": historical_rows,
        "not_found_rows": not_found_rows
    }
