# Restaurant ETL Pipeline: Wansoft & Zenput Integration (FAR)

A robust, enterprise-grade ETL (Extract, Transform, Load) suite designed to automate the extraction of operational, financial, and inventory data from multiple cloud endpoints into a centralized, local MySQL Data Warehouse. 

This project bridges the gap between legacy SOAP-based ERPs and modern RESTful platforms to fuel Business Intelligence (BI) dashboards.

## 🚀 Overview & Architecture

The integration engine handles two radically different data ecosystems:

1.  **Wansoft (ERP):** A legacy point-of-sale and restaurant management system. The extraction relies heavily on the `zeep` library to interact with SOAP Web Services, processing complex XML hierarchies.
2.  **Crunchtime Zenput:** A modern operational management platform. Extraction uses standard `requests` to interact with RESTful APIs, handling pagination, rate limiting (HTTP 429), and dynamic JSON payloads.

The engine is designed to run as **Daily Scheduled Cron Jobs**, ensuring that the local analytical database is perfectly synchronized with the official cloud systems.

## 📡 Endpoints & Data Connectivity

The pipeline connects to specific endpoints to extract granular data. Below is the detailed mapping of the data sources.

### 1. Wansoft (SOAP / XML)
All Wansoft connections point to a single WSDL endpoint but invoke different methods depending on the data required.
*   **WSDL URL:** `https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl`
*   **Authentication:** Requires Branch ID (`subsidiaryId`) and a specific Branch Password (`pwdWebService`).

**Key Methods Implemented:**
*   `GetAllOrdersByDay_Xml`: Extracts granular ticket-level sales data, including items sold, modifiers, and payment methods. Includes a "Z-Closing" lock logic to prevent discrepancies.
*   `GetGlobalCashClosing_Xml`: Fetches the official financial daily closing (Corte Z), including cash, credit cards, tips, and cancellations.
*   `GetCostReport_Xml` & `GetTotalCostByDate`: Extracts theoretical and real costs, inventory shrinkage (merma), waste, and marginal utility.
*   `GetInputInventory_Xml` & `GetOutgoingInventory_Xml`: Tracks all warehouse movements, purchases, and store transfers.
*   `GetExpenses_Xml`: Retrieves supplier invoices, tax breakdowns, and registered expenses.
*   `GetTablajeriaReport_Xml`: Specialized endpoint to track meat processing yields and costs.

### 2. Crunchtime Zenput (REST / JSON)
Zenput provides a modern API architecture. The pipeline handles recursive pagination and deeply nested JSON structures.
*   **Base URL:** `https://www.zenput.com/api`
*   **Authentication:** Requires an API Token passed via headers (`X-API-TOKEN`).

**Key Endpoints Implemented:**
*   `GET /v1/tasks/list_tasks`: Retrieves all assigned operational tasks across all branches, tracking assignees, deadlines, and completion statuses. Implements offset pagination (`limit` & `start`).
*   `GET /v1/forms/list_templates/`: Fetches the metadata for all available field-form templates.
*   `GET /v3/submissions?form_template_id={id}`: A deep extraction endpoint. Retrieves the actual answers submitted by employees for specific forms, flattening complex objects (like photo arrays or GPS coordinates) into relational database structures.

## 📁 Project Structure

*   `automaticos/`: Core sales, inventory, and expense synchronization scripts from Wansoft.
*   `descargarCostoWansoft/`: Financial reports and global cash closings logic.
*   `Zenput/`: Extraction of operational tasks and dynamic form submissions.
*   `database.py`: Centralized, secure database connection manager router.

## 🔐 Security Model (The `.env` Approach)

Because this repository is public, **NO CREDENTIALS ARE HARDCODED**. 
The project utilizes `python-dotenv` to decouple secrets from the source code. To run this project locally, you must create a `.env` file in the root directory containing:
```env
# MySQL Routing
DB_HOST_WANSOFT=...
DB_USER_WANSOFT=...
DB_PASS_WANSOFT=...
DB_NAME_WANSOFT=...

DB_HOST_ZENPUT=...
DB_USER_ZENPUT=...
DB_PASS_ZENPUT=...
DB_NAME_ZENPUT=...

# Zenput API
ZENPUT_API_TOKEN=...

# Wansoft Branch Passwords mapping (e.g., WANSOFT_PWD_5320=...)