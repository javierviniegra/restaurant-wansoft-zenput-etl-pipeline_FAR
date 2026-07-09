import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from core.config.companies import (
    get_company_source_key,
    get_domain_company_source,
    should_include_company_in_final_domain,
)


PURCHASE_DOMAIN = "purchases"


def load_mysql_table(table_name: str) -> pd.DataFrame:
    """
    Loads a MySQL table into a DataFrame.
    """
    conn = get_db_connection(target="wansoft")

    query = f"""
    SELECT *
    FROM {table_name}
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def classify_purchase_company_source(row):
    """
    Classifies whether a row from an Odoo purchase snapshot should be eligible
    for the final canonical purchase layer.

    Rules:
    - COMPANY_SOURCE is authoritative.
    - Purchases follow COMPANY_SOURCE.
    - Internal providers are excluded from final branch-level facts.
    - Odoo rows are final-eligible only when source = odoo and include_final = True.
    """
    company_name = row.get("company_name")

    source_key = get_company_source_key(company_name)
    domain_source = get_domain_company_source(company_name, PURCHASE_DOMAIN)
    include_final = should_include_company_in_final_domain(company_name, PURCHASE_DOMAIN)

    if not include_final:
        final_purchase_source_status = "exclude_internal_provider"
    elif domain_source == "odoo":
        final_purchase_source_status = "final_odoo_enabled"
    elif domain_source == "wansoft":
        final_purchase_source_status = "wansoft_only"
    else:
        final_purchase_source_status = "unknown_source_review"

    return {
        "company_source_key": source_key,
        "domain_source": domain_source,
        "include_final_company": include_final,
        "final_purchase_source_status": final_purchase_source_status,
    }


def apply_purchase_company_source_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies COMPANY_SOURCE governance flags to a purchase snapshot DataFrame.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    classified = out.apply(
        classify_purchase_company_source,
        axis=1,
        result_type="expand"
    )

    for col in [
        "company_source_key",
        "domain_source",
        "include_final_company",
        "final_purchase_source_status",
    ]:
        out[col] = classified[col]

    return out


def summarize_purchase_source_eligibility(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Summarizes source eligibility by company and final source status.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "snapshot",
            "company_name",
            "company_source_key",
            "domain_source",
            "include_final_company",
            "final_purchase_source_status",
            "rows_count",
        ])

    summary = (
        df.groupby(
            [
                "company_name",
                "company_source_key",
                "domain_source",
                "include_final_company",
                "final_purchase_source_status",
            ],
            dropna=False
        )
        .size()
        .reset_index(name="rows_count")
        .sort_values(
            [
                "final_purchase_source_status",
                "company_name",
                "rows_count",
            ],
            ascending=[True, True, False]
        )
    )

    summary.insert(0, "snapshot", label)

    return summary


def build_purchase_company_source_eligibility_report():
    """
    Builds eligibility reports for all Odoo purchase snapshots.

    Snapshots evaluated:
    - odoo_purchase_order_snapshot
    - odoo_purchase_order_line_snapshot
    - odoo_purchase_receipt_snapshot
    - odoo_purchase_receipt_move_snapshot
    """
    tables = {
        "orders": "odoo_purchase_order_snapshot",
        "lines": "odoo_purchase_order_line_snapshot",
        "receipts": "odoo_purchase_receipt_snapshot",
        "receipt_moves": "odoo_purchase_receipt_move_snapshot",
    }

    results = {}

    for label, table_name in tables.items():
        df_raw = load_mysql_table(table_name)
        df_flagged = apply_purchase_company_source_flags(df_raw)
        df_summary = summarize_purchase_source_eligibility(df_flagged, label)

        results[label] = {
            "raw": df_raw,
            "flagged": df_flagged,
            "summary": df_summary,
        }

    return results


def build_combined_purchase_company_source_eligibility_summary():
    """
    Builds one combined summary for all purchase snapshots.
    """
    reports = build_purchase_company_source_eligibility_report()

    summaries = []

    for label, payload in reports.items():
        summaries.append(payload["summary"])

    if not summaries:
        return pd.DataFrame()

    return pd.concat(summaries, ignore_index=True)


def build_final_odoo_candidate_samples(limit=50):
    """
    Returns samples from Odoo purchase snapshots that are eligible
    to feed the final canonical purchase layer.
    """
    reports = build_purchase_company_source_eligibility_report()

    samples = {}

    for label, payload in reports.items():
        df = payload["flagged"]

        if df is None or df.empty:
            samples[label] = df
            continue

        sample = (
            df[df["final_purchase_source_status"] == "final_odoo_enabled"]
            .head(limit)
            .copy()
        )

        samples[label] = sample

    return samples