#!/usr/bin/env python3
"""Make the printable PDF checklists in assets/pdf from the guide pages.

    python3 _src/build.py && python3 _src/make_pdfs.py

A guide gets a PDF when its front matter has "pdf" (the file name),
"pdf_title" and "pdf_sections" (the ids of the h2 sections to include, in
order). Checklists become tick boxes without their explanations; other
lists, tables and warnings are kept as they are. Needs Playwright with
Chromium and BeautifulSoup. Rebuild the PDFs whenever those sections change, and after changing BASE
in build.py (the PDFs print the page addresses).
"""

import base64
import html
import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

OUT = build.ROOT / 'assets' / 'pdf'
FONTS = build.ROOT / 'assets' / 'fonts'


def data_uri(path, mime):
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()


def font_faces():
    faces = [('Space Grotesk', 700, 'space-grotesk-latin-700-normal.woff2'),
             ('Public Sans', 400, 'public-sans-latin-400-normal.woff2'),
             ('Public Sans', 700, 'public-sans-latin-700-normal.woff2')]
    return '\n'.join(
        f"@font-face {{ font-family: '{fam}'; font-weight: {w}; src: url('{data_uri(FONTS / f, 'font/woff2')}') format('woff2'); }}"
        for fam, w, f in faces)


CSS = """
@page { size: Letter; margin: 0.45in 0.6in 0.6in; }
* { box-sizing: border-box; }
body { margin: 0; font: 400 9.8pt/1.33 'Public Sans', sans-serif; color: #15170f; }
header { display: flex; align-items: center; gap: 14px; border-bottom: 3px solid #15170f; padding-bottom: 10px; margin-bottom: 8px; }
header img { width: 46px; height: 46px; border-radius: 10px; }
header .t { flex: 1; }
h1 { font: 700 22pt/1.05 'Space Grotesk', sans-serif; letter-spacing: -0.02em; margin: 0; }
header p { margin: 3px 0 0; color: #555a4b; font-size: 8.5pt; }
header p.nb { color: #15170f; font-weight: 700; }
.brand { font: 700 12pt 'Space Grotesk', sans-serif; text-align: right; }
.brand span { display: block; font: 400 8pt 'Public Sans', sans-serif; color: #555a4b; }
h2 { font: 700 13pt/1.2 'Space Grotesk', sans-serif; margin: 12px 0 5px; break-after: avoid; }
h3 { font: 700 9.5pt/1.2 'Public Sans', sans-serif; text-transform: uppercase; letter-spacing: 0.04em; color: #3d4232; margin: 8px 0 3px; break-after: avoid; }
p { margin: 0 0 6px; }
ul.check { list-style: none; padding: 0; margin: 0 0 6px; columns: 2; column-gap: 26px; }
ul.check li { position: relative; padding: 2px 0 2px 20px; break-inside: avoid; }
ul.check li::before { content: ''; position: absolute; left: 0; top: 4px; width: 11px; height: 11px; border: 1.5px solid #15170f; border-radius: 2px; }
ul.plain, ol { margin: 0 0 6px; padding-left: 18px; }
ul.plain li, ol li { margin-bottom: 2px; break-inside: avoid; }
table { width: 100%; border-collapse: collapse; margin: 4px 0 6px; font-size: 9pt; break-inside: avoid; }
th, td { text-align: left; vertical-align: top; border-bottom: 1px solid #c9ccbf; padding: 4px 6px; }
th { font-family: 'Space Grotesk', sans-serif; }
.warn { border: 1.5px solid #c2410c; border-radius: 6px; padding: 7px 10px; margin: 6px 0 8px; break-inside: avoid; }
.warn p { margin: 0; }
section { break-inside: auto; }
footer { margin-top: 10px; border-top: 1px solid #c9ccbf; padding-top: 6px; font-size: 7.5pt; color: #555a4b; break-inside: avoid; }
footer b { color: #15170f; }
"""


def text_only(el):
    """Replace links with their text: a printed page can't click them."""
    for a in el.find_all('a'):
        a.unwrap()
    return el


def section_html(soup, sid):
    h2 = soup.find('h2', id=sid)
    if not h2:
        raise SystemExit(f'no <h2 id="{sid}">')
    parts = [f'<h2>{html.escape(h2.get_text())}</h2>']
    for el in h2.find_next_siblings():
        if el.name == 'h2':
            break
        if isinstance(el, Comment) or el.name is None:
            continue
        text_only(el)
        if el.name == 'ul' and 'checklist' in (el.get('class') or []):
            items = []
            for li in el.find_all('li', recursive=False):
                for why in li.select('.why'):
                    why.decompose()
                items.append(f'<li>{li.decode_contents().strip()}</li>')
            parts.append(f'<ul class="check">{"".join(items)}</ul>')
        elif el.name == 'ul':
            el['class'] = 'plain'
            parts.append(str(el))
        elif el.name in ('ol', 'h3', 'p', 'table') or 'warn' in (el.get('class') or []):
            parts.append(str(el))
    return '<section>' + ''.join(parts) + '</section>'


def page_html(p):
    body = p['body'].replace('{{root}}', build.BASE).replace('<!--cta-->', '')
    soup = BeautifulSoup(body, 'html.parser')
    sections = ''.join(section_html(soup, s) for s in p['pdf_sections'])
    url = build.BASE + p['path']
    updated = date.fromisoformat(p['updated']).strftime('%B %-d, %Y')
    icon = data_uri(build.ROOT / 'assets' / 'img' / 'icon-192.png', 'image/png')
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(p['pdf_title'])} | BugOut</title>
<style>{font_faces()}{CSS}</style></head>
<body>
<header><img src="{icon}" alt=""><div class="t"><h1>{html.escape(p['pdf_title'])}</h1>
<p>From the free guide at {html.escape(url)}, which lists its sources ({html.escape(p['checked'])}). Updated {updated}.</p>
<p class="nb">General safety information, not medical advice or a substitute for training. In an emergency, call 911.</p></div>
<div class="brand">BugOut<span>Offline survival guide for iPhone</span></div></header>
{sections}
</body></html>'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [p for p in build.load_pages() if p.get('pdf')]
    footer = ('<div style="width:100%;font:8px sans-serif;color:#777;padding:0 0.6in;display:flex;justify-content:space-between">'
              '<span>BugOut, the free offline survival app for iPhone · {site}</span><span><span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for p in pages:
            page.set_content(page_html(p), wait_until='load')
            page.evaluate('document.fonts.ready')
            dest = OUT / p['pdf']
            page.pdf(path=str(dest), format='Letter', print_background=True, display_header_footer=True,
                     header_template='<div></div>',
                     footer_template=footer.replace('{site}', html.escape(re.sub(r'^https?://', '', build.BASE + p['path']))),
                     margin={'top': '0.45in', 'bottom': '0.6in', 'left': '0.6in', 'right': '0.6in'})
            print('wrote', dest.relative_to(build.ROOT), f'{dest.stat().st_size // 1024} KB')
        browser.close()


if __name__ == '__main__':
    main()
