#!/usr/bin/env python3
"""Applicability scope — the layer between the audit and the conformance claim.

Pattern learned from the Government of Canada CIO wizard (EN 301 549 V4.1.1):
conformance is not "run all 55", it is "answer what the product IS, then the
applicable clauses fall out". Their wizard asks 118 questions a human answers
by hand. This engine does the semi-automatic inverse: it reads what the
audit actually SAW (the features block: media elements, form controls) and
proposes the structural exclusions a human only needs to confirm.

The honesty rule is load-bearing, borrowed from the evidence pack:
  - the machine PROPOSES ('proposed-excluded') from positive evidence —
    zero <video> elements is evidence, "no 1.2.x finding fired" is NOT
    (absence of signal ≠ absence of content);
  - only a human answer turns a proposal into 'excluded';
  - only 'excluded' rows may become not-applicable downstream (evidence
    pack matrix, VPAT/OpenACR levels). A proposal never excludes anything.

With --standard en301549 every row carries its EN 301 549 V4.1.1 clause
(9.x web / 10.x documents / 11.x software — numbering identity verified
55/55 against the official wizard), and the EN-only families (5, 6, 7, 8,
12, 13) appear as honest applicability rows this engine does not evaluate.

CLI:
  a11yscope.py audit.json [otro.json …] [--standard en301549] [--target web]
                         [--answers human.json] [--lang en] [-o scope.json]
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

STANDARDS = ('wcag22', 'en301549', 'rgaa')   # 508 GSA tree: capa privada pro
STATUS_ORDER = ('in-scope', 'proposed-excluded', 'excluded')

# Criterios cuya aplicabilidad depende de un rasgo ESTRUCTURAL detectable:
# si el rasgo está AUSENTE en la muestra auditada, el criterio se propone
# excluido (el humano confirma). Fuera de estos dos grupos, nada se propone:
# la ausencia de señal no es evidencia de ausencia.
_MEDIA_CRITERIA = ('1.2.1', '1.2.2', '1.2.3', '1.2.4', '1.2.5', '1.4.2')
_FORM_CRITERIA = ('1.3.5', '3.3.1', '3.3.2', '3.3.3', '3.3.4', '3.3.7', '3.3.8',
                  '3.3.9')


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _sha256(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


def collect_features(reports):
    """Suma el bloque features de todos los informes que lo lleven.

    Devuelve (features, disponible): sin features (informes previos a la
    versión que los introduce) NO hay propuestas — se dice, no se inventa.
    """
    feats = {'video': 0, 'audio': 0, 'track': 0, 'embed': 0, 'iframe': 0,
             'object': 0, 'form': 0, 'input': 0, 'select': 0, 'textarea': 0,
             'table': 0}
    seen = False
    for rep in reports:
        block = rep.get('features')
        if not isinstance(block, dict):
            continue
        seen = True
        for k in feats:
            v = block.get(k)
            if isinstance(v, int) and v > 0:
                feats[k] += v
    return feats, seen


def _media_state(feats, findings_codes):
    """'present' | 'embedded' | 'absent'.

    iframe/embed/object PUEDEN portar vídeo (YouTube embebido): si solo hay
    embeds, los medios quedan 'embedded' — indeterminado, el criterio se
    mantiene en alcance porque la exclusión exige ausencia estructural.
    """
    if feats['video'] or feats['audio'] or feats['track']:
        return 'present'
    # respaldo positivo: un hallazgo 1.2.x SÓLO dispara si el parser vio
    # medios — no es ausencia de señal, es contenido con problema
    if any(c.startswith('1.2.') for c in findings_codes):
        return 'present'
    if feats['embed'] or feats['iframe'] or feats['object']:
        return 'embedded'
    return 'absent'


def _forms_present(feats, findings_codes):
    if feats['form'] or feats['input'] or feats['select'] or feats['textarea']:
        return True
    # señales 3.3.x/1.3.5: solo disparan sobre campos reales
    return any(c.startswith('3.3.') or c == '1.3.5' for c in findings_codes)


def build_scope(reports, standard='wcag22', target='web', answers=None,
                lang='en', targets=None):
    """Informes (lista de dicts) + respuestas humanas → alcance a11y-scope/1."""
    if standard not in STANDARDS:
        raise ValueError(f"standard must be one of {STANDARDS}, got {standard!r}")
    from . import a11yen301549 as enstd
    from .a11yi18n import pack
    from .a11ycrit import _C
    tx = pack(lang).get('scope', {}) or {}

    if targets:
        targets = [x for x in targets if x in ('web', 'documents', 'software')] or [target]
    else:
        targets = [target]
    reports = [r for r in reports if isinstance(r, dict)]
    findings_codes = set()
    for rep in reports:
        raw = rep.get('findings')
        if not isinstance(raw, list):
            continue   # informe malformado: sin hallazgos aprovechables
        for h in raw:
            if not isinstance(h, dict):
                continue
            crit = h.get('criterion')
            if isinstance(crit, str) and crit:
                findings_codes.add(crit.split(' ')[0])

    feats, features_seen = collect_features(reports)
    media = _media_state(feats, findings_codes) if features_seen else 'unknown'
    forms = _forms_present(feats, findings_codes) if features_seen else None

    answers = answers or {}
    if not isinstance(answers, dict):
        raise ValueError('answers must be an object keyed by criterion code')

    codes_aa = sorted(k for k, v in _C.items() if v[0] in ('A', 'AA'))
    criteria = []
    for code in codes_aa:
        name = (_C[code][1].get(lang) or _C[code][1]['en'])[0]
        row = {'criterion': f'{code} {name}', 'level': _C[code][0]}
        if standard == 'en301549':
            row['clause'] = enstd.clause_for(code, targets[0])
            if len(targets) > 1:
                row['clauses'] = {tg: enstd.clause_for(code, tg) for tg in targets}

        ans = answers.get(code)
        if isinstance(ans, str):        # abreviatura: "excluded"/"in-scope"
            ans = {'status': ans}
        if isinstance(ans, dict) and ans.get('status') in STATUS_ORDER:
            row['status'] = ans['status']
            row['evidence_source'] = 'human'
            if ans.get('reason'):
                row['reason'] = str(ans['reason'])[:500]
        elif code in _MEDIA_CRITERIA and media == 'absent':
            row['status'] = 'proposed-excluded'
            row['evidence_source'] = 'machine:features'
            row['evidence'] = tx.get('evidence_media_absent')
        elif code in _MEDIA_CRITERIA and media == 'embedded':
            # embeds pueden portar vídeo: indeterminado, queda en alcance
            row['status'] = 'in-scope'
            row['evidence'] = tx.get('evidence_media_embedded')
        elif code == '1.2.4' and media == 'present':
            # con medios presentes, en directo vs pregrabado no se distingue
            # en estático: queda en alcance con nota de decisión humana
            row['status'] = 'in-scope'
            row['evidence'] = tx.get('evidence_live_human')
        elif code in _FORM_CRITERIA and forms is False:
            row['status'] = 'proposed-excluded'
            row['evidence_source'] = 'machine:features'
            row['evidence'] = tx.get('evidence_forms_absent')
        else:
            row['status'] = 'in-scope'
            if code in _MEDIA_CRITERIA:
                row['evidence'] = tx.get('evidence_media_present')
            elif code in _FORM_CRITERIA:
                row['evidence'] = tx.get('evidence_forms_present')
        criteria.append(row)

    if standard == 'rgaa':
        from . import a11yrgaa
        criteria = [{'criterion': c['num'] + ' ' + c['title'],
                     'status': 'in-scope'} for c in a11yrgaa.CRITERIA]
        # las respuestas humanas también aplican a RGAA (antes se descartaban:
        # counters.excluded siempre 0). La máquina NUNCA propone en rgaa —
        # solo una respuesta humana mueve filas. La clave puede venir como el
        # num exacto ('1.1') o con cola de test ('1.1.1'): el num de la fila
        # es el prefijo — el match con separador evita 1.1 vs 1.10.
        for key, ans in answers.items():
            if not isinstance(key, str):
                continue
            a = {'status': ans} if isinstance(ans, str) else (
                ans if isinstance(ans, dict) else None)
            if not a or a.get('status') not in STATUS_ORDER:
                continue
            for row in criteria:
                num = row['criterion'].split(' ')[0]
                if key == num or key.startswith(num + '.'):
                    row['status'] = a['status']
                    row['evidence_source'] = 'human'
                    if a.get('reason'):
                        row['reason'] = str(a['reason'])[:500]

    std508_block = None   # 508 GSA tree: moved to the private pro layer

    counters = {
        'criteria': len(criteria),
        'in_scope': sum(1 for r in criteria if r['status'] == 'in-scope'),
        'proposed_excluded': sum(1 for r in criteria if r['status'] == 'proposed-excluded'),
        'excluded': sum(1 for r in criteria if r['status'] == 'excluded'),
    }
    if standard == 'en301549':
        # el contador espejo del "Total Clauses" del wizard oficial: solo
        # cuentan las cláusulas EN aplicables (en alcance o excluidas por
        # humano — una propuesta no descuenta)
        counters['en_clauses_applicable'] = counters['in_scope'] + counters['excluded']

    scope = {
        'section508': std508_block,
        'format': 'a11y-scope/1',
        'lang': lang,
        'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'tool': 'a11y-toolkit (github.com/kinti/a11y-toolkit)',
        'standard': (enstd.STANDARD_NAME if standard == 'en301549'
                 else a11yrgaa.STANDARD_NAME if standard == 'rgaa'
                 else 'WCAG 2.2 (A/AA)'),
        'target': target,
        'features_observed': feats if features_seen else None,
        'features_evidence': bool(features_seen),
        'criteria': criteria,
        'counters': counters,
        'notice': tx.get('notice'),
    }
    if not features_seen:
        scope['limitations'] = [tx.get('no_features_note')]
    if standard == 'en301549':
        fam_rows = []
        for fam in enstd.family_rows(lang):
            def _status_for(tg):
                if fam['family'] == '12':
                    return 'in-scope'
                if fam['family'] in ('6', '7', '8') and tg == 'web':
                    # un producto web no lleva RTT/transmisión de vídeo/hardware:
                    # propuesta de la MISMA lógica que usa el wizard oficial
                    return 'proposed-excluded'
                return 'human-review'
            status = _status_for(targets[0])
            row_f = {**fam, 'status': status,
                     'evaluated_by_toolkit': False}
            if len(targets) > 1:
                row_f['status_per_target'] = {tg: _status_for(tg) for tg in targets}
            fam_rows.append(row_f)
        scope['en301549_families'] = fam_rows
        if 'software' in targets:
            # cláusulas EN-only de la cláusula 11 (11.5-11.7): aplicabilidad
            # honesta que este motor NO evalúa — revisión humana, jamás una
            # propuesta (la forma del producto NO las decide, a diferencia de
            # 6/7/8 en web) y jamás un claim de conformidad
            scope['en301549_software_clauses'] = [
                {**row, 'status': 'human-review', 'evaluated_by_toolkit': False}
                for row in enstd.software_clause_rows(lang)]
    # el sello excluye el reloj: re-emitir el mismo alcance → mismo sha
    scope['sha256'] = _sha256({k: v for k, v in scope.items() if k != 'generated'})
    return scope


def main(argv):
    from .a11yen301549 import TARGETS
    ap = argparse.ArgumentParser(description='Applicability scope (semi-automatic)')
    ap.add_argument('reports', nargs='+', help='audit report JSON files (any mode)')
    ap.add_argument('--standard', choices=STANDARDS, default='wcag22',
                    help='en301549 adds EN 301 549 V4.1.1 clause refs + families')
    ap.add_argument('--target', choices=TARGETS, default='web',
                    help='ICT target: web (9.x), documents (10.x), software (11.x)')
    ap.add_argument('--answers', help='JSON file: human confirmations keyed by code '
                    '{"1.2.4": {"status": "excluded", "reason": "…"}}')
    ap.add_argument('--lang', default='en', choices=('es', 'en'))
    ap.add_argument('-o', '--out', default='scope.json')
    ap.add_argument('--targets', default=None,
                    help='comma-separated ICT targets for combined scope (e.g. web,documents)')
    # (--solicitation se retiró: el generador de anexos vive en a11y-toolkit-pro)
    a = ap.parse_args(argv)
    reports = [json.load(open(r, encoding='utf-8')) for r in a.reports]
    answers = json.load(open(a.answers, encoding='utf-8')) if a.answers else None
    tgts = [t.strip() for t in a.targets.split(',')] if a.targets else None
    scope = build_scope(reports, standard=a.standard, target=a.target,
                        answers=answers, lang=a.lang, targets=tgts)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(scope, f, ensure_ascii=False, indent=1)
    print(json.dumps({'scope': a.out, 'sha256': scope['sha256'],
                      'counters': scope['counters']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
