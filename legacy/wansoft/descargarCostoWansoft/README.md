# Financial & Cash Closings ETL (`/descargarCostoWansoft`)

This module is strictly dedicated to deep financial audits, cost analysis, and global cash closings (Cortes Z) from the Wansoft ERP. It provides the financial backbone for the Business Intelligence dashboards.

## 🔐 Security & Installation
Like the rest of the project, it relies on the root `.env` to authenticate against the Wansoft SOAP API (`https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl`).

## 📄 File Structure & Documentation

*   **`descargarCostoWansoft.py`**: Month-to-date cost per branch and day into `costeomensual` (cost of goods sold, merma and, for Wansoft branches, ideal cost, waste, theft, consumo, marginal utility). It updates a row only when a value differs by more than `$0.01`. Courtesies and cancellations come from the cash closing (sale value, all branches, owner's decision 2026-09-17). Each (branch, day) is sourced from Wansoft or Odoo by `extract/costs/cost_routing.py`, including the automatic Wansoft-to-Odoo switch of the October wave and the month-to-date continuity across a mid-month switch: see **"Cost routing"** in `../automaticos/README.md`.
*   **`getGlobalCashClosing.py`**: Daily Cash Closing (Corte Z). Parses the hierarchical XML to extract payment methods (cash, tips), order counts, guest counts, cancellations, discounts and promotions into `getglobalcashclosing`. Always Wansoft, for every branch.
