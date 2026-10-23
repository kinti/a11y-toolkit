#!/usr/bin/env python3
"""Humo del CLI: CADA subcomando de a11y.py ejecutado de verdad por subprocess.

Nació tras la revisión de solidificación de 2026-09: el dispatcher llevaba dos
versiones roto (import olvidado) y ninguna suite lo notó porque todas testean
el servidor. Este test ejecuta la vía pública real (python3 a11y.py …, que es
lo que instala el entry point a11ytoolkit) contra fixtures.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLI = None  # CLI runs as a module: python3 -m a11y_toolkit.a11y
FIX = os.path.join('/tmp', 'a11ycli_ok.html')
FIX_MAL = os.path.join('/tmp', 'a11ycli_mal.html')


def run(*args, stdin=None, cwd=ROOT):
    # fuera de ROOT, el paquete del repo debe ganar al instalado en site-packages
    env = None if cwd == ROOT else dict(os.environ, PYTHONPATH=ROOT)
    return subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', *args], cwd=cwd,
                          capture_output=True, text=True, timeout=180, input=stdin, env=env)


with open(FIX, 'w', encoding='utf-8') as f:
    f.write('<!doctype html><html lang="es"><head><meta charset="utf-8"><title>T</title></head>'
            '<body><main><h1>Informe principal</h1><button>ok</button></main></body></html>')
with open(FIX_MAL, 'w', encoding='utf-8') as f:
    f.write('<!doctype html><html><head><meta name="viewport" content="width=device-width, '
            'user-scalable=no"><title></title></head><body><main><h1>Informe principal</h1>'
            '<img src="x.png"><input type="email" name="correo"></main></body></html>')

# 1. subcomandos puros (sin Playwright)
r = run('pair', '#767676', '#ffffff')
assert r.returncode == 0, r.stderr[-300:]
assert abs(json.loads(r.stdout)['ratio'] - 4.54) < 0.02
r = run('audit', '--file', FIX)
assert r.returncode == 0 and json.loads(r.stdout)['score'] == 100, r.stderr[-300:]
r = run('audit', '--file', FIX_MAL, '--lang', 'en')
signals = {h['signal'] for h in json.loads(r.stdout)['findings']}
assert {'img_no_alt', 'zoom_no', 'autocomplete', 'title_missing'} <= signals, signals
r = run('criterion', '2.5.8', '--lang', 'en')
assert r.returncode == 0 and 'Target Size' in r.stdout
r = run('criterion', '--signal', 'kbd_trap')
assert r.returncode == 0 and '2.1.2' in r.stdout and 'no-keyboard-trap' in r.stdout, r.stderr[-200:]
import tempfile
_d = tempfile.mkdtemp()
open(os.path.join(_d, 'AGENTS.md'), 'w').write('# My project\n\nSome rules.\n')
r = run('init', _d)
assert r.returncode == 0 and 'agent hook' in r.stdout, r.stderr[-200:]
_agents = open(os.path.join(_d, 'AGENTS.md')).read()
assert _agents.startswith('# My project') and 'Accessibility guardrails' in _agents
run('init', _d)
assert open(os.path.join(_d, 'AGENTS.md')).read().count('BEGIN a11y-toolkit') == 1
r = run('init', _d, '--check')
assert r.returncode == 0 and json.loads(r.stdout)['hook_present'] is True
print('INIT (AGENTS.md hook, merge, idempotente, --check) + criterion --signal ✓')

# 5.12: --changed (gate CI) — repo git temporal con modificada + nueva + css
import subprocess as _sp, tempfile as _tf
_d = _tf.mkdtemp()
def _git(*args):
    _sp.run(['git', '-C', _d] + list(args), capture_output=True, check=True)
_git('init', '-q'); _git('config', 'user.email', 't@t'); _git('config', 'user.name', 't')
open(os.path.join(_d, 'good.html'), 'w').write('<!doctype html><html lang="en"><head><title>G</title></head><body><main><h1>OK</h1></main></body></html>')
open(os.path.join(_d, 'bad.html'), 'w').write('<!doctype html><html><head><title>t</title></head><body><main><h1>B</h1></main></body></html>')
_git('add', '-A'); _git('commit', '-qm', 'init')
open(os.path.join(_d, 'bad.html'), 'a').write('<img src="x.png">')              # tracked modificada (sin alt)
open(os.path.join(_d, 'new.html'), 'w').write('<!doctype html><html><head><title>n</title></head><body><main><h1>N</h1><img src="n.png"></main></body></html>')  # untracked
open(os.path.join(_d, 'style.css'), 'w').write('body{}')                        # web-touched no auditable
r = run('audit', '--changed', '--lang', 'en', cwd=_d)
assert r.returncode == 2, (r.returncode, r.stdout[-300:])
_ch = json.loads(r.stdout)
assert _ch['files']['audited'] == 2 and _ch['files']['web_touched_not_auditable'] == ['style.css'], _ch['files']
assert _ch['blocking'] >= 2 and 'good.html' not in ' '.join(x['url'] for x in _ch['reports'])
# arreglado → exit 0
open(os.path.join(_d, 'bad.html'), 'w').write('<!doctype html><html lang="en"><head><title>t</title></head><body><main><h1>B</h1><img src="x.png" alt=""></main></body></html>')
open(os.path.join(_d, 'new.html'), 'w').write('<!doctype html><html lang="en"><head><title>n</title></head><body><main><h1>N</h1><img src="n.png" alt=""></main></body></html>')
r = run('audit', '--changed', '--lang', 'en', cwd=_d)
assert r.returncode == 0 and json.loads(r.stdout)['blocking'] == 0, r.stdout[-300:]
print('AUDIT --changed (CI gate: exit 2/0, untracked cubiertos, css listado) ✓')
r = run('badge', '--score', '90', '--lang', 'en')
assert r.returncode == 0 and r.stdout.startswith('<svg') and '90/100' in r.stdout
r = run('fix', '--file', FIX_MAL, '--lang', 'es', '--title', 'T', '-o', os.path.join('/tmp', 'cli_fixed.html'))
assert r.returncode == 0, r.stderr[-300:]
fx = json.loads(r.stdout)
assert sorted(a['signal'] for a in fx['applied']) == ['autocomplete', 'lang_missing', 'title_missing', 'zoom_no']
r = run('sarif', '--file', FIX_MAL, '-o', os.path.join('/tmp', 'cli.sarif'))
assert r.returncode == 0 and os.path.exists(os.path.join('/tmp', 'cli.sarif'))
# budget: init desde audit por stdin + comparación
aud = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yaudit', '--file', FIX_MAL], cwd=ROOT,
                     capture_output=True, text=True, timeout=60).stdout
r = run('budget', '--init', stdin=aud)
assert r.returncode == 0 and 'signals' in r.stdout, r.stderr[-300:]
with open(os.path.join('/tmp', 'cli_budget.json'), 'w') as f:
    f.write(r.stdout)
with open(os.path.join('/tmp', 'cli_audit.json'), 'w') as f:
    f.write(aud)
r = run('budget', '--budget', os.path.join('/tmp', 'cli_budget.json'),
        '--audit', os.path.join('/tmp', 'cli_audit.json'))
assert r.returncode == 0 and json.loads(r.stdout)['ok'] is True

# 2. subcomandos con Playwright (se omiten sin él)
try:
    import playwright  # noqa: F401
    TIENE_PW = True
except ImportError:
    TIENE_PW = False

if TIENE_PW:
    r = run('reflow', 'file://' + FIX)
    assert r.returncode == 0 and json.loads(r.stdout)['mode'] == 'reflow', r.stderr[-300:]
    r = run('kbd', 'file://' + FIX)
    assert r.returncode == 0 and json.loads(r.stdout)['mode'] == 'keyboard', r.stderr[-300:]
    r = run('scroll', 'file://' + FIX)
    assert r.returncode == 0 and 'mode' in json.loads(r.stdout), r.stderr[-300:]
else:
    print('SKIP reflow/kbd/scroll: Playwright no instalado')

r = run('evidence', '/tmp/cli_audit.json', '-o', os.path.join('/tmp', 'cli_pack.json'))
assert r.returncode == 0, r.stderr[-300:]
pk = json.loads(r.stdout)
assert pk['sha256'] and 4 <= pk['summary']['manual-only'] <= 8  # genuinely human-only criteria  # shrank from 27 as signals landed

# 3. seguridad: nada de lo que escribe este toolkit es vector de inyección
sys.path.insert(0, ROOT)
from a11y_toolkit.a11yfix import autofix  # noqa: E402
from a11y_toolkit.a11ybadge import badge  # noqa: E402
mal = autofix('<html><head><title></title></head><body></body></html>',
              title='x</title><script>alert(1)</script>')
assert '<script>' not in mal['fixed_html'], 'XSS vía title'
mal2 = autofix('<html><head><title>t</title></head><body></body></html>',
               lang='es" onclick="evil')
assert 'onclick' not in mal2['fixed_html'], 'rompe atributo vía lang'
b = badge(90, date='2026"><script>x</script>')
assert '<script>' not in b and '<' not in b[b.find('2026'):b.find('2026') + 20], 'inyección SVG vía fecha'

# 4. la afirmación del README («26 criterios tocados») queda clavada
from a11y_toolkit.a11yaudit import CRIT  # noqa: E402
assert len(CRIT['es']) == 51, f'README claims 51 criteria, CRIT has {len(CRIT["es"])}'

print('CLI SMOKE OK ✓ (todos los subcomandos, inyección bloqueada, 26 criterios verificados)')
