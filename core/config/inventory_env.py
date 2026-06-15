import os


def parse_csv_env(value: str):
    if value is None:
        return []
    value = str(value).strip()
    if value == "":
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def get_inventory_etl_config():
    return {
        "sales_reference_scope": os.getenv("INVENTORY_ETL_SALES_REFERENCE_SCOPE", "restaurantes"),
        "sales_reference_source": os.getenv("INVENTORY_ETL_SALES_REFERENCE_SOURCE", "sales_reference"),
        "scope_include": parse_csv_env(os.getenv("INVENTORY_ETL_SCOPE_INCLUDE", "shared_cross_company")),
        "scope_backlog": parse_csv_env(
            os.getenv(
                "INVENTORY_ETL_SCOPE_BACKLOG",
                "bodegon,empanadas,bodegon_candidate,empanadas_candidate,review_scope"
            )
        ),
    }


def get_inventory_not_found_config():
    return {
        "bucket": os.getenv("INVENTORY_NOT_FOUND_BUCKET", "not_found"),
        "scope_include": parse_csv_env(os.getenv("INVENTORY_SCOPE_INCLUDE", "")),
        "scope_exclude": parse_csv_env(os.getenv("INVENTORY_SCOPE_EXCLUDE", "")),
        "export_enabled": os.getenv("INVENTORY_NOT_FOUND_EXPORT", "false").strip().lower() == "true",
        "export_file": os.getenv("INVENTORY_NOT_FOUND_EXPORT_FILE", "inventory_not_found_analysis.csv"),
    }