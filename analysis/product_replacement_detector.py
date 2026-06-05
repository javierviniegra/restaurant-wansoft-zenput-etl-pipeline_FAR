import re
import pandas as pd
from difflib import SequenceMatcher
from analysis.odoo_no_code_classifier import classify_odoo_no_code


def normalize_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def remove_presentation_tokens(name: str) -> str:
    """
    Limpia el nombre quitando tokens típicos de presentación:
    700 ml, 750ml, 1 lt, 1l, 500 grs, 250 g, etc.
    """
    text = normalize_text(name)

    patterns = [
        r"\b\d+\s?ml\b",
        r"\b\d+\s?l\b",
        r"\b\d+\s?lt\b",
        r"\b\d+\s?grs\b",
        r"\b\d+\s?gr\b",
        r"\b\d+\s?g\b",
        r"\b\d+\s?kg\b",
        r"\b\d+\s?pza\b",
        r"\b\d+\s?pz\b",
        r"\b\d+\s?pieza\b",
        r"\b\d+\s?botellas?\b",
        r"\b\d+\s?pack\b",
    ]

    for p in patterns:
        text = re.sub(p, "", text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_presentation(name: str) -> str | None:
    """
    Extrae presentación si detecta ml/g/kg/l/lt/etc.
    """
    text = normalize_text(name)
    patterns = [
        r"(\d+\s?ml)",
        r"(\d+\s?l\b)",
        r"(\d+\s?lt\b)",
        r"(\d+\s?grs\b)",
        r"(\d+\s?gr\b)",
        r"(\d+\s?g\b)",
        r"(\d+\s?kg\b)",
        r"(\d+\s?pza\b)",
        r"(\d+\s?pz\b)",
        r"(\d+\s?pieza\b)",
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).replace(" ", "")
    return None


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() * 100


def detect_replacements(threshold: float = 92.0) -> pd.DataFrame:
    """
    Detecta posibles productos reemplazados dentro del grupo venta_sin_codigo.
    Ejemplo:
    Ginebra 750 ml -> Ginebra 700 ml
    """
    df = classify_odoo_no_code()

    if df is None or df.empty:
        return pd.DataFrame()

    # Nos enfocamos solo en productos de venta sin código
    candidates = df[df["classification"] == "venta_sin_codigo"].copy()

    if candidates.empty:
        return pd.DataFrame()

    candidates["base_name"] = candidates["product_name"].apply(remove_presentation_tokens)
    candidates["presentation"] = candidates["product_name"].apply(extract_presentation)

    rows = []

    # Comparamos entre ellos para detectar posibles reemplazos históricos
    for i, row_i in candidates.iterrows():
        for j, row_j in candidates.iterrows():
            if i >= j:
                continue

            # mismo nombre base
            if row_i["base_name"] == row_j["base_name"] and row_i["base_name"] != "":
                # distinta presentación
                if row_i["presentation"] != row_j["presentation"]:
                    score = similarity(row_i["base_name"], row_j["base_name"])
                    if score >= threshold:
                        rows.append({
                            "product_name_a": row_i["product_name"],
                            "product_name_b": row_j["product_name"],
                            "base_name": row_i["base_name"],
                            "presentation_a": row_i["presentation"],
                            "presentation_b": row_j["presentation"],
                            "replacement_score": round(score, 2),
                            "replacement_reason": "same_base_name_different_presentation",
                            "recommended_lifecycle_a": "historical",
                            "recommended_lifecycle_b": "review",
                            "review_status": "pending_review"
                        })

    return pd.DataFrame(rows)