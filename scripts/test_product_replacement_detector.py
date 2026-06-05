from analysis.product_replacement_detector import detect_replacements


if __name__ == "__main__":
    print("==== TEST PRODUCT REPLACEMENT DETECTOR ====\n")

    df = detect_replacements(threshold=92)

    if df.empty:
        print("No se detectaron reemplazos potenciales.")
    else:
        print(df.head(50).to_string(index=False))
        print(f"\nTotal reemplazos potenciales: {len(df)}")

    print("\n==== DONE ✅ ====")