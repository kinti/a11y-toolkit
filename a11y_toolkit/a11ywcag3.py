#!/usr/bin/env python3
"""WCAG 3 preview — re-groups WCAG 2.2 findings under the draft's outcomes.

The W3C publishes WCAG 3 as a Working Draft that "will change substantially".
This module is a VIEW layer, not an evaluation: it takes an audit report
(a11y_audit_url / a11y_audit_dom / a11y_disprove …) and re-presents its
findings grouped by the outcomes of the September 2026 draft.

Honest boundaries, by design:
  - NO score, NO tier, NO conformance claim: the draft's tier thresholds
    are explicitly "to-be-determined" by the W3C.
  - NO severity-tag assignment: physical-harm/risk/barrier/friction tags
    qualify the draft's core requirements, not WCAG 2.2 findings.
  - The criterion→outcome mapping is OURS. The W3C has published no
    official WCAG 2 → WCAG 3 mapping (transition materials are planned);
    every grouping is a documented approximation.

CLI:
  a11ywcag3.py --from-audit informe.json [--lang es] [-o salida.json]
  a11ywcag3.py --url https://…      # audita primero, luego previsualiza
"""

import argparse
import json
import re
import sys

from .a11yi18n import pair
from .a11ycrit import _SIGNAL_CRIT

TXT = pair('wcag3')  # locales/<lang>.json — community-editable

# borrador contra el que se previsualiza (re-baselinear en cada publicación
# de marzo/septiembre: outcomes, mapa y metadatos)
DRAFT = {
    'standard': 'W3C Accessibility Guidelines (WCAG) 3.0',
    'stage': 'Working Draft — in progress, will change substantially',
    'draft_date': '10 September 2026',
    'url': 'https://www.w3.org/TR/wcag-3.0/',
    'intro': 'https://www.w3.org/WAI/standards-guidelines/wcag/wcag3-intro/',
    # lo que el propio W3C dice sobre la coexistencia: WCAG 3 no sustituye a
    # WCAG 2 y WCAG 2 no quedará obsoleto durante años
    'supersede_note': 'WCAG 3 does not supersede WCAG 2; WCAG 2 will not be '
                      'deprecated for several years after WCAG 3 is final. '
                      'W3C advice: meet WCAG 2.2 now.',
}

# los 46 outcomes del borrador de sept-2026 (§2, Guidelines) — nombres
# EXACTOS del documento; re-baselinear en la próxima publicación
_OUTCOMES = {
    '2.1.1': 'Image alternatives', '2.1.2': 'Figure captions',
    '2.1.3': 'Non-text alternatives', '2.1.4': 'Transcripts',
    '2.1.5': 'Captions', '2.1.6': 'Audio descriptions',
    '2.1.7': 'Sign language', '2.1.8': 'Single sense',
    '2.1.9': 'Accessible media player',
    '2.2.1': 'Text appearance', '2.2.2': 'Text-to-speech',
    '2.2.3': 'Clear language',
    '2.3.1': 'Keyboard focus appearance',
    '2.3.2': 'Pointer focus appearance', '2.3.3': 'Navigating content',
    '2.3.4': 'Expected behavior', '2.3.5': 'Control information',
    '2.4.1': 'Keyboard interface input',
    '2.4.2': 'Physical or cognitive effort when using keyboard',
    '2.4.3': 'Pointer input', '2.4.4': 'Speech and voice input',
    '2.4.5': 'Input operation', '2.4.6': 'Authentication',
    '2.5.1': 'Correct errors', '2.5.2': 'Prevent errors',
    '2.6.1': 'Avoid physical harm',
    '2.7.1': 'Recognizable layouts', '2.7.2': 'User orientation',
    '2.7.3': 'Structure', '2.7.4': 'No obstruction',
    '2.8.1': 'Consistency',
    '2.9.1': 'Avoid exclusionary cognitive tasks', '2.9.2': 'Adequate time',
    '2.9.3': 'Avoid deception', '2.9.4': 'Retain information',
    '2.9.5': 'Complete tasks', '2.9.6': 'Unnecessary steps',
    '2.10.1': 'Risk', '2.10.2': 'Algorithms',
    '2.11.1': 'Help available', '2.11.2': 'Feedback',
    '2.12.1': 'Assistive technology control', '2.12.2': 'Control text',
    '2.12.3': 'Adjustable viewport', '2.12.4': 'Media control',
    '2.12.5': 'Content changes',
}

# criterio WCAG 2.2 → outcomes del borrador. CURADO por a11y-toolkit:
# el W3C no ha publicado mapeo oficial (los materiales de transición están
# planificados). Cubre el 100% de los criterios alcanzables por señales del
# toolkit (pinned por tests/test_wcag3.py) más los evidentes sin señal.
_CRIT_OUTCOME = {
    '1.1.1': ['2.1.1', '2.1.3'],        # alt texto / alternativas no textuales
    '1.2.2': ['2.1.5'],
    '1.2.3': ['2.1.6', '2.1.4'],
    '1.2.4': ['2.1.5'],
    '1.2.5': ['2.1.6'],
    '1.3.1': ['2.7.3'],
    '1.3.2': ['2.7.3'],
    '1.3.3': ['2.2.3'],                 # instrucciones sin rasgos sensoriales
    '1.3.4': ['2.12.3'],
    '1.3.5': ['2.3.5'],
    '1.4.1': ['2.2.1'],                 # "Hue not relied on" es core req del draft
    '1.4.2': ['2.12.4'],
    '1.4.3': ['2.2.1'],
    '1.4.4': ['2.2.1', '2.12.3'],
    '1.4.5': ['2.2.1'],
    '1.4.10': ['2.12.3'],
    '1.4.12': ['2.2.1'],
    '1.4.13': ['2.3.4'],
    '2.1.1': ['2.4.1'],
    '2.1.2': ['2.4.1'],
    '2.1.4': ['2.4.5'],
    '2.2.1': ['2.9.2'],
    '2.2.2': ['2.12.5'],
    '2.3.1': ['2.6.1'],                 # sin señal hoy; la vía del daño físico
    '2.4.1': ['2.3.3'],
    '2.4.2': ['2.7.2'],
    '2.4.3': ['2.3.3'],
    '2.4.4': ['2.3.5'],
    '2.4.5': ['2.3.3'],
    '2.4.6': ['2.7.3', '2.2.3'],
    '2.4.7': ['2.3.1'],
    '2.4.11': ['2.7.4'],
    '2.5.1': ['2.4.3'],
    '2.5.2': ['2.4.3'],
    '2.5.3': ['2.4.4', '2.3.5'],
    '2.5.4': ['2.4.5'],
    '2.5.7': ['2.4.3'],
    '2.5.8': ['2.4.3'],
    '3.1.1': ['2.2.2'],
    '3.1.2': ['2.2.2'],
    '3.2.1': ['2.3.4'],
    '3.2.2': ['2.3.4'],
    '3.2.3': ['2.8.1'],
    '3.2.4': ['2.8.1'],
    '3.2.5': ['2.3.4'],
    '3.2.6': ['2.11.1'],
    '3.3.1': ['2.5.1'],
    '3.3.2': ['2.3.5', '2.5.2'],
    '3.3.3': ['2.5.1'],
    '3.3.4': ['2.5.2'],
    '3.3.7': ['2.9.6'],                 # el draft lo llama "Unnecessary steps"
    '3.3.8': ['2.4.6'],
    '4.1.2': ['2.3.5'],
    '4.1.3': ['2.12.5'],
}

_CODE = re.compile(r'^(\d+\.\d+\.\d+)')


def preview(report, lang='en'):
    """Re-agrupa un informe WCAG 2.2 bajo los outcomes del borrador WCAG 3.

    report: dict de auditoría (con 'findings') — cualquier tool de auditoría
    del toolkit. Devuelve dict SIN score/tier/claim de conformidad.
    """
    t = TXT.get(lang, TXT['en'])
    if not isinstance(report, dict) or not isinstance(report.get('findings'), list):
        return {'error': 'report must be an audit report object with a findings list '
                         '(from a11y_audit_url, a11y_audit_dom, …)',
                'hint': 'audit first, then preview the same report'}

    per_outcome = {}
    unmapped = []
    mapped_count = 0
    for i, f in enumerate(report['findings']):
        if not isinstance(f, dict):
            # nada desaparece en silencio: un finding deforme también se reporta
            unmapped.append({'finding': i, 'signal': None, 'criterion': None,
                             'reason': 'not a finding object'})
            continue
        code = None
        m = _CODE.match(str(f.get('criterion') or ''))
        if m:
            code = m.group(1)
        else:
            sig = str(f.get('signal') or '')
            code = _SIGNAL_CRIT.get(sig)
        if not code or code not in _CRIT_OUTCOME:
            unmapped.append({'finding': i, 'signal': f.get('signal'),
                             'criterion': f.get('criterion')})
            continue
        mapped_count += 1
        for oc in _CRIT_OUTCOME[code]:
            entry = per_outcome.setdefault(
                oc, {'findings': 0, 'high': 0, 'medium': 0, 'low': 0,
                     'signals': set(), 'criteria_22': set()})
            entry['findings'] += 1
            sev = str(f.get('severity') or '').lower()
            # membresía contra la TUPLE de severidades, no contra el dict
            # acumulador: 'findings'/'signals' como severity no pueden colarse
            if sev in ('high', 'medium', 'low'):
                entry[sev] += 1
            entry['signals'].add(str(f.get('signal') or code))
            entry['criteria_22'].add(code)

    def _vers(oc):
        return tuple(int(x) for x in oc.split('.'))

    outcomes = []
    for oc in sorted(per_outcome, key=_vers):
        e = per_outcome[oc]
        outcomes.append({
            'outcome': f"{oc} {_OUTCOMES[oc]}",
            'draft_url': DRAFT['url'],
            'findings': e['findings'],
            'severity': {'high': e['high'], 'medium': e['medium'], 'low': e['low']},
            'signals': sorted(e['signals']),
            'criteria_22': sorted(e['criteria_22']),
        })

    return {
        'mode': 'wcag3-preview',
        'lang': lang,
        'draft': dict(DRAFT),
        'disclaimer': t['disclaimer'],
        'mapping_note': t['mapping_note'],
        'no_score': t['no_score'],
        'conformance_model': {
            'levels': 'single conformance level (no A/AA/AAA in the draft)',
            'core_requirement_tags': t['model_tags'],
            'reporting_tiers': t['model_tiers'],
            'source': DRAFT['intro'],
        },
        'outcomes': outcomes,
        'counts': {
            'findings_total': len(report['findings']),
            'findings_mapped': mapped_count,
            'findings_unmapped': len(unmapped),
            'outcomes_touched': len(outcomes),
            'outcomes_in_draft': len(_OUTCOMES),
        },
        'unmapped': unmapped,
        'source_report': {'url': report.get('url'), 'mode': report.get('mode')},
    }


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--from-audit', help='audit report JSON file (or - for stdin)')
    p.add_argument('--url', help='audit this URL first, then preview')
    p.add_argument('--lang', default='en', choices=['en', 'es'])
    p.add_argument('-o', '--output', help='write the JSON result here')
    a = p.parse_args(argv)
    if not a.from_audit and not a.url:
        p.error('either --from-audit or --url is required')
    if a.url:
        from .a11yaudit import audit_url
        report = audit_url(a.url, lang=a.lang)
        if 'error' in report:
            print(json.dumps({'error': f"audit failed for {a.url}: {report['error']}",
                              'hint': 'fix the URL/network, then retry'}, ensure_ascii=False),
                  file=sys.stderr)
            return 1
    else:
        raw = sys.stdin.read() if a.from_audit == '-' else open(a.from_audit, encoding='utf-8').read()
        report = json.loads(raw)
    res = preview(report, lang=a.lang)
    out = json.dumps(res, ensure_ascii=False, indent=1)
    if a.output:
        with open(a.output, 'w', encoding='utf-8') as f:
            f.write(out)
    else:
        print(out)
    return 0 if 'error' not in res else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
