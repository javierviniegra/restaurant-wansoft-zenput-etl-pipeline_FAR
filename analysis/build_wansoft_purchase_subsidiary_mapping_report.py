import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from core.config.companies import (
    get_domain_company_source,
    should_include_company_in_final_domain,
)

try:
    from core.config.companies import WANSOFT_SUBSIDIARY_SOURCE_KEY
except ImportError:
    WANSOFT_SUBSIDIARY_SOURCE_KEY = {}


PURCHASE_DOMAIN = "purchases"


def normalize_text(value):
    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def resolve_wansoft_company_source_key(subsidiary_name):
    """
    Resolves Wansoft subsidiary identifier/name to COMPANY_SOURCE key.
    """
    normalized = normalize_text(subsidiary_name)

    if normalized is None:
        return None

    return WANSOFT_SUBSIDIARY_SOURCE_KEY.get(normalized)


def build_wansoft_purchase_subsidiary_mapping_report():
    """
    Builds a coverage report for Wansoft purchase-like rows.

    Source:
    - getinputinventory_entrada

    Filter:
    - TipoEntrada = 'Factura'
    """

    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        subsidiary_name,
        COUNT(*) AS total_rows,
        MIN(FechaEntrada) AS min_fecha_entrada,
        MAX(FechaEntrada) AS max_fecha_entrada,
        SUM(COALESCE(Cantidad, 0)) AS total_qty,
        SUM(COALESCE(Cantidad, 0) * COALESCE(CostoUnitario, 0)) AS total_amount
    FROM getinputinventory_entrada
    WHERE TipoEntrada = 'Factura'
    GROUP BY subsidiary_name
    ORDER BY total_rows DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return df

    df["company_source_key"] = df["subsidiary_name"].apply(
        resolve_wansoft_company_source_key
    )

    df["mapping_status"] = df["company_source_key"].apply(
        lambda x: "mapped" if pd.notna(x) and str(x).strip() != "" else "missing_mapping"
    )

    df["domain_source"] = df["company_source_key"].apply(
        lambda x: get_domain_company_source(x, PURCHASE_DOMAIN) if pd.notna(x) else "unknown"
    )

    df["include_final_company"] = df["company_source_key"].apply(
        lambda x: should_include_company_in_final_domain(x, PURCHASE_DOMAIN) if pd.notna(x) else False
    )

    def classify(row):
        if row["mapping_status"] == "missing_mapping":
            return "missing_subsidiary_mapping"

        if not row["include_final_company"]:
            return "exclude_internal_provider"

        if row["domain_source"] == "wansoft":
            return "final_wansoft_enabled"

        if row["domain_source"] == "odoo":
            return "requires_cutoff_split"

        return "unknown_source_review"

    df["wansoft_purchase_load_status"] = df.apply(classify, axis=1)

    return df


def summarize_wansoft_purchase_subsidiary_mapping_report(df: pd.DataFrame):
    """
    Summarizes Wansoft subsidiary mapping coverage.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "mapping_status",
            "domain_source",
            "wansoft_purchase_load_status",
            "subsidiaries",
            "total_rows",
            "total_amount",
        ])

    summary = (
        df.groupby(
            [
                "mapping_status",
                "domain_source",
                "wansoft_purchase_load_status",
            ],
            dropna=False
        )
        .agg(
            subsidiaries=("subsidiary_name", "nunique"),
            total_rows=("total_rows", "sum"),
            total_amount=("total_amount", "sum"),
        )
        .reset_index()
        .sort_values("total_rows", ascending=False)
    )

    return summary