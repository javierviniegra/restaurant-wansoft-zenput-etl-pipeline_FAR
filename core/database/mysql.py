"""
MySQL Connection Manager (Multi-Source)

Supports:
- Wansoft
- Zenput
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()


def get_mysql_connection(source: str = "wansoft"):

    if source == "wansoft":
        return mysql.connector.connect(
            host=os.getenv("WANSOFT_DB_HOST"),
            user=os.getenv("WANSOFT_DB_USER"),
            password=os.getenv("WANSOFT_DB_PASSWORD"),
            database=os.getenv("WANSOFT_DB_NAME")
        )

    elif source == "zenput":
        return mysql.connector.connect(
            host=os.getenv("ZENPUT_DB_HOST"),
            user=os.getenv("ZENPUT_DB_USER"),
            password=os.getenv("ZENPUT_DB_PASSWORD"),
            database=os.getenv("ZENPUT_DB_NAME")
        )

    else:
        raise ValueError(f"Unknown MySQL source: {source}")