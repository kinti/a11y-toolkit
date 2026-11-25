#!/usr/bin/env python3
"""bench/compara.py and bench/pr-flow.py: the two comparators must measure
for real, under the engine's DEFAULT browser configuration.

compara(): the monthly benchmark. The rendered audit leaves the engine's
browser pool alive (a Playwright driver with its own asyncio loop in this
thread); the bench used to open a second sync session for axe and died with
"Sync API inside the asyncio loop". The workflow ran exactly that
configuration, so the monthly run could only pass with A11Y_BROWSER_POOL=0.
A row is evidence only with results from the three engines: --check enforces
it (the old gate looked at the toolkit alone).

pr-flow.py: a regression harness that reports zero new findings when a page
went from 6 to 7 images without alt is not measuring. Instances are compared
by element, axe by failing node, a finding past the report's carried cap is
declared insufficient evidence with its count delta, and a pass that fails
is an error with exit 1, never "zero findings".

Without Playwright the whole file is skipped (same as dom/scroll). The
axe-core part needs a local copy (bench/axe.min.js or the user cache the
monthly benchmark fills) and is skipped with a notice otherwise; the part
that pins the pool bug needs no axe at all.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_bench_flow: sin Playwright (como dom y scroll)')
    sys.exit(0)

# el pool por defecto es justo el que fallaba: este archivo no admite que la
# variable de entorno lo apague
os.environ.pop('A11Y_BROWSER_POOL', None)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'bench', f'{name}.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


compara = _load('compara')
pr_flow = _load('pr-flow')
assert compara.browser is pr_flow.browser, 'los dos scripts deben compartir bench/browser.py'
assert os.path.dirname(compara.browser.__file__) == os.path.join(ROOT, 'bench')

# ── página local: una imagen sin alt (la ven los dos motores), título y lang ──
_D = tempfile.mkdtemp()
_PAGE = ('<!doctype html><html lang="en"><head><title>Bench</title></head><body>'
         '<header><a href="/">Home</a></header><main id="c"><h1>One</h1>'
         '<img src="a.png"><p>hello</p></main></body></html>')
with open(os.path.join(_D, 'index.html'), 'w', encoding='utf-8') as _f:
    _f.write(_PAGE)


class _H(BaseHTTPRequestHandler):
    """index.html para cualquier ruta, salvo dos que solo cambian para
    Chromium y solo a partir de su SEGUNDA navegación (la primera es el pase
    renderizado del toolkit; la segunda, la carga de axe): /flip.html responde
    404 y /jump.html redirige a index.html. Así los dos pases del toolkit
    reciben la página buena y solo la carga de axe recibe otra cosa."""
    _navegaciones = {'/flip.html': 0, '/jump.html': 0}

    def do_GET(self):
        with open(os.path.join(_D, 'index.html'), 'rb') as f:
            body = f.read()
        status, location = 200, None
        es_chromium = 'Chrome' in self.headers.get('User-Agent', '')
        if self.path == '/split.html' and not es_chromium:
            status, location = 302, '/index.html'
        if self.path == '/crawl.html':
            body = (b'<!doctype html><html lang="en"><head><title>Fixture</title></head>'
                    b'<body><a href="/outage.html">Page</a></body></html>')
        if self.path == '/outage.html':
            status = 503
        if self.path == '/asset.html':
            body = (b'<!doctype html><html lang="en"><head><title>Fixture</title></head>'
                    b'<body><main><img src="/outage.html" alt="Fixture"></main></body></html>')
        if self.path == '/account.html':
            account = b'<img src="/picture.png">' if 'qa_session=fixture' in self.headers.get('Cookie', '') \
                else b'<p>Sign in to continue</p>'
            body = (b'<!doctype html><html lang="en"><head><title>Fixture</title></head>'
                    b'<body><main><h1>Account</h1>' + account + b'</main></body></html>')
        if es_chromium and self.path in self._navegaciones:
            self._navegaciones[self.path] += 1
            if self._navegaciones[self.path] >= 2:       # la 2ª navegación ya es la de axe
                if self.path == '/flip.html':
                    status = 404
                else:
                    status, location = 302, '/index.html'
        self.send_response(status)
        if location:
            self.send_header('Location', location)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


_srv = HTTPServer(('127.0.0.1', 0), _H)
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{_srv.server_port}/index.html'
_HAS_AXE = compara.browser.axe_file() is not None
_real_axe = compara.axe_en_pagina

# ── 1. el préstamo de página tras el pase renderizado (sin axe: la causa) ─────
# Antes: sync_playwright() propio después de audit_dom_url → «Sync API inside
# the asyncio loop» y la fila salía como fallida con la configuración por defecto
_seen = []
compara.axe_en_pagina = lambda page, axe_js=None: (_seen.append(page.title()), {
    'violations': [], 'inapplicable_count': 0})[1]
try:
    _row = compara.compara(URL)
    _sample_findings = [{'criterion': '1.4.1 Use of Color'}, {'criterion': '1.4.10 Reflow'}]
    with patch.object(compara, 'audit_url', return_value={'url': URL, 'findings': _sample_findings}):
        _detail = compara.compara(URL)['divergencias_detalle']['solo_toolkit']
    assert _detail['1.4.1'] == [_sample_findings[0]], _detail
    assert _sample_findings[1] in _detail['1.4.10'], _detail
finally:
    compara.axe_en_pagina = _real_axe
assert _seen == ['Bench', 'Bench'], _seen
assert _row['engines'] == {'toolkit_static': 'ok', 'toolkit_rendered': 'ok', 'axe': 'ok'}
assert _row['toolkit']['criterios'], _row['toolkit']
print('1. compara con el pool por defecto: página prestada, fila completa ✓')

# ── 2. los DOS motores encuentran la imagen sin alt (necesita axe local) ──────
if _HAS_AXE:
    _both = compara.compara(URL)
    assert 'failed' not in _both and _both['engines'] == {'toolkit_static': 'ok',
                                                          'toolkit_rendered': 'ok', 'axe': 'ok'}
    assert '1.1.1' in _both['toolkit']['criterios'], _both['toolkit']
    assert '1.1.1' in _both['axe']['criterios'], _both['axe']
    assert '1.1.1' in _both['coinciden'], _both
    assert _both['axe']['rules_inapplicable'] > 0, 'axe no llegó a ejecutar sus reglas'
    assert _both['axe']['http_status'] == 200, _both['axe']
    assert _both['axe']['url_final'] == _both['toolkit']['url_final'] == URL, _both
    assert compara.problems([_both], expected=1, min_signals=0) == []
    print('2. compara: toolkit y axe devuelven resultados de verdad sobre la misma página ✓')
else:
    print('2. compara con axe real: SKIP (sin axe.min.js local ni en caché)')

# ── 2b. la carga de axe tiene que ser LA MISMA página y una respuesta sana ────
# Antes: con 200 para los dos pases del toolkit y un 404 en la carga de axe,
# la fila salía con los tres motores «ok» y --check la daba por buena (axe
# aportaba los criterios de la página de error). No hace falta axe real: el
# problema se detecta ANTES de ejecutarlo, que es lo que el espía demuestra
_base = URL.rsplit('/', 1)[0]
_axe_espia_llamadas = []


def _axe_espia(page, axe_js=None):
    _axe_espia_llamadas.append(page.url)
    return {'violations': [], 'inapplicable_count': 0}


compara.axe_en_pagina = _axe_espia
try:
    for _ruta, _texto in ((f'{_base}/flip.html', 'axe cargó una respuesta HTTP 404'),
                          (f'{_base}/jump.html', 'no es la misma página'),
                          (f'{_base}/split.html', 'estático terminó en')):
        try:
            compara.compara(_ruta)
        except RuntimeError as _e:
            assert _texto in str(_e), (_ruta, _e)
        else:
            raise AssertionError(f'{_ruta}: la fila salió como buena')
    assert _axe_espia_llamadas == [], f'axe corrió sobre otra página: {_axe_espia_llamadas}'
finally:
    compara.axe_en_pagina = _real_axe
# por la CLI la fila viaja como fallida y el exit code dice la verdad (el
# contador del servidor se reinicia para repetir el escenario desde el principio)
_H._navegaciones['/flip.html'] = 0
_out = io.StringIO()
with contextlib.redirect_stdout(_out), contextlib.redirect_stderr(io.StringIO()):
    _rc = compara.main([f'{_base}/flip.html'])
_filas = json.loads(_out.getvalue())
assert _rc == 1 and _filas[0]['failed'] \
    and 'axe cargó una respuesta HTTP 404' in _filas[0]['error'], (_rc, _filas[0])
print('2b. la carga de axe con un 404 o con otra página final: fila rechazada ✓')

# ── 3. el gate: una fila solo es evidencia con los tres motores, sobre la
# misma página y con una respuesta sana en la carga de axe ────────────────────
_PAG = 'http://u/p'
_good = {'url': 'http://u/', 'engines': {'toolkit_static': 'ok', 'toolkit_rendered': 'ok', 'axe': 'ok'},
         'toolkit': {'criterios': ['1.1.1', '1.3.1', '1.4.10', '2.4.3'],
                     'url_final_static': _PAG, 'url_final': _PAG},
         'axe': {'violaciones': [], 'criterios': [], 'rules_inapplicable': 60,
                 'http_status': 200, 'url_final': _PAG}}


def _axe(**cambios):
    return dict(_good['axe'], **cambios)


assert compara.problems([_good], expected=1) == []
assert compara.problems([dict(_good, engines=None)]) == [
    'http://u/: no results from toolkit_static', 'http://u/: no results from toolkit_rendered',
    'http://u/: no results from axe']
# el formato anterior a esta comprobación no llevaba estado HTTP ni URL final
assert compara.problems([dict(_good, axe={'violaciones': [], 'criterios': []})]) == [
    'http://u/: axe executed no rules', 'http://u/: axe audited HTTP None, not the requested page',
    'http://u/: toolkit and axe did not audit the same final page']
assert compara.problems([dict(_good, engines={'toolkit_static': 'ok', 'axe': 'ok'})]) == [
    'http://u/: no results from toolkit_rendered']
assert compara.problems([{'url': 'http://u/', 'failed': True, 'error': 'boom'}], min_signals=0) == [
    'http://u/: run failed: boom']
assert compara.problems([_good], expected=4) == ['expected 4 results, got 1']
assert compara.problems([_good, dict(_good, url='http://U:80#section')]) == ['http://U:80#section: duplicate requested page']
assert compara.problems([_good, dict(_good, url='http://alias/')]) == [
    'http://alias/: reached the same final page as http://u/']
assert compara.problems([dict(_good, toolkit=dict(_good['toolkit'], criterios=['1.1.1'] * 5))]) == [
    'toolkit found almost nothing (1 criteria) collector regression?']
assert compara.problems([None], min_signals=0) == ['row 1: result must be a JSON object']
assert compara.problems([dict(_good, axe=['invalid'])], min_signals=0) == [
    'http://u/: engine results must be JSON objects']
assert compara.problems([dict(_good, toolkit={'criterios': ['1.1.1']})]) == [
    'http://u/: toolkit and axe did not audit the same final page',
    'toolkit found almost nothing (1 criteria) collector regression?']
# axe sobre una respuesta de error, aunque el navegador la haya cargado bien
for _st in (404, 500, None, '200', True):
    assert compara.problems([dict(_good, axe=_axe(http_status=_st))], min_signals=0) == [
        'http://u/: axe audited HTTP %s, not the requested page' % _st], _st
# axe sobre otra página que el toolkit
assert compara.problems([dict(_good, axe=_axe(url_final='http://u/otra'))], min_signals=0) == [
    'http://u/: toolkit and axe did not audit the same final page']
assert compara.problems([dict(_good, toolkit=dict(_good['toolkit'], url_final_static='http://u/otra'))]) == [
    'http://u/: toolkit and axe did not audit the same final page']
_tagged = {'violations': [
    {'id': 'aria-required-parent', 'nodos': 1, 'impacto': 'critical',
     'tags': ['wcag2a', 'wcag131', 'wcag1410']},
    {'id': 'region', 'nodos': 1, 'impacto': 'moderate', 'tags': ['best-practice']},
]}
assert set(compara.axe_a_criterios(_tagged)) == {'1.3.1', '1.4.10'}
assert compara.problems([dict(_good, toolkit={'criterios': ['1.1.1'] * 5})], min_signals=0) == [
    'http://u/: toolkit and axe did not audit the same final page']
# --check por CLI sobre un fichero de verdad: verde con filas completas, 1 si no
_p_ok, _p_bad = os.path.join(_D, 'ok.json'), os.path.join(_D, 'bad.json')
_urls = [f'http://u/{index}' for index in range(4)]
_pages = [dict(_good, url=url,
               toolkit=dict(_good['toolkit'], url_final=url, url_final_static=url),
               axe=_axe(url_final=url)) for url in _urls]
for _p, _rows in ((_p_ok, _pages), (_p_bad, _pages[:3] + [dict(_pages[-1], engines=None)])):
    with open(_p, 'w', encoding='utf-8') as _f:
        json.dump(_rows, _f)


def _cli(mod, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        return mod.main(list(args)), out.getvalue()


assert _cli(compara, '--check', _p_ok, '--expect', '4')[0] == 0
assert _cli(compara, '--check', _p_ok, *_urls)[0] == 0
_rc, _out = _cli(compara, '--check', _p_ok, *_urls[:3], 'http://u/substitute')
assert _rc == 1 and 'missing requested page: http://u/substitute' in _out \
    and 'unexpected requested page: http://u/3' in _out, _out
_rc_bad, _out_bad = _cli(compara, '--check', _p_bad, '--expect', '4')
assert _rc_bad == 1 and 'no results from axe' in _out_bad, _out_bad
print('3. gate del benchmark: sin resultados de un motor no hay verde ✓')

from a11y_toolkit import a11y
from a11y_toolkit.a11yaudit import audit_site
from a11y_toolkit.a11ybudget import compare as budget_compare, init as budget_init
from a11y_toolkit.a11ydisprove import disprove
from a11y_toolkit.a11ydom import audit_dom_url, audit_forms, audit_keyboard, audit_reflow
from a11y_toolkit.a11yevidence import build_pack
from a11y_toolkit.a11yledger import record as ledger_record
_crawl = audit_site(f'{_base}/crawl.html', max_pages=2, from_sitemap=False)
assert _crawl['pages'] == 1 and _crawl['page_errors'][0]['url'] == f'{_base}/outage.html', _crawl
assert '503' in _crawl['page_errors'][0]['error'], _crawl
assert budget_init(_crawl).get('error'), _crawl

_maintenance = f'{_base}/outage.html'
_unavailable = [audit(_maintenance) for audit in (audit_keyboard, audit_reflow, audit_forms)]
assert all(r.get('error') and r.get('http_status') == 503 for r in _unavailable), _unavailable
_sealed = build_pack(_unavailable)
assert all(a['report_status'] == 'failed' for a in _sealed['artifacts'])
assert _sealed['summary']['not-flagged'] == 0, _sealed['summary']
for _tool in ('kbd', 'reflow', 'forms'):
    _status, _body = _cli(a11y, _tool, _maintenance)
    assert _status == 1 and json.loads(_body)['http_status'] == 503, (_status, _body)

_url = f'{_base}/account.html'
_state_path = os.path.join(_D, 'session.json')
with open(_state_path, 'w', encoding='utf-8') as _state_file:
    json.dump({'cookies': [{'name': 'qa_session', 'value': 'fixture', 'domain': '127.0.0.1',
                            'path': '/', 'expires': -1, 'httpOnly': False, 'secure': False,
                            'sameSite': 'Lax'}], 'origins': []}, _state_file)
_authenticated = audit_dom_url(_url, auth_state=_state_path)
_guest = audit_dom_url(_url)
assert _authenticated['score'] == 88 and _guest['score'] == 100
assert _authenticated['authenticated'] and not _guest['authenticated']
assert 'qa_session' not in json.dumps(_authenticated) and _state_path not in json.dumps(_authenticated)
_unverified = disprove(_url, report=_authenticated)
assert not _unverified['disprover']['executed'] and _unverified['score'] == _authenticated['score']
_verified = disprove(_url, report=_authenticated, auth_state=_state_path)
assert _verified['disprover']['confirmed'] == 1 and _verified['score'] == _authenticated['score']
assert 'error' in budget_compare(budget_init(_authenticated), _guest)
_ledger_path = os.path.join(_D, 'account-ledger.json')
assert 'error' not in ledger_record(_url, _authenticated, path=_ledger_path)
with open(_ledger_path, 'rb') as _ledger_file:
    _ledger_original = _ledger_file.read()
assert 'error' in ledger_record(_url, _guest, path=_ledger_path)
with open(_ledger_path, 'rb') as _ledger_file:
    assert _ledger_file.read() == _ledger_original

from a11y_toolkit.a11ytrace import trace, trace_diff
_reference = trace(f'{_base}/crawl.html', steps=1)
_outage = trace(f'{_base}/crawl.html', script=[{'kind': 'click', 'selector': 'a'}])
assert _outage.get('http_status') == 503 and not trace_diff(_reference, _outage)['ok'], _outage
assert 'error' not in trace(f'{_base}/asset.html', steps=1)


# ── 4. pr-flow ────────────────────────────────────────────────────────────────
_ALT = ' alt="pic"'      # fuera de la f-string: una barra dentro de sus llaves
                        # no compila antes de Python 3.12 (el repo promete 3.9+)


def _page(imgs, broken):
    return ('<!doctype html><html lang="en"><head><title>t</title></head><body><main><h1>x</h1>'
            + ''.join(f'<img src="p{i}.png"{"" if i in broken else _ALT}>'
                      for i in range(imgs)) + '</main></body></html>')


def _write(name, html):
    path = os.path.join(_D, name)
    with open(path, 'w', encoding='utf-8') as _f:
        _f.write(html)
    return path


def _run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = pr_flow.main(list(args))
    return rc, json.loads(out.getvalue())


F = {'b6': _write('b6.html', _page(6, range(6))), 'a7': _write('a7.html', _page(7, range(7))),
     'mv_b': _write('mv_b.html', _page(6, {2})), 'mv_a': _write('mv_a.html', _page(6, {5})),
     'clean': _write('clean.html', _page(3, {0})),
     'new1': _write('new1.html', _page(3, {0, 2}))}

# 4a. de 6 a 7 imágenes sin alt: ANTES new=[] (el informe recorta a 5 rutas y
# los dos snapshots eran idénticos). Ahora: 1 nueva sin localizar, por el
# recuento del mensaje, y la señal declarada como evidencia insuficiente
rc, r = _run(F['b6'], F['a7'])
_st = r['tools']['toolkit_static']
assert rc == 0 and r['summary']['failed'] == [], r
assert r['new_per_tool'] == {'toolkit_static': 1}, r['summary']
assert r['summary']['new_unlocated_per_tool'] == {'toolkit_static': 1}
assert r['summary']['inconclusive'] == {'toolkit_static': ['img_no_alt']}
_ev = _st['insufficient_evidence']
assert len(_ev) == 1 and _ev[0]['signal'] == 'img_no_alt', _ev
assert (_ev[0]['carried_before'], _ev[0]['count_before'], _ev[0]['count_after']) == (5, 6, 7)
assert _ev[0]['new'] == 1 and _ev[0]['fixed'] == 0 and _ev[0]['delta_known']

# 4b. fallo trasladado de la imagen 3 a la 6 (mismo recuento): por ELEMENTO
rc, r = _run(F['mv_b'], F['mv_a'])
_st = r['tools']['toolkit_static']
assert rc == 0 and len(_st['new']) == 1 and len(_st['fixed']) == 1 and _st['same'] == 2, _st
assert _st['new'][0][2].endswith('img:nth-of-type(6)') and _st['fixed'][0][2].endswith(
    'img:nth-of-type(3)'), (_st['new'], _st['fixed'])
assert _st['insufficient_evidence'] == [] and r['summary']['inconclusive'] == {}

# 4c. dos snapshots idénticos: cero nuevas, cero arregladas, sin ruido
rc, r = _run(F['clean'], F['clean'])
assert rc == 0 and r['tools']['toolkit_static']['new'] == [] \
    and r['tools']['toolkit_static']['fixed'] == [] and r['summary']['inconclusive'] == {}, r

# 4d. un hallazgo NUEVO por debajo del tope se localiza (y sin «arreglada» fantasma)
rc, r = _run(F['clean'], F['new1'])
assert rc == 0 and r['new_per_tool'] == {'toolkit_static': 1}, r['summary']
assert r['tools']['toolkit_static']['new'][0][2].endswith('img:nth-of-type(3)')
assert r['tools']['toolkit_static']['fixed'] == [], r['tools']['toolkit_static']

# 4g. hallazgos de PÁGINA (van sin elemento: falta el título). ANTES no
# entraban en el diff: una página que perdía el título daba cero nuevas.
# Ahora son UNA instancia propia, en los dos sentidos, y no inventan fantasmas
_CON_T = ('<!doctype html><html lang="en"><head><title>t</title></head>'
          '<body><main><h1>x</h1><p>hi</p></main></body></html>')
_SIN_T = ('<!doctype html><html lang="en"><head></head>'
          '<body><main><h1>x</h1><p>hi</p></main></body></html>')
F['con_t'], F['sin_t'] = _write('con_t.html', _CON_T), _write('sin_t.html', _SIN_T)
rc, r = _run(F['con_t'], F['sin_t'])
_st = r['tools']['toolkit_static']
assert rc == 0 and _st['new'] == [['2.4.2', 'title_missing', None]] and _st['fixed'] == [], _st
assert r['new_per_tool'] == {'toolkit_static': 1}, r['summary']
rc, r = _run(F['sin_t'], F['con_t'])
assert r['tools']['toolkit_static']['fixed'] == [['2.4.2', 'title_missing', None]] \
    and r['tools']['toolkit_static']['new'] == [], r['tools']['toolkit_static']
assert r['summary']['fixed_per_tool'] == {'toolkit_static': 1}, r['summary']
rc, r = _run(F['sin_t'], F['sin_t'])
assert r['tools']['toolkit_static']['new'] == [] and r['tools']['toolkit_static']['fixed'] == [] \
    and r['tools']['toolkit_static']['same'] >= 1, r['tools']['toolkit_static']
# y en el pase renderizado, que re-ejecuta el repertorio estático sobre el DOM vivo
rc, r = _run(F['con_t'], F['sin_t'], '--rendered')
_rt = r['tools']['toolkit_rendered']
assert rc == 0 and 'error' not in _rt and any('title' in x[1] for x in _rt['new']), _rt

# 4e. el pase estático FALLA → error y exit 1 (antes: cero hallazgos y exit 0).
# Ninguna entrada conocida hace caer al motor (red de seguridad
# err_unparseable): se ejercita el mismo camino sustituyendo la función
_real_audit = pr_flow.audit_html
pr_flow.audit_html = lambda *a, **k: {'error': 'boom'}
try:
    rc, r = _run(F['clean'], F['new1'])
finally:
    pr_flow.audit_html = _real_audit
assert rc == 1 and 'boom' in r['tools']['toolkit_static']['error'], (rc, r)
assert r['summary']['failed'] == ['toolkit_static'] and r['new_per_tool'] == {}, r['summary']

# 4f. fichero ilegible: JSON con el error y exit 1 (antes: traza sin salida)
rc, r = _run(os.path.join(_D, 'nope.html'), F['clean'])
assert rc == 1 and 'cannot read' in r['tools']['toolkit_static']['error'], (rc, r)
print('4. pr-flow estático: 6→7 declarada, traslado por elemento, hallazgos de página, error = exit 1 ✓')

# 5. --rendered y --axe con el pool por defecto (antes: traza y sin JSON,
# porque --axe abría su propia sesión de Playwright encima del pool)
rc, r = _run(F['b6'], F['a7'], '--rendered')
assert rc == 0 and 'error' not in r['tools']['toolkit_rendered'], r['tools']
assert r['new_per_tool'] == {'toolkit_static': 1, 'toolkit_rendered': 1}, r['summary']
if _HAS_AXE:
    rc, r = _run(F['mv_b'], F['mv_a'], '--rendered', '--axe')
    assert rc == 0 and r['summary']['failed'] == [] and r['summary']['skipped'] == [], r['summary']
    # axe ANTES devolvía new=[] fixed=[]: comparaba regla + recuento y el
    # traslado conserva los dos. Ahora compara por NODO (regla + selector)
    assert r['tools']['axe']['new'] == [['axe', 'image-alt', '["img[src$=\\"p5.png\\"]"]']], r['tools']['axe']
    assert r['tools']['axe']['fixed'] == [['axe', 'image-alt', '["img[src$=\\"p2.png\\"]"]']]
    assert r['new_per_tool'] == {'toolkit_static': 1, 'toolkit_rendered': 1, 'axe': 1}
    rc, r = _run(F['clean'], F['clean'], '--axe')
    assert rc == 0 and r['tools']['axe']['new'] == [] and r['tools']['axe']['fixed'] == []
    print('5. pr-flow --rendered --axe: sin traza, traslado visible en axe por nodo ✓')
else:
    rc, r = _run(F['mv_b'], F['mv_a'], '--rendered')
    assert rc == 0, r
    print('5. pr-flow --rendered ✓ (parte con axe: SKIP, sin axe.min.js local)')

# 6. sin axe disponible --axe degrada CON AVISO y no cuenta como medido
_v, _c = pr_flow.browser.AXE_VENDORED, pr_flow.browser.AXE_CACHED
pr_flow.browser.AXE_VENDORED = pr_flow.browser.AXE_CACHED = os.path.join(_D, 'no-axe.min.js')
try:
    rc, r = _run(F['mv_b'], F['mv_a'], '--axe')
finally:
    pr_flow.browser.AXE_VENDORED, pr_flow.browser.AXE_CACHED = _v, _c
assert rc == 0 and 'axe-core not found' in r['tools']['axe']['skipped'], r['tools']
assert r['summary']['skipped'] == ['axe'] and r['summary']['failed'] == []
assert r['new_per_tool'] == {'toolkit_static': 1}, r['summary']
print('6. pr-flow sin axe: skipped con aviso, no cuenta como medido ✓')

_srv.shutdown()
print('OK test_bench_flow: los dos comparadores miden con la configuración por defecto')
