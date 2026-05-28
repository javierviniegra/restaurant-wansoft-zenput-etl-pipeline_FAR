from pathlib import Path
from dotenv import load_dotenv

def load_environment():

    # Buscar el .env desde el root del proyecto
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / "core" / "config" / ".env"

    if not env_path.exists():
        raise FileNotFoundError(f".env no encontrado en: {env_path}")

    load_dotenv(dotenv_path=env_path)

    print(f".env cargado desde: {env_path}")
