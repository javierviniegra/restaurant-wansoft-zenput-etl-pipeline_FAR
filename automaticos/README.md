# Wansoft Automated Core ETL (`/automaticos`)

This directory contains the primary automated scripts scheduled to run daily. Their main goal is to extract operational data, sales, inventory movements, and expenses from all Fonda Argentina branches using the Wansoft SOAP API.

## 🔐 Security & Installation
This module strictly requires the centralized `.env` and `database.py` files located in the root of the project to run safely without exposing hardcoded passwords or paths.
1. Ensure the `python-dotenv`, `mysql-connector-python`, and `zeep` packages are installed.
2. Ensure the `XML_DOWNLOAD_DIR` is correctly set in your root `.env` file to handle large payloads locally.

## 📄 File Structure & Documentation

Here is a detailed breakdown of what each script does and what data it brings to the MySQL database:

*   **`extractAllOrdersByDay.py`**: A utility script responsible solely for downloading the raw XML files representing the daily orders for each branch[cite: 2]. It saves them locally to avoid overloading the API during subsequent parsing operations.
*   **`getAllOrdersByDay.py`**: The most critical and complex script in the suite[cite: 1]. It handles the "Candado" (Lock) logic: it compares the sum of sales in the database against the official "Z-Closing" total from Wansoft. If they match, it skips; if there is a discrepancy, it purges the day's records and rewrites the data. It populates four core tables: `_new_Venta`, `_new_DetalleVenta`, `_new_Modificador`, and `_new_Pago`[cite: 1].
*   **`getCostReport_SemanaPyQ.py`**: Retrieves the weekly cost reports, including the cost of goods sold, margins, and operational costs[cite: 3]. Data is upserted into the `costeomensual_semanapyq` table, tracking historical variances[cite: 3].
*   **`getExpenses.py`**: Connects to Wansoft to download all registered supplier invoices and expenses (`Facturas`)[cite: 4]. It captures tax details (IVA, IEPS), subtotals, and supplier RFCs, storing them in the `getexpenses_factura` table[cite: 4].
*   **`getInputInventory.py`**: Tracks all inventory entries (purchases, store transfers)[cite: 5]. It captures unit costs, expiration dates, and quantities, updating the `getinputinventory_entrada` table[cite: 5].
*   **`getOutgoingInventory.py`**: The counterpart to inputs; it tracks inventory outputs, mapping products to specific departments and warehouses[cite: 6]. It writes to the `getOutgoingInventory_Salida` table[cite: 6].
*   **`getTablajeriaReport.py`**: A specialized script for meat processing (Tablajería)[cite: 7]. It tracks the yield of base products into generated products (e.g., breaking down a whole cut into steaks), capturing shrinkage (merma) and costs[cite: 7]. Results are stored in `gettablajeriareport`[cite: 7].
*   **`getTotalCostByDate.py`**: A high-level aggregate script that fetches the total daily cost of sales (`CostoTotalVenta`) and stores it chronologically in `getTotalCostByDate` for quick executive dashboards[cite: 8].