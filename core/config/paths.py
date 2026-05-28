import os

def get_xml_download_dir():
    env = os.getenv("ENV", "prod").lower()

    if env == "dev":
        path = os.getenv("XML_DOWNLOAD_DIR_DEV")
    else:
        path = os.getenv("XML_DOWNLOAD_DIR")

    print("[DEBUG] ENV:", env)
    print("[DEBUG] XML PATH:", path)

    if not path:
        raise ValueError(
            "No se encontró XML_DOWNLOAD_DIR / XML_DOWNLOAD_DIR_DEV en el .env"
        )

    return path
