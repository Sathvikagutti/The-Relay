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
@page { size: A4; margin: 9mm 10mm 8mm 10mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 7.8pt; line-height: 1.22;
       color: #111; margin: 0; }
h1 { font-size: 12pt; margin: 0 0 3pt 0; letter-spacing: -0.2pt; }
h2 { font-size: 9pt; margin: 5pt 0 1.5pt 0; border-bottom: 0.5pt solid #bbb;
     padding-bottom: 0.8pt; page-break-after: avoid; }
p { margin: 0 0 2.4pt 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 1.5pt 0 3pt 0; font-size: 6.7pt; }
th, td { border: 0.4pt solid #999; padding: 0.9pt 2pt; text-align: left; }
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


def build() -> Path:
    body = to_html(SOURCE.read_text(encoding="utf-8"))
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
