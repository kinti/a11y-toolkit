#!/usr/bin/env python3
"""a11y_corpus — the versioned audit corpus (the VK-LSVD translation).

Cross-industry translation: VK-LSVD (WWW '26, arXiv 2602.04567) turned an
industrial dataset into ecosystem gravity — dataset + documented schema +
published baselines + a challenge on top. This module does the same for
accessibility evaluation: FROZEN pages with a sealed ground truth (the
mutant bank: one injected violation per page, placebo controls for false
positives), a NEUTRAL evaluation contract any engine can answer (criterion
codes, not our signal names), a reference baseline from this engine, and a
versioned manifest with a hash seal — same tamper-evidence DNA as the
evidence pack.

Why frozen beats regenerated: the mutant generator evolves with the engine;
a corpus that silently changed underneath a published score is a broken
benchmark. A published corpus version is never edited (D12 applied to
data): pages ship as files, the manifest seals every hash, changes ship as
a new version with a changelog entry.

The challenge shape: third parties produce a submission (one JSON line per
case with the WCAG criteria their evaluator flags), `corpus evaluate`
scores it deterministically — kill rate on mutants, false positives on
placebos, per-criterion confusion. `corpus reference` re-runs this engine
over the frozen pages and ships the baseline with it.

CLI (this is infrastructure, not a tool — D17):
  a11ycorpus.py build  [--version 2026.10.0] [--seed 7] [--n 18] [--out corpus]
  a11ycorpus.py verify [dir]
  a11ycorpus.py evaluate --submission sub.jsonl [dir]
  a11ycorpus.py reference [dir]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

from .a11ymutants import generate as generate_exam
from .a11yaudit import audit_html

CORPUS_FORMAT = 'a11y-corpus/1'
EVAL_FORMAT = 'a11y-corpus-evaluation/1'

_NOTE_README = """# a11y corpus {version}

Frozen pages with sealed ground truth for evaluation-benchmarking ANY
accessibility engine. Version {version}, {n_total} entries ({n_mutants}
sealed mutants + {n_control} placebo controls). Format `{fmt}`.

## The contract (engine-neutral)

One JSON line per case in your submission file:

{{"case_id": "m7-0", "criteria_found": ["1.1.1"]}}

`criteria_found` = the WCAG 2.x criteria YOUR evaluator reports as failing
on that page (criterion codes, e.g. "1.4.4" — not tool-specific rule ids).
Placebo entries accept the same shape; anything you flag on them counts as a
false positive by construction (no violation was injected).

Score it:

    a11ytoolkit corpus evaluate --submission my-submission.jsonl {rel}

## Verify this corpus (no toolkit needed)

Every file hash and the manifest seal are plain sha256:

    cd {rel} && shasum -a 256 -c <(python3 -c \\
      "import json;m=json.load(open('MANIFEST.json'));[print(v+'  '+k) for k,v in m['files'].items()]")

The seal `MANIFEST.json.sha256` covers the canonical manifest without the
seal itself — recompute and compare (see a11ycorpus.py `verify`).

## Baseline

`results/reference.json` is this engine's own submission scored by the same
harness (published WITH the dataset, LSVD-style). A published corpus
version is never edited; changes ship as a new version + changelog entry.
"""


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))


def _sha(data_bytes):
    return hashlib.sha256(data_bytes).hexdigest()


def _side_features(html_text):
    """Características baratas y declaradas por página (para estratificar)."""
    lang = re.search(r'<html[^>]*\blang="([a-z-]+)"', html_text, re.I)
    title = re.search(r'<title>([^<]*)</title>', html_text)
    return {
        'bytes': len(html_text.encode('utf-8')),
        'lang': lang.group(1) if lang else None,
        'title': title.group(1) if title else None,
        'imgs': len(re.findall(r'<img\b', html_text)),
        'buttons': len(re.findall(r'<button\b', html_text)),
        'links': len(re.findall(r'<a\b', html_text)),
    }


def build(version='2026.10.0', seeds=(7,), n_per_seed=18, out='corpus',
          date=None, with_reference=True):
    """Congela un examen del banco de mutantes como corpus versionado.
    Determinista dadas (version, seeds, n, date) y la versión del motor (el
    baseline reference la embebe) — mismo insumo, mismos bytes."""
    if len(set(seeds)) != len(seeds):
        # los ids de caso llevan la seed (m{seed}-{i}): duplicarla colisiona
        # TODOS los ids y el manifiesto mentiría sobre el número de casos
        raise ValueError('duplicate seeds collide every case id: %s' % list(seeds))
    date = date or datetime.date.today().isoformat()
    os.makedirs(os.path.join(out, 'pages'), exist_ok=True)
    os.makedirs(os.path.join(out, 'results'), exist_ok=True)
    entries = []
    for seed in seeds:
        exam = generate_exam(seed, n_per_seed)
        for item in exam['mutants'] + exam['control_pages']:
            fname = 'pages/%s.html' % item['id']
            with open(os.path.join(out, fname), 'w', encoding='utf-8') as f:
                f.write(item['html'])
            s = item['sealed']
            case = {'case_id': item['id'], 'kind': 'mutant', 'file': fname,
                    'side_features': _side_features(item['html']),
                    'expected': {'criterion': s['criterion'],
                                 'operator': s['operator'],
                                 'detail': s['detail']}}
            if item['id'].startswith('p'):
                case['kind'] = 'placebo'
                case['expected'] = None
            entries.append(case)
    entries.sort(key=lambda c: c['case_id'])
    with open(os.path.join(out, 'cases.jsonl'), 'w', encoding='utf-8') as f:
        for c in entries:
            f.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + '\n')

    n_mut = sum(1 for c in entries if c['kind'] == 'mutant')
    n_pla = len(entries) - n_mut
    changelog = ('# Corpus changelog\n\n'
                 '## %s\n\n- initial release: %d sealed mutants + %d placebo '
                 'controls (a11ymutants seeds %s, n=%d per seed, frozen '
                 'byte-for-byte)\n' % (version, n_mut, n_pla,
                                       list(seeds), n_per_seed))
    with open(os.path.join(out, 'CHANGELOG.md'), 'w', encoding='utf-8') as f:
        f.write(changelog)

    manifest = {
        'format': CORPUS_FORMAT,
        'version': version,
        'date': date,
        'generator': {'source': 'a11ymutants (sealed exam)', 'seeds': list(seeds),
                      'n_per_seed': n_per_seed},
        'counts': {'cases': len(entries), 'mutants': n_mut, 'placebos': n_pla,
                   'criteria_covered': sorted({c['expected']['criterion']
                                               for c in entries if c['expected']})},
        'contract': {'submission': 'JSONL {case_id, criteria_found: [WCAG codes]}',
                     'scoring': 'kill = expected criterion flagged on a mutant; '
                                'any flag on a placebo = false positive by '
                                'construction'},
        'license_note': 'pages are engine-generated fixtures (MIT, same as the '
                        'toolkit); no third-party crawl ships here',
        'files': {},
    }
    if with_reference:
        ref = reference(out)
        ref_text = json.dumps(ref, ensure_ascii=False, indent=1, sort_keys=True)
        with open(os.path.join(out, 'results', 'reference.json'), 'w',
                  encoding='utf-8') as f:
            f.write(ref_text)
        manifest['files']['results/reference.json'] = _sha(ref_text.encode('utf-8'))
    for rel in sorted(set(['cases.jsonl', 'CHANGELOG.md']
                          + ['pages/%s.html' % c['case_id'] for c in entries])):
        with open(os.path.join(out, rel), 'rb') as f:
            manifest['files'][rel] = _sha(f.read())
    manifest['sha256'] = _sha(_canon({k: v for k, v in manifest.items()
                                      if k != 'sha256'}).encode('utf-8'))
    with open(os.path.join(out, 'MANIFEST.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    readme = _NOTE_README.format(version=version, n_total=len(entries),
                                 n_mutants=n_mut, n_control=n_pla,
                                 fmt=CORPUS_FORMAT, rel=out.rstrip('/') or '.')
    with open(os.path.join(out, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme)
    return manifest


def verify(directory='corpus'):
    """(ok, detail): cada hash del manifiesto + el sello del propio manifiesto."""
    mpath = os.path.join(directory, 'MANIFEST.json')
    if not os.path.exists(mpath):
        return False, 'MANIFEST.json missing'
    try:
        manifest = json.load(open(mpath, encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, 'manifest unreadable: %s' % e
    if not isinstance(manifest, dict):
        return False, 'manifest must be a JSON object'
    seal = manifest.pop('sha256', None)
    if seal is None:
        return False, 'manifest has no seal'
    if _sha(_canon(manifest).encode('utf-8')) != seal:
        return False, 'manifest seal broken (MANIFEST.json edited)'
    table = manifest.get('files')
    if not isinstance(table, dict) or not table:
        return False, 'manifest has no files table'
    for rel, expected in table.items():
        if not isinstance(rel, str) or '..' in rel or rel.startswith('/'):
            return False, 'illegal path in manifest: %r' % rel
        path = os.path.join(directory, rel)
        if not os.path.exists(path):
            return False, 'missing file: %s' % rel
        with open(path, 'rb') as f:
            if _sha(f.read()) != expected:
                return False, 'hash mismatch: %s' % rel
    return True, '%d files + seal verified' % len(table)


def _load_entries(directory='corpus'):
    entries = {}
    with open(os.path.join(directory, 'cases.jsonl'), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                c = json.loads(line)
                entries[c['case_id']] = c
    return entries


def engine_submission(directory='corpus'):
    """Este motor sobre las páginas congeladas → submission (mismo contrato
    que un tercero: criterios que reporta por página)."""
    sub = []
    for cid, case in sorted(_load_entries(directory).items()):
        html_text = open(os.path.join(directory, case['file']),
                         encoding='utf-8').read()
        rep = audit_html(html_text, case['file'], lang='en')
        found = sorted({h['criterion'].split(' ')[0]
                        for h in rep.get('findings', [])})
        sub.append({'case_id': cid, 'criteria_found': found})
    return sub


def evaluate(submission, directory='corpus', submission_name='submission'):
    """Submission (lista de {case_id, criteria_found}) → veredicto determinista:
    kill rate sobre mutantes, falsos positivos sobre placebos, confusión por
    criterio. Contrato NEUTRAL: códigos WCAG, no señales nuestras."""
    entries = _load_entries(directory)
    by_id = {}
    unknown = []
    invalid = []
    for entry in submission:
        if not isinstance(entry, dict):
            unknown.append(repr(entry)[:40])
            continue
        cid = entry.get('case_id')
        if cid not in entries:
            unknown.append(cid)
            continue
        found = entry.get('criteria_found', [])
        if not isinstance(found, list):
            # un string iteraría CARACTERES y mentiría el veredicto en
            # silencio: se rechaza declarado, jamás se traga
            invalid.append({'case_id': cid,
                            'criteria_found': repr(found)[:60]})
            continue
        by_id[cid] = [str(c) for c in found]
    killed, missed, fps, additional = [], [], [], []
    per_crit = {}
    for cid, case in sorted(entries.items()):
        found = by_id.get(cid, [])
        if case['kind'] == 'placebo':
            if found:
                fps.append({'case_id': cid, 'criteria_flagged': found})
            continue
        exp = case['expected']['criterion']
        per_crit.setdefault(exp, {'expected': 0, 'killed': 0})
        per_crit[exp]['expected'] += 1
        if exp in found:
            killed.append(cid)
            per_crit[exp]['killed'] += 1
        else:
            missed.append({'case_id': cid, 'expected_criterion': exp,
                           'operator': case['expected']['operator'],
                           'found_instead': [c for c in found if c != exp]})
        extra = [c for c in found if c != exp]
        if extra:
            additional.append({'case_id': cid, 'additional_criteria': extra})
    n_mut = sum(1 for c in entries.values() if c['kind'] == 'mutant')
    n_pla = len(entries) - n_mut
    return {
        'format': EVAL_FORMAT,
        'submission_name': submission_name,
        'mutants': n_mut, 'killed': len(killed),
        'kill_rate': round(len(killed) / n_mut, 4) if n_mut else None,
        'missed_detail': missed,
        'control_pages': n_pla,
        'false_positives': fps,
        'additional_findings_on_mutants': {'count': len(additional),
                                           'note': 'reported, not scored: only '
                                                   'placebo flags are false '
                                                   'positives by construction',
                                           'sample': additional[:10]},
        'per_criterion': per_crit,
        'unknown_case_ids': unknown,
        'invalid_entries': invalid,
        'cases_without_submission': [cid for cid in sorted(entries)
                                     if cid not in by_id][:10],
    }


def reference(directory='corpus'):
    """Baseline LSVD-style: este motor sobre el corpus congelado, puntuado
    por el MISMO arnés que un tercero. Va publicado con el dataset."""
    from . import server
    sub = engine_submission(directory)
    res = evaluate(sub, directory, submission_name='a11y-toolkit reference')
    res['engine'] = {'name': 'a11y-toolkit', 'version': server.VERSION}
    return res


def _read_submission(path):
    """JSONL (un objeto por línea) o UN array JSON completo: el contrato es
    neutral y terceros mandan ambos; el lector acepta los dos."""
    with open(path, encoding='utf-8') as f:
        text = f.read().strip()
    if not text:
        return []
    if text.startswith('['):
        return [e for e in json.loads(text) if isinstance(e, dict)]
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description='Versioned audit corpus (VK-LSVD translation)')
    sub = ap.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build', help='freeze a corpus version from the mutant bank')
    b.add_argument('--version', default='2026.10.0')
    b.add_argument('--seed', type=int, action='append', default=None)
    b.add_argument('--n', type=int, default=18)
    b.add_argument('--out', default='corpus')
    b.add_argument('--date', help='release date ISO (default: today)')
    b.add_argument('--no-reference', action='store_true')
    v = sub.add_parser('verify', help='recompute every hash + the manifest seal')
    v.add_argument('directory', nargs='?', default='corpus')
    e = sub.add_parser('evaluate', help='score a neutral submission (JSONL)')
    e.add_argument('--submission', required=True)
    e.add_argument('directory', nargs='?', default='corpus')
    r = sub.add_parser('reference', help='this engine over the frozen pages → baseline')
    r.add_argument('--force', action='store_true',
                   help='rewrite the baseline of a sealed corpus (publishes a '
                        'new engine baseline; breaks the old manifest seal)')
    r.add_argument('directory', nargs='?', default='corpus')
    a = ap.parse_args(argv)
    if a.action == 'build':
        m = build(version=a.version, seeds=tuple(a.seed or [7]), n_per_seed=a.n,
                  out=a.out, date=a.date, with_reference=not a.no_reference)
        print(json.dumps({'corpus': a.out, 'version': m['version'],
                          'cases': m['counts']['cases'],
                          'sha256': m['sha256']}, ensure_ascii=False))
        return 0
    if a.action == 'verify':
        ok, detail = verify(a.directory)
        print(json.dumps({'ok': ok, 'detail': detail}, ensure_ascii=False))
        return 0 if ok else 1
    if a.action == 'evaluate':
        res = evaluate(_read_submission(a.submission), a.directory,
                       submission_name=os.path.basename(a.submission))
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    if a.action == 'reference':
        outp = os.path.join(a.directory, 'results', 'reference.json')
        manifest_path = os.path.join(a.directory, 'MANIFEST.json')
        if (os.path.exists(outp) and os.path.exists(manifest_path)
                and not a.force):
            # un corpus sellado es inmutable (D22): re-escribir su baseline
            # tras un bump del motor rompería el sello y el pin del repo
            print(json.dumps({'error': ('results/reference.json already exists '
                                        'in a sealed corpus — rewriting it '
                                        'breaks the manifest; use --force to '
                                        'publish a NEW engine baseline')},
                             ensure_ascii=False))
            return 2
        res = reference(a.directory)
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with open(outp, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(json.dumps({'reference': outp, 'kill_rate': res['kill_rate'],
                          'false_positives': len(res['false_positives']),
                          'engine': res['engine']}, ensure_ascii=False))
        return 0
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
