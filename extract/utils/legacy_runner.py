from pathlib import Path
import runpy
import os

from core.config.env_loader import load_environment


# ✅ cargar UNA vez
load_environment()


def run_legacy_script(script_relative_path: str, company_name: str = None):

    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / script_relative_path

    if not script_path.exists():
        raise FileNotFoundError(f"No existe el script legacy: {script_path}")

    if company_name:
        os.environ["CURRENT_COMPANY"] = company_name

    print(f"▶ Ejecutando legacy: {script_path}")
    if company_name:
        print(f"   Empresa: {company_name}")

    return runpy.run_path(str(script_path), run_name="__main__")
