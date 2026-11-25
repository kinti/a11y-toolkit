#!/usr/bin/env python3
"""Regressions from the 2026-11-25 review of the static + CLI family.

  1. the gate fails CLOSED: an engine error is never `allow`
  2. autofix propagates the audit error instead of an empty not_applied
  3. a slow but complete HTTP body is measured (a truncated one still errors)
  4. failed URLs do not spend the page quota of a crawl
  5. the budget matches instances by stable identity (id, data-testid, ARIA)
     and says when a count comes only from examples
  6. the budget CLI answers a clean exit 1 on unreadable inputs
  7. the bench keeps WCAG 2.2 A/AA criteria only
  8. the disprover decides with sampled paths and survives numeric fields
  9. a corrupt DOCX never escapes as a traceback
"""

import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'bench'))

from a11y_toolkit.a11yaudit import MAX_HTML, audit_html, audit_site, audit_url  # noqa: E402
from a11y_toolkit import a11ypatches  # noqa: E402
from a11y_toolkit.a11ybudget import (compare as budget_compare,  # noqa: E402
                                     init as budget_init, main as budget_main)
from a11y_toolkit.a11ydisprove import _classify_findings, disprove  # noqa: E402
from a11y_toolkit.a11ydocx import docx_screen  # noqa: E402
from a11y_toolkit.a11yfix import autofix  # noqa: E402
from a11y_toolkit.a11ygate import guard_hook, verdict  # noqa: E402
import compara  # noqa: E402

results = []


def check(name, cond, detail=None):
    results.append((name, bool(cond)))
    line = ('ok  ' if cond else 'FAIL') + ' ' + name
    if not cond and detail is not None:
        line += '  -> ' + repr(detail)[:300]
    print(line)


def section(fn):
    """Run one regression now; a red one must not hide the rest."""
    try:
        fn()
    except Exception as error:  # noqa: BLE001
        check(fn.__name__ + ' raised', False, type(error).__name__ + ': ' + str(error))
    return fn


def _run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=ROOT)


def _dump(obj, path):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(obj, handle)


def _signals(html, url='https://site/page'):
    return audit_html(html, url)['findings']


# ── local server: one slow-but-complete page, one truncated, crawl pages ────
_PAGE = ('<html lang="en"><head><title>Sample</title></head><body><main><h1>Sample</h1>'
         '<img src="a.png"></main></body></html>')
_EIGHT = ('<html lang="en"><head><title>Sample</title></head><body><main><h1>Sample</h1>'
          + '<img src="p.png">' * 8 + '</main></body></html>')
_LINKS = {'/entry': ['/dead1', '/dead2', '/good1', '/good2', '/good3', '/good4'],
          '/many': ['/dead%d' % index for index in range(40)]}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        try:
            if path == '/slow':
                body = _PAGE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                # 7 bytes at 0.9 s each: 6.3 s in total, past the 5 s read
                # window, and every gap well under the 2 s socket timeout
                self.wfile.write(body[:1])
                self.wfile.flush()
                for byte in body[1:8]:
                    time.sleep(0.9)
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                self.wfile.write(body[8:])
                return
            if path == '/truncated':
                body = _PAGE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body) + 20))
                self.end_headers()
                self.wfile.write(body[:len(body) // 2])
                return
            if path in _LINKS:
                body = ('<html lang="en"><head><title>Links</title></head><body>'
                        + ''.join('<a href="%s">Link</a>' % href for href in _LINKS[path])
                        + '</body></html>').encode('utf-8')
            elif path == '/eight':
                body = _EIGHT.encode('utf-8')
            elif path.startswith('/good') or path == '/page':
                body = _PAGE.encode('utf-8')
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass

    def log_message(self, *args):
        pass


_http = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
threading.Thread(target=_http.serve_forever, daemon=True).start()
BASE_URL = 'http://127.0.0.1:%d' % _http.server_port

CLEAN = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Ok</title></head>'
         '<body><main><h1>Ok</h1><img src="a.png" alt="Chart of monthly sales"><button>Send</button></main>'
         '</body></html>')
OVERSIZED = ('<!doctype html><html lang="en"><head><title>Big</title></head><body>'
             + '<p>filler</p>' * (MAX_HTML // 11 + 2) + '<img src="a.png"></body></html>')


# ── 1. the gate fails closed ────────────────────────────────────────────────
@section
def gate_fails_closed():
    check('1-pre. the oversized page is an engine error with an image without alt',
          len(OVERSIZED) > MAX_HTML and 'error' in audit_html(OVERSIZED) and '<img src="a.png">' in OVERSIZED)
    v = verdict('', OVERSIZED, 'page.html')
    check('1a. gate: page over 3 MB with an image without alt is never `allow`',
          v['decision'] == 'error' and v.get('error') and v.get('failed') == 'new'
          and not v['blocked'], v)
    v = verdict(OVERSIZED, CLEAN, 'page.html')
    check('1b. gate: a git HEAD version that cannot be audited is not `allow` either',
          v['decision'] == 'error' and v.get('failed') == 'old', v)
    en = verdict('', OVERSIZED, 'page.html', lang='en')
    es = verdict('', OVERSIZED, 'page.html', lang='es')
    check('1c. gate: the error message exists in en and in es',
          en['note'] != es['note'] and en['error'] != es['error']
          and 'A11Y_GATE=off' in en['note'] and 'A11Y_GATE=off' in es['note'], (en, es))
    payload = json.dumps({'tool_name': 'Write',
                          'tool_input': {'file_path': 'page.html', 'content': OVERSIZED}})
    code, err = guard_hook(payload)
    check('1d. gate: the hook refuses (exit 2) a save it could not audit',
          code == 2 and 'could not audit' in err and 'Traceback' not in err, (code, err))
    code, err = guard_hook(payload, lang='es')
    check('1e. gate: the hook explains it in Spanish on request',
          code == 2 and 'no pudo auditar' in err, (code, err))
    payload = json.dumps({'tool_name': 'Write',
                          'tool_input': {'file_path': 'page.html', 'content': CLEAN}})
    check('1f. gate: a clean audited save still passes', guard_hook(payload)[0] == 0)
    check('1g. gate: an unreadable payload still fails open (nothing to judge)',
          guard_hook('not json')[0] == 0)
    payload = json.dumps({'tool_name': 'Write',
                          'tool_input': {'file_path': 'page.html', 'content': OVERSIZED}})
    os.environ['A11Y_GATE'] = 'off'
    try:
        bypassed = guard_hook(payload)
    finally:
        del os.environ['A11Y_GATE']
    check('1h. gate: A11Y_GATE=off is the documented way through', bypassed == (0, ''), bypassed)
    with tempfile.TemporaryDirectory() as tmp:
        big = os.path.join(tmp, 'page.html')
        with open(big, 'w', encoding='utf-8') as handle:
            handle.write(OVERSIZED)
        proc = _run(['-m', 'a11y_toolkit.a11ygate', '--file', big])
        out = json.loads(proc.stdout)
        check('1i. gate CLI: decision `error`, exit 1, JSON on stdout',
              proc.returncode == 1 and out.get('decision') == 'error' and out.get('error')
              and 'Traceback' not in proc.stderr, (proc.returncode, proc.stdout[:200]))


# ── 2. autofix propagates the audit error ───────────────────────────────────
@section
def autofix_propagates_the_audit_error():
    res = autofix(OVERSIZED)
    check('2a. autofix: the audit error travels in the result',
          isinstance(res, dict) and 'HTML larger than 3 MB' in (res.get('error') or '')
          and res.get('fixed_html'), res.get('error'))
    built = a11ypatches.build(OVERSIZED)
    check('2b. patches: no sealed record from a failed audit',
          built.get('error') and not built.get('patch_set'), built.get('error'))
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, 'in.html'), os.path.join(tmp, 'out.html')
        with open(src, 'w', encoding='utf-8') as handle:
            handle.write(OVERSIZED)
        proc = _run(['-m', 'a11y_toolkit.a11y', 'fix', '--file', src, '-o', dst])
        out = json.loads(proc.stdout)
        check('2c. fix CLI: exit 1 with the error in the JSON (the fixes are still written)',
              proc.returncode == 1 and 'error' in out and os.path.exists(dst)
              and 'Traceback' not in proc.stderr, (proc.returncode, proc.stdout[:200]))
        clean = os.path.join(tmp, 'clean.html')
        with open(clean, 'w', encoding='utf-8') as handle:
            handle.write(CLEAN)
        proc = _run(['-m', 'a11y_toolkit.a11y', 'fix', '--file', clean, '-o', dst])
        out = json.loads(proc.stdout)
        check('2d. fix CLI: a normal page keeps exit 0 and no error key',
              proc.returncode == 0 and 'error' not in out, (proc.returncode, proc.stdout[:200]))


# ── 3. slow but complete body ───────────────────────────────────────────────
@section
def slow_but_complete_body_is_measured():
    started = time.monotonic()
    report = audit_url(BASE_URL + '/slow', timeout=2)
    elapsed = time.monotonic() - started
    check('3a. a complete body that takes longer than the read window is audited',
          'error' not in report and any(h['signal'] == 'img_no_alt' for h in report.get('findings', []))
          and elapsed >= 5, (report.get('error'), round(elapsed, 1)))
    broken = audit_url(BASE_URL + '/truncated', timeout=2)
    check('3b. a truncated body is still an error',
          'Incomplete HTTP response' in (broken.get('error') or ''), broken.get('error'))


# ── 4. failed URLs do not spend the page quota ──────────────────────────────
@section
def failed_urls_do_not_spend_the_page_quota():
    site = audit_site(BASE_URL + '/entry', max_pages=5, from_sitemap=False)
    urls = [page.get('url') for page in site.get('reports', [])]
    check('4a. crawl: two dead links do not cost two pages of a quota of 5',
          site.get('pages') == 5 and len(site.get('page_errors', [])) == 2
          and [url.rsplit('/', 1)[1] for url in urls] == ['entry'] + ['good%d' % n for n in range(1, 5)],
          (site.get('pages'), urls))
    many = audit_site(BASE_URL + '/many', max_pages=2, from_sitemap=False)
    check('4b. crawl: dead links are bounded (twice the quota) and the report says so',
          len(many.get('page_errors', [])) == 4 and many.get('failed_pages_capped') is True
          and many.get('pages') == 1, (len(many.get('page_errors', [])), many.get('pages')))


# ── 5. the budget: stable identity, rendered counts ─────────────────────────
URL = 'https://site/page'


def _anchored(extra=''):
    return ('<html lang="en"><head><title>T</title></head><body><main><h1>T</h1>' + extra
            + '<img id="logo" src="a.png"><img data-testid="hero" src="b.png"></main></body></html>')


def _img_finding(html):
    return next(h for h in _signals(html, URL) if h['signal'] == 'img_no_alt')


@section
def budget_matches_by_stable_identity():
    from a11y_toolkit.a11yaudit import _stable_anchor
    check('5a. engine: stable anchor from id, data-testid and ARIA name',
          [_stable_anchor(a) for a in ({'id': 'buy'}, {'data-testid': 'hero'}, {'aria-label': 'Close'},
                                       {'aria-labelledby': 'lbl'}, {'class': 'x'}, {'id': 'a b'})]
          == ['#buy', '[data-testid="hero"]', '[aria-label="Close"]', '[aria-labelledby="lbl"]',
              None, '[id="a b"]'])
    finding = _img_finding(_anchored())
    check('5b. engine: findings carry the stable path aligned with each positional path',
          finding.get('stable_paths') == ['#logo', '[data-testid="hero"]'] and len(finding['paths']) == 2,
          finding)
    plain = _img_finding('<html lang="en"><body><img src="a.png"></body></html>')
    check('5c. engine: nothing is invented when the element has no stable attribute',
          'stable_paths' not in plain and plain['paths'], plain)
    base = budget_init(audit_html(_anchored(), URL))
    shifted = audit_html(_anchored('<img src="banner.png" alt="Spring collection announced this week">'), URL)
    v = budget_compare(base, shifted)
    check('5d. budget: a sibling inserted in front does not make an old defect new',
          v.get('ok') is True and not v.get('changes'), v)
    grown = budget_compare(base, audit_html(_anchored().replace('</main>', '<img src="c.png"></main>'), URL))
    check('5e. budget: a real new instance is still blocked',
          not grown.get('ok') and grown.get('new_blocking_count') == 1, grown.get('changes'))
    # the banner shifts everything, hero is fixed, a new image without alt appears
    after = _anchored('<img src="banner.png" alt="Spring collection announced this week">')
    after = after.replace('<img data-testid="hero" src="b.png">',
                          '<img src="b.png" alt="The whole team in spring"><img src="c.png">')
    renamed = budget_compare(base, audit_html(after, URL))
    change = next((c for c in renamed.get('changes', []) if c.get('signal') == 'img_no_alt'), {})
    check('5f. budget: a changed identity is reported and the basis says it rested on stable paths',
          not renamed.get('ok') and change.get('new') == 1 and change.get('resolved') == 1
          and change.get('basis') == 'stable-paths', renamed.get('changes'))
    legacy = json.loads(json.dumps(base))
    del legacy['pages'][URL]['findings']['img_no_alt']['anchors']
    check('5g. budget: baselines saved without the new key still compare',
          budget_compare(legacy, audit_html(_anchored(), URL)).get('ok') is True)
    with tempfile.TemporaryDirectory() as tmp:
        bpath, apath = os.path.join(tmp, 'b.json'), os.path.join(tmp, 'a.json')
        _dump(base, bpath)
        _dump(shifted, apath)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = budget_main(['--budget', bpath, '--audit', apath])
    check('5h. budget CLI: the shifted page exits 0', code == 0, buf.getvalue()[:200])


def _rendered(count=None):
    finding = {'severity': 'high', 'criterion': '1.1.1 (WCAG)', 'signal': 'img_no_alt',
               'issue': 'images', 'remediation': 'x',
               'examples': ['a.png', 'b.png', 'c.png', 'd.png', 'e.png', 'f.png']}
    if count is not None:
        finding['count'] = count
    return {'url': URL, 'mode': 'rendered', 'score': 50, 'findings': [finding],
            'color_scheme': 'light', 'authenticated': False, 'browser': 'chromium'}


@section
def budget_counts_rendered_instances():
    grown = budget_compare(budget_init(_rendered(8)), _rendered(11))
    check('5i. budget: a rendered report that carries `count` detects 8 to 11',
          not grown.get('ok') and grown.get('new_blocking_count') == 3, grown)
    same = budget_compare(budget_init(_rendered(11)), _rendered(11))
    check('5j. budget: the same rendered count stays ok', same.get('ok') is True, same)
    blind = budget_compare(budget_init(_rendered()), _rendered())
    check('5k. budget: without `count` the verdict names the signals measured only through examples',
          blind.get('sampled_counts') == ['img_no_alt'] and 'sampled_counts' in blind.get('note', ''),
          blind)
    check('5l. budget: an exact count leaves the sampled list empty', grown.get('sampled_counts') == [])


# ── 6. the budget CLI on unreadable inputs ──────────────────────────────────
@section
def budget_cli_answers_clean_errors():
    report = audit_html(_anchored(), URL)
    with tempfile.TemporaryDirectory() as tmp:
        missing, bad, good = (os.path.join(tmp, name) for name in ('nope.json', 'bad.json', 'good.json'))
        _dump(report, good)
        with open(bad, 'w', encoding='utf-8') as handle:
            handle.write('{"url": ')
        cases = [('6a. budget CLI: --init --audit with a missing file', ['--init', '--audit', missing]),
                 ('6b. budget CLI: --init --audit with broken JSON', ['--init', '--audit', bad]),
                 ('6c. budget CLI: --init-snapshot with a missing file', ['--init-snapshot', missing]),
                 ('6d. budget CLI: --snapshot with a missing budget', ['--budget', missing, '--snapshot', good]),
                 ('6e. budget CLI: compare with a missing report', ['--budget', good, '--audit', missing])]
        for name, argv in cases:
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    code = budget_main(argv)
            except Exception as error:  # noqa: BLE001 — the traceback this test forbids
                check(name, False, type(error).__name__ + ': ' + str(error))
                continue
            out = buf.getvalue()
            parsed = json.loads(out)
            check(name, code == 1 and parsed.get('error'), (code, out[:200]))
        real_stdin, sys.stdin = sys.stdin, io.StringIO('{"elements": ')
        code, out = None, ''
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = budget_main(['--init-snapshot', '-'])
            out = buf.getvalue()
        except Exception as error:  # noqa: BLE001
            out = type(error).__name__ + ': ' + str(error)
        finally:
            sys.stdin = real_stdin
        check('6f. budget CLI: --init-snapshot - with broken stdin JSON',
              code == 1 and '"error"' in out, (code, out[:200]))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = budget_main(['--init', '--audit', good])
        check('6g. budget CLI: a valid --init --audit still exits 0', code == 0, buf.getvalue()[:200])


# ── 7. the bench keeps WCAG 2.2 A/AA only ───────────────────────────────────
_AXE = {'violations': [
    {'id': 'color-contrast-enhanced', 'nodos': 1, 'impacto': 'serious',
     'tags': ['wcag146', 'wcag249', 'wcag411', 'wcag143', 'wcag2aa', 'best-practice']},
    {'id': 'aria-required-parent', 'nodos': 1, 'impacto': 'critical',
     'tags': ['wcag2a', 'wcag131', 'wcag1410']},
]}


@section
def bench_keeps_wcag22_a_aa_only():
    kept = compara.axe_a_criterios(_AXE)
    check('7a. bench: only WCAG 2.2 A and AA criteria reach the comparison',
          set(kept) == {'1.3.1', '1.4.10', '1.4.3'}, kept)
    check('7b. bench: the criteria left out are listed, not hidden',
          compara.axe_out_of_scope(_AXE) == ['1.4.6', '2.4.9', '4.1.1'])


# ── 8. the disprover ────────────────────────────────────────────────────────
def _stored(shift=0, **override):
    finding = {'criterion': '1.1.1 (WCAG)', 'signal': 'img_no_alt', 'severity': 'high',
               'count': 8, 'issue': 'x', 'remediation': 'y',
               'paths': ['html>body>main:nth-of-type(1)>img:nth-of-type(%d)' % n
                         for n in range(1 + shift, 6 + shift)]}
    finding.update(override)
    return finding


@section
def disprover_decides_with_sampled_paths():
    current, historical = _classify_findings([_stored()], [dict(_stored())], 'en')
    check('8a. disprove: 8 instances with 5 stored paths are confirmed',
          current[0].get('status') == 'confirmed' and not historical, (current, historical))
    current, historical = _classify_findings([_stored()], [dict(_stored(1))], 'en')
    check('8b. disprove: the same count on a shifted sample is confirmed',
          current[0].get('status') == 'confirmed' and not historical, (current, historical))
    gone = _stored(count=5)
    other = _stored(count=5, paths=['html>body>footer:nth-of-type(1)>img:nth-of-type(%d)' % n
                                    for n in range(1, 6)])
    current, historical = _classify_findings([gone], [other], 'en')
    check('8c. disprove: complete evidence still rejects a finding whose elements are gone',
          len(historical) == 1 and historical[0].get('status') == 'rejected'
          and current[0].get('status') != 'confirmed', (current, historical))
    numeric = {'criterion': 1.1, 'signal': 'img_no_alt', 'severity': 'high', 'paths': 5, 'count': 8}
    current, historical = _classify_findings([numeric], [dict(_stored())], 'en')
    check('8d. disprove: numeric criterion and paths do not raise',
          len(historical) == 1 and historical[0].get('status') == 'rejected', historical)
    current, historical = _classify_findings([_stored()], [dict(_stored())] * 2, 'en')
    check('8e. disprove: two fresh candidates with the same key stay not-rechecked',
          len(historical) == 1 and historical[0].get('disprover_status') == 'not-rechecked', historical)
    report = audit_html(_EIGHT, BASE_URL + '/eight')
    res = disprove(BASE_URL + '/eight', report=report)
    stale = [h for h in res.get('disprover', {}).get('previous_findings', [])
             if h.get('disprover_status') == 'not-rechecked']
    check('8f. disprove: a live re-check of 8 images decides instead of leaving not-rechecked',
          res.get('disprover', {}).get('executed') is True and not stale
          and res['disprover']['confirmed'] >= 1, (res.get('error'), stale))
    report = {'url': BASE_URL + '/page', 'mode': 'static', 'score': 1,
              'findings': [{'criterion': 1.1, 'severity': 'high', 'signal': 'img_no_alt', 'paths': 5}]}
    res = disprove(BASE_URL + '/page', report=report)
    check('8g. disprove: a live re-check with numeric fields answers instead of raising',
          res.get('disprover', {}).get('executed') is True and res['disprover']['rejected'] == 1,
          res.get('error'))
    res = disprove(BASE_URL + '/page', report={'url': BASE_URL + '/page', 'mode': 'static',
                                                'findings': [5]})
    check('8h. disprove: a findings list that is not a list of findings is an error',
          res.get('error') and res.get('disprover', {}).get('executed') is False, res)


# ── 9. a corrupt DOCX never escapes as a traceback ──────────────────────────
_W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
_DOC = ('<w:document xmlns:w="%s"><w:body>' % _W_NS
        + '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title</w:t></w:r></w:p>'
        + '<w:p><w:r><w:t>Body</w:t></w:r></w:p>'
        + '<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/'
          'drawingml/2006/wordprocessingDrawing"><wp:docPr id="1" name="Picture 1"/>'
          '</wp:inline></w:drawing></w:r></w:p></w:body></w:document>')
_STYLES = ('<w:styles xmlns:w="%s"><w:docDefaults><w:rPrDefault><w:rPr>' % _W_NS
           + '<w:lang w:val="en-US"/></w:rPr></w:rPrDefault></w:docDefaults>'
           + '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
           + '</w:styles>')


def _docx(document=_DOC, styles=_STYLES, compression=zipfile.ZIP_DEFLATED):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression) as archive:
        archive.writestr('[Content_Types].xml',
                         '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive.writestr('word/document.xml', document)
        archive.writestr('word/styles.xml', styles)
    return buf.getvalue()


def _variants():
    good = _docx()
    out = [('empty', b''), ('not-a-zip', b'MZ' + good[2:])]
    size = len(good)
    out += [('truncated-%d' % cut, good[:cut])
            for cut in (size // 5, size // 2, size * 4 // 5, size - 3)]
    rng = random.Random(20261125)
    for index in range(60):
        data = bytearray(good)
        for _ in range(rng.randint(1, 3)):
            data[rng.randrange(size)] ^= 1 << rng.randrange(8)
        out.append(('bitflip-%d' % index, bytes(data)))
    for index in range(12):
        data = bytearray(good)
        start = rng.randrange(max(1, size - 16))
        data[start:start + 16] = bytes(16)
        out.append(('zeroed-%d' % index, bytes(data)))
    bad_parts = [('unknown-encoding', '<?xml version="1.0" encoding="no-such-encoding"?>' + _DOC),
                 ('cut-xml', _DOC[:len(_DOC) // 2]),
                 ('doctype', '<!DOCTYPE d [<!ENTITY e "x">]>' + _DOC),
                 ('unclosed', _DOC + '<w:p>'),
                 ('junk', 'not xml at all'),
                 ('duplicate-namespace', _DOC.replace('<w:document ', '<w:document xmlns:w="%s" ' % _W_NS)),
                 ('bad-number', _DOC.replace('id="1"', 'id="x"'))]
    out += [('document-' + name, _docx(document=part)) for name, part in bad_parts]
    out += [('styles-' + name, _docx(styles=part)) for name, part in bad_parts]
    # stored (uncompressed) member whose bytes are edited in place
    stored = bytearray(_docx(compression=zipfile.ZIP_STORED))
    start = stored.index(b'<w:document')
    stored[start + 60] = 0x3C
    out.append(('stored-member-corrupt', bytes(stored)))
    # compression method 99 exists in no decoder
    data = bytearray(good)
    data[8:10] = (99).to_bytes(2, 'little')
    out.append(('unknown-compression-local', bytes(data)))
    end = data.index(b'PK\x05\x06')
    central = data.index(b'PK\x01\x02')
    data[central + 10:central + 12] = (99).to_bytes(2, 'little')
    out.append(('unknown-compression-central', bytes(data[:end + 22])))
    # end of the central directory lost
    data = bytearray(good)
    data[data.index(b'PK\x05\x06'):data.index(b'PK\x05\x06') + 4] = b'XXXX'
    out.append(('central-directory-lost', bytes(data)))
    return out


@section
def corrupt_docx_never_tracebacks():
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, 'corrupt.docx')
        with open(os.path.join(tmp, 'ok.docx'), 'wb') as handle:
            handle.write(_docx())
        sane = docx_screen(os.path.join(tmp, 'ok.docx'))
        check('9-pre. the generated DOCX is a real document (image without alt is found)',
              'error' not in sane and 'docx_no_alt' in {h['signal'] for h in sane['findings']}, sane)
        variants = _variants()
        raised, errors = [], 0
        for name, data in variants:
            with open(target, 'wb') as handle:
                handle.write(data)
            try:
                out = docx_screen(target)
            except Exception as error:  # noqa: BLE001 — exactly what must not happen
                raised.append((name, type(error).__name__))
                continue
            well_formed = (isinstance(out, dict) and out.get('mode') == 'docx'
                           and (out.get('error') or isinstance(out.get('findings'), list)))
            if not well_formed:
                raised.append((name, 'malformed result ' + repr(out)[:80]))
            elif out.get('error'):
                errors += 1
                # keep the FIRST corrupt sample that answered with an error
                if errors == 1:
                    with open(os.path.join(tmp, 'sample.docx'), 'wb') as handle:
                        handle.write(data)
        check('9a. docx: %d corrupt variants, not one traceback' % len(variants),
              not raised, raised[:12])
        check('9b. docx: the corrupt ones answer with the promised error', errors >= 25, errors)
        proc = _run(['-m', 'a11y_toolkit.a11ydocx', os.path.join(tmp, 'sample.docx')])
        parsed = json.loads(proc.stdout)
        check('9c. docx CLI: JSON with `error` on stdout, exit 1, no traceback on stderr',
              proc.returncode == 1 and parsed.get('error') and parsed.get('mode') == 'docx'
              and 'Traceback' not in proc.stderr, (proc.returncode, proc.stdout[:200], proc.stderr[:200]))


_http.shutdown()
fails = [name for name, ok in results if not ok]
print('\n%d/%d checks' % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)
