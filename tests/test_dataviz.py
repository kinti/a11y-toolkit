#!/usr/bin/env python3
"""canvas_no_accessible_layer (1.1.1) — the data-viz signal.

Hermetic static checks (audit_html) always run; the rendered judge
(audit_dom on a live canvas) auto-skips without Playwright, same doctrine
as test_dom/test_walk."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yaudit import audit_html  # noqa: E402

BASE = '<html lang="en"><head><title>t</title></head><body>%s</body></html>'


def hits(html):
    r = audit_html(BASE % html)
    return [h for h in r['findings'] if h['signal'] == 'canvas_no_accessible_layer']


# --- 1. bare canvas → medium 1.1.1 with path + examples ---
h = hits('<canvas width="300" height="150"></canvas>')
assert len(h) == 1 and h[0]['severity'] == 'medium' and h[0]['criterion'].startswith('1.1.1')
assert h[0]['paths'] and h[0]['remediation']
print('1. bare canvas → canvas_no_accessible_layer (medium, 1.1.1, path) ✓')

# --- 2. accessible layers present → silent ---
for html in ('<canvas aria-label="Sales chart"></canvas>',
             '<canvas>Quarterly sales as a table below</canvas>',
             '<canvas role="img" aria-label="Trend"></canvas>',
             '<canvas aria-labelledby="cap"></canvas><p id="cap">Chart of Q1-Q4</p>',
             '<canvas title="Chart"></canvas>'):
    assert not hits(html), html
print('2. aria-label / fallback / role=img / labelledby / title → silent ✓')

# --- 3. decorative or hidden → not accused (conservative) ---
for html in ('<canvas role="presentation"></canvas>',
             '<canvas role="none"></canvas>',
             '<canvas aria-hidden="true"></canvas>'):
    assert not hits(html), html
print('3. presentation / none / aria-hidden → silent ✓')

# --- 4. bilingual: es issue+rem from the twin catalog ---
r = audit_html(BASE % '<canvas></canvas>', lang='es')
h = [x for x in r['findings'] if x['signal'] == 'canvas_no_accessible_layer'][0]
assert 'capa accesible' in h['issue'] and 'rendered' in h['remediation'], h
print('4. es issue/rem gemelos ✓')

# --- 5. svg[role=img] without a name keeps falling into img_no_alt (pinned) ---
r = audit_html(BASE % '<svg role="img"></svg>')
assert any(x['signal'] == 'img_no_alt' for x in r['findings'])
print('5. svg[role=img] sin nombre → img_no_alt (ya cubierto, pinned) ✓')

# --- 6. rendered judge: live canvas (auto-skip without Playwright) ---
try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP rendered canvas: Playwright no instalado')
    sys.exit(0)

from a11y_toolkit.a11ydom import audit_dom_url  # noqa: E402

fixture = os.path.join('/tmp', 'a11y_canvas_fixture.html')
with open(fixture, 'w', encoding='utf-8') as fh:
    fh.write('<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<title>Canvas fixture</title></head><body><main><h1>Charts</h1>'
             '<canvas id="bare" width="300" height="150"></canvas>'
             '<canvas id="named" aria-label="Quarterly sales" width="300" height="150"></canvas>'
             '<canvas id="fb" width="300" height="150">Sales table below</canvas>'
             '<canvas id="hid" aria-hidden="true" width="300" height="150"></canvas>'
             '</main></body></html>')
r = audit_dom_url('file://' + fixture)
chs = [x for x in r['findings'] if x['signal'] == 'canvas_no_accessible_layer']
assert len(chs) == 1 and chs[0]['severity'] == 'high' and 'bare' in chs[0]['examples'][0], chs
assert not [x for x in r['findings'] if x['signal'] == 'img_no_alt']
os.remove(fixture)
print('6. rendered: bare acusa (high), named/fallback/hidden limpios ✓')

print('OK test_dataviz: 6 checks')
