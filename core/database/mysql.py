import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# Carga el .env desde core/config/.env
env_path = Path(__file__).resolve().parents[2] / "core" / "config" / ".env"
load_dotenv(dotenv_path=env_path)


def get_mysql_connection(target="wansoft"):
    """
    target:
        - wansoft
        - zenput
    ENV:
        - dev
        - prod
    """

    env = os.getenv("ENV", "prod").lower()

    if target == "wansoft":
        if env == "dev":
            return mysql.connector.connect(
                host=os.getenv("WANSOFT_DB_HOST_DEV"),
                user=os.getenv("WANSOFT_DB_USER_DEV"),
                password=os.getenv("WANSOFT_DB_PASSWORD_DEV"),
                database=os.getenv("WANSOFT_DB_NAME_DEV"),
            )

        return mysql.connector.connect(
            host=os.getenv("WANSOFT_DB_HOST"),
            user=os.getenv("WANSOFT_DB_USER"),
            password=os.getenv("WANSOFT_DB_PASSWORD"),
            database=os.getenv("WANSOFT_DB_NAME"),
        )

    if target == "zenput":
        if env == "dev":
            return mysql.connector.connect(
                host=os.getenv("ZENPUT_DB_HOST_DEV"),
                user=os.getenv("ZENPUT_DB_USER_DEV"),
                password=os.getenv("ZENPUT_DB_PASSWORD_DEV"),
                database=os.getenv("ZENPUT_DB_NAME_DEV"),
            )

        return mysql.connector.connect(
            host=os.getenv("ZENPUT_DB_HOST"),
            user=os.getenv("ZENPUT_DB_USER"),
            password=os.getenv("ZENPUT_DB_PASSWORD"),
            database=os.getenv("ZENPUT_DB_NAME"),
        )

    raise ValueError(f"Unknown target: {target}")


# Alias de compatibilidad para legacy
def get_db_connection(target="wansoft"):
    return get_mysql_connection(target=target)