import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def lookback_days(env_name, default):
    """Days each daily run re-checks backwards, read from .env; falls back to `default` if unset."""
    raw = os.getenv(env_name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{env_name} must be an integer number of days, got {raw!r}")
    if value < 1:
        raise ValueError(f"{env_name} must be >= 1, got {value}")
    return value


SALES_LOOKBACK_DAYS = lookback_days("SALES_LOOKBACK_DAYS", 10)
WANSOFT_LOOKBACK_DAYS = lookback_days("WANSOFT_LOOKBACK_DAYS", 31)
PURCHASES_LOOKBACK_DAYS = lookback_days("PURCHASES_LOOKBACK_DAYS", 35)
