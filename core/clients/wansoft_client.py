from pathlib import Path
import os

from lxml import etree
from zeep import Client, Settings

from core.config.env_loader import load_environment


REMOTE_WANSOFT_WSDL_URL = "https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl"


def get_project_root() -> Path:
    """
    Returns the project root based on this file location.

    Expected location:
    core/clients/wansoft_client.py
    """
    return Path(__file__).resolve().parents[2]


def resolve_wansoft_wsdl_path() -> str:
    """
    Resolves the Wansoft WSDL path.

    Recommended mode:
    - local WSDL stored at resources/wsdl/wansoft.wsdl

    For local files, this returns the filesystem path as string.
    This is usually more stable on Windows than file:// URI paths.
    """
    load_environment()

    use_local_wsdl = os.getenv("WANSOFT_USE_LOCAL_WSDL", "true").strip().lower() == "true"

    if not use_local_wsdl:
        return REMOTE_WANSOFT_WSDL_URL

    wsdl_relative_path = os.getenv(
        "WANSOFT_WSDL_PATH",
        "resources/wsdl/wansoft.wsdl"
    ).strip()

    wsdl_path = get_project_root() / wsdl_relative_path

    if not wsdl_path.exists():
        raise FileNotFoundError(
            f"Wansoft WSDL file was not found at: {wsdl_path}"
        )

    return str(wsdl_path.resolve())


def validate_local_wsdl_file(wsdl_path: str) -> dict:
    """
    Validates that the local WSDL file exists and contains valid XML.

    This prevents Zeep from failing with unclear XML parsing errors.
    """
    path = Path(wsdl_path)

    if not path.exists():
        raise FileNotFoundError(f"WSDL file does not exist: {path}")

    file_size = path.stat().st_size

    if file_size == 0:
        raise ValueError(f"WSDL file is empty: {path}")

    raw_text = path.read_text(encoding="utf-8", errors="replace").strip()

    if not raw_text:
        raise ValueError(f"WSDL file contains no readable text: {path}")

    first_chars = raw_text[:300]

    lower_text = raw_text.lower()

    if "<html" in lower_text or "<!doctype html" in lower_text:
        raise ValueError(
            "The WSDL file appears to contain HTML instead of WSDL XML. "
            "Download/save the raw WSDL XML, not the browser documentation page."
        )

    try:
        xml_root = etree.fromstring(raw_text.encode("utf-8"))
    except Exception as exc:
        raise ValueError(
            f"The WSDL file is not valid XML. Path: {path}. Error: {exc}"
        ) from exc

    root_tag = xml_root.tag

    if "definitions" not in root_tag.lower():
        raise ValueError(
            f"The WSDL XML root does not look like a WSDL definitions document. "
            f"Root tag found: {root_tag}"
        )

    return {
        "path": str(path),
        "file_size": file_size,
        "root_tag": root_tag,
        "first_chars": first_chars,
    }


def get_wansoft_client() -> Client:
    """
    Creates a Zeep SOAP client for Wansoft using the configured WSDL.

    Important:
    - The recommended production mode is local WSDL.
    - This function does not call any Wansoft method by itself.
    """
    wsdl = resolve_wansoft_wsdl_path()

    use_local_wsdl = os.getenv("WANSOFT_USE_LOCAL_WSDL", "true").strip().lower() == "true"

    if use_local_wsdl:
        validate_local_wsdl_file(wsdl)

    settings = Settings(
        strict=False,
        xml_huge_tree=True
    )

    return Client(
        wsdl=wsdl,
        settings=settings
    )