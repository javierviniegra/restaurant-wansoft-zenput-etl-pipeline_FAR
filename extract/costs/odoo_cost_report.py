"""
Odoo Cost-of-Sales Extraction (read-only)

Provides a company-agnostic replacement for the Wansoft cost-report SOAP
calls (GetTotalCostByDate, GetCostReport_Xml) for companies whose
COMPANY_SOURCE is "odoo" (Puebla, CentroMyJ, and any future branch that
migrates). Applies to any Odoo company automatically, no per-branch
hardcoding.

Source of truth: account.move.line, filtered to accounts with
account_type = 'expense_direct_cost' (Odoo's standard, company-agnostic
cost-of-revenue classification -- account.account.code is NOT reliable
across companies, some have it populated with a dotted numbering scheme,
others leave it empty and rely on account name only), move_type =
'out_invoice' (customer invoice, i.e. cost recognized at time of sale,
matching the project owner's description: "el costo se debe obtener de
las facturas de clientes"), parent_state = 'posted'.

Category split (verified against Puebla id 34 and CentroMyJ id 35, same
account names in both, 2026-08-26):
- CostoTotal: sum of every expense_direct_cost account.
- CostoDeProductosVendidos: sum of the food/beverage category accounts
  plus "Gastos de venta" (project owner decision, 2026-08-26: should be
  part of product cost). Excludes packaging, gas, cleaning, platform
  commissions, logistics -- those stay operational, not product cost.
- CostoDeMerma: the "Mermas y Desperdicios" account specifically.
- CostoDeCortesias, CostoDeCancelaciones, CostoDeRobo, CostoDeConsumo,
  AjustePorSobrantes, CostoIdealDeProductosPendientesDeRebaja,
  UtilidadMarginal: no reliable Odoo equivalent found (no theft/
  cancellation accounts exist; "Cortesias" exists but is account_type
  'expense', not 'expense_direct_cost', and mixes with other concepts).
  Callers should leave these NULL for Odoo-sourced rows, not approximate
  them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from core.database.odoo import get_odoo_connection
from core.config.companies import ODOO_COMPANY_SOURCE_KEY


PRODUCT_COST_ACCOUNT_NAMES = {
    "Cost of sales",
    "Frutas y Verduras",
    "Carnes",
    "Embutidos",
    "Quesos y Lacteos",
    "Abarrotes",
    "Pan",
    "Tortilla",
    "Empanadas",
    "Postres",
    "Pizza",
    "Con Alcohol",
    "Sin Alcohol",
    "Gastos de venta",
}

MERMA_ACCOUNT_NAME = "Mermas y Desperdicios"


def resolve_odoo_company_id(models: Any, uid: int, db: str, password: str, company_source_key: str) -> Optional[int]:
    """
    Resolves a company_source_key (e.g. "Puebla") to its Odoo res.company id,
    via the existing ODOO_COMPANY_SOURCE_KEY name mapping. No hardcoded ids,
    so this keeps working as more branches migrate to Odoo.
    """
    odoo_names = [
        name for name, key in ODOO_COMPANY_SOURCE_KEY.items()
        if key == company_source_key
    ]

    if not odoo_names:
        return None

    companies = models.execute_kw(
        db, uid, password, "res.company", "search_read",
        [[["name", "in", odoo_names]]],
        {"fields": ["id", "name"]}
    )

    if not companies:
        return None

    return companies[0]["id"]


def get_cost_accounts(models: Any, uid: int, db: str, password: str, odoo_company_id: int) -> Dict[str, List[int]]:
    """
    Returns the expense_direct_cost account ids for a company, split into
    all / product-only / merma-only buckets.
    """
    accounts = models.execute_kw(
        db, uid, password, "account.account", "search_read",
        [[["company_ids", "in", [odoo_company_id]], ["account_type", "=", "expense_direct_cost"]]],
        {"fields": ["id", "name"]}
    )

    all_ids = [a["id"] for a in accounts]
    product_ids = [a["id"] for a in accounts if a["name"] in PRODUCT_COST_ACCOUNT_NAMES]
    merma_ids = [a["id"] for a in accounts if a["name"] == MERMA_ACCOUNT_NAME]

    return {"all_ids": all_ids, "product_ids": product_ids, "merma_ids": merma_ids}


def get_earliest_cost_date(models: Any, uid: int, db: str, password: str, odoo_company_id: int) -> Optional[str]:
    """
    Returns the earliest date (YYYY-MM-DD) with a posted cost-of-sale line
    for this company, or None if there is none. Used to size a historical
    backfill without hardcoding a start date per branch.
    """
    accounts = get_cost_accounts(models, uid, db, password, odoo_company_id)

    if not accounts["all_ids"]:
        return None

    lines = models.execute_kw(
        db, uid, password, "account.move.line", "search_read",
        [[
            ["company_id", "=", odoo_company_id],
            ["account_id", "in", accounts["all_ids"]],
            ["move_type", "=", "out_invoice"],
            ["parent_state", "=", "posted"],
        ]],
        {"fields": ["date"], "order": "date asc", "limit": 1}
    )

    if not lines:
        return None

    return lines[0]["date"]


def get_daily_cost(
    models: Any,
    uid: int,
    db: str,
    password: str,
    odoo_company_id: int,
    date_from: str,
    date_to: str,
) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per date in [date_from, date_to],
    columns: fecha, CostoTotal, CostoDeProductosVendidos, CostoDeMerma.
    Dates with no posted cost-of-sale lines are simply absent from the
    result (callers should treat missing dates as zero, not error).
    """
    accounts = get_cost_accounts(models, uid, db, password, odoo_company_id)

    if not accounts["all_ids"]:
        return pd.DataFrame(columns=["fecha", "CostoTotal", "CostoDeProductosVendidos", "CostoDeMerma"])

    lines = models.execute_kw(
        db, uid, password, "account.move.line", "search_read",
        [[
            ["company_id", "=", odoo_company_id],
            ["account_id", "in", accounts["all_ids"]],
            ["move_type", "=", "out_invoice"],
            ["parent_state", "=", "posted"],
            ["date", ">=", date_from],
            ["date", "<=", date_to],
        ]],
        {"fields": ["date", "account_id", "balance"]}
    )

    if not lines:
        return pd.DataFrame(columns=["fecha", "CostoTotal", "CostoDeProductosVendidos", "CostoDeMerma"])

    df = pd.DataFrame(lines)
    df["account_id"] = df["account_id"].apply(lambda v: v[0] if isinstance(v, list) else v)

    product_set = set(accounts["product_ids"])
    merma_set = set(accounts["merma_ids"])

    df["is_product"] = df["account_id"].isin(product_set)
    df["is_merma"] = df["account_id"].isin(merma_set)

    grouped = df.groupby("date").apply(
        lambda g: pd.Series({
            "CostoTotal": g["balance"].sum(),
            "CostoDeProductosVendidos": g.loc[g["is_product"], "balance"].sum(),
            "CostoDeMerma": g.loc[g["is_merma"], "balance"].sum(),
        }),
        include_groups=False,
    ).reset_index().rename(columns={"date": "fecha"})

    return grouped
