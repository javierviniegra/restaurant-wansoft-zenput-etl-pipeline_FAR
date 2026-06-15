import pandas as pd
import unicodedata
from core.database.mysql import get_mysql_connection as get_db_connection


def normalize_text(text: str) -> str:
    """
    Normaliza texto para matching estable por nombre:
    - minúsculas
    - sin acentos
    - sin espacios extra
    """
    if text is None or pd.isna(text):
        return ""

    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = " ".join(text.split())
    return text


class InventoryDictionaryLookup:
    """
    Lookup en memoria del diccionario de inventory.

    Prioridad de búsqueda:
    1. odoo_product_id
    2. odoo_product_name normalizado
    """

    def __init__(self, df_dictionary: pd.DataFrame):
        self.df = df_dictionary.copy()

        if "odoo_product_name" in self.df.columns:
            self.df["odoo_product_name_norm"] = self.df["odoo_product_name"].apply(normalize_text)
        else:
            self.df["odoo_product_name_norm"] = ""

        if "mapping_status" not in self.df.columns:
            self.df["mapping_status"] = None

        if "similarity_score" in self.df.columns:
            self.df["similarity_score"] = pd.to_numeric(self.df["similarity_score"], errors="coerce")
        else:
            self.df["similarity_score"] = None

        # Índice por id Odoo
        self.by_odoo_id = {}
        if "odoo_product_id" in self.df.columns:
            temp = self.df[self.df["odoo_product_id"].notna()].copy()
            for _, row in temp.iterrows():
                try:
                    self.by_odoo_id[int(row["odoo_product_id"])] = row.to_dict()
                except Exception:
                    pass

        # Índice por nombre normalizado
        self.by_name = {}
        for _, row in self.df.iterrows():
            key = row["odoo_product_name_norm"]
            if not key:
                continue

            current = self.by_name.get(key)
            if current is None:
                self.by_name[key] = row.to_dict()
            else:
                self.by_name[key] = self._pick_best(current, row.to_dict())

    def _status_priority(self, status: str) -> int:
        priorities = {
            "approved": 1,
            "pending_review": 2,
            "historical_only": 3,
            "rejected": 4,
            "unresolved": 5,
        }
        return priorities.get(status, 99)

    def _pick_best(self, a: dict, b: dict) -> dict:
        """
        Decide cuál fila conservar cuando hay choque por nombre.
        Prioriza:
        1. mapping_status
        2. similarity_score
        """
        pa = self._status_priority(a.get("mapping_status"))
        pb = self._status_priority(b.get("mapping_status"))

        if pa < pb:
            return a
        if pb < pa:
            return b

        sa = a.get("similarity_score")
        sb = b.get("similarity_score")

        sa = -1 if pd.isna(sa) else sa
        sb = -1 if pd.isna(sb) else sb

        return a if sa >= sb else b

    def lookup(
        self,
        odoo_product_name: str,
        odoo_product_id=None,
        allow_pending: bool = False,
        allow_historical: bool = False
    ) -> dict:
        """
        Devuelve el mejor match del diccionario.

        Resultado estándar:
        {
            "found": bool,
            "lookup_method": "odoo_product_id" | "odoo_product_name" | None,
            "mapping_status": str | None,
            "usable_for_etl": bool,
            "wansoft_code": str | None,
            "wansoft_product_name": str | None,
            "wansoft_department": str | None,
            "lifecycle_candidate": str | None,
            "similarity_score": float | None,
            "notes": str | None
        }
        """

        result = {
            "found": False,
            "lookup_method": None,
            "mapping_status": None,
            "usable_for_etl": False,
            "wansoft_code": None,
            "wansoft_product_name": None,
            "wansoft_department": None,
            "lifecycle_candidate": None,
            "similarity_score": None,
            "notes": None,
        }

        row = None

        # 1) Lookup por ID Odoo
        if odoo_product_id is not None:
            try:
                row = self.by_odoo_id.get(int(odoo_product_id))
                if row:
                    result["lookup_method"] = "odoo_product_id"
            except Exception:
                row = None

        # 2) Fallback por nombre
        if row is None:
            key = normalize_text(odoo_product_name)
            row = self.by_name.get(key)
            if row:
                result["lookup_method"] = "odoo_product_name"

        # 3) No encontrado
        if row is None:
            return result

        # 4) Armar respuesta
        result["found"] = True
        result["mapping_status"] = row.get("mapping_status")
        result["wansoft_code"] = row.get("wansoft_code")
        result["wansoft_product_name"] = row.get("wansoft_product_name")
        result["wansoft_department"] = row.get("wansoft_department")
        result["lifecycle_candidate"] = row.get("lifecycle_candidate")
        result["similarity_score"] = row.get("similarity_score")
        result["notes"] = row.get("notes")

        status = row.get("mapping_status")

        if status == "approved":
            result["usable_for_etl"] = True
        elif status == "pending_review" and allow_pending:
            result["usable_for_etl"] = True
        elif status == "historical_only" and allow_historical:
            result["usable_for_etl"] = True
        else:
            result["usable_for_etl"] = False

        return result


def load_inventory_mapping_dictionary() -> InventoryDictionaryLookup:
    """
    Carga el diccionario de inventory desde MySQL y devuelve
    un objeto listo para hacer lookups en memoria.
    """
    conn = get_db_connection(target="wansoft")

    query = """
    SELECT
        odoo_product_id,
        odoo_product_name,
        odoo_category_name,
        wansoft_code,
        wansoft_product_name,
        wansoft_department,
        mapping_source,
        mapping_status,
        lifecycle_candidate,
        similarity_score,
        notes
    FROM inventory_mapping_dictionary
    WHERE domain = 'inventory'
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return InventoryDictionaryLookup(df)