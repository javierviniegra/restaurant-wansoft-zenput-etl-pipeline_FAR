"""
Inventory Company Source Eligibility Report

Paso 18.19. Classifies analytics_inventory_snapshot rows (Odoo-only, since
that table has no source_system column and is built exclusively from
odoo_inventory_snapshot) against COMPANY_SOURCE governance.

Unlike Purchases, analytics_inventory_snapshot does not carry a real Odoo
company_name. It is resolved here by joining against
stg_odoo_inventory_location_master on source_location_id, which reads
company_id/company_name directly from Odoo's stock.location configuration
(Paso 18.18).

Any company_name not explicitly present in ODOO_COMPANY_SOURCE_KEY,
ODOO_INTERNAL_PROVIDER_COMPANIES or ODOO_OUT_OF_SCOPE_COMPANIES is treated
as unmapped_location_pending_review. It is never allowed to fall back to a
default source system, unlike the permissive default used elsewhere for
Purchases-style resolution.
"""

import pandas as pd

from core.database.mysql import get_mysql_connection as get_db_connection
from core.config.companies import (
    COMPANY_SOURCE,
    ODOO_COMPANY_SOURCE_KEY,
    ODOO_INTERNAL_PROVIDER_COMPANIES,
    ODOO_OUT_OF_SCOPE_COMPANIES,
    get_company_source_key,
    get_domain_company_source,
    should_include_company_in_final_domain,
)


INVENTORY_DOMAIN = "inventory"
SNAPSHOT_TABLE = "analytics_inventory_snapshot"
LOCATION_MASTER_TABLE = "stg_odoo_inventory_location_master"


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


def load_inventory_snapshot_with_company() -> pd.DataFrame:
    """
    Loads analytics_inventory_snapshot joined against
    stg_odoo_inventory_location_master to resolve the real Odoo
    company_id / company_name per row.

    The join is performed in SQL, not with a pandas merge(). A pandas
    merge on source_location_id was tried first and silently dropped
    matches for some rows due to a dtype mismatch between the two
    independently-read DataFrames (both columns are VARCHAR(100) in
    MySQL, but pandas inferred different in-memory dtypes for each
    query result). The equivalent SQL LEFT JOIN was verified to produce
    zero unmatched rows against the same dev data, confirming the mismatch
    was a Python-side artifact, not a real data gap.

    analytics_inventory_snapshot's own company_source_key column is not
    used here: it depends on inventory_location_company_mapping_config,
    which remains empty (0 approved mappings, Paso 18.14/18.15).
    """
    conn = get_db_connection(target="wansoft")

    query = f"""
    SELECT
        s.*,
        m.odoo_company_id,
        m.odoo_company_name
    FROM {SNAPSHOT_TABLE} s
    LEFT JOIN {LOCATION_MASTER_TABLE} m
        ON m.source_location_id = s.source_location_id
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def is_known_company(company_name: str) -> bool:
    """
    Returns True only when the Odoo company_name is explicitly present in
    one of the project's governance dictionaries. This is intentionally
    stricter than get_company_source(), which defaults unknown companies
    to wansoft. Here an unknown company must be flagged for review, not
    silently defaulted.
    """
    if not company_name:
        return False

    return (
        company_name in ODOO_COMPANY_SOURCE_KEY
        or company_name in ODOO_INTERNAL_PROVIDER_COMPANIES
        or company_name in ODOO_OUT_OF_SCOPE_COMPANIES
    )


def classify_inventory_company_source(row):
    """
    Classifies an inventory snapshot row using COMPANY_SOURCE governance,
    resolved from the real Odoo company_name (odoo_company_name), never
    inferred from location_name text.
    """
    company_name = row.get("odoo_company_name")

    if pd.isna(company_name) or not is_known_company(company_name):
        return {
            "company_source_key": None,
            "domain_source": "unmapped",
            "include_final_company": False,
            "final_inventory_source_status": "unmapped_location_pending_review",
        }

    source_key = get_company_source_key(company_name)
    domain_source = get_domain_company_source(company_name, INVENTORY_DOMAIN)
    include_final = should_include_company_in_final_domain(company_name, INVENTORY_DOMAIN)

    if domain_source == "out_of_scope":
        final_inventory_source_status = "out_of_scope_excluded"
    elif domain_source == "internal_provider":
        final_inventory_source_status = "internal_provider_excluded"
    elif domain_source == "odoo":
        final_inventory_source_status = "final_odoo_enabled"
    elif domain_source == "wansoft":
        final_inventory_source_status = "parallel_diagnostic_odoo"
    else:
        final_inventory_source_status = "unknown_source_review"

    return {
        "company_source_key": source_key,
        "domain_source": domain_source,
        "include_final_company": include_final,
        "final_inventory_source_status": final_inventory_source_status,
    }


def apply_inventory_company_source_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies COMPANY_SOURCE governance flags to an inventory snapshot
    DataFrame already joined with the Odoo location master.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    classified = out.apply(
        classify_inventory_company_source,
        axis=1,
        result_type="expand"
    )

    for col in [
        "company_source_key",
        "domain_source",
        "include_final_company",
        "final_inventory_source_status",
    ]:
        out[col] = classified[col]

    return out


def summarize_inventory_source_eligibility(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarizes source eligibility by resolved Odoo company and final
    inventory source status.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "odoo_company_name",
            "company_source_key",
            "domain_source",
            "include_final_company",
            "final_inventory_source_status",
            "distinct_locations",
            "rows_count",
        ])

    summary = (
        df.groupby(
            [
                "odoo_company_name",
                "company_source_key",
                "domain_source",
                "include_final_company",
                "final_inventory_source_status",
            ],
            dropna=False
        )
        .agg(
            distinct_locations=("source_location_id", "nunique"),
            rows_count=("source_location_id", "size"),
        )
        .reset_index()
        .sort_values(
            [
                "final_inventory_source_status",
                "odoo_company_name",
                "rows_count",
            ],
            ascending=[True, True, False]
        )
    )

    return summary


def build_inventory_company_source_eligibility_report():
    """
    Builds the full eligibility report for analytics_inventory_snapshot.

    Returns a dict with:
    - raw: snapshot joined with the Odoo location master, unflagged
    - flagged: same, with governance columns applied
    - summary: distribution by company and final_inventory_source_status
    """
    df_raw = load_inventory_snapshot_with_company()
    df_flagged = apply_inventory_company_source_flags(df_raw)
    df_summary = summarize_inventory_source_eligibility(df_flagged)

    return {
        "raw": df_raw,
        "flagged": df_flagged,
        "summary": df_summary,
    }


def print_report():
    report = build_inventory_company_source_eligibility_report()

    print("=====================================================")
    print("INVENTORY COMPANY SOURCE ELIGIBILITY REPORT")
    print("=====================================================")

    summary = report["summary"]

    if summary is None or summary.empty:
        print("No rows found in analytics_inventory_snapshot.")
        return

    total_rows = int(summary["rows_count"].sum())
    print(f"total_rows: {total_rows}")
    print()

    for status in summary["final_inventory_source_status"].unique():
        subset = summary[summary["final_inventory_source_status"] == status]
        status_rows = int(subset["rows_count"].sum())
        print(f"--- {status} (rows: {status_rows}) ---")
        for _, r in subset.iterrows():
            print(
                f"  {r['odoo_company_name']!s:40s} "
                f"company_source_key={r['company_source_key']!s:20s} "
                f"locations={r['distinct_locations']:>4} "
                f"rows={r['rows_count']:>6}"
            )
        print()


if __name__ == "__main__":
    print_report()
