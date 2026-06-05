from core.database.odoo import get_odoo_connection
import pandas as pd
import re


def extract_odoo_inventory():

    uid, models, db, password = get_odoo_connection()

    inventory = models.execute_kw(
        db,
        uid,
        password,
        'stock.quant',
        'search_read',
        [[]],
        {
            'fields': [
                'product_id',
                'location_id',
                'quantity'
            ]
        }
    )

    df = pd.DataFrame(inventory)

    # Separar campos many2one
    df["source_product_id"] = df["product_id"].apply(lambda x: x[0] if x else None)
    df["product_name_raw"] = df["product_id"].apply(lambda x: x[1] if x else None)

    df["source_location_id"] = df["location_id"].apply(lambda x: x[0] if x else None)
    df["location_name"] = df["location_id"].apply(lambda x: x[1] if x else None)

    # Extraer código entre corchetes
    df["product_code"] = df["product_name_raw"].apply(
        lambda x: re.search(r"\[(.*?)\]", x).group(1) if x and "[" in x else None
    )

    # Nombre limpio sin el código
    df["product_name"] = df["product_name_raw"].apply(
        lambda x: re.sub(r"^\[.*?\]\s*", "", x).strip() if x else None
    )

    df = df.rename(columns={"quantity": "stock_qty"})

    df["source"] = "odoo"

    cols = [
        "source",
        "source_product_id",
        "product_code",
        "product_name",
        "source_location_id",
        "location_name",
        "stock_qty"
    ]

    return df[cols]