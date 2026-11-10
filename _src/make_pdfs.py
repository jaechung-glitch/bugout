#!/usr/bin/env python3
"""Make the printable PDF checklists in assets/pdf from the guide pages.

    python3 _src/build.py && python3 _src/make_pdfs.py

Each checklist comes in two sizes: Letter for printing, and a phone-shaped
page (one column, bigger text, tables turned into stacked blocks) for
reading and keeping on a phone, saved as the same name with "-phone".

A guide gets a PDF when its front matter has "pdf" (the file name),
"pdf_title" and "pdf_sections" (the ids of the h2 sections to include, in
order). Checklists become tick boxes, each keeping its explanation in small
print (some carry safety notes); other lists, tables and warnings are kept
as they are. Needs Playwright with Chromium and BeautifulSoup. Rebuild the
PDFs whenever those sections change, and after changing BASE in build.py
(the PDFs print the page addresses).
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
ul.check li small { display: block; font-size: 8pt; line-height: 1.3; color: #555a4b; }
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

# A phone-shaped page (about 9:19.5): viewers fit it to the screen width, so
# 4.5 inches across shows 11pt text at roughly 13pt on an iPhone.
PHONE_W, PHONE_H = '4.5in', '9.75in'
PHONE_CSS = """
* { box-sizing: border-box; }
body { margin: 0; font: 400 11pt/1.4 'Public Sans', sans-serif; color: #15170f; }
header { border-bottom: 3px solid #15170f; padding-bottom: 8px; margin-bottom: 6px; }
header .top { display: flex; align-items: center; gap: 10px; }
header img { width: 34px; height: 34px; border-radius: 8px; }
h1 { font: 700 19pt/1.05 'Space Grotesk', sans-serif; letter-spacing: -0.02em; margin: 0; }
header p { margin: 6px 0 0; color: #555a4b; font-size: 8.5pt; line-height: 1.35; }
header p.nb { color: #15170f; font-weight: 700; font-size: 9pt; }
h2 { font: 700 14.5pt/1.2 'Space Grotesk', sans-serif; margin: 16px 0 6px; break-after: avoid; }
h3 { font: 700 10pt/1.2 'Public Sans', sans-serif; text-transform: uppercase; letter-spacing: 0.04em; color: #3d4232; margin: 12px 0 4px; break-after: avoid; }
p { margin: 0 0 8px; }
ul.check { list-style: none; padding: 0; margin: 0 0 8px; }
ul.check li { position: relative; padding: 7px 0 7px 30px; border-bottom: 1px solid #dfe1d7; break-inside: avoid; }
ul.check li small { display: block; font-size: 9pt; line-height: 1.35; color: #555a4b; margin-top: 2px; }
ul.check li::before { content: ''; position: absolute; left: 0; top: 8px; width: 17px; height: 17px; border: 2px solid #15170f; border-radius: 3px; }
ul.plain, ol { margin: 0 0 8px; padding-left: 20px; }
ul.plain li, ol li { margin-bottom: 5px; break-inside: avoid; }
.rows { margin: 4px 0 10px; }
.rows div { border-bottom: 1px solid #dfe1d7; padding: 7px 0; break-inside: avoid; }
.rows b { display: block; font-family: 'Space Grotesk', sans-serif; }
.rows p { margin: 2px 0 0; }
.rows i { font-style: normal; color: #555a4b; }
.warn { border: 2px solid #c2410c; border-radius: 8px; padding: 9px 11px; margin: 8px 0 10px; break-inside: avoid; }
.warn p { margin: 0; }
.app { margin-top: 16px; border: 1.5px solid #15170f; border-radius: 8px; padding: 9px 11px; font-size: 9.5pt; break-inside: avoid; }
"""


def text_only(el):
    """Replace links with their text: a printed page can't click them."""
    for a in el.find_all('a'):
        a.unwrap()
    return el


def stacked(table):
    """A table as stacked blocks, which read better than columns on a phone."""
    heads = [th.get_text(' ', strip=True) for th in table.select('thead th')]
    blocks = []
    for tr in table.select('tbody tr'):
        cells = tr.find_all(['th', 'td'])
        title, rest = cells[0].decode_contents(), cells[1:]
        if len(cells) == 2:
            lines = f'<p>{rest[0].decode_contents()}</p>'
        else:
            lines = ''.join(f'<p><i>{html.escape(h)}:</i> {c.decode_contents()}</p>' if h else f'<p>{c.decode_contents()}</p>'
                            for h, c in zip(heads[1:], rest))
        blocks.append(f'<div><b>{title}</b>{lines}</div>')
    return '<div class="rows">' + ''.join(blocks) + '</div>'


def section_html(soup, sid, phone=False):
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
                # Keep each item's explanation: some carry safety notes.
                for why in li.select('.why'):
                    why.name = 'small'
                    del why['class']
                items.append(f'<li>{li.decode_contents().strip()}</li>')
            parts.append(f'<ul class="check">{"".join(items)}</ul>')
        elif el.name == 'ul':
            el['class'] = 'plain'
            parts.append(str(el))
        elif el.name == 'table' and phone:
            parts.append(stacked(el))
        elif el.name in ('ol', 'h3', 'p', 'table') or 'warn' in (el.get('class') or []):
            parts.append(str(el))
    return '<section>' + ''.join(parts) + '</section>'


def phone_name(p):
    return p['pdf'].replace('.pdf', '-phone.pdf')


def page_html(p, phone=False):
    body = p['body'].replace('{{root}}', build.BASE).replace('<!--cta-->', '')
    soup = BeautifulSoup(body, 'html.parser')
    sections = ''.join(section_html(soup, s, phone) for s in p['pdf_sections'])
    url = build.BASE + p['path']
    updated = build.long_date(p['updated'])
    icon = data_uri(build.ROOT / 'assets' / 'img' / 'icon-192.png', 'image/png')
    if phone:
        return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(p['pdf_title'])} | BugOut</title>
<style>{font_faces()}{PHONE_CSS}</style></head>
<body>
<header><div class="top"><img src="{icon}" alt=""><h1>{html.escape(p['pdf_title'])}</h1></div>
<p class="nb">General safety information, not medical advice or a substitute for training. In an emergency, call 911.</p>
<p>From the free guide at {html.escape(url)}, which lists its sources. Updated {updated}.</p></header>
{sections}
<div class="app"><b>Tick items off on your iPhone.</b> BugOut, the free offline survival app, lets you make your own checklists and keeps its guides on your phone with no signal.</div>
</body></html>'''
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
    phone_footer = ('<div style="width:100%;font:7px sans-serif;color:#777;padding:0 0.3in;display:flex;justify-content:space-between">'
                    '<span>BugOut · free offline survival app for iPhone</span><span><span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for p in pages:
            site = html.escape(re.sub(r'^https?://', '', build.BASE + p['path']))
            page.set_content(page_html(p), wait_until='load')
            page.evaluate('document.fonts.ready')
            dest = OUT / p['pdf']
            page.pdf(path=str(dest), format='Letter', print_background=True, display_header_footer=True,
                     header_template='<div></div>', footer_template=footer.replace('{site}', site),
                     margin={'top': '0.45in', 'bottom': '0.6in', 'left': '0.6in', 'right': '0.6in'})
            print('wrote', dest.relative_to(build.ROOT), f'{dest.stat().st_size // 1024} KB')
            page.set_content(page_html(p, phone=True), wait_until='load')
            page.evaluate('document.fonts.ready')
            dest = OUT / phone_name(p)
            page.pdf(path=str(dest), width=PHONE_W, height=PHONE_H, print_background=True, display_header_footer=True,
                     header_template='<div></div>', footer_template=phone_footer,
                     margin={'top': '0.32in', 'bottom': '0.42in', 'left': '0.3in', 'right': '0.3in'})
            print('wrote', dest.relative_to(build.ROOT), f'{dest.stat().st_size // 1024} KB')
        browser.close()


if __name__ == '__main__':
    main()
