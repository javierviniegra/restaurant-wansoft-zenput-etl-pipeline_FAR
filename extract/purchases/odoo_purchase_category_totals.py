"""
Odoo Purchase Totals by Product-Category Expense Account (read-only)

Classifies purchase.order.line rows by the expense account tied to each
product's category, reusing the same account_type='expense_direct_cost'
accounts already validated for Costos (extract/costs/odoo_cost_report.py).
Built during the Inventory/Purchases acceptance gate (2026-08-27, Acoxpa
July 2026) as a company-agnostic replacement for comparing "Compras
Materia Prima" against production Power BI, which computes it from
Wansoft's Departamento field on getinputinventory_entrada.

Why this exists instead of joining on wansoft_department:
canonical_purchase_order_line_snapshot.wansoft_department only covers
~8% of Odoo purchase line amounts for a tested branch/month (most lines
fall into unmapped_inventory_candidate / unmapped_bodegon / etc. product
mapping buckets) -- nowhere near enough for a reliable comparison.

Critical gotcha found live against Odoo: product.category's
property_account_expense_categ_id is a company-dependent field
(ir.property in Odoo). Reading it via XML-RPC without an explicit company
context returns the wrong (effectively arbitrary/default) account for
every category -- confirmed by the project owner directly in the Odoo UI
for Acoxpa (Carbon -> "504.01.05 Carbon", Higienicos desechables ->
"504.01.08 Art. de Limpieza"), which only reproduced once the calls below
passed context={"company_id": ..., "allowed_company_ids": [...],
"force_company": ...} explicitly. Always pass that context when reading
company-dependent Odoo fields (property_account_* and similar).

Verified against Acoxpa, July 2026: total purchase line amount matched
production Power BI's "Compras Materia Prima" within ~2-3%, with only
$1,219.60 of ~$2.75M unclassified (2 lines) -- full usable coverage,
unlike the wansoft_department bridge.

Second gotcha found against Tepeyac (2026-08-27): purchase.order.line
rows include cancelled and draft orders unless explicitly excluded --
for Tepeyac, August 2026, 55 cancelled lines ($341,589.04) and 2 draft
lines ($3,396.00) were inflating the total against a ~$1.04M real
total. Filtered to state not in ('cancel', 'draft').
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from extract.costs.odoo_cost_report import get_cost_accounts


def _company_context(odoo_company_id: int) -> Dict[str, Any]:
    return {
        "company_id": odoo_company_id,
        "allowed_company_ids": [odoo_company_id],
        "force_company": odoo_company_id,
    }


def get_purchase_lines_with_account(
    models: Any,
    uid: int,
    db: str,
    password: str,
    odoo_company_id: int,
    date_from: str,
    date_to: str,
) -> pd.DataFrame:
    """
    Returns one row per purchase.order.line in [date_from, date_to] for this
    company, with columns: product_id, price_subtotal, account_id,
    account_name. account_id/account_name are None when the product has no
    category or the category has no expense account configured.
    """
    ctx = _company_context(odoo_company_id)

    lines = models.execute_kw(
        db, uid, password, "purchase.order.line", "search_read",
        [[
            ["order_id.company_id", "=", odoo_company_id],
            ["order_id.date_order", ">=", date_from],
            ["order_id.date_order", "<=", date_to],
            ["product_id", "!=", False],
            ["state", "not in", ["cancel", "draft"]],
        ]],
        {"fields": ["product_id", "price_subtotal"], "context": ctx}
    )

    if not lines:
        return pd.DataFrame(columns=["product_id", "price_subtotal", "account_id", "account_name"])

    product_ids = list({l["product_id"][0] for l in lines})
    products = models.execute_kw(
        db, uid, password, "product.product", "search_read",
        [[["id", "in", product_ids]]],
        {"fields": ["id", "product_tmpl_id"]}
    )
    product_to_tmpl = {p["id"]: p["product_tmpl_id"][0] for p in products}

    tmpl_ids = list(set(product_to_tmpl.values()))
    templates = models.execute_kw(
        db, uid, password, "product.template", "search_read",
        [[["id", "in", tmpl_ids]]],
        {"fields": ["id", "categ_id"], "context": ctx}
    )
    tmpl_to_categ = {t["id"]: t["categ_id"][0] for t in templates if t.get("categ_id")}

    categ_ids = list(set(tmpl_to_categ.values()))
    categories = models.execute_kw(
        db, uid, password, "product.category", "search_read",
        [[["id", "in", categ_ids]]],
        {"fields": ["id", "property_account_expense_categ_id"], "context": ctx}
    )
    categ_to_account = {
        c["id"]: (c["property_account_expense_categ_id"][0] if c.get("property_account_expense_categ_id") else None)
        for c in categories
    }

    account_ids = list({a for a in categ_to_account.values() if a is not None})
    account_names: Dict[int, str] = {}
    if account_ids:
        accounts = models.execute_kw(
            db, uid, password, "account.account", "search_read",
            [[["id", "in", account_ids]]],
            {"fields": ["id", "name"]}
        )
        account_names = {a["id"]: a["name"] for a in accounts}

    rows = []
    for line in lines:
        product_id = line["product_id"][0]
        tmpl_id = product_to_tmpl.get(product_id)
        categ_id = tmpl_to_categ.get(tmpl_id)
        account_id = categ_to_account.get(categ_id)
        rows.append({
            "product_id": product_id,
            "price_subtotal": line["price_subtotal"],
            "account_id": account_id,
            "account_name": account_names.get(account_id) if account_id else None,
        })

    return pd.DataFrame(rows)


def get_purchase_totals_by_bucket(
    models: Any,
    uid: int,
    db: str,
    password: str,
    odoo_company_id: int,
    date_from: str,
    date_to: str,
) -> Dict[str, Any]:
    """
    Returns total_all, total_product_cost (same account bucket as Costos'
    CostoDeProductosVendidos), total_unmapped, and a per-account breakdown
    for purchase.order.line amounts in [date_from, date_to].
    """
    accounts = get_cost_accounts(models, uid, db, password, odoo_company_id)
    product_set = set(accounts["product_ids"])

    df = get_purchase_lines_with_account(models, uid, db, password, odoo_company_id, date_from, date_to)

    if df.empty:
        return {
            "total_all": 0.0,
            "total_product_cost": 0.0,
            "total_unmapped": 0.0,
            "unmapped_line_count": 0,
            "by_account": {},
        }

    total_all = float(df["price_subtotal"].sum())
    is_product = df["account_id"].isin(product_set)
    is_unmapped = df["account_id"].isna()

    total_product_cost = float(df.loc[is_product, "price_subtotal"].sum())
    total_unmapped = float(df.loc[is_unmapped, "price_subtotal"].sum())
    unmapped_line_count = int(is_unmapped.sum())

    by_account = (
        df.loc[is_product]
        .groupby("account_name")["price_subtotal"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    return {
        "total_all": total_all,
        "total_product_cost": total_product_cost,
        "total_unmapped": total_unmapped,
        "unmapped_line_count": unmapped_line_count,
        "by_account": by_account,
    }
