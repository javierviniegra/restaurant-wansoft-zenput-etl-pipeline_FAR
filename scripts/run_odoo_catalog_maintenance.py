from core.config.env_loader import load_environment
from analysis.odoo_no_code_classifier import classify_odoo_no_code, summarize
from analysis.product_replacement_detector import detect_replacements
from analysis.save_product_replacements import save_product_replacements


if __name__ == "__main__":
    load_environment()

    print("==== ODOO CATALOG MAINTENANCE START ====\n")

    # 1. Clasificación de no-code
    df_classified = classify_odoo_no_code()
    print("Clasificación odoo_no_code:")
    print(summarize(df_classified))

    # 2. Detección de reemplazos
    df_replacements = detect_replacements(threshold=92)
    if df_replacements.empty:
        print("\nNo se detectaron reemplazos potenciales.")
    else:
        print("\nReemplazos potenciales detectados:")
        print(df_replacements.head(20).to_string(index=False))
        save_product_replacements()

    print("\n==== ODOO CATALOG MAINTENANCE END ✅ ====")