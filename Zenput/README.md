# Crunchtime Zenput Operational ETL (`/Zenput`)

This module connects to the Crunchtime Zenput ecosystem. Unlike the Wansoft integrations (which use SOAP/XML), this module uses a modern RESTful architecture returning JSON payloads to extract field operations, task completions, and custom form submissions.

## 🔐 Security & Installation
This module requires the `ZENPUT_API_TOKEN` and the specific Zenput database credentials (`DB_USER_ZENPUT`, etc.) to be defined in the root `.env` file. It connects to the `zenput` MySQL database using the central `database.py` router.

## 📄 File Structure & Documentation

*   **`zenput_mysql-tasks.py`**: Orchestrates the extraction of Zenput Tasks using offset-based pagination (`limit` and `start`)[cite: 11]. It handles API Rate Limiting (HTTP 429) automatically. It extracts task metadata, status, assignee, completion details, and geographic coordinates, performing a bulk `UPSERT` into the `zenput_tasks` table[cite: 11].
*   **`zenput_mysql-forms.py`**: A complex, two-phase ETL script[cite: 13]. 
    1.  **Phase 1:** Fetches all available form templates and stores their metadata in the `form_templates` table[cite: 13].
    2.  **Phase 2:** Iterates through each form to fetch user submissions. It flattens the nested JSON structure, storing the submission metadata in the `submissions` table, and breaks down every individual question/answer into the `submission_answers` table[cite: 13].
*   **`last_run_timestamp.txt`**: A simple local state-management file[cite: 12]. It stores the last successful execution timestamp (in UTC ISO 8601 format) to allow scripts to perform delta/incremental loads in the future, avoiding the need to download the entire history every day[cite: 11, 12].