#!/usr/bin/env python3
"""Make the social-card image (1200x630) for each guide that doesn't have one.

    python3 _src/make_og.py            # only missing images
    python3 _src/make_og.py --all      # redo every guide's image

Each guide's "og" file name and "og_title" come from its front matter; an
optional "og_label" sets the small line above the title (default: "Printable
checklist" for guides with a PDF, otherwise "Survival guide").
"""

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

ROOT = build.ROOT
IMG = ROOT / 'assets' / 'img'


def card(p):
    label = p.get('og_label') or ('Printable checklist' if p.get('pdf') else 'Survival guide')
    a = ROOT.as_uri() + '/assets'
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: SG; font-weight: 700; src: url('{a}/fonts/space-grotesk-latin-700-normal.woff2'); }}
@font-face {{ font-family: SG; font-weight: 500; src: url('{a}/fonts/space-grotesk-latin-500-normal.woff2'); }}
@font-face {{ font-family: PS; font-weight: 400; src: url('{a}/fonts/public-sans-latin-400-normal.woff2'); }}
@font-face {{ font-family: PS; font-weight: 600; src: url('{a}/fonts/public-sans-latin-600-normal.woff2'); }}
* {{ margin: 0; box-sizing: border-box; }}
body {{ width: 1200px; height: 630px; background: #0e0f0c url('{a}/topo-bg.webp') center / cover; position: relative; overflow: hidden; }}
body::before {{ content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse 75% 70% at 30% 40%, rgba(14,15,12,0.92), rgba(14,15,12,0.35) 80%); }}
.in {{ position: absolute; inset: 0; padding: 70px 82px; display: flex; flex-direction: column; }}
.label {{ font: 600 26px/1 PS; color: #a9c47c; margin-bottom: 30px; }}
h1 {{ font: 700 84px/1.04 SG; letter-spacing: -0.035em; color: #fff; max-width: 900px; }}
.brand {{ margin-top: auto; display: flex; align-items: center; gap: 22px; font: 700 34px/1 SG; color: #fff; letter-spacing: -0.02em; }}
.brand img {{ width: 56px; height: 56px; border-radius: 12px; }}
.brand span {{ font: 400 24px/1 PS; color: #9a9e90; letter-spacing: 0; margin-left: 6px; }}
.mark {{ position: absolute; right: 40px; top: 40px; width: 56px; height: 56px; border-top: 6px solid #e9f5c9; border-right: 6px solid #e9f5c9; }}
.mark::after {{ content: ''; position: absolute; left: 12px; bottom: 6px; width: 22px; height: 22px; background: #ff7346; }}
</style></head><body><div class="in">
<div class="label">{html.escape(label)}</div>
<h1>{html.escape(p.get('og_title', p['h1']))}</h1>
<div class="brand"><img src="{a}/img/icon-192.png" alt="">BugOut<span>Offline survival guide for iPhone</span></div>
</div><div class="mark"></div></body></html>'''


def main():
    redo = '--all' in sys.argv
    pages = [p for p in build.load_pages() if p['type'] == 'guide' and (redo or not (IMG / p['og']).exists())]
    if not pages:
        print('every guide has its image')
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 630})
        tmp = ROOT / '_src' / '_og_tmp.html'
        for p in pages:
            tmp.write_text(card(p), encoding='utf-8')
            page.goto(tmp.as_uri())
            page.evaluate('document.fonts.ready')
            # Shrink long titles until they fit above the brand line.
            page.evaluate('''() => { const h = document.querySelector('h1'); let s = 84;
                while (h.getBoundingClientRect().bottom > 470 && s > 48) { s -= 4; h.style.fontSize = s + 'px'; } }''')
            page.screenshot(path=str(IMG / p['og']), type='jpeg', quality=88)
            print('wrote', (IMG / p['og']).relative_to(ROOT))
        tmp.unlink()
        browser.close()


if __name__ == '__main__':
    main()
