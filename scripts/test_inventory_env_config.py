from core.config.env_loader import load_environment
from core.config.inventory_env import (
    get_inventory_etl_config,
    get_inventory_not_found_config
)


if __name__ == "__main__":
    print("==== TEST INVENTORY ENV CONFIG ====\n")

    load_environment()

    etl_cfg = get_inventory_etl_config()
    not_found_cfg = get_inventory_not_found_config()

    print("--- ETL CONFIG ---")
    for k, v in etl_cfg.items():
        print(f"{k}: {v}")

    print("\n--- NOT_FOUND CONFIG ---")
    for k, v in not_found_cfg.items():
        print(f"{k}: {v}")

    print("\n==== DONE ✅ ====")