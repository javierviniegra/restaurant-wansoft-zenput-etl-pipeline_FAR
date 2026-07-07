import traceback

from core.clients.wansoft_client import (
    resolve_wansoft_wsdl_path,
    validate_local_wsdl_file,
    get_wansoft_client
)


if __name__ == "__main__":
    print("==== TEST WANSOFT LOCAL WSDL CLIENT ====\n")

    try:
        wsdl_path = resolve_wansoft_wsdl_path()
        print(f"WSDL resolved path: {wsdl_path}")

        print("\n--- LOCAL WSDL VALIDATION ---")
        validation = validate_local_wsdl_file(wsdl_path)

        print(f"path: {validation['path']}")
        print(f"file_size: {validation['file_size']}")
        print(f"root_tag: {validation['root_tag']}")

        print("\n--- WSDL FIRST CHARS ---")
        print(validation["first_chars"])

        client = get_wansoft_client()

        print("\n--- SERVICES ---")
        for service_name in client.wsdl.services:
            print(service_name)

        print("\n--- PORTS / OPERATIONS ---")
        for service in client.wsdl.services.values():
            for port_name, port in service.ports.items():
                print(f"\nPort: {port_name}")

                operations = sorted(port.binding._operations.keys())

                for operation_name in operations:
                    print(f" - {operation_name}")

        print("\n==== DONE ✅ ====")

    except Exception:
        print("\n==== ERROR ❌ ====")
        traceback.print_exc()