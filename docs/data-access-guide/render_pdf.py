"""Renders data-access-guide.es.html to data-access-guide.es.pdf (same layout as
the ControlPresupuestos_AP manuals).

xhtml2pdf is not part of this project's requirements; run it with any Python
that has it, e.g. ControlPresupuestos_AP's virtual environment:
    <ControlPresupuestos_AP>\\.venv\\Scripts\\python.exe docs\\data-access-guide\\render_pdf.py
"""
from pathlib import Path

from xhtml2pdf import pisa

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "data-access-guide.es.html"
TARGET = HERE / "data-access-guide.es.pdf"
LOGO = HERE / "logo.png"


def main():
    html = SOURCE.read_text(encoding="utf-8").replace("{{ logo_path }}", str(LOGO))
    with TARGET.open("wb") as out:
        result = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if result.err:
        raise SystemExit(f"xhtml2pdf reported {result.err} error(s)")
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
