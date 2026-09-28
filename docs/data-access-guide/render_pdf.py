"""Renders data-access-guide.<lang>.html to data-access-guide.<lang>.pdf, for
Spanish and English (same layout as the ControlPresupuestos_AP manuals).

The Spanish HTML is edited by hand; the English HTML is generated from the
English Markdown by build_en_html.py (run that first when the .en.md changes).

xhtml2pdf is not part of this project's requirements; run it with any Python
that has it, e.g. ControlPresupuestos_AP's virtual environment:
    <ControlPresupuestos_AP>\\.venv\\Scripts\\python.exe docs\\data-access-guide\\render_pdf.py [es|en]
"""
import sys
from pathlib import Path

from xhtml2pdf import pisa

HERE = Path(__file__).resolve().parent
LOGO = HERE / "logo.png"


def render(lang, target=None):
    source = HERE / f"data-access-guide.{lang}.html"
    target = Path(target) if target else HERE / f"data-access-guide.{lang}.pdf"
    html = source.read_text(encoding="utf-8").replace("{{ logo_path }}", str(LOGO))
    with target.open("wb") as out:
        result = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if result.err:
        raise SystemExit(f"xhtml2pdf reported {result.err} error(s) for {lang}")
    print(f"Wrote {target}")


def main():
    for lang in sys.argv[1:] or ["es", "en"]:
        render(lang)


if __name__ == "__main__":
    main()
