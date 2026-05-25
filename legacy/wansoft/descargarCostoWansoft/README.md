# Financial & Cash Closings ETL (`/descargarCostoWansoft`)

This module is strictly dedicated to deep financial audits, cost analysis, and global cash closings (Cortes Z) from the Wansoft ERP. It provides the financial backbone for the Business Intelligence dashboards.

## 🔐 Security & Installation
Like the rest of the project, it relies on the root `.env` to authenticate against the Wansoft SOAP API (`https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl`).

## 📄 File Structure & Documentation

*   **`descargarCostoWansoft.py`**: Iterates through all active branches to extract detailed monthly or daily cost reports[cite: 9]. It captures highly granular operational metrics such as ideal costs, shrinkages (merma), waste, stolen goods, courtesies, cancellations, and marginal utility[cite: 9]. It checks if the Wansoft totals differ by more than `$0.01` from the database; if so, it updates the `costeoMensual` table[cite: 9].
*   **`getGlobalCashClosing.py`**: Responsible for retrieving the daily Cash Closing (Corte Z)[cite: 10]. It deeply parses complex hierarchical XML structures to extract payment methods (cash, tips), order counts, guest counts, cancellations, discounts, and promotions[cite: 10]. Data is stored in the massive `getglobalcashclosing` table to allow granular auditing of daily operations[cite: 10].