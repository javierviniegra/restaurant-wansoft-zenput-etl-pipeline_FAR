"""
Copies of a Wansoft cash closing (getglobalcashclosing).

A cashier sometimes saves the same corte several times (14 times in 3 minutes
at San Jeronimo on 2026-04-12), or saves last night's corte again the next
morning. Wansoft returns each save with its own Fecha, so the loader's key
(subsidiary_id, fecha_corte) lets every copy in and sums count it twice
(tukan's P77, 2026-11-23: 297 copies, 40 of the 242 groups on two days).

A row is a copy when another row of the same subsidiary, at most
WINDOW_HOURS away, has exactly the same figures in every amount and count
column (subtotal .. cupones). Cortes with total_ventas = 0 are never copies.
The first one (earliest fecha_corte, then lowest id) is the corte; the rest
are copies. The loader does not insert a copy, and
scripts/remove_cash_closing_copies.py removes the ones already loaded.
"""
from decimal import Decimal

WINDOW_HOURS = 48

FIGURE_COLUMNS = [
    "subtotal", "iva", "ieps", "total_ventas", "efectivo_por_ventas", "efectivo_por_propina",
    "fondo_de_caja", "efectivo_real", "no_ordenes", "no_platillos", "total_personas",
    "promedio_platillos_orden", "promedio_por_orden", "promedio_por_persona",
    "total_ordenes_para_llevar", "total_mesas_atendidas", "total_ordenes_a_domicilio",
    "total_ordenes_recoger", "no_cortesias_en_cuentas", "cortesias_en_cuentas",
    "no_cortesias_en_platillos", "cortesias_en_platillos", "no_cancelaciones_en_cuentas",
    "cancelaciones_en_cuentas", "no_cancelaciones_en_platillos", "cancelaciones_en_platillos",
    "no_descuentos_en_cuentas", "descuentos_en_cuentas", "no_descuentos_en_platillos",
    "descuentos_en_platillos", "no_anulaciones_en_cuentas", "anulaciones_en_cuentas",
    "no_anulaciones_en_platillos", "anulaciones_en_platillos", "no_dxu_platillos", "dxu_platillos",
    "no_descuentos_megapuntos", "descuentos_megapuntos", "no_promociones", "promociones",
    "no_cupones", "cupones",
]


def _as_db(value):
    """The value as the DECIMAL(10,2)/INT column stores it, so '=' compares like the table."""
    if isinstance(value, float):
        return Decimal(str(round(value, 2)))
    return value


def find_original(cursor, subsidiary_id, fecha_corte, data):
    """id of an already loaded corte that this new one copies, or None."""
    if not data.get("total_ventas"):
        return None
    same = " AND ".join(f"{c} = %s" for c in FIGURE_COLUMNS)
    cursor.execute(
        f"""SELECT id FROM getglobalcashclosing
            WHERE subsidiary_id = %s AND fecha_corte <> %s
              AND fecha_corte BETWEEN %s - INTERVAL {WINDOW_HOURS} HOUR AND %s + INTERVAL {WINDOW_HOURS} HOUR
              AND {same}
            ORDER BY fecha_corte, id LIMIT 1""",
        [subsidiary_id, fecha_corte, fecha_corte, fecha_corte] + [_as_db(data[c]) for c in FIGURE_COLUMNS],
    )
    row = cursor.fetchone()
    return row[0] if row else None


# Every loaded copy with the corte it copies: an earlier row of the same
# subsidiary (by fecha_corte, then id) with the same figures within the window.
COPIES_SQL = f"""
    SELECT c.id AS copy_id, MIN(o.id) AS original_id
    FROM getglobalcashclosing c
    JOIN getglobalcashclosing o
      ON o.subsidiary_id = c.subsidiary_id
     AND (o.fecha_corte < c.fecha_corte OR (o.fecha_corte = c.fecha_corte AND o.id < c.id))
     AND o.fecha_corte >= c.fecha_corte - INTERVAL {WINDOW_HOURS} HOUR
     AND {" AND ".join(f"o.{col} = c.{col}" for col in FIGURE_COLUMNS)}
    WHERE c.total_ventas <> 0
    GROUP BY c.id
"""
