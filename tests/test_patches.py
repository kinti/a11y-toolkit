#!/usr/bin/env python3
"""a11y_patches: the sealed record of an autofix run.

Contract: sha-keyed (a set never blind-applies to another page), deterministic
reproduction verified patch-for-patch, tampering detected, declined fixes in
the record, bilingual notes, hostile HTML never crashes."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit.a11ypatches import build, apply_patches, FORMAT  # noqa: E402
from a11y_toolkit import server  # noqa: E402

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(('ok  ' if cond else 'FAIL') + ' ' + name)


HTML_BAD = ('<html lang="es"><head>'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0, '
            'maximum-scale=1.0, user-scalable=no">'
            '<title>OK</title></head><body><p>Hola</p></body></html>')
HTML_OTHER = '<html lang="es"><head><title>Otra</title></head><body><p>Distinta</p></body></html>'

# ── build: the sealed record matches the run ────────────────────────────────
b = build(HTML_BAD)
ps = b['patch_set']
check('format sealed as a11y-patches/1', ps['format'] == FORMAT)
check('source sha present and 64-hex', len(ps['source_sha256']) == 64
      and all(c in '0123456789abcdef' for c in ps['source_sha256']))
check('engine version stamped', bool(ps['engine_version']))
check('created_at iso', 'T' in ps['created_at'])
check('count equals fixes', ps['count'] == len(ps['fixes']) >= 1)
check('viewport fix recorded with criterion',
      any('zoom_no' == f['signal'] and '1.4.4' in f['fix'] for f in ps['fixes']))

# ── verify: same page reproduces exactly ────────────────────────────────────
v = apply_patches(HTML_BAD, ps)
check('same page → reproduced', v['status'] == 'reproduced')
check('reproduced returns fixed html', b['fixed_html'] == v['fixed_html'])

# ── verify: another page is stale, never applied ────────────────────────────
v2 = apply_patches(HTML_OTHER, ps)
check('other page → stale', v2['status'] == 'stale')
check('stale carries both shas', v2.get('expected_sha256') == ps['source_sha256']
      and v2.get('source_sha256') != ps['source_sha256'])
check('stale has no fixed_html', 'fixed_html' not in v2)

# ── verify: tampered set → mismatch with both lists ────────────────────────
ps_t = dict(ps)
ps_t['fixes'] = []
v3 = apply_patches(HTML_BAD, ps_t)
check('tampered fixes → mismatch', v3['status'] == 'mismatch'
      and v3.get('recorded') == [] and len(v3.get('reproduced', [])) >= 1)

bad_fmt = {'format': 'other-format/1'}
check('bad format → mismatch', apply_patches(HTML_BAD, bad_fmt)['status'] == 'mismatch')
check('non-dict → mismatch', apply_patches(HTML_BAD, None)['status'] == 'mismatch')

# ── declined fixes travel in the record ────────────────────────────────────
HTML_SOME = ('<html lang="es"><head><title>OK</title></head><body>'
             '<p>Todo bien aqui.</p></body></html>')
b2 = build(HTML_SOME)
check('clean page: zero fixes sealed', b2['patch_set']['count'] == 0
      and b2['patch_set']['fixes'] == [])
check('clean page still verifies', apply_patches(HTML_SOME, b2['patch_set'])['status']
      == 'reproduced')

# ── bilingual notes ──────────────────────────────────────────────────────────
v_es = apply_patches(HTML_OTHER, ps, lang='es')
check('stale note in Spanish', 'invalida' in v_es['note'] or 'no se aplica' in v_es['note'])
en = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'a11y_toolkit', 'locales', 'en.json'),
    encoding='utf-8'))['patches']
es = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'a11y_toolkit', 'locales', 'es.json'),
    encoding='utf-8'))['patches']
check('patches es/en key parity', set(en) == set(es) and len(en) == 4)

# ── hostile HTML never crashes ──────────────────────────────────────────────
ok = True
for hostile in ('<button><button>A', '<html', '<<<>>>', '\x00<meta\x01>\xff', ''):
    try:
        bb = build(hostile)
        apply_patches(hostile, bb['patch_set'])
    except Exception as e:  # noqa: BLE001
        ok = False
        print('   crash:', repr(hostile[:20]), e)
        break
check('hostile HTML never crashes', ok)

# ── sealed params: verify replays the autofix with the BUILD's arguments ────
# (regression: the replay used to run form_errors=False, so every set carrying
#  the form-error layer verified as 'mismatch' — a false tampering accusation)
HTML_FORM = ('<html lang="es"><head><title>OK</title></head><body>'
             '<form><input type="email" required></form></body></html>')
bf = build(HTML_FORM)
psf = bf['patch_set']
check('params sealed in the set', psf.get('params') == {'lang': None, 'title': None,
                                                        'form_errors': True})
check('form layer recorded', any(f['signal'] == 'form_error_missing' for f in psf['fixes']))
vf = apply_patches(HTML_FORM, psf)
check('form set round-trips → reproduced (params sealed)', vf['status'] == 'reproduced')
check('reproduced html matches the build', 'fixed_html' in vf
      and bf['fixed_html'] == vf['fixed_html'])
# a set built with non-default params replays with THOSE params
bf_es = build(HTML_FORM, lang='es', form_errors=False)
check('build with lang/form_errors round-trips',
      apply_patches(HTML_FORM, bf_es['patch_set'])['status'] == 'reproduced')
# tampered params → mismatch (the replay no longer reproduces the fixes)
ps_p = dict(psf)
ps_p['params'] = {'lang': None, 'title': None, 'form_errors': False}
check('tampered params → mismatch', apply_patches(HTML_FORM, ps_p)['status'] == 'mismatch')
# pre-params sets (old format) verify with the build defaults
ps_old = dict(psf)
del ps_old['params']
check('old set without params verifies with build defaults',
      apply_patches(HTML_FORM, ps_old)['status'] == 'reproduced')

# ── MCP surface ──────────────────────────────────────────────────────────────
names = [t['name'] for t in server.TOOLS]
check('tool registered as a11y_patches (#37)', names.count('a11y_patches') == 1
      and len(server.TOOLS) == 37)
resp = server.invoke('a11y_patches', {'html': HTML_BAD})
built_full = json.loads(resp['content'][0]['text'])
built = built_full.get('patch_set') or {}
check('MCP build returns patch_set', built.get('format') == FORMAT
      and built.get('count', 0) >= 1)
check('MCP build also returns the fixed html', bool(built_full.get('fixed_html')))
resp2 = server.invoke('a11y_patches', {'html': HTML_BAD, 'action': 'verify',
                                       'patch_set': built})
check('MCP verify reproduces', json.loads(
    resp2['content'][0]['text'])['status'] == 'reproduced')

fails = [n for n, okc in results if not okc]
print(f"\n{len(results) - len(fails)}/{len(results)} checks")
sys.exit(1 if fails else 0)
