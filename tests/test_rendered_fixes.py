#!/usr/bin/env python3
"""Regression tests for the rendered-family fixes of the 2026-11-25 review.

A. Closed <details>: its content keeps layout boxes in Chromium, so it passed
   the visibility filter while innerText came back empty — every link of a
   closed menu was reported as «no accessible name» (4.1.2) and «never
   receives focus» (2.4.7). A really empty link is still reported.
B. a11y_snapshot right after a pooled tool in the SAME process: the pool
   leaves its loop as the thread's running loop and the second sync session
   died with «Playwright Sync API inside the asyncio loop».
C. contrast_walk: a load timeout came out as an exception; it is now the
   same clean error as an HTTP 400.
D. audit_dom: `load` timing out on a hanging subresource while the DOM is
   complete audits the page and leaves the record in page_errors.
E. a11y_scroll reported its load error in Spanish when lang=en; two catalog
   texts mixed languages or said nothing.
F. Rendered findings carry the total in `count` (examples are capped at 6).
G. Two real rendered reports (8 and 11 images without alt) through the
   budget: the total in `count` is what detects the growth.

Sections take an optional argument each (`python3 tests/test_rendered_fixes.py B D`).
The browser parts skip when Playwright is not installed (same rule as test_dom).
"""
import asyncio
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit import a11yi18n, a11ydom, a11ydiff, a11yscroll  # noqa: E402

ONLY = set(sys.argv[1:])


def _want(tag):
    return not ONLY or tag in ONLY


def _examples(report, signal):
    return [e for f in report.get('findings', []) if f['signal'] == signal
            for e in f.get('examples', [])]


# ── E (no browser): the catalog texts, one language per catalog ──────────────
def _catalogs():
    scroll = a11yi18n.pair('scroll')
    assert 'screen reader' not in scroll['es']['limits'], scroll['es']['limits']
    assert 'lector de pantalla' in scroll['es']['limits'], scroll['es']['limits']
    assert 'screen-reader' in scroll['en']['limits'], scroll['en']['limits']
    for lang, kept in (('es', '(teclado, lector de pantalla, contraste real)'),
                       ('en', '(keyboard, screen reader, real contrast)')):
        with open(os.path.join(ROOT, 'a11y_toolkit', 'locales', lang + '.json'), encoding='utf-8') as f:
            catalog = json.load(f)
        # the section every audit family (static, rendered, docx) shows
        limits = next(v['limits'] for v in catalog.values()
                      if isinstance(v, dict) and 'list_structure' in v)
        assert kept in limits, limits
    with open(os.path.join(ROOT, 'a11y_toolkit', 'a11yscroll.py'), encoding='utf-8') as f:
        source = f.read()
    assert "'no se pudo cargar: {e}'" not in source, 'a11y_scroll still hard-codes one language'


if _want('E'):
    _catalogs()
    print('E catalogs: scroll limits in one language each, limits pair without the untranslatable item, no hard-coded load error ✓')

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_rendered_fixes (browser parts): Playwright not installed')
    sys.exit(0)


# ── fixtures ──────────────────────────────────────────────────────────────────
CLOSED = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Closed</title>
<style>a{display:inline-block;padding:8px}a:focus,summary:focus{outline:2px solid #000}</style>
</head><body><h1>Closed details</h1>
<details id="menu"><summary>Menu</summary><ul>
<li><a href="/a">Pricing</a></li>
<li><a href="/b" aria-label="Contact sales">?</a></li>
<li><a href="/l"><img alt="Acme logo" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="></a></li>
<li><a href="/e" id="empty-hidden"></a></li>
<li><span id="lbl">Hidden label</span></li>
</ul></details>
<details open id="faq"><summary>Help</summary><p><a href="/d">Open item</a></p></details>
<p><button id="btn" aria-labelledby="lbl"></button> <a href="/empty" id="empty"></a></p>
</body></html>'''
_closed = os.path.join('/tmp', 'a11y_closed_details.html')
with open(_closed, 'w', encoding='utf-8') as _f:
    _f.write(CLOSED)
URL = 'file://' + _closed

PAGE = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Slow</title></head>'
        '<body><main><h1>Slow</h1>'
        '<p style="color:#999;background:#fff">low contrast text</p>'
        '<img src="/hang.gif" alt="decoration"></main></body></html>')


class _Handler(BaseHTTPRequestHandler):
    """page.html: complete DOM, one subresource that never answers in time."""

    def do_GET(self):
        if self.path == '/hang.gif':
            time.sleep(4)
            body, kind = b'GIF8', 'image/gif'
        elif self.path == '/hang.html':
            time.sleep(4)
            body, kind = PAGE.encode('utf-8'), 'text/html; charset=utf-8'
        elif self.path == '/page.html':
            body, kind = PAGE.encode('utf-8'), 'text/html; charset=utf-8'
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass   # the client drops the hanging request on purpose


_SERVER = None


def _base():
    global _SERVER
    if _SERVER is None:
        _SERVER = _Server(('127.0.0.1', 0), _Handler)
        threading.Thread(target=_SERVER.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d' % _SERVER.server_address[1]


# ── A: closed <details> ──────────────────────────────────────────────────────
def _closed_details():
    # source pins (they fail without a browser too)
    assert _JS_PIN.count('textOf(') == 3 and 'const textOf = el =>' in _JS_PIN, \
        'nameOf must read text without depending on the layout'
    assert "(ref.innerText || '').trim()" not in _JS_PIN
    assert 'innerText.trim()' not in _JS_PIN
    assert "!hiddenContent(el)" in a11ydom._JS
    # behaviour
    r = a11ydom.audit_dom_url(URL, lang='en')
    assert 'error' not in r, r.get('error')
    assert _examples(r, 'ctrl_name') == ['#empty-hidden', '#empty'], _examples(r, 'ctrl_name')
    assert not _examples(r, 'focus_not_focusable'), _examples(r, 'focus_not_focusable')
    assert not _examples(r, 'field_label'), _examples(r, 'field_label')


_JS_PIN = a11ydom._JS_NAMEOF


# ── B: pooled tool, then a second sync session, same thread ──────────────────
def _pinned_to_pool():
    # after the second session the thread is exactly as the pool expects it:
    # its loop is the running loop again and the pool works without _get_browser()
    loop = a11ydom._pool_loop()
    assert loop is not None and asyncio._get_running_loop() is loop
    assert a11ydom._POOL['browser'].is_connected()


def _no_pool():
    assert a11ydom._pool_loop() is None
    assert asyncio._get_running_loop() is None


def _sequence(url, rounds, follow):
    for _ in range(rounds):
        a = a11ydom.audit_dom_url(url)
        assert 'error' not in a and a['mode'] == 'rendered', a
        s = a11ydiff.snapshot(url)   # used to raise «Sync API inside the asyncio loop»
        assert 'error' not in s and s['elements'], s
        follow()


def _pool_then_snapshot():
    _sequence(URL, rounds=2, follow=_pinned_to_pool)
    # the escape hatch keeps working: one cycle per call, nothing shared
    a11ydom._close_pool()
    os.environ['A11Y_BROWSER_POOL'] = '0'
    try:
        _sequence(URL, rounds=1, follow=_no_pool)
    finally:
        os.environ.pop('A11Y_BROWSER_POOL', None)
    # another thread (threadpool hosts): its own pool, the same sequence
    box = []

    def worker():
        try:
            _sequence(URL, rounds=1, follow=_pinned_to_pool)
        except BaseException as error:  # noqa: BLE001
            box.append(error)
        finally:
            a11ydom._close_pool()   # the pool born in this thread dies in this thread
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert not box, box[0]


# ── C: contrast_walk load timeout ─────────────────────────────────────────────
def _contrast_walk_timeout():
    base = _base()
    url = base + '/page.html'
    out = a11ydom.contrast_walk(url, max_walk=20, timeout=2)   # used to raise TimeoutError
    assert out.get('error', '').startswith('could not load: Page.goto: Timeout 2000ms'), out
    assert out['url'] == url and 'elements' not in out, out
    http = a11ydom.contrast_walk(base + '/missing.html', timeout=5)
    assert http.get('http_status') == 404 and http.get('error', '').startswith('HTTP 404'), http


# ── D: audit_dom when `load` times out on a rendered page ─────────────────────
def _slow_load():
    from a11y_toolkit.a11yaudit import completed_report_pages
    base = _base()
    url = base + '/page.html'
    r = a11ydom.audit_dom_url(url, timeout=2, lang='en')
    assert 'error' not in r, r.get('error')
    assert r['mode'] == 'rendered' and isinstance(r.get('findings'), list), r
    assert any('contrast' in f['signal'] for f in r['findings']), r['findings']
    note = r.get('page_errors')
    assert isinstance(note, list) and len(note) == 1 and isinstance(note[0], dict), note
    assert note[0]['url'] == url, note
    assert 'load event did not fire within 2 s' in note[0]['error'], note
    # honest for the layers above: audited, but not a complete measurement
    pages, reason = completed_report_pages(r)
    assert pages == [] and reason['error'].startswith('the audit did not complete'), reason
    r_es = a11ydom.audit_dom_url(url, timeout=2, lang='es')
    assert 'no llegó en 2 s' in r_es['page_errors'][0]['error'], r_es.get('page_errors')
    # a main document that never answers is still a clean load error: nothing to audit
    dead = a11ydom.audit_dom_url(base + '/hang.html', timeout=2)
    assert 'error' in dead and 'page_errors' not in dead, dead


# ── E: a11y_scroll load error follows lang ────────────────────────────────────
def _scroll_language():
    hang = _base() + '/hang.html'
    en = a11yscroll.audit_scroll(hang, lang='en', timeout=2)
    assert en.get('error', '').startswith('could not load'), en
    es = a11yscroll.audit_scroll(hang, lang='es', timeout=2)
    assert es.get('error', '').startswith('no se pudo cargar'), es


# ── F: rendered findings carry the total in `count` ──────────────────────────
_PX = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='
MANY = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Many</title></head>'
        '<body><h1>Many</h1>' + ''.join(
            '<p><img src="%s" width="40" height="40"></p>' % _PX for _ in range(8))
        + '</body></html>')


def _count_field():
    path = os.path.join('/tmp', 'a11y_many_no_alt.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(MANY)
    r = a11ydom.audit_dom_url('file://' + path, lang='en')
    assert 'error' not in r, r.get('error')
    finding = next((f for f in r['findings'] if f['signal'] == 'img_no_alt'), None)
    assert finding is not None, r['findings']
    assert finding['count'] == 8, finding          # the total, not the examples shown
    assert 0 < len(finding['examples']) <= a11ydom.MAX_EXAMPLES < 8, finding['examples']
    for f in r['findings']:
        if 'count' in f:   # signals that report no total keep no field
            assert f['count'] >= len(f.get('examples', [])), f
    # no usable n → no field (the helper alone; the key is not a catalog entry,
    # so the message carries no placeholder)
    out = []
    a11ydom._add(out, 'en', 'low', '1.3.1', 'count_field_probe', examples=['x'])
    assert 'count' not in out[0], out[0]
    a11ydom._add(out, 'en', 'low', '1.3.1', 'count_field_probe', examples=['x'], n=0)
    assert 'count' not in out[1], out[1]


# G: two real rendered reports through the budget
def _rendered_images(total):
    path = os.path.join('/tmp', 'a11y_budget_chain.html')   # one URL: before and after
    with open(path, 'w', encoding='utf-8') as f:
        f.write('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Chain</title></head>'
                '<body><h1>Chain</h1>' + ''.join(
                    '<p><img src="%s" width="40" height="40"></p>' % _PX for _ in range(total))
                + '</body></html>')
    report = a11ydom.audit_dom_url('file://' + path, lang='en')
    assert 'error' not in report, report.get('error')
    return report


def _count_through_budget():
    # no hand-made finding here: the budget reads what a real rendered audit emits
    from a11y_toolkit.a11ybudget import compare as budget_compare
    from a11y_toolkit.a11ybudget import init as budget_init
    before, after = _rendered_images(8), _rendered_images(11)
    grown = budget_compare(budget_init(before), after)
    assert not grown.get('ok') and grown.get('new_blocking_count') == 3, grown
    change = next(c for c in grown['changes'] if c.get('signal') == 'img_no_alt')
    assert change['new'] == 3 and change['basis'] == 'count', change   # a measured total, not a sample
    assert 'img_no_alt' not in grown.get('sampled_counts', []), grown
    same = budget_compare(budget_init(after), _rendered_images(11))
    assert same.get('ok') is True, same


_SECTIONS = {'A': ('closed <details>: named from the tree, not accused of missing focus; empty link still reported', _closed_details),
             'B': ('pooled tool then a11y_snapshot in the same thread, pool off and worker thread', _pool_then_snapshot),
             'C': ('contrast_walk timeout: same clean error as HTTP 400', _contrast_walk_timeout),
             'D': ('audit_dom audits a rendered page whose load timed out and records it in page_errors', _slow_load),
             'E': ('a11y_scroll load error in the report language', _scroll_language),
             'F': ('rendered findings carry count = total instances; no n, no field', _count_field),
             'G': ('two real rendered reports, 8 then 11 images without alt: the budget sees the growth',
                   _count_through_budget)}
try:
    for _tag in sorted(_SECTIONS):
        if _want(_tag):
            _SECTIONS[_tag][1]()
            print(_tag + ' ' + _SECTIONS[_tag][0] + ' ✓')
finally:
    a11ydom._close_pool()
print('RENDERED FIXES 2026-11-25 OK ✓')
