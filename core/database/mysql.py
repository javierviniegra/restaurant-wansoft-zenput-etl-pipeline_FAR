"""
MySQL Connection Manager (Multi-Source)

Supports:
- Wansoft
- Zenput
"""

import mysql.connector
import os
from dotenv import load_dotenv

from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / "core" / "config" / ".env"
load_dotenv(dotenv_path=env_path)


def get_mysql_connection(target: str = "wansoft"):

    if target == "wansoft":
        return mysql.connector.connect(
            host=os.getenv("WANSOFT_DB_HOST"),
            user=os.getenv("WANSOFT_DB_USER"),
            password=os.getenv("WANSOFT_DB_PASSWORD"),
            database=os.getenv("WANSOFT_DB_NAME")
        )

    elif target == "zenput":
        return mysql.connector.connect(
            host=os.getenv("ZENPUT_DB_HOST"),
            user=os.getenv("ZENPUT_DB_USER"),
            password=os.getenv("ZENPUT_DB_PASSWORD"),
            database=os.getenv("ZENPUT_DB_NAME")
        )

    else:
        raise ValueError(f"Unknown MySQL target: {target}")