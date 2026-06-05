import pandas as pd
from analysis.odoo_no_code_classifier import classify_odoo_no_code_products


def export_odoo_no_code_for_review():

    df = classify_odoo_no_code_products()

    if df.empty:
        print("No hay productos pendientes.")
        return

    export_cols = [
        "product_name",
        "category_name",
        "sale_ok",
        "purchase_ok",
        "classification_bucket",
        "likely_domain",
        "recommended_action",
        "priority"
    ]

    df_export = df[export_cols].copy()

    file_path = "odoo_no_code_review.csv"
    df_export.to_csv(file_path, index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {file_path}")
    print(f"Total registros: {len(df_export)}")


if __name__ == "__main__":
    export_odoo_no_code_for_review()