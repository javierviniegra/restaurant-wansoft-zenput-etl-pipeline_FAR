import pandas as pd


def build_mapping_stats(df_mapping: pd.DataFrame) -> dict:

    if df_mapping is None or df_mapping.empty:
        return {
            "summary": pd.DataFrame(),
            "match_type_counts": pd.DataFrame(),
            "status_counts": pd.DataFrame(),
            "confidence_stats": pd.DataFrame(),
            "top_fuzzy": pd.DataFrame(),
            "top_pending": pd.DataFrame()
        }

    total = len(df_mapping)

    # Limpieza segura
    df_mapping["confidence_score"] = pd.to_numeric(
        df_mapping["confidence_score"],
        errors="coerce"
    )

    # MATCH TYPE
    match_type_counts = df_mapping["match_type"].value_counts(dropna=False).reset_index()
    match_type_counts.columns = ["match_type", "count"]
    match_type_counts["pct"] = (match_type_counts["count"] / total * 100).round(2)

    # STATUS
    status_counts = df_mapping["status"].value_counts(dropna=False).reset_index()
    status_counts.columns = ["status", "count"]
    status_counts["pct"] = (status_counts["count"] / total * 100).round(2)

    # CONFIDENCE
    conf_series = df_mapping["confidence_score"].dropna()

    if not conf_series.empty:
        confidence_stats = pd.DataFrame({
            "min": [conf_series.min()],
            "max": [conf_series.max()],
            "mean": [round(conf_series.mean(), 2)],
            "count": [len(conf_series)]
        })
    else:
        confidence_stats = pd.DataFrame()

    # TOP FUZZY
    top_fuzzy = df_mapping[df_mapping["match_type"] == "fuzzy_name"].copy()
    if not top_fuzzy.empty:
        top_fuzzy = top_fuzzy.sort_values(by="confidence_score", ascending=False).head(20)
    else:
        top_fuzzy = pd.DataFrame()

    # ODOO SIN CÓDIGO
    top_pending = df_mapping[df_mapping["match_type"] == "odoo_no_code"].copy()
    if not top_pending.empty:
        top_pending = top_pending.head(20)
    else:
        top_pending = pd.DataFrame()

    # SUMMARY
    summary = pd.DataFrame([
        {"metric": "total_rows", "value": total},
        {"metric": "exact_code", "value": int((df_mapping["match_type"] == "exact_code").sum())},
        {"metric": "fuzzy_name", "value": int((df_mapping["match_type"] == "fuzzy_name").sum())},
        {"metric": "odoo_no_code", "value": int((df_mapping["match_type"] == "odoo_no_code").sum())},
        {"metric": "approved", "value": int((df_mapping["status"] == "approved").sum())},
        {"metric": "suggested", "value": int((df_mapping["status"] == "suggested").sum())},
        {"metric": "pending", "value": int((df_mapping["status"] == "pending").sum())},
    ])

    return {
        "summary": summary,
        "match_type_counts": match_type_counts,
        "status_counts": status_counts,
        "confidence_stats": confidence_stats,
        "top_fuzzy": top_fuzzy,
        "top_pending": top_pending
    }


def print_mapping_stats(stats: dict):

    if stats["summary"].empty:
        print("No hay datos de mapping.")
        return

    print("\n===== SUMMARY =====")
    print(stats["summary"].to_string(index=False))

    print("\n===== MATCH TYPE =====")
    print(stats["match_type_counts"].to_string(index=False))

    print("\n===== STATUS =====")
    print(stats["status_counts"].to_string(index=False))

    if not stats["confidence_stats"].empty:
        print("\n===== CONFIDENCE =====")
        print(stats["confidence_stats"].to_string(index=False))

    if not stats["top_fuzzy"].empty:
        print("\n===== TOP FUZZY =====")
        cols = [c for c in ["wansoft_code", "odoo_code", "canonical_name", "confidence_score"] if c in stats["top_fuzzy"].columns]
        print(stats["top_fuzzy"][cols].to_string(index=False))

    if not stats["top_pending"].empty:
        print("\n===== ODOO SIN CÓDIGO =====")
        cols = [c for c in ["canonical_name", "status", "notes"] if c in stats["top_pending"].columns]
        print(stats["top_pending"][cols].to_string(index=False))