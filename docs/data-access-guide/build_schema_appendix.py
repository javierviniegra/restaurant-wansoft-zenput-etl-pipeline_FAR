"""Builds Appendix A of the data access guide: the columns of every table the
read-only users can read, taken from the production schema.

The table list is the GRANT lines of sql/maintenance/create_tukan_readonly_users.sql
(`wansoft`) plus every table of `zenput` (granted as `zenput`.*), so the
appendix always matches what the users can actually open. A granted table
missing from GROUPS below stops the script: give it a group and a description.

Reads information_schema only, with the production credentials of
core/config/.env (WANSOFT_DB_* and ZENPUT_DB_*), in a read-only session.
Rewrites the block between the appendix markers in data-access-guide.es.md,
data-access-guide.en.md and data-access-guide.es.html (the English HTML is then
rebuilt from the English Markdown):
    python docs\\data-access-guide\\build_schema_appendix.py
    python docs\\data-access-guide\\build_en_html.py
    <ControlPresupuestos_AP>\\.venv\\Scripts\\python.exe docs\\data-access-guide\\render_pdf.py
"""
import html
import os
import re
from datetime import date
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRANTS_SQL = ROOT / "sql" / "maintenance" / "create_tukan_readonly_users.sql"
START, END = "<!-- schema-appendix:start -->", "<!-- schema-appendix:end -->"

# (Spanish title, English title, [(table, Spanish description, English description)])
GROUPS = [
    ("Ventas", "Sales", [
        ("getallordenesbyday_new_venta", "encabezado del ticket (5.1)", "ticket header (5.1)"),
        ("getallordenesbyday_new_detalleventa", "renglones del ticket (5.1)", "ticket lines (5.1)"),
        ("getallordenesbyday_new_pago", "pagos del ticket (5.1)", "ticket payments (5.1)"),
        ("getallordenesbyday_new_modificador", "modificadores de los renglones (5.1)", "line modifiers (5.1)"),
        ("getglobalcashclosing", "cierre de caja (corte Z) por sucursal y día (5.1)", "cash closing (Z report) per branch and day (5.1)"),
    ]),
    ("Costos", "Costs", [
        ("costeomensual", "costo acumulado del mes, foto diaria (5.2)", "month-to-date cost, daily snapshot (5.2)"),
        ("costeomensual_semanapyq", "costo acumulado de la semana (5.2)", "week-to-date cost (5.2)"),
        ("gettotalcostbydate", "costo de venta del día (5.2)", "cost of sales of the day (5.2)"),
        ("gettablajeriareport", "rendimientos de tablajería, solo histórico Wansoft (5.2)", "butchery yields, Wansoft history only (5.2)"),
        ("costs_source_by_company", "fuente del costo por sucursal (5.2)", "cost source per branch (5.2)"),
    ]),
    ("Compras y facturas", "Purchases and invoices", [
        ("analytics_purchase_order_lines", "renglones de compra, Wansoft + Odoo (5.3)", "purchase lines, Wansoft + Odoo (5.3)"),
        ("analytics_purchase_orders", "órdenes de compra / facturas, Wansoft + Odoo (5.3)", "purchase orders / invoices, Wansoft + Odoo (5.3)"),
        ("analytics_purchase_daily_company_product", "compras por sucursal × día × producto (5.3)", "purchases per branch × day × product (5.3)"),
        ("getexpenses_factura", "facturas de proveedor de Wansoft por cuenta contable (5.3)", "Wansoft supplier invoices by account (5.3)"),
    ]),
    ("Inventario", "Inventory", [
        ("analytics_inventory_balance", "existencias de hoy, las 19 sucursales (5.4)", "today's stock, all 19 branches (5.4)"),
        ("analytics_inventory_current_product_location", "existencias de hoy de Odoo por ubicación (5.4)", "today's Odoo stock by location (5.4)"),
        ("getinputinventory_entrada", "entradas de inventario de Wansoft (5.4)", "Wansoft inventory entries (5.4)"),
        ("getoutgoinginventory_salida", "salidas de inventario de Wansoft (5.4)", "Wansoft inventory exits (5.4)"),
        ("wansoft_parallel_inputinventory_entrada", "entradas que las sucursales de Odoo siguen capturando en Wansoft, solo para comparar (5.4)", "entries the Odoo branches keep capturing in Wansoft, comparison only (5.4)"),
        ("wansoft_parallel_outgoinginventory_salida", "salidas que las sucursales de Odoo siguen capturando en Wansoft, solo para comparar (5.4)", "exits the Odoo branches keep capturing in Wansoft, comparison only (5.4)"),
        ("odoo_inventory_quant_daily", "existencias de Odoo día por día, desde 2026-10-08 (5.4)", "Odoo stock day by day, since 2026-10-08 (5.4)"),
        ("analytics_inventory_movements", "movimientos de inventario unificados, Wansoft + Odoo (5.4)", "unified inventory movements, Wansoft + Odoo (5.4)"),
        ("analytics_odoo_product_code", "código de Wansoft de cada producto de Odoo (5.4)", "Wansoft code of each Odoo product (5.4)"),
    ]),
    ("Gobierno y dimensiones", "Governance and dimensions", [
        ("analytics_company_domain_coverage", "fuente de cada dominio por sucursal (5.6)", "source of each domain per branch (5.6)"),
        ("dim_company_analytical", "sucursales y empresas (5.6)", "branches and companies (5.6)"),
        ("dim_product", "productos (5.3)", "products (5.3)"),
        ("dim_vendor", "proveedores (5.3)", "vendors (5.3)"),
        ("dim_time", "calendario (5.6)", "calendar (5.6)"),
    ]),
    ("Zenput (base zenput)", "Zenput (database zenput)", [
        ("form_templates", "plantillas de checklist (5.5)", "checklist templates (5.5)"),
        ("submissions", "checklists contestados (5.5)", "submitted checklists (5.5)"),
        ("submission_answers", "respuestas (5.5)", "answers (5.5)"),
        ("zenput_tasks", "tareas (5.5)", "tasks (5.5)"),
    ]),
]

TEXT = {
    "es": {
        "title": "Apéndice A. Esquema de las tablas",
        "intro": ("Columnas de cada tabla que el usuario de solo lectura puede consultar, "
                  "tomadas del esquema de producción el {day}. **Nulo**: si la columna admite "
                  "NULL. **Llave**: `PRI` llave primaria, `UNI` parte de una llave única, `MUL` "
                  "parte de un índice. El significado de los campos importantes está en la "
                  "sección indicada entre paréntesis."),
        "header": ("Columna", "Tipo", "Nulo", "Llave"),
        "yes": "sí", "no": "no", "columns": "columnas",
    },
    "en": {
        "title": "Appendix A. Table schemas",
        "intro": ("Columns of every table the read-only user can query, taken from the "
                  "production schema on {day}. **Null**: whether the column accepts NULL. "
                  "**Key**: `PRI` primary key, `UNI` part of a unique key, `MUL` part of an "
                  "index. The meaning of the important fields is in the section shown in "
                  "brackets."),
        "header": ("Column", "Type", "Null", "Key"),
        "yes": "yes", "no": "no", "columns": "columns",
    },
}


def granted_wansoft_tables():
    sql = GRANTS_SQL.read_text(encoding="utf-8")
    return re.findall(r"^GRANT SELECT ON `wansoft`\.`(\w+)`", sql, re.M)


def read_columns(prefix, schema, tables=None):
    conn = mysql.connector.connect(
        host=os.getenv(f"{prefix}_DB_HOST"),
        port=int(os.getenv(f"{prefix}_DB_PORT") or 3306),
        user=os.getenv(f"{prefix}_DB_USER"),
        password=os.getenv(f"{prefix}_DB_PASSWORD"),
        database="information_schema",
    )
    try:
        cur = conn.cursor()
        cur.execute("SET SESSION TRANSACTION READ ONLY")
        query = ("SELECT table_name, column_name, column_type, is_nullable, column_key "
                 "FROM columns WHERE table_schema = %s")
        params = [schema]
        if tables is not None:
            query += " AND table_name IN (" + ", ".join(["%s"] * len(tables)) + ")"
            params += tables
        cur.execute(query + " ORDER BY table_name, ordinal_position", params)
        columns = {}
        for table, name, ctype, nullable, key in cur.fetchall():
            columns.setdefault(table, []).append((name, ctype, nullable == "YES", key))
        return columns
    finally:
        conn.close()


def collect():
    wansoft = granted_wansoft_tables()
    columns = read_columns("WANSOFT", "wansoft", wansoft)
    zenput = read_columns("ZENPUT", "zenput")
    columns.update(zenput)
    expected = set(wansoft) | set(zenput)
    grouped = {t for _, _, items in GROUPS for t, _, _ in items}
    missing = sorted(expected - grouped)
    if missing:
        raise SystemExit(f"Granted tables without a group in GROUPS: {missing}")
    absent = sorted(t for t in expected if t not in columns)
    if absent:
        raise SystemExit(f"Granted tables not found in production: {absent}")
    return columns, expected


def render_markdown(lang, columns, expected, day):
    t = TEXT[lang]
    out = [START, "", f"## {t['title']}", "", t["intro"].format(day=day), ""]
    for n, (title_es, title_en, items) in enumerate(GROUPS, 1):
        out += [f"### A.{n} {title_es if lang == 'es' else title_en}", ""]
        for table, desc_es, desc_en in items:
            if table not in expected:
                continue
            cols = columns[table]
            desc = desc_es if lang == "es" else desc_en
            out += [f"**`{table}`**: {desc}. {len(cols)} {t['columns']}.", ""]
            out += ["| " + " | ".join(t["header"]) + " |", "|---|---|---|---|"]
            for name, ctype, nullable, key in cols:
                out.append(f"| `{name}` | {ctype} | {t['yes'] if nullable else t['no']} | {key or ''} |")
            out.append("")
    out.append(END)
    return "\n".join(out)


def render_html_es(columns, expected, day):
    t = TEXT["es"]
    intro = html.escape(t["intro"].format(day=day))
    intro = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", intro)
    intro = re.sub(r"`(.+?)`", r"<code>\1</code>", intro)
    out = [START, '<div class="salto"></div>', f"<h1>{t['title']}</h1>", f"<p>{intro}</p>"]
    for n, (title_es, _, items) in enumerate(GROUPS, 1):
        out.append(f"<h2>A.{n} {html.escape(title_es)}</h2>")
        for table, desc_es, _ in items:
            if table not in expected:
                continue
            cols = columns[table]
            out.append(f"<p><b><code>{table}</code></b>: {html.escape(desc_es)}. {len(cols)} {t['columns']}.</p>")
            widths = (40, 40, 10, 10)
            head = "".join(f'<th width="{w}%">{h}</th>' for h, w in zip(t["header"], widths))
            rows = "".join(
                f"<tr><td><code>{name}</code></td><td>{html.escape(ctype)}</td>"
                f"<td>{t['yes'] if nullable else t['no']}</td><td>{key or '—'}</td></tr>"
                for name, ctype, nullable, key in cols
            )
            out.append(f'<table class="compacta"><tr>{head}</tr>{rows}</table>')
    out.append(END)
    return "\n".join(out)


def inject(path, block, before):
    text = path.read_text(encoding="utf-8")
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        idx = text.index(before) if before else len(text)
        text = text[:idx].rstrip("\n") + "\n\n" + block + "\n\n" + text[idx:].lstrip("\n")
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path.name}")


def main():
    load_dotenv(ROOT / "core" / "config" / ".env")
    columns, expected = collect()
    day = date.today().isoformat()
    total = sum(len(columns[t]) for t in expected)
    print(f"{len(expected)} tables, {total} columns")
    inject(HERE / "data-access-guide.es.md", render_markdown("es", columns, expected, day), None)
    inject(HERE / "data-access-guide.en.md", render_markdown("en", columns, expected, day), None)
    inject(HERE / "data-access-guide.es.html", render_html_es(columns, expected, day), '<div id="footer_content">')


if __name__ == "__main__":
    main()
