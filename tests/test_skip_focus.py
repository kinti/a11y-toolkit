#!/usr/bin/env python3
"""Rendered 2.4.1 check: a real skip link must land on exposed content.

audit_keyboard activates the first real skip link it finds and reports
`skip_target_hidden` (medium, 2.4.1) only when the target is still not
exposed after activation (display:none, hidden, closed details, aria-hidden
subtree). Focus landing on the target is NOT required: modern browsers move
the sequential-focus start to the fragment target with or without
tabindex="-1", so requiring activeElement==target would fabricate failures
(the tabindex tip is a quality recommendation, not a conformance rule).

The static half (signal map, locale twins) runs without a browser; the
rendered fixtures run only when Playwright is importable, mirroring
tests/test_engines.py and tests/test_tetra_acl.py.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from a11y_toolkit import a11ycrit  # noqa: E402

# ── 1. static: the signal joins the criterion map and the locale twins ─────
assert a11ycrit._SIGNAL_CRIT.get('skip_target_hidden') == '2.4.1', \
    a11ycrit._SIGNAL_CRIT.get('skip_target_hidden')
for lang in ('es', 'en'):
    catalog = json.load(open(os.path.join(
        ROOT, 'a11y_toolkit', 'locales', f'{lang}.json'), encoding='utf-8'))
    dom = catalog['dom']
    assert 'skip_target_hidden' in dom and 'skip_target_hidden_rem' in dom, lang
    assert '{label}' in dom['skip_target_hidden'] and '{id}' in dom['skip_target_hidden'], lang
print('1. estático: señal en el mapa 2.4.1 y gemelas _rem en es/en ✓')

# ── 2. rendered fixtures ────────────────────────────────────────────────────
try:
    import playwright  # noqa: F401 — probe the real dependency, not our wrapper
    from a11y_toolkit import a11ydom
    HAVE_PW = True
except Exception:
    HAVE_PW = False

if not HAVE_PW:
    print('2. SKIP rendered: Playwright no instalado (igual que test_engines)')
else:
    import tempfile
    d = tempfile.mkdtemp(prefix='a11y-skip-')

    def write(name, body):
        path = os.path.join(d, name)
        open(path, 'w', encoding='utf-8').write(body)
        return 'file://' + path

    GOOD = write('good.html', """<!DOCTYPE html><html lang="en"><head><title>good</title>
<style>.skip{position:absolute;left:-9999px}.skip:focus{left:0}</style></head>
<body><header><a class="skip" href="#main">Skip to main content</a>
<nav><a href="/x">nav</a></nav></header>
<main id="main" tabindex="-1"><h1>Hello</h1><p>Real content.</p></main>
</body></html>""")

    BROKEN = write('broken.html', """<!DOCTYPE html><html lang="en"><head><title>broken</title></head>
<body><a href="#main">Skip to main content</a>
<div id="main" style="display:none"><h1>Hidden</h1></div>
</body></html>""")

    COLLAPSED = write('collapsed.html', """<!DOCTYPE html><html lang="en"><head><title>collapsed</title></head>
<body><a href="#main">Skip to main content</a>
<details><summary>More</summary><div id="main"><h1>In details</h1></div></details>
</body></html>""")

    ARIA = write('aria.html', """<!DOCTYPE html><html lang="en"><head><title>aria</title></head>
<body><a href="#main">Skip to main content</a>
<div aria-hidden="true"><div id="main"><h1>Hidden from AT</h1></div></div>
</body></html>""")

    REVEALED = write('revealed.html', """<!DOCTYPE html><html lang="en"><head><title>revealed</title>
<script>window.addEventListener('hashchange', () => {
  const t = document.getElementById('main');
  const d = t.closest('details'); if (d) d.open = true; });</script></head>
<body><a href="#main">Skip to main content</a>
<details><summary>More</summary><div id="main"><h1>In details</h1></div></details>
</body></html>""")

    NONE = write('none.html', """<!DOCTYPE html><html lang="en"><head><title>none</title></head>
<body><a href="#missing">Skip to main content</a>
<a href="#other">read more</a><div id="other"><p>x</p></div>
</body></html>""")

    def findings_of(rep):
        return [(f.get('signal'), f.get('severity'),
                 (f.get('criterion') or '').split(' ')[0]) for f in rep.get('findings', [])]

    kb = a11ydom.audit_keyboard(GOOD, max_steps=20, lang='en')
    assert kb['skip_link']['checked'] == 1, kb['skip_link']
    assert kb['skip_link']['target_exposed'] is True, kb['skip_link']
    assert kb['skip_link']['focus_after'] == 'main#main', kb['skip_link']
    assert 'skip_target_hidden' not in [f[0] for f in findings_of(kb)], findings_of(kb)
    assert kb['score'] == 100, kb['score']
    print('2a. good: expuesto, foco en main#main, score 100 ✓')

    kb = a11ydom.audit_keyboard(BROKEN, max_steps=20, lang='en')
    sig = [(s, sev, c) for (s, sev, c) in findings_of(kb) if s == 'skip_target_hidden']
    assert sig == [('skip_target_hidden', 'medium', '2.4.1')], sig
    assert kb['skip_link']['target_exposed'] is False, kb['skip_link']
    print('2b. broken: hallazgo medium 2.4.1 por destino display:none ✓')

    kb = a11ydom.audit_keyboard(COLLAPSED, max_steps=20, lang='en')
    assert 'skip_target_hidden' not in [f[0] for f in findings_of(kb)], findings_of(kb)
    assert kb['skip_link']['target_exposed'] is True, kb['skip_link']
    print('2c. collapsed: el navegador ABRE el details en la navegación al fragmento, no dispara ✓')

    kb = a11ydom.audit_keyboard(ARIA, max_steps=20, lang='en')
    sig = [(s, sev, c) for (s, sev, c) in findings_of(kb) if s == 'skip_target_hidden']
    assert sig == [('skip_target_hidden', 'medium', '2.4.1')], sig
    print('2d. aria: hallazgo por subárbol aria-hidden (nada perceivable) ✓')

    kb = a11ydom.audit_keyboard(REVEALED, max_steps=20, lang='en')
    assert 'skip_target_hidden' not in [f[0] for f in findings_of(kb)], findings_of(kb)
    assert kb['skip_link']['target_exposed'] is True, kb['skip_link']
    print('2e. revealed: el patrón hashchange-expande NO dispara (recomendación upstream) ✓')

    kb = a11ydom.audit_keyboard(NONE, max_steps=20, lang='en')
    assert kb['skip_link']['checked'] == 0, kb['skip_link']
    assert not findings_of(kb), findings_of(kb)
    print('2f. none: destino inexistente y anchor no-skip no cuentan ✓')

    kb = a11ydom.audit_keyboard(BROKEN, max_steps=20, lang='es')
    assert 'skip link' in json.dumps([f['issue'] for f in kb['findings']]).lower() or \
        kb['findings'], 'falta hallazgo en es'
    assert 'skip link' in kb['limits'].lower(), 'los límites deben mencionar el chequeo'
    print('2g. catálogo es y límites mencionan el chequeo ✓')

print('SKIP-FOCUS OK ✓')
