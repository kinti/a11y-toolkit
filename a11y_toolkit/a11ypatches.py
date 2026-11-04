#!/usr/bin/env python3
"""a11y_patches — the sealed record of an autofix run: what changed, on what
page, reproducible or stale.

The doctrine this serves: fixing the ORIGINAL web is the client's job (their
agent, their CI, their credentials). The engine never touches the real web;
what it hands over is a patch-set — a versioned, sha-keyed artifact listing
the deterministic fixes that were applied to a copy, so anyone can repeat
them upstream and PROVE they did the right thing.

The honesty rules, same as everywhere:
  - A patch-set is keyed by the source page's SHA-256. Hand it a different
    page and it declares itself `stale` — patches never blind-apply.
  - `verify` re-runs the deterministic autofix and cross-checks: same engine,
    same page → the same fixes must reproduce, patch for patch. Anything else
    is reported as a mismatch, never silently accepted.
  - Fixes that autofix declined to apply travel in the set too (`not_applied`),
    so the record matches the run.

Artifact (format a11y-patches/1):
  {'format': 'a11y-patches/1', 'source_sha256': str, 'engine_version': str,
   'created_at': iso8601, 'params': {lang, title, form_errors}, 'count': int,
   'fixes': [{signal, fix}, ...], 'not_applied': [{signal, criterion, ...}]}

`params` are SEALED in the set: `verify` repeats the autofix with exactly the
arguments of the build (an older set without `params` verifies with the build
defaults). Without them, every set carrying the form-error layer verified as
`mismatch` — the replay silently dropped lang/title/form_errors.

CLI:
  a11ytoolkit patches --file page.html -o patches.json          # build
  a11ytoolkit patches --file page.html --verify patches.json    # verify
"""

import argparse
import datetime
import hashlib
import json
import sys

from .a11yfix import autofix as _autofix
from . import a11yi18n

FORMAT = 'a11y-patches/1'

T = a11yi18n.pair('patches')


def _t(lang, key):
    return T.get(lang, T['en']).get(key, key)


def _sha(text):
    return hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()


def build(html_text, lang=None, title=None, form_errors=True):
    """Run the deterministic autofix once; return its sealed patch-set and
    the fixed html. The record is a fact about this run, not a promise."""
    from .server import VERSION   # lazy: server importa este módulo arriba
    res = _autofix(html_text, lang=lang, title=title, form_errors=form_errors)
    patch_set = {
        'format': FORMAT,
        'source_sha256': _sha(html_text),
        'engine_version': VERSION,
        'created_at': datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec='seconds'),
        # params sellados: verify repite el autofix CON ESTOS argumentos
        'params': {'lang': lang, 'title': title, 'form_errors': form_errors},
        'count': len(res['applied']),
        'fixes': res['applied'],
        'not_applied': res['not_applied'],
    }
    return {'patch_set': patch_set, 'fixed_html': res['fixed_html'],
            'result': res}


def apply_patches(html_text, patch_set, lang='en'):
    """Verify-and-repeat: the patch-set is reproduced on the SAME page.

    Returns {'status': 'reproduced'|'stale'|'mismatch', ...}. `stale` means
    the page is not the one the set was built from (sha mismatch) — the set
    invalidates itself rather than blind-applying. `mismatch` means the same
    page no longer produces the same fixes (engine drift or tampered set)."""
    if not isinstance(patch_set, dict) or patch_set.get('format') != FORMAT:
        return {'status': 'mismatch', 'note': _t(lang, 'pat_bad_format')}
    sha = _sha(html_text)
    if sha != patch_set.get('source_sha256'):
        return {'status': 'stale', 'source_sha256': sha,
                'expected_sha256': patch_set.get('source_sha256'),
                'note': _t(lang, 'pat_stale')}
    # replay with the SEALED build params (build defaults for pre-params sets):
    # re-running with different arguments invents a mismatch that is not there
    params = patch_set.get('params') or {}
    res = _autofix(html_text,
                   lang=params.get('lang'),
                   title=params.get('title'),
                   form_errors=params.get('form_errors', True))
    if res['applied'] != patch_set.get('fixes'):
        return {'status': 'mismatch', 'source_sha256': sha,
                'reproduced': res['applied'],
                'recorded': patch_set.get('fixes'),
                'note': _t(lang, 'pat_mismatch')}
    return {'status': 'reproduced', 'source_sha256': sha,
            'count': len(res['applied']), 'fixed_html': res['fixed_html'],
            'note': _t(lang, 'pat_reproduced')}


def main(argv):
    ap = argparse.ArgumentParser(
        description='Build or verify a sealed patch-set of deterministic fixes')
    ap.add_argument('html_file', nargs='?', help='the HTML file')
    ap.add_argument('--file', dest='html_opt', help='the HTML file (alt form)')
    ap.add_argument('-o', '--out', help='write the patch-set JSON here (build)')
    ap.add_argument('--verify', metavar='PATCHSET',
                    help='verify this patch-set against the HTML instead')
    ap.add_argument('--fixed', dest='fixed_out',
                    help='write the fixed html here (build)')
    ap.add_argument('--lang', default='en', choices=['es', 'en'])
    a = ap.parse_args(argv)
    path = a.html_file or a.html_opt
    if not path:
        ap.error('an HTML file is required (positional or --file)')
    html_text = open(path, encoding='utf-8', errors='replace').read()
    if a.verify:
        patch_set = json.load(open(a.verify, encoding='utf-8'))
        res = apply_patches(html_text, patch_set)
        # JSON SIEMPRE válido: el fixed_html completo no se imprime (una
        # salida cortada a [:2000] partía escapes y dejaba JSON roto) —
        # quien quiera la copia arreglada usa --fixed
        out = {k: v for k, v in res.items() if k != 'fixed_html'}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        if a.fixed_out and res.get('status') == 'reproduced':
            with open(a.fixed_out, 'w', encoding='utf-8') as f:
                f.write(res['fixed_html'])
        return 0 if res['status'] in ('reproduced', 'stale') else 1
    res = build(html_text)
    payload = json.dumps(res['patch_set'], ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(payload)
        print(json.dumps({'out': a.out, 'count': res['patch_set']['count'],
                          'source_sha256': res['patch_set']['source_sha256']},
                         ensure_ascii=False))
    else:
        print(payload)
    if a.fixed_out:
        with open(a.fixed_out, 'w', encoding='utf-8') as f:
            f.write(res['fixed_html'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
