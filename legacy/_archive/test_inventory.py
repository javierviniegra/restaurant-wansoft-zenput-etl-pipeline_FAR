"""
Test script for inventory extraction (Wansoft)
"""

from extract.inventory.wansoft_inventory import extract_inventory


def main():
    print("Testing Wansoft Inventory Extraction...\n")

    extract_inventory()

    print("\nTest completed ✅")


if __name__ == "__main__":
    main()