#!/usr/bin/env python3
"""ledger recurrence (chronic signals without ML) + evidence --build (sealed
claim→artifact chain). Hermetic: temp ledger files, no network."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yledger import recurrence, record  # noqa: E402
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402

tmp = os.path.join(tempfile.mkdtemp(), 'ledger.json')

# --- 1. empty ledger → honest note, no crash ---
assert recurrence(ledger={'entries': {}})['total_urls'] == 0
print('1. ledger vacío → honesto ✓')

# --- 2. chronic aggregation: a signal active on 2 urls leads ---
record('https://a.example', {'score': 80, 'mode': 'static',
       'findings': [{'signal': 'img_no_alt', 'severity': 'high'}]}, path=tmp)
record('https://b.example', {'score': 90, 'mode': 'rendered',
       'findings': [{'signal': 'img_no_alt', 'severity': 'high'},
                    {'signal': 'kbd_trap', 'severity': 'high'}]}, path=tmp)
rec = recurrence(path=tmp)
chronic = {c['signal']: c for c in rec['signals_chronic']}
assert chronic['img_no_alt']['active_on'] == 2
assert chronic['img_no_alt']['recurring'] is False
assert chronic['kbd_trap']['active_on'] == 1
print('2. crónica: img_no_alt en 2 urls encabeza ✓')

# --- 3. recurring = resolved somewhere AND still active elsewhere ---
record('https://c.example', {'score': 95, 'mode': 'rendered',
       'findings': [{'signal': 'kbd_trap', 'severity': 'high'}]}, path=tmp)
record('https://a.example', {'score': 88, 'mode': 'static', 'findings': []}, path=tmp)
rec = recurrence(path=tmp)
chronic = {c['signal']: c for c in rec['signals_chronic']}
assert chronic['img_no_alt']['recurring'] is True and chronic['img_no_alt']['resolved_on'] == 1
assert chronic['img_no_alt']['active_on'] == 1
print('3. recurring: resuelta en a, activa aún en b ✓')

# --- 4. hot_urls: worst score first (a=88 tras su fix, b=90, c=95) ---
rec = recurrence(path=tmp)
scores = [x['score'] for x in rec['hot_urls']]
assert scores == sorted(scores), scores
assert rec['hot_urls'][0]['url'] == 'https://a.example' and scores[0] == 88
print('4. hot_urls ordenadas por score ascendente ✓')

# --- 5. CLI: ledger recurrence runs ---
from a11y_toolkit.a11yledger import main as ledger_main  # noqa: E402
assert ledger_main(['recurrence', '--ledger', tmp]) == 0
print('5. CLI ledger recurrence ✓')

# --- 6. evidence --build: the build reference is SEALED into the sha ---
rep = {'mode': 'static', 'url': 'https://x', 'score': 90, 'findings': []}
p1 = build_pack([rep], build={'commit': 'abc123'})
p2 = build_pack([rep], build={'commit': 'abc123'})
p3 = build_pack([rep], build={'commit': 'def456'})
p4 = build_pack([rep])
assert p1['build'] == {'commit': 'abc123'}
assert p1['sha256'] == p2['sha256']          # re-emission is stable
assert p1['sha256'] != p3['sha256']          # another build = another seal
assert p4['build'] is None and p1['sha256'] != p4['sha256']
print('6. evidence build sellado en el sha ✓')

# --- 7. CLI: --build plain string and JSON both land ---
from a11y_toolkit.a11yevidence import main as evidence_main  # noqa: E402
repf = os.path.join(tempfile.mkdtemp(), 'r.json')
with open(repf, 'w', encoding='utf-8') as f:
    json.dump(rep, f)
outf = os.path.join(tempfile.mkdtemp(), 'p.json')
assert evidence_main([repf, '--build', 'git:716d870', '-o', outf]) == 0
with open(outf, encoding='utf-8') as f:
    assert json.load(f)['build'] == {'ref': 'git:716d870'}
assert evidence_main([repf, '--build', '{"commit":"abc"}', '-o', outf]) == 0
with open(outf, encoding='utf-8') as f:
    assert json.load(f)['build'] == {'commit': 'abc'}
print('7. CLI --build string/JSON ✓')

# ── 8. (2026-11) resoluciones persistentes: no se evaporan tras un audit
#        limpio adicional — la evidencia de cuándo se arregló sobrevive ──────
from a11y_toolkit.a11yledger import gaps, summary  # noqa: E402

tmp2 = os.path.join(tempfile.mkdtemp(), 'ledger2.json')
FIX_URL = 'https://fix.example'
e1 = record(FIX_URL, {'score': 70, 'mode': 'static',
                      'findings': [{'signal': 'img_no_alt', 'severity': 'high'}]},
            path=tmp2)
e2 = record(FIX_URL, {'score': 100, 'mode': 'static', 'findings': []}, path=tmp2)
assert e2['resolved_signals'] == ['img_no_alt'], e2
_first_date = e2['resolutions']['img_no_alt']['resolved_on']
e3 = record(FIX_URL, {'score': 100, 'mode': 'static', 'findings': []}, path=tmp2)
# ANTES: e3 recalculaba contra e2 (limpio) → resolved_signals vacío y la
# resolución se olvidaba; AHORA persiste con su fecha ORIGINAL
assert e3['resolved_signals'] == ['img_no_alt'], e3
assert e3['resolutions']['img_no_alt']['resolved_on'] == _first_date
assert e3['resolutions']['img_no_alt']['seen_count'] == 2
assert summary(path=tmp2)['total_resolved'] == 1
# y si la señal VUELVE, la resolución caduca (honestidad en los dos sentidos)
e4 = record(FIX_URL, {'score': 70, 'mode': 'static',
                      'findings': [{'signal': 'img_no_alt', 'severity': 'high'}]},
            path=tmp2)
assert e4['resolved_signals'] == [] and e4['active_signals'] == ['img_no_alt']
print('8. resolución persiste con fecha original; recaída la caduca ✓')

# ── 9. (2026-11) gaps sobre URL auditada: el complemento A/AA real ───────────
record(FIX_URL, {'score': 70, 'mode': 'static',
                 'findings': [{'signal': 'img_no_alt', 'severity': 'high'},
                              {'signal': 'kbd_trap', 'severity': 'high'}]},
       path=tmp2)
g = gaps(FIX_URL, path=tmp2)
assert g['status'] == 'audited'
assert g['criteria_with_signal'] == ['1.1.1', '2.1.2'], g
assert isinstance(g['criteria_without_signal'], list) and g['criteria_without_signal']
assert '1.1.1' not in g['criteria_without_signal']      # señalada → cubierta
assert '2.1.2' not in g['criteria_without_signal']
assert '1.4.3' in g['criteria_without_signal']          # nunca señalada → gap
assert len(g['criteria_without_signal']) == 55 - 2      # catálogo A/AA completo
assert 'criteria_without_signal' in g['note']           # documentado en la salida
gn = gaps('https://never.example', path=tmp2)
assert gn['status'] == 'never_audited' and isinstance(gn['criteria_without_signal'], int)
print(f"9. gaps auditada: {len(g['criteria_without_signal'])} criterios sin señal ✓")

print('OK test_recurrence: 9 checks')
