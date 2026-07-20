from extract.purchases.canonical_purchase_etl import (
    run_canonical_purchase_wansoft_etl
)


if __name__ == "__main__":
    print("==== TEST CANONICAL PURCHASE WANSOFT ETL ====\n")

    run_canonical_purchase_wansoft_etl()

    print("\n==== DONE ✅ ====")