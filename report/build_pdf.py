"""Render report/REPORT.md to a two-page PDF with the browser already on the machine.

No new dependency: the markdown subset used here is small (headings, paragraphs,
tables, blockquotes, ordered lists, bold, code), and Edge/Chrome can print HTML to
PDF headlessly. Page count is verified afterwards with pypdf, because "2 pages max"
is a requirement, not an aspiration.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "REPORT.md"
HTML_PATH = ROOT / "report.html"
PDF_PATH = ROOT / "REPORT.pdf"

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 8mm 9mm 7mm 9mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 7.6pt; line-height: 1.18;
       color: #111; margin: 0; }
h1 { font-size: 12pt; margin: 0 0 3pt 0; letter-spacing: -0.2pt; }
h2 { font-size: 9pt; margin: 3.4pt 0 1pt 0; border-bottom: 0.5pt solid #bbb;
     padding-bottom: 0.7pt; page-break-after: avoid; }
p { margin: 0 0 2.1pt 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 1pt 0 2.2pt 0; font-size: 5.9pt;
        table-layout: auto; }
th, td { border: 0.4pt solid #999; padding: 0.6pt 1.4pt; text-align: left; }
th { background: #eee; }
blockquote { margin: 2pt 0 4pt 0; padding: 3pt 5pt; border-left: 2pt solid #888;
             background: #f6f6f6; font-style: italic; }
ol { margin: 1pt 0 3pt 0; padding-left: 12pt; }
li { margin-bottom: 1pt; }
code { font-family: Consolas, monospace; font-size: 7.6pt; background: #f2f2f2; }
strong { font-weight: 600; }
"""


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def to_html(markdown: str) -> str:
    out: list[str] = []
    lines = markdown.splitlines()
    index = 0
    paragraph: list[str] = []
    ordered: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_ordered() -> None:
        if ordered:
            out.append("<ol>" + "".join(f"<li>{inline(item)}</li>" for item in ordered) + "</ol>")
            ordered.clear()

    while index < len(lines):
        line = lines[index]
        if line.startswith("|"):
            flush_paragraph()
            flush_ordered()
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            body = [row for row in rows if not all(set(cell) <= set("-: ") for cell in row)]
            out.append("<table>")
            for position, row in enumerate(body):
                tag = "th" if position == 0 else "td"
                out.append("<tr>" + "".join(f"<{tag}>{inline(cell)}</{tag}>" for cell in row) + "</tr>")
            out.append("</table>")
            continue
        if line.startswith("## "):
            flush_paragraph()
            flush_ordered()
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            flush_paragraph()
            flush_ordered()
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("> "):
            flush_paragraph()
            flush_ordered()
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        elif re.match(r"^\d+\. ", line):
            flush_paragraph()
            ordered.append(re.sub(r"^\d+\. ", "", line))
        elif not line.strip():
            flush_paragraph()
            flush_ordered()
        else:
            flush_ordered()
            paragraph.append(line.strip())
        index += 1
    flush_paragraph()
    flush_ordered()
    return "\n".join(out)


def find_browser() -> str:
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
    on_path = shutil.which("msedge") or shutil.which("chrome")
    if on_path:
        return on_path
    raise SystemExit("no Edge or Chrome found to print the PDF")


def table_block(key: str) -> str:
    """Return the pipe table for `key` straight out of the generated TABLES.md.

    The report used to carry its own copy of Tables 1-3. One load re-run later the
    copy disagreed with results.csv and the numbers in the prose disagreed with both.
    Tables now have exactly one source: `relay tables --write`.
    """
    text = (ROOT / "TABLES.md").read_text(encoding="utf-8")
    wanted = key.lower()
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## Table "):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    for block in blocks:
        heading = block[0].lower()
        number = re.match(r"## table ([0-9a-z]+)", heading)
        if number and number.group(1) == wanted:
            rows = [line for line in block if line.startswith("|")]
            if not rows:
                raise SystemExit(f"TABLES.md has no pipe table for {{%table:{key}%}}")
            return "\n".join(rows)
    raise SystemExit(f"TABLES.md has no section for {{%table:{key}%}}")


def expand_tables(markdown: str) -> str:
    return re.sub(
        r"\{\{table:([0-9a-zA-Z]+)\}\}",
        lambda match: table_block(match.group(1)),
        markdown,
    )


def build() -> Path:
    body = to_html(expand_tables(SOURCE.read_text(encoding="utf-8")))
    HTML_PATH.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
        f"<body>{body}</body></html>",
        encoding="utf-8",
    )
    browser = find_browser()
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--user-data-dir={profile}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={PDF_PATH}",
                HTML_PATH.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    if not PDF_PATH.exists():
        raise SystemExit(f"{Path(browser).name} exited 0 but wrote no PDF")
    return PDF_PATH


def page_count(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


if __name__ == "__main__":
    pdf = build()
    pages = page_count(pdf)
    print(f"{pdf} -> {pages} page(s)")
    sys.exit(0 if pages <= 2 else 1)
