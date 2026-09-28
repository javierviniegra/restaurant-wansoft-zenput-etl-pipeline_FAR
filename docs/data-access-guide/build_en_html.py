"""Builds data-access-guide.en.html from data-access-guide.en.md, reusing the
Spanish HTML's stylesheet so both PDFs share the same layout.

Needs the `markdown` package (present in the base Anaconda Python, not in
ControlPresupuestos_AP's venv), so it is a separate step from render_pdf.py:
    python docs\\data-access-guide\\build_en_html.py
    <ControlPresupuestos_AP>\\.venv\\Scripts\\python.exe docs\\data-access-guide\\render_pdf.py
"""
import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "data-access-guide.en.md"
STYLE_FROM = HERE / "data-access-guide.es.html"
TARGET = HERE / "data-access-guide.en.html"

# Column widths (%) for tables whose table-name column needs room.
COLUMN_WIDTHS = {
    ("Question", "Table", "Filter / note"): (30, 48, 22),
    ("Data", "Table", "Source", "Since", "Notes"): (17, 36, 11, 10, 26),
    ("Table", "Grain", "Key fields"): (42, 16, 42),
}

# Sections that start on a new page, as in the Spanish PDF.
PAGE_BREAK_BEFORE = ("<h1>3.", "<h1>4.", "<h2>4.1", "<h1>5.")


def main():
    md = SOURCE.read_text(encoding="utf-8")
    # Drop the title line, the language link and the Markdown contents list:
    # the PDF has its own header and a page-numbered table of contents.
    md = re.sub(r"\A# .*?\n", "", md)
    md = re.sub(r"^\*Spanish version:.*?\n", "", md, flags=re.M)
    md = re.sub(r"^## Contents\n.*?^---\n", "", md, flags=re.M | re.S)

    # Python-Markdown needs a blank line before a list that follows a paragraph
    # line (GitHub does not), otherwise the list is merged into the paragraph.
    lines, fixed = md.split("\n"), []
    for line in lines:
        prev = fixed[-1] if fixed else ""
        if re.match(r"(- |\d+\. )", line) and prev.strip() and not re.match(r"\s*(- |\d+\. )|\s", prev):
            fixed.append("")
        fixed.append(line)
    md = "\n".join(fixed)

    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    body = body.replace("<hr />", "")
    # One level up: ## -> h1, ### -> h2 (xhtml2pdf builds the TOC from h1/h2).
    body = re.sub(r"<(/?)h2>", r"<\1h1>", body)
    body = re.sub(r"<(/?)h3>", r"<\1h2>", body)
    body = re.sub(r"<pre><code[^>]*>", '<pre class="bloque-codigo">', body).replace("</code></pre>", "</pre>")
    body = body.replace("<table>", '<table class="compacta">')
    body = re.sub(r"<td>\s*</td>", "<td>—</td>", body)
    # xhtml2pdf only honours width attributes on header cells; long table
    # names otherwise spill into the next column.
    for header, widths in COLUMN_WIDTHS.items():
        cells = [f"<th>{h}</th>" for h in header]
        sized = [f'<th width="{w}%">{h}</th>' for h, w in zip(header, widths)]
        body = body.replace("\n".join(cells), "\n".join(sized))
    for marker in PAGE_BREAK_BEFORE:
        body = body.replace(marker, '<div class="salto"></div>\n' + marker, 1)

    style = re.search(r"<style>.*?</style>", STYLE_FROM.read_text(encoding="utf-8"), re.S).group(0)
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Data Access Guide</title>
{style}
</head>
<body>

<table style="border: none; margin-bottom: 4px;">
  <tr style="border: none;">
    <td style="border: none; width: 100px; padding: 0;"><img class="logo" src="{{{{ logo_path }}}}"></td>
    <td style="border: none; padding: 0;">
      <p class="titulo">Data Access Guide</p>
      <p class="subtitulo">Analytical databases <code>wansoft</code> and <code>zenput</code> | Fonda Argentina | Version 2026-09-28</p>
    </td>
  </tr>
</table>

<p class="indice-titulo">Contents</p>
<div><pdf:toc /></div>

<div class="salto"></div>

{body}

<div id="footer_content">
Fonda Argentina | Data Access Guide | Page <pdf:pagenumber /> of <pdf:pagecount />
</div>

</body>
</html>
"""
    TARGET.write_text(html, encoding="utf-8")
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
