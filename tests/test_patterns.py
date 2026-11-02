#!/usr/bin/env python3
"""a11y_patterns — APG keyboard contracts (dialog / tablist / disclosure),
tested live against correct + broken fixtures. Auto-skips without Playwright
(same doctrine as test_dom/test_walk)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_patterns: Playwright no instalado')
    sys.exit(0)

from a11y_toolkit.a11ypatterns import audit_patterns  # noqa: E402

GOOD = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Good</title></head><body><main>
<div role="dialog" aria-modal="true" aria-label="Confirm" id="dlg">
  <p>Proceed?</p><button>Yes</button><button>No</button>
</div>
<div role="tablist" id="tl">
  <button role="tab" aria-selected="true" tabindex="0">One</button>
  <button role="tab" aria-selected="false" tabindex="-1">Two</button>
  <button role="tab" aria-selected="false" tabindex="-1">Three</button>
</div>
<button aria-expanded="false" aria-controls="panel" id="disc">Details</button>
<div id="panel" hidden>Panel content</div>
<script>
const dlg = document.getElementById('dlg');
dlg.addEventListener('keydown', e => { if (e.key === 'Escape') dlg.remove(); });
const tl = [...document.querySelectorAll('#tl [role="tab"]')];
tl.forEach((t, i) => t.addEventListener('keydown', e => {
  let j = null;
  if (e.key === 'ArrowRight') j = Math.min(tl.length - 1, i + 1);
  if (e.key === 'ArrowLeft') j = Math.max(0, i - 1);
  if (j !== null) { tl[j].focus(); tl[j].setAttribute('aria-selected', 'true');
    t.setAttribute('aria-selected', 'false'); e.preventDefault(); }
}));
document.getElementById('disc').addEventListener('click', function () {
  const open = this.getAttribute('aria-expanded') === 'true';
  this.setAttribute('aria-expanded', String(!open));
  document.getElementById('panel').hidden = open;
});
</script></main></body></html>'''

BROKEN = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Broken</title></head><body>
<a href="#bg">Background link</a>
<main>
<div role="dialog" aria-modal="true" aria-label="Confirm">
  <p>Proceed?</p><button>Yes</button><button>No</button>
</div>
<div role="tablist" id="tl">
  <button role="tab" aria-selected="true" tabindex="0">One</button>
  <button role="tab" aria-selected="false" tabindex="-1">Two</button>
  <button role="tab" aria-selected="false" tabindex="-1">Three</button>
</div>
<button aria-expanded="false" id="disc">Details</button>
<script>
document.querySelector('[role=dialog]').addEventListener('cancel', e => e.preventDefault());
document.querySelector('[role=dialog]').addEventListener('keydown', e => e.stopPropagation());
document.getElementById('disc').addEventListener('click', e => e.preventDefault());
</script></main></body></html>'''

d = '/tmp/a11y_patterns_fixture'
os.makedirs(d, exist_ok=True)
for name, html in (('good.html', GOOD), ('broken.html', BROKEN)):
    with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
        fh.write(html)

# --- 1. correct widget contracts → clean pass, patterns counted ---
g = audit_patterns('file://' + os.path.join(d, 'good.html'))
assert 'error' not in g, g
assert g['patterns_seen'] == {'dialog': 1, 'tablist': 1, 'tabs': 3, 'disclosure': 1}, g['patterns_seen']
assert g['findings'] == [], g['findings']
print('1. contratos correctos → pase limpio (dialog+tablist+3 tabs+disclosure) ✓')

# --- 2. broken contracts → the three findings, right criteria ---
b = audit_patterns('file://' + os.path.join(d, 'broken.html'))
sigs = {f['signal']: f for f in b['findings']}
assert 'pattern_dialog_esc_no_close' in sigs, sigs
assert sigs['pattern_dialog_esc_no_close']['criterion'].startswith('2.1.2')
assert sigs['pattern_dialog_esc_no_close']['severity'] == 'high'
assert 'pattern_tabs_arrows_dead' in sigs, sigs
assert sigs['pattern_tabs_arrows_dead']['criterion'].startswith('2.1.1')
assert 'pattern_disclosure_state_frozen' in sigs, sigs
assert sigs['pattern_disclosure_state_frozen']['criterion'].startswith('4.1.2')
assert sigs['pattern_disclosure_state_frozen']['remediation']
print('2. contratos rotos → 3 hallazgos pattern_* con criterio y remedio ✓')

# --- 3. bilingual twins: es catalog serves the same signals clean ---
ge = audit_patterns('file://' + os.path.join(d, 'good.html'), lang='es')
assert ge['findings'] == []
be = audit_patterns('file://' + os.path.join(d, 'broken.html'), lang='es')
sigs_es = {f['signal'] for f in be['findings']}
assert sigs_es == set(sigs)
assert all('diálogo' in f['issue'] or 'tablist' in f['issue'] or 'aria-expanded' in f['issue']
           for f in be['findings'])
print('3. bilingüe: mismas señales, catálogo es ✓')

# --- 4. honest limits declared ---
assert 'VISIBLE at page load' in g['limits'] and 'future operators' in g['limits']
print('4. límites honestos declarados ✓')

print('OK test_patterns: 4 checks')
