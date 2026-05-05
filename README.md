# Restaurant ETL Pipeline: Wansoft & Zenput Integration (FAR)

A robust, enterprise-grade ETL (Extract, Transform, Load) suite designed to automate the extraction of operational, financial, and inventory data from multiple cloud endpoints into a centralized, local MySQL Data Warehouse. 

This project bridges the gap between legacy SOAP-based ERPs and modern RESTful platforms to fuel Business Intelligence (BI) dashboards.

## 🚀 Overview & Architecture

The integration engine handles two radically different data ecosystems:

1.  **Wansoft (ERP):** A legacy point-of-sale and restaurant management system. The extraction relies heavily on the `zeep` library to interact with SOAP Web Services, processing complex XML hierarchies.
2.  **Crunchtime Zenput:** A modern operational management platform. Extraction uses standard `requests` to interact with RESTful APIs, handling pagination, rate limiting (HTTP 429), and dynamic JSON payloads.

The engine is designed to run as **Daily Scheduled Cron Jobs**, ensuring that the local analytical database is perfectly synchronized with the official cloud systems.

## ⏱️ Automation & Scheduling

For this pipeline to be fully robust and autonomous, the scripts are designed for headless execution (no user interaction required). They should be scheduled to run daily using OS-level task schedulers.

### Windows (Task Scheduler)
If you are hosting this on a Windows Server or a local Windows machine, the recommended approach is using the **Windows Task Scheduler**:

1. Create a `.bat` (Batch) file to ensure the script runs within the correct project directory and virtual environment. Example (`run_wansoft_orders.bat`):
   ```bat
   @echo off
   cd "C:\Path\To\Your\Project"
   python automaticos/getAllOrdersByDay.py