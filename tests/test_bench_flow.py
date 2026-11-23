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
    def do_GET(self):
        path = os.path.join(_D, 'index.html')
        if not os.path.exists(path):
            self.send_error(404)
            return
        with open(path, 'rb') as f:
            body = f.read()
        self.send_response(200)
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
finally:
    compara.axe_en_pagina = _real_axe
assert _seen == ['Bench'], _seen
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
    assert compara.problems([_both], expected=1, min_signals=0) == []
    print('2. compara: toolkit y axe devuelven resultados de verdad ✓')
else:
    print('2. compara con axe real: SKIP (sin axe.min.js local ni en caché)')

# ── 3. el gate: una fila solo es evidencia con los tres motores ───────────────
_good = {'url': 'u', 'engines': {'toolkit_static': 'ok', 'toolkit_rendered': 'ok', 'axe': 'ok'},
         'toolkit': {'criterios': ['1.1.1'] * 5},
         'axe': {'violaciones': [], 'criterios': [], 'rules_inapplicable': 60}}
assert compara.problems([_good], expected=1) == []
assert compara.problems([dict(_good, engines=None)]) == [
    'u: no results from toolkit_static', 'u: no results from toolkit_rendered',
    'u: no results from axe']
assert compara.problems([dict(_good, axe={'violaciones': [], 'criterios': []})]) == [
    'u: axe executed no rules']
assert compara.problems([dict(_good, engines={'toolkit_static': 'ok', 'axe': 'ok'})]) == [
    'u: no results from toolkit_rendered']
assert compara.problems([{'url': 'u', 'failed': True, 'error': 'boom'}], min_signals=0) == [
    'u: run failed: boom']
assert compara.problems([_good], expected=4) == ['expected 4 results, got 1']
assert compara.problems([dict(_good, toolkit={'criterios': ['1.1.1']})]) == [
    'toolkit found almost nothing (1 criteria) collector regression?']
# --check por CLI sobre un fichero de verdad: verde con filas completas, 1 si no
_p_ok, _p_bad = os.path.join(_D, 'ok.json'), os.path.join(_D, 'bad.json')
for _p, _rows in ((_p_ok, [_good] * 4), (_p_bad, [_good] * 3 + [dict(_good, engines=None)])):
    with open(_p, 'w', encoding='utf-8') as _f:
        json.dump(_rows, _f)


def _cli(mod, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        return mod.main(list(args)), out.getvalue()


assert _cli(compara, '--check', _p_ok, '--expect', '4')[0] == 0
_rc_bad, _out_bad = _cli(compara, '--check', _p_bad, '--expect', '4')
assert _rc_bad == 1 and 'no results from axe' in _out_bad, _out_bad
print('3. gate del benchmark: sin resultados de un motor no hay verde ✓')


# ── 4. pr-flow ────────────────────────────────────────────────────────────────
def _page(imgs, broken):
    return ('<!doctype html><html lang="en"><head><title>t</title></head><body><main><h1>x</h1>'
            + ''.join(f'<img src="p{i}.png"{"" if i in broken else " alt=\"pic\""}>'
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

# 4d. un hallazgo NUEVO por debajo del tope se localiza
rc, r = _run(F['clean'], F['new1'])
assert rc == 0 and r['new_per_tool'] == {'toolkit_static': 1}, r['summary']
assert r['tools']['toolkit_static']['new'][0][2].endswith('img:nth-of-type(3)')

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
print('4. pr-flow estático: 6→7 declarada, traslado por elemento, error = exit 1 ✓')

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
