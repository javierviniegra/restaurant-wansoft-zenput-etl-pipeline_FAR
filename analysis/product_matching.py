from rapidfuzz import fuzz


def suggest_fuzzy_matches(df_w, df_o, threshold=95):

    suggestions = []

    for _, w_row in df_w.iterrows():

        for _, o_row in df_o.iterrows():

            score = fuzz.ratio(
                w_row["product_name"].lower(),
                o_row["product_name"].lower()
            )

            if score >= threshold:
                suggestions.append({
                    "wansoft_code": w_row["product_code"],
                    "odoo_code": o_row["product_code"],
                    "wansoft_name": w_row["product_name"],
                    "odoo_name": o_row["product_name"],
                    "score": score
                })

    return suggestions
