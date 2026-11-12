#!/usr/bin/env python3
"""Build the BugOut website from _src/pages into the repo root.

    python3 _src/build.py

Each page in _src/pages starts with a JSON block in an HTML comment
(<!--{...}-->), followed by the page body. This script wraps every page in
the shared head (title, description, canonical, social cards, structured
data), header and footer, builds the guide tables of contents, and writes
sitemap.xml. GitHub Pages ignores folders that start with an underscore, so
_src is never published.

To move the site to a custom domain, change BASE below and rebuild.
"""

import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path

BASE = 'https://jaechung-glitch.github.io/bugout/'
SITE_NAME = 'BugOut'
APP_ID = '6761040937'
APP_STORE = f'https://apps.apple.com/us/app/id{APP_ID}'
INDEXNOW_KEY = '76c6d38f06237106f8128185b52db26e'
ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / '_src' / 'pages'

STORE_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="2" width="12" height="20" rx="2.5"/>'
              '<path d="M12 7v7m-3-3 3 3 3-3"/></svg>')


PDF_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
            '<path d="M14 3v5h5M9 13l3 3 3-3M12 10v6"/></svg>')


def phone_pdf(p):
    return p['pdf'].replace('.pdf', '-phone.pdf')


def pdf_link(p, root):
    """Download buttons for a guide's checklist PDFs (made by _src/make_pdfs.py):
    Letter size to print, and a phone-shaped version to keep on a phone."""
    if not p.get('pdf'):
        return ''
    return (f'<div class="pdf-link">{PDF_ICON}'
            f'<div class="pdf-text"><b>Download the checklist (PDF)</b>'
            f'<span>{html.escape(p["pdf_title"])}: free to print, share and keep with your kit.</span></div>'
            f'<div class="pdf-btns">'
            f'<a class="btn btn-ghost pdf-print" href="{root}assets/pdf/{p["pdf"]}" type="application/pdf">Print version</a>'
            f'<a class="btn btn-ghost pdf-phone" href="{root}assets/pdf/{phone_pdf(p)}" type="application/pdf">Phone version</a>'
            f'</div></div>')


def store_button(label='Get BugOut on the App Store', extra=''):
    return (f'<a class="btn btn-primary{extra}" href="{APP_STORE}" rel="noopener">'
            f'{STORE_ICON}{html.escape(label)}</a>')


def load_pages():
    pages = []
    for f in sorted(PAGES.glob('*.html')):
        text = f.read_text(encoding='utf-8')
        m = re.match(r'\s*<!--(\{.*?\})-->\s*', text, re.S)
        if not m:
            raise SystemExit(f'{f.name}: missing JSON front matter')
        meta = json.loads(m.group(1))
        meta['body'] = text[m.end():]
        meta['src'] = f.name
        pages.append(meta)
    return pages


def rel_root(path):
    """Relative prefix from a page's folder back to the site root."""
    depth = path.count('/') if path.endswith('/') else path.count('/')
    return '../' * depth


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '</script>'


def head(p, root):
    url = BASE + p['path']
    og = BASE + 'assets/img/' + p.get('og', 'og-home.jpg')
    title = html.escape(p['title'])
    desc = html.escape(p['description'])
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="alternate" type="text/plain" title="BugOut for AI assistants (llms.txt)" href="{root}llms.txt">
<meta name="theme-color" content="#0e0f0c">
<meta name="apple-itunes-app" content="app-id={APP_ID}">
<meta property="og:type" content="{'article' if p['type'] == 'guide' else 'website'}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{html.escape(p.get('og_title', p['title']))}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(p.get('og_title', p['title']))}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og}">
<link rel="icon" type="image/png" sizes="32x32" href="{root}assets/img/favicon-32.png">
<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
<link rel="preload" href="{root}assets/fonts/space-grotesk-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{root}assets/fonts/public-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/site.css">
{schema(p)}
</head>'''


def header(root):
    return f'''<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{root or './'}"><img src="{root}assets/img/icon-96.png" width="34" height="34" alt="">BugOut</a>
    <nav class="nav" aria-label="Main">
      <a class="nav-guides" href="{root}guides/"><span class="wide">Survival </span>guides</a>
      <a href="{root}#wally">Ask Wally</a>
      <a href="{root}#faq">FAQ</a>
      <a class="btn btn-primary" href="{APP_STORE}" rel="noopener">Get the app</a>
    </nav>
  </div>
</header>'''


def footer(root, pages_by_path=None):
    popular = ''
    if pages_by_path:
        links = ''.join(f'<a href="{root}{q["path"]}">{html.escape(q["card"])}</a>'
                        for q in sorted(pages_by_path.values(), key=lambda x: x.get('order', 99)) if q['type'] == 'guide')
        popular = f'<nav class="footer-guides" aria-label="Survival guides"><b>Survival guides</b>{links}</nav>'
    return f'''<footer class="site-footer">
  <div class="wrap">
    {popular}
    <nav aria-label="Footer">
      <a href="{root or './'}">Home</a>
      <a href="{root}guides/">Survival guides</a>
      <a href="{root}support.html">Support</a>
      <a href="{root}privacy-policy.html">Privacy</a>
      <a href="{root}terms.html">Terms</a>
    </nav>
    <span>BugOut: Offline Survival Kit for iPhone</span>
    <p class="fine">BugOut and these guides share general safety information drawn from public sources such as the CDC, EPA, FEMA and the U.S. Army. They are not a substitute for training or professional medical advice. In an emergency, call 911.</p>
    <p class="fine">BugOut is independent: it isn't affiliated with or endorsed by the CDC, EPA, FEMA, the U.S. military, the American Red Cross or any other agency or organization whose guidance it cites.</p>
    <p class="fine">Apple, iPhone, Apple Intelligence and App Store are trademarks of Apple Inc., registered in the U.S. and other countries and regions.</p>
  </div>
</footer>
</body>
</html>
'''


def schema(p):
    url = BASE + p['path']
    org = {'@type': 'Organization', '@id': BASE + '#org', 'name': SITE_NAME, 'url': BASE,
           'email': 'bugoutsurvivalguides@gmail.com',
           'logo': BASE + 'assets/img/icon-512.png', 'sameAs': [APP_STORE],
           'description': 'Makers of BugOut: Offline Survival Kit, an iPhone app for emergency preparedness that works with no internet.'}
    graph = []
    if p['type'] == 'home':
        graph.append(org)
        graph.append({'@type': 'WebSite', '@id': BASE + '#website', 'url': BASE, 'name': SITE_NAME,
                      'inLanguage': 'en-US', 'publisher': {'@id': BASE + '#org'}})
        graph.append({
            '@type': 'MobileApplication', '@id': BASE + '#app', 'name': 'BugOut: Offline Survival Kit',
            # The App Store name until 1.1.1, so engines tie the two together.
            'alternateName': ['BugOut', 'BugOut: Offline Survival Guide'], 'operatingSystem': 'iOS 16.0 or later', 'softwareRequirements': 'iPhone with iOS 16.0 or later',
            'applicationCategory': 'ReferenceApplication', 'applicationSubCategory': 'Survival and emergency preparedness',
            'url': BASE, 'downloadUrl': APP_STORE, 'installUrl': APP_STORE, 'inLanguage': 'en-US', 'countriesSupported': 'US',
            'description': p['app_description'], 'image': BASE + 'assets/img/icon-512.png',
            'screenshot': [BASE + 'assets/img/wally-answer-720.webp', BASE + 'assets/img/survival-essentials-720.webp',
                           BASE + 'assets/img/scenarios-720.webp', BASE + 'assets/img/power-grid-720.webp'],
            'featureList': p['feature_list'], 'isAccessibleForFree': True,
            'offers': [
                {'@type': 'Offer', 'name': 'BugOut (free download)', 'price': '0', 'priceCurrency': 'USD'},
                {'@type': 'Offer', 'name': 'BugOut Pro, monthly', 'price': '6.99', 'priceCurrency': 'USD',
                 'priceSpecification': {'@type': 'UnitPriceSpecification', 'price': '6.99', 'priceCurrency': 'USD', 'billingDuration': 'P1M'}},
                {'@type': 'Offer', 'name': 'BugOut Pro, yearly', 'price': '54.99', 'priceCurrency': 'USD',
                 'priceSpecification': {'@type': 'UnitPriceSpecification', 'price': '54.99', 'priceCurrency': 'USD', 'billingDuration': 'P1Y'}},
            ],
            'publisher': {'@id': BASE + '#org'},
        })
    if p.get('faq'):
        graph.append({'@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': re.sub(r'<[^>]+>', '', a)}}
            for q, a in p['faq']]})
    if p['type'] == 'guide':
        graph.append({
            '@type': 'Article', 'headline': p['h1'], 'description': p['description'], 'mainEntityOfPage': url,
            'image': BASE + 'assets/img/' + p['og'], 'datePublished': p['published'], 'dateModified': p['updated'],
            'inLanguage': 'en-US', 'isAccessibleForFree': True, 'about': p.get('about', []),
            'citation': [u for _, u in p['sources'] if u], 'author': org, 'publisher': org,
        })
    if p['type'] == 'hub' and p.get('_guides'):
        graph.append({'@type': 'CollectionPage', '@id': url, 'url': url, 'name': p['title'], 'description': p['description'],
                      'isPartOf': {'@id': BASE + '#website'}, 'inLanguage': 'en-US',
                      'mainEntity': {'@type': 'ItemList', 'itemListElement': [
                          {'@type': 'ListItem', 'position': i + 1, 'url': BASE + q['path'], 'name': q['h1']}
                          for i, q in enumerate(p['_guides'])]}})
    if p.get('terms'):
        graph.append({'@type': 'DefinedTermSet', '@id': url + '#terms', 'name': p['h1'], 'url': url,
                      'hasDefinedTerm': [{'@type': 'DefinedTerm', 'name': t['term'], 'url': f"{url}#{t['id']}",
                                          'description': re.sub(r'<[^>]+>', '', t['def'])} for t in p['terms']]})
    crumbs = breadcrumbs(p)
    if len(crumbs) > 1:
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': BASE + u} for i, (n, u) in enumerate(crumbs)]})
    return jsonld({'@context': 'https://schema.org', '@graph': graph})


def breadcrumbs(p):
    if p['type'] not in ('hub', 'guide'):
        return [('Home', '')]
    if p['type'] == 'hub':
        return [('Home', ''), ('Survival guides', 'guides/')]
    return [('Home', ''), ('Survival guides', 'guides/'), (p['crumb'], p['path'])]


def crumbs_html(p, root):
    items = breadcrumbs(p)
    lis = []
    for i, (n, u) in enumerate(items):
        if i == len(items) - 1:
            lis.append(f'<li aria-current="page">{html.escape(n)}</li>')
        else:
            lis.append(f'<li><a href="{root}{u}">{html.escape(n)}</a></li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>'


def app_cta(p, root):
    return f'''<div class="app-cta">
  <img src="{root}assets/img/icon-192.png" width="96" height="96" alt="BugOut app icon">
  <div>
    <h2>{html.escape(p['cta_title'])}</h2>
    <p>{p['cta']}</p>
    {store_button()}
  </div>
</div>'''


def quick_answers(p):
    """Question-and-answer pairs at the end of a guide, mirrored in FAQPage
    structured data, so search and AI answer engines can quote one answer."""
    if not p.get('faq'):
        return ''
    qa = ''.join(f'<h3>{html.escape(q)}</h3><p>{a}</p>' for q, a in p['faq'])
    return f'<h2 id="quick-answers">Quick answers</h2>\n<div class="quick">{qa}</div>'


def facts_html(facts):
    rows = ''.join(f'<div><dt>{html.escape(k)}</dt><dd>{v}</dd></div>' for k, v in facts)
    return f'<dl class="facts">{rows}</dl>'


def terms_html(terms):
    """A glossary: each term is a linkable definition, mirrored in
    DefinedTermSet structured data so answer engines can quote one."""
    rows = ''.join(f'<div id="{t["id"]}"><dt>{html.escape(t["term"])}</dt><dd>{t["def"]}</dd></div>'
                   for t in sorted(terms, key=lambda t: t['term'].lower()))
    return f'<dl class="terms">{rows}</dl>'


def guide_body(p, pages_by_path, root):
    body = p['body'].replace('<!--cta-->', app_cta(p, root))
    if p.get('terms'):
        body = body.replace('<!--terms-->', terms_html(p['terms']))
    if p.get('pdf'):
        # The download block goes right after the short answer at the top.
        m = re.search(r'<div class="answer">.*?</div>', body, re.S)
        at = m.end() if m else 0
        body = body[:at] + '\n' + pdf_link(p, root) + body[at:]
    # The short answer (and the checklist download) sit above the two columns,
    # so on a phone they come before the table of contents, not after it.
    lead = ''
    m = re.search(r'<div class="answer">.*?</div>\s*(<div class="pdf-link">.*?</div></div>)?', body, re.S)
    if m and not p.get('tool'):
        lead, body = f'<div class="lead">{m.group(0)}</div>', body[:m.start()] + body[m.end():]
    toc = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body)
    if p.get('faq'):
        toc.append(('quick-answers', 'Quick answers'))
    toc.append(('sources', 'Sources'))
    toc_html = ''.join(f'<li><a href="#{i}">{re.sub(r"<[^>]+>", "", t)}</a></li>' for i, t in toc)
    sources = ''.join(
        f'<li><a href="{u}" rel="noopener">{html.escape(n)}</a></li>' if u else f'<li>{html.escape(n)}</li>'
        for n, u in p['sources'])
    related = ''.join(
        f'<li><a href="{root}{r}"><h3>{html.escape(pages_by_path[r]["card"])}</h3><p>{html.escape(pages_by_path[r]["card_text"])}</p></a></li>'
        for r in p['related'])
    updated = long_date(p['updated'])
    pdf_toc = (f'<br>Checklist PDF: <a href="{root}assets/pdf/{p["pdf"]}" type="application/pdf">print</a> · '
               f'<a href="{root}assets/pdf/{phone_pdf(p)}" type="application/pdf">phone</a>') if p.get('pdf') else ''
    return f'''<main id="main">
<div class="wrap">
  {crumbs_html(p, root)}
  <header class="article-head">
    <h1>{html.escape(p['h1'])}</h1>
    <p class="dek">{p['dek']}</p>
    <p class="byline">By the BugOut team. Updated {updated}. Checked against {html.escape(p['checked'])}.</p>
  </header>{chr(10) + '  ' + lead if lead else ''}
  <div class="article{' tool' if p.get('tool') else ''}">
    <div class="body">
{body}
{quick_answers(p)}
      <h2 id="sources">Sources</h2>
      <ul class="sources">{sources}</ul>
      <p class="disclaimer">This guide is general safety information, not medical advice or a substitute for training. Guidance changes; check your local emergency management office for advice specific to where you live. In an emergency, call 911.</p>
    </div>
    <aside>
      <nav class="toc" aria-label="On this page"><b>On this page</b><ol>{toc_html}</ol>
        <p class="print"><button type="button" class="linklike" onclick="window.print()">Print this guide</button>{pdf_toc}</p></nav>
      <div class="side-app"><p>{html.escape(p['side'])}</p>{store_button('Get BugOut')}</div>
    </aside>
  </div>
</div>
<section class="related"><div class="wrap"><h2>More survival guides</h2><ul class="guide-list">{related}</ul></div></section>
</main>'''


def long_date(iso):
    d = date.fromisoformat(iso)
    return f'{d.strftime("%B")} {d.day}, {d.year}'


def git_date(name, fallback):
    """Date a hand-written page last changed, from git; the fallback covers a
    file that has never been committed."""
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', name], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        return out or fallback
    except OSError:
        return fallback


def render(p, pages_by_path):
    root = rel_root(p['path'])
    body = p['body']
    if p['type'] == 'guide':
        main = guide_body(p, pages_by_path, root)
    else:
        main = body
        if p['type'] == 'hub':
            cards = ''.join(
                f'<li><a href="{root}{q["path"]}"><h3>{html.escape(q["card"])}</h3><p>{html.escape(q["card_text"])}</p></a></li>'
                for q in sorted(pages_by_path.values(), key=lambda x: x.get('order', 99)) if q['type'] == 'guide')
            qa = ''.join(f'<h3>{html.escape(q)}</h3><p>{a}</p>' for q, a in p.get('faq', []))
            main = main.replace('<!--guides-->', cards).replace('<!--crumbs-->', crumbs_html(p, root)).replace('<!--faq-->', qa)
        if p['type'] == 'home':
            cards = ''.join(
                f'<li><a href="{root}{q["path"]}"><h3>{html.escape(q["card"])}</h3><p>{html.escape(q["card_text"])}</p></a></li>'
                for q in sorted(pages_by_path.values(), key=lambda x: x.get('order', 99)) if q['type'] == 'guide')
            faq = ''.join(f'<details><summary>{html.escape(q)}</summary><div class="a"><p>{a}</p></div></details>' for q, a in p['faq'])
            main = main.replace('<!--guides-->', cards).replace('<!--faq-->', faq).replace('<!--facts-->', facts_html(p['facts']))
    main = main.replace('{{store}}', store_button()).replace('{{store_url}}', APP_STORE).replace('{{root}}', root)
    return head(p, root) + '\n' + header(root) + '\n' + main + '\n' + footer(root, pages_by_path)


def page_markdown(p, full_html):
    """The page's main content as Markdown, with absolute links, for llms-full.txt."""
    from bs4 import BeautifulSoup
    from markdownify import markdownify
    soup = BeautifulSoup(full_html, 'html.parser')
    main = soup.find('main')
    for sel in ['aside', '.related', '.app-cta', '.crumbs', '.hero-phone', '.screens', '.actions', '.cta-note', '.signal', '.closing', '.calc', 'script']:
        for el in main.select(sel):
            el.decompose()
    for why in main.select('.why'):
        # A checklist item's explanation reads as its own sentence in plain text.
        why.insert_before('. ' if not re.search(r'[.!?:]$', why.parent.get_text().split(why.get_text())[0].strip()) else ' ')
    page_url = BASE + p['path']
    for a in main.find_all('a', href=True):
        h = a['href']
        if not h.startswith(('http://', 'https://', '#', 'javascript:')):
            from urllib.parse import urljoin
            a['href'] = urljoin(page_url, h)
    md = markdownify(str(main), heading_style='ATX', bullets='-', strip=['img'])
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md


def llms_txt(pages, home):
    guides = sorted((q for q in pages if q['type'] == 'guide'), key=lambda x: x.get('order', 99))
    facts = '\n'.join(f'- {k}: {re.sub(r"<[^>]+>", "", v)}' for k, v in home['facts'])
    lines = [
        '# BugOut',
        '',
        f"> {home['app_description']}",
        '',
        'This file summarizes the BugOut website for AI assistants and search engines. The full text of every page is in '
        f'[llms-full.txt]({BASE}llms-full.txt).',
        '',
        '## Key facts',
        '',
        facts,
        '',
        '## The app',
        '',
        f'- [BugOut: offline survival app for iPhone]({BASE}): what the app does, Ask Wally, free vs Pro, and FAQ',
        f'- [BugOut on the App Store]({APP_STORE}): download page',
        '',
        '## Survival guides',
        '',
    ]
    lines += [f'- [{q["h1"]}]({BASE}{q["path"]}): {q["description"]}' for q in guides]
    lines += ['', '## Printable checklists (PDF)', '']
    lines += [f'- [{q["pdf_title"]} (PDF)]({BASE}assets/pdf/{q["pdf"]}): from [{q["h1"]}]({BASE}{q["path"]}); '
              f'[phone version]({BASE}assets/pdf/{phone_pdf(q)})'
              for q in guides if q.get('pdf')]
    lines += [
        '',
        '## Optional',
        '',
        f'- [Support]({BASE}support.html): contact, Pro subscription help and FAQ',
        f'- [Privacy policy]({BASE}privacy-policy.html)',
        f'- [Terms of use]({BASE}terms.html)',
        '',
    ]
    return '\n'.join(lines)


def not_found(pages_by_path):
    """GitHub Pages serves 404.html for any missing URL. Links are absolute
    because the page is shown at whatever address was asked for."""
    p = {'path': '404.html', 'type': 'page', 'title': 'Page not found | BugOut',
         'description': 'That page is not here. Find the BugOut survival guides and the app.'}
    guides = sorted((q for q in pages_by_path.values() if q['type'] == 'guide'), key=lambda x: x.get('order', 99))
    cards = ''.join(f'<li><a href="{BASE}{q["path"]}"><h3>{html.escape(q["card"])}</h3><p>{html.escape(q["card_text"])}</p></a></li>'
                    for q in guides)
    main = f'''<main id="main"><div class="wrap">
  <header class="hub-head"><h1>That page isn't here</h1>
  <p>The link may be old or mistyped. Start from the <a href="{BASE}">BugOut home page</a>, or pick a guide below.</p></header>
  <h2 class="sr-only">Survival guides</h2>
  <ul class="guide-list">{cards}</ul>
</div></main>'''
    page = head(p, BASE) + '\n' + header(BASE) + '\n' + main + '\n' + footer(BASE, pages_by_path)
    return page.replace('content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"', 'content="noindex"') \
               .replace(f'<link rel="canonical" href="{BASE}404.html">\n', '')


def out_path(path):
    return ROOT / (path + 'index.html' if path == '' or path.endswith('/') else path)


def main():
    pages = load_pages()
    by_path = {p['path']: p for p in pages}
    newest = max(p['updated'] for p in pages if p['type'] == 'guide')
    guides = sorted((q for q in pages if q['type'] == 'guide'), key=lambda x: x.get('order', 99))
    for p in pages:
        if p['type'] in ('home', 'hub'):
            p['updated'] = max(p['updated'], newest)
            p['_guides'] = guides
    (ROOT / '404.html').write_text(not_found(by_path), encoding='utf-8')
    full = []
    for p in sorted(pages, key=lambda x: (x['type'] != 'home', x['type'] != 'hub', x.get('order', 99))):
        dest = out_path(p['path'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        page_html = render(p, by_path)
        dest.write_text(page_html, encoding='utf-8')
        print('wrote', dest.relative_to(ROOT))
        md = page_markdown(p, page_html)
        first, _, rest = md.partition('\n')
        if not first.startswith('# '):
            first, rest = f"# {p.get('h1', p['title'])}", md
        full.append(f"{first}\n\nURL: {BASE}{p['path']}\nUpdated: {p['updated']}\n{rest}\n")
    home = by_path['']
    (ROOT / 'llms.txt').write_text(llms_txt(pages, home), encoding='utf-8')
    (ROOT / 'llms-full.txt').write_text(
        f"# BugOut website, full text\n\n> {home['app_description']}\n\n" + '\n---\n\n'.join(full), encoding='utf-8')
    # IndexNow lets Bing (which feeds ChatGPT search and Copilot) and other engines
    # pick up new and changed pages quickly. The key file must stay published.
    (ROOT / f'{INDEXNOW_KEY}.txt').write_text(INDEXNOW_KEY, encoding='utf-8')
    print('wrote llms.txt, llms-full.txt and the IndexNow key file')
    urls = [(BASE + p['path'], p['updated']) for p in pages]
    urls += [(BASE + f, git_date(f, date.today().isoformat())) for f in ('support.html', 'privacy-policy.html', 'terms.html')]
    urls += [(BASE + 'assets/pdf/' + p['pdf'], p['updated']) for p in pages if p.get('pdf')]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f'  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>' for u, d in urls]
    sm.append('</urlset>')
    (ROOT / 'sitemap.xml').write_text('\n'.join(sm) + '\n', encoding='utf-8')
    print('wrote sitemap.xml with', len(urls), 'urls')


if __name__ == '__main__':
    main()
