"""
Company Data Source Configuration
"""


import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)


# Lista base (la que ya tienes)
CUENTAS_SUCURSALES = [
    ("5320", "Acoxpa", os.getenv("WANSOFT_PWD_5320")),
    ("4959", "Aeropuerto", os.getenv("WANSOFT_PWD_4959")),
    ("4958", "Isabel La Católica", os.getenv("WANSOFT_PWD_4958")),
    ("4960", "Antenas", os.getenv("WANSOFT_PWD_4960")),
    ("5321", "Taquería parroquia", os.getenv("WANSOFT_PWD_5321")),
    ("5318", "Vía Vallejo", os.getenv("WANSOFT_PWD_5318")),
    ("4961", "Viaducto", os.getenv("WANSOFT_PWD_4961")),
    ("4962", "Taquería Viaducto", os.getenv("WANSOFT_PWD_4962")),
    ("5319", "San Jeronimo", os.getenv("WANSOFT_PWD_5319")),
    ("6560", "Tepeyac", os.getenv("WANSOFT_PWD_6560")),
    ("6174", "Playa del Carmen", os.getenv("WANSOFT_PWD_6174")),
    ("5943", "Oceanía", os.getenv("WANSOFT_PWD_5943")),
    ("6175", "Cancun", os.getenv("WANSOFT_PWD_6175")),
    ("4433", "Napoles", os.getenv("WANSOFT_PWD_4433")),
    ("4752", "Metepec", os.getenv("WANSOFT_PWD_4752")),
    ("5396", "Versalles", os.getenv("WANSOFT_PWD_5396")),
    ("12057", "La Esquina Coyoacán", os.getenv("WANSOFT_PWD_12057")),
    ("12802", "CentroMyJ", os.getenv("WANSOFT_PWD_12802")),
    ("12806", "Puebla", os.getenv("WANSOFT_PWD_12806"))
]

# 🔥 CONFIGURACIÓN DE FUENTE POR EMPRESA
COMPANY_SOURCE = {
    "Acoxpa": "wansoft",
    "Aeropuerto": "wansoft",
    "Isabel La Católica": "wansoft",
    "Antenas": "odoo",
    "Taquería parroquia": "wansoft",
    "Vía Vallejo": "wansoft",
    "Viaducto": "wansoft",
    "Taquería Viaducto": "wansoft",
    "San Jeronimo": "wansoft",
    "Tepeyac": "wansoft",
    "Playa del Carmen": "wansoft",
    "Oceanía": "wansoft",
    "Cancun": "wansoft",
    "Napoles": "wansoft",
    "Metepec": "wansoft",
    "Versalles": "wansoft",
    "La Esquina Coyoacán": "wansoft",
    "CentroMyJ": "wansoft",
    "Puebla": "wansoft"
}