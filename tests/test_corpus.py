#!/usr/bin/env python3
"""Tests del corpus versionado (a11ycorpus, traducción VK-LSVD): sellado de
hashes, contrato neutral de evaluación, baseline publicado y determinismo."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from a11y_toolkit import a11ycorpus  # noqa: E402

# ── 1. build + verify + sello (tmpdir, fecha fija) ──────────────────────────
with tempfile.TemporaryDirectory() as d:
    m = a11ycorpus.build(version='2026.10.0', seeds=(7,), n_per_seed=6,
                         out=d, date='2026-10-30')
    ok, detail = a11ycorpus.verify(d)
    assert ok, detail
    assert m['counts']['cases'] == 7 and m['counts']['placebos'] == 1
    assert '1.1.1' in m['counts']['criteria_covered']
    assert m['format'] == 'a11y-corpus/1' and len(m['sha256']) == 64
    # copias DENTRO del tempdir: la limpieza del contexto se las lleva
    # (una por experimento: romper sello y borrar fichero son fallos distintos)
    shutil.copytree(d, os.path.join(d, 'copia-sello'))
    shutil.copytree(d, os.path.join(d, 'copia-falta'))
    # manipular una página → el hash del manifiesto grita
    page = os.path.join(d, 'pages', 'm7-0.html')
    original = open(page, encoding='utf-8').read()
    with open(page, 'w', encoding='utf-8') as f:
        f.write(original + '<!-- x -->')
    ok, detail = a11ycorpus.verify(d)
    assert not ok and 'hash mismatch' in detail, detail
    # editar el MANIFEST → sello roto (D22: jamás se edita lo publicado)
    mp = os.path.join(d, 'copia-sello', 'MANIFEST.json')
    man = json.load(open(mp, encoding='utf-8'))
    man['version'] = '9999.99.99'
    json.dump(man, open(mp, 'w'), ensure_ascii=False)
    ok, detail = a11ycorpus.verify(os.path.join(d, 'copia-sello'))
    assert not ok and 'seal broken' in detail, detail
    # fichero ausente (sello intacto) → falta, no crash
    os.remove(os.path.join(d, 'copia-falta', 'cases.jsonl'))
    ok, detail = a11ycorpus.verify(os.path.join(d, 'copia-falta'))
    assert not ok and 'missing' in detail, detail
    # restaura la página: el resto de la suite trabaja sobre el corpus saneado
    with open(page, 'w', encoding='utf-8') as f:
        f.write(original)
    ok, detail = a11ycorpus.verify(d)
    assert ok, detail

    # ── 2. contrato neutral: perfecta / vacía / con FP / desconocidos ──────
    cases = [json.loads(l) for l in open(os.path.join(d, 'cases.jsonl'),
                                         encoding='utf-8')]
    perfect = [{'case_id': c['case_id'],
                'criteria_found': [c['expected']['criterion']] if c['expected'] else []}
               for c in cases]
    res = a11ycorpus.evaluate(perfect, d)
    assert res['kill_rate'] == 1.0 and res['false_positives'] == []
    assert all(v['killed'] == v['expected'] for v in res['per_criterion'].values())
    res_vacia = a11ycorpus.evaluate([{'case_id': c['case_id'], 'criteria_found': []}
                                     for c in cases], d)
    assert res_vacia['kill_rate'] == 0.0 and res_vacia['missed_detail']
    # FP por construcción: flag inventado SOLO en placebos
    con_fp = [{'case_id': c['case_id'],
               'criteria_found': (['2.4.4'] if c['kind'] == 'placebo'
                                  else ([c['expected']['criterion']] if c['expected'] else []))}
              for c in cases]
    res_fp = a11ycorpus.evaluate(con_fp, d)
    assert res_fp['kill_rate'] == 1.0 and len(res_fp['false_positives']) == 1
    assert res_fp['false_positives'][0]['criteria_flagged'] == ['2.4.4']
    # case_id desconocido y submission parcial: contados, no crash
    res_raro = a11ycorpus.evaluate([{'case_id': 'no-existe', 'criteria_found': ['1.1.1']}], d)
    assert res_raro['unknown_case_ids'] == ['no-existe']
    assert res_raro['kill_rate'] == 0.0 and res_raro['cases_without_submission']
    # criteria_found no-lista (string/None): RECHAZO declarado, jamás iterar
    # caracteres en silencio ni tronar (revisión 30-oct — contrato neutral)
    res_malo = a11ycorpus.evaluate(
        [{'case_id': 'm7-0', 'criteria_found': '1.1.1'},
         {'case_id': 'm7-1', 'criteria_found': None}], d)
    assert len(res_malo['invalid_entries']) == 2 and res_malo['kill_rate'] == 0.0
    assert all('m7-' in e['case_id'] for e in res_malo['invalid_entries'])
    # seeds duplicados colisionan TODOS los ids → build se niega (no sella
    # un manifiesto que mienta sobre el número de casos)
    try:
        a11ycorpus.build(version='x', seeds=(7, 7), n_per_seed=3,
                         out=os.path.join(d, 'roto'), date='2026-10-30')
        raise SystemExit('seeds duplicados debían lanzar')
    except ValueError:
        pass
    # MANIFEST hostil: truncado y sin tabla files → ok:False, SIN traceback
    ruta_man = os.path.join(d, 'copia-falta', 'MANIFEST.json')
    with open(ruta_man, 'w', encoding='utf-8') as f:
        f.write('{"format": "a11y-corpus/1", "ver')      # JSON roto
    ok, detail = a11ycorpus.verify(os.path.join(d, 'copia-falta'))
    assert not ok and 'unreadable' in detail, detail
    import hashlib as _h
    sin_files = {'format': 'a11y-corpus/1', 'version': 'x'}
    sin_files['sha256'] = _h.sha256(
        json.dumps(sin_files, sort_keys=True, separators=(',', ':'))
        .encode('utf-8')).hexdigest()                       # sello VÁLIDO, sin files
    json.dump(sin_files, open(ruta_man, 'w'))
    ok, detail = a11ycorpus.verify(os.path.join(d, 'copia-falta'))
    assert not ok and 'files' in detail, detail

    # ── 3. reference: este motor pasa su propio examen congelado ───────────
    ref = a11ycorpus.reference(d)
    assert ref['kill_rate'] == 1.0 and ref['false_positives'] == []
    assert ref['engine']['name'] == 'a11y-toolkit' and ref['engine']['version']

    # ── 4. determinismo: mismo insumo → MISMO sello (ubicación da igual) ────
    d2 = tempfile.mkdtemp()
    try:
        m2 = a11ycorpus.build(version='2026.10.0', seeds=(7,), n_per_seed=6,
                              out=d2, date='2026-10-30')
        assert m2['sha256'] == m['sha256'], 'el sello depende de la ubicación'
        for f in ('cases.jsonl', 'results/reference.json'):
            assert open(os.path.join(d, f), 'rb').read() == \
                open(os.path.join(d2, f), 'rb').read()
    finally:
        shutil.rmtree(d2)

# ── 5. el corpus DEL REPO no puede derivar en silencio (pin permanente) ─────
ok, detail = a11ycorpus.verify(os.path.join(ROOT, 'corpus'))
assert ok, 'el corpus commiteado diverge de su manifiesto: ' + detail
repo_m = json.load(open(os.path.join(ROOT, 'corpus', 'MANIFEST.json'), encoding='utf-8'))
assert repo_m['version'] == '2026.10.0' and repo_m['counts']['mutants'] == 18
repo_ref = json.load(open(os.path.join(ROOT, 'corpus', 'results', 'reference.json'),
                          encoding='utf-8'))
assert repo_ref['kill_rate'] == 1.0 and repo_ref['false_positives'] == []

# ── 6. CLI end-to-end (boundary: el subcommand existe y verify sale 0) ─────
with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'corpus',
                        'build', '--out', os.path.join(d, 'c'),
                        '--date', '2026-10-30', '--n', '6'],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    assert r.returncode == 0, r.stderr[-300:]
    r2 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'corpus',
                         'verify', os.path.join(d, 'c')],
                        capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r2.returncode == 0 and '"ok": true' in r2.stdout, r2.stdout + r2.stderr

print('CORPUS OK ✓ (sello+manifiesto, contrato neutral (kill/FP/confusión), '
      'reference 1.0, determinismo ubicación-independiente, pin del corpus '
      'del repo, CLI boundary)')
