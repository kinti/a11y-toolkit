#!/usr/bin/env python3
"""Evidence pack — the machine→human handoff object for WCAG conformance work.

The design lesson comes from outside: an agent can produce a thorough audit
and still not produce a conformance statement, because conformance needs a
named person behind it, reachable later by a supervising authority. This
module builds the vendor-neutral bridge: a tamper-evident bundle of what the
machines found, what remains for a human, and an empty signature block whose
statement references the pack's own hash.

No third parties, no network, no claim of conformance: the pack IS the thing
any qualified human (the maintainer, a marketplace auditor, a regulator-facing
consultant) reviews and signs.

  criterios: full matrix — every WCAG 2.2 A/AA criterion with a status:
             automated-fail / automated-review / not-flagged / manual-only
             (not-flagged ≠ pass: it means no signal fired on this sample)
  artefactos: the input reports with their SHA-256, timestamps, tool version
  firma: empty human block (nombre, credencial, fecha, alcance) — any
         signature must reference pack.sha256 to be verifiable
  pack.sha256: hash of the pack without the hash field itself

CLI:
  a11yevidence.py audit.json [otro.json …] [--snapshot snap.json] -o pack.json
"""

import argparse
import hashlib
import json

from .a11yaudit import normalize_report  # noqa: E402  (compat 5.10)
import sys
from datetime import datetime, timezone

# Criterios A/AA de WCAG 2.2 SIN señal automatizada en este toolkit:
# lo que toda evaluación humana pendiente debe cubrir, digan lo que digan
# las herramientas.
MANUAL_AA = [
    '1.2.1 Audio-only and Video-only (Prerecorded)',
    '1.2.4 Captions (Live)',
    '2.3.1 Three Flashes or Below Threshold',
    '3.3.7 Redundant Entry',
]

_STATES = ('automated-fail', 'automated-review', 'not-flagged', 'manual-only',
            'agent-verified', 'not-run')


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _sha256(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


def build_pack(reports, snapshot=None, reviewer=None, notes=None, verified=None,
               sr_transcript=None, lang='en'):
    """Informes (lista de dicts JSON) → paquete de evidencia verificable.

    verificados: lista de códigos de criterio ("1.4.1", "3.3.1"…) que un
    agente o una persona han verificado manualmente sobre esta muestra
    (protocolo del checklist del skill). El criterio pasa a estado
    'agent-verified' — salvo que una señal automática diera fail, que
    permanece como fail (el fallo no se borra verificando). La fuente
    (agente/humano, fecha) queda registrada en el bloque verificacion."""
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    from . import a11yi18n
    tx = a11yi18n.pack(lang).get('evidence', {})
    language = lang if tx else 'en'
    tx = tx or a11yi18n.pack('en')['evidence']
    reports = [normalize_report(i) for i in reports]  # compat 5.10: señales previas al rename

    # matriz de criterios: los que tocamos (estado según hallazgos) + manuales
    from .a11ycrit import _C as _CAT, effort
    codes_aa = sorted(k for k, v in _CAT.items() if v[0] in ('A', 'AA'))
    modes_included = {inf.get('mode', 'static') for inf in reports}
    touched = {}
    for inf in reports:
        for h in inf.get('findings', []):
            if (h.get('status') == 'rejected'
                    or h.get('disprover_status') in ('rejected', 'not-rechecked')):
                # un hallazgo desmentido (o no reverificado) no puede volver a
                # convertirse en fallo dentro del pack
                continue
            crit = h.get('criterion')
            if not crit or not isinstance(crit, str):   # informe malformado: saltar
                continue
            code = crit.split(' ')[0]
            severity = h.get('severity')
            state = 'automated-review' if severity == 'low' else 'automated-fail'
            # el peor estado gana: fail > review
            if touched.get(code) != 'automated-fail':
                touched[code] = state

    verified = {v.split(' ')[0] for v in (verified or [])}
    # extraer valores medidos clave de los hallazgos (ratio, ejemplos)
    values = {}
    for inf in reports:
        for h in inf.get('findings', []):
            code = (h.get('criterion') or '').split(' ')[0]
            if code not in values:
                val = {}
                if 'ratio' in h.get('issue', '').lower() or ':' in h.get('issue', ''):
                    import re as _re
                    m = _re.search(r'([\d.]+):1', h.get('issue', ''))
                    if m:
                        val['measured'] = f'{m.group(1)}:1'
                _ex_list = h.get('examples', [])
                if _ex_list:
                    val['example'] = str(_ex_list[0])[:80]
                if val:
                    values[code] = val

    # criterios que requieren modo rendered (si solo corrió static, su estado
    # real es not-run, no not-flagged: la herramienta SÍ tiene señal pero el
    # modo que la produce no se incluyó)
    from .a11ycrit import RENDERED_ONLY as _RENDERED_ONLY  # canónico (a11ycrit)

    verified_set = {v.split(' ')[0] for v in (verified or [])}

    matrix = []
    _manual_codes = {m.split(' ')[0] for m in MANUAL_AA}
    for code in codes_aa:
        if code in _manual_codes:
            continue  # covered by the manual-only rows appended below
        state = touched.get(code, 'not-flagged')

        # not-run: el criterio requiere rendered y este pack no lo incluye
        if state == 'not-flagged' and code in _RENDERED_ONLY and 'rendered' not in modes_included:
            state = 'not-run'

        # verificados: promueve not-flagged/not-run/manual-only → agent-verified
        # (pero automated-fail permanece: un fallo no se borra verificando)
        if code in verified_set and state != 'automated-fail':
            state = 'agent-verified'

        note = None
        if state == 'not-flagged':
            note = tx['not_flagged']
        elif state == 'not-run':
            note = ('requires rendered mode (a11y_audit_dom) — this pack only '
                    'includes the static audit, so no signal was tried')
        elif state == 'agent-verified':
            note = tx['verified']

        entry = {'criterion': f"{code} {(_CAT[code][1].get(language) or _CAT[code][1]['en'])[0]}",
                 'status': state, 'note': note}
        ef = effort(code)
        if ef:
            # human-effort class: what the HUMAN still does after the machine's
            # best signal (pricing input for human-review scoping)
            entry['effort'] = {'class': ef['class'], 'minutes': ef['minutes'],
                                   'why': ef['why']}
        if code in values:
            entry['value'] = values[code]
        matrix.append(entry)
    manual_remaining = [m for m in MANUAL_AA if m.split(' ')[0] not in verified]
    # los not-run son adicionalmente "pendientes" (la máquina no miró)
    for name in manual_remaining:
        code = name.split(' ')[0]
        # el nombre viaja en el idioma del pack como el resto de la matriz:
        # manual_pending también es un entregable que va al cliente
        row = {'criterion': f"{code} {(_CAT[code][1].get(language) or _CAT[code][1]['en'])[0]}",
               'status': 'manual-only',
                'note': tx['no_signal']}
        ef = effort(code)
        if ef:
            row['effort'] = {'class': ef['class'], 'minutes': ef['minutes'],
                                'why': ef['why']}
        matrix.append(row)
    for code in sorted(verified):
        if any(code in m for m in MANUAL_AA) and not any(m.startswith(code) for m in manual_remaining):
            row = {'criterion': f"{code} {(_CAT[code][1].get(language) or _CAT[code][1]['en'])[0]}",
                   'status': 'agent-verified',
                    'note': 'verified against this sample per the manual checklist protocol'}
            ef = effort(code)
            if ef:
                row['effort'] = {'class': ef['class'], 'minutes': ef['minutes'],
                                    'why': ef['why']}
            matrix.append(row)

    summary = {e: sum(1 for m in matrix if m['status'] == e) for e in _STATES}

    # remaining human review, in minutes: MIN/MED/MAX per class summed over
    # every row a human still has to touch (everything except agent-verified).
    # This is the scope input for human review: agent output in,
    # priced human scope out.
    _MIN = {'MIN': (1, 3), 'MED': (5, 10), 'MAX': (15, 30)}
    pend = {}
    for m in matrix:
        if m['status'] == 'agent-verified':
            continue
        ef = m.get('effort')
        if ef:
            lo, hi = _MIN[ef['class']]
            pend.setdefault(ef['class'], [0, 0])
            pend[ef['class']][0] += lo
            pend[ef['class']][1] += hi
    pending_effort = {
        'by_class': {k: {'criteria': sum(1 for m in matrix
                                           if m['status'] != 'agent-verified'
                                           and m.get('effort', {}).get('class') == k),
                          'minutes': v}
                      for k, v in sorted(pend.items())},
        'total_minutes': [sum(v[0] for v in pend.values()), sum(v[1] for v in pend.values())],
        'note': tx['manual_remaining'],
    }

    artifacts = []
    for i, inf in enumerate(reports):
        artifacts.append({'type': f"report:{inf.get('mode', 'static')}",
                           'url': inf.get('url'), 'sha256': _sha256(inf),
                           'score': inf.get('score'),
                           'body': inf})  # embedded: pack self-verifying
    if snapshot:
        artifacts.append({'type': 'snapshot:a11y', 'url': snapshot.get('url'),
                           'sha256': _sha256(snapshot), 'elements': len(snapshot.get('elements', []))})
    if sr_transcript:
        artifacts.append({'type': 'sr_transcript', 'url': sr_transcript.get('url'),
                           'sha256': _sha256(sr_transcript), 'announcements': sr_transcript.get('total', 0),
                           'linearized': sr_transcript.get('announcements', [])[:50]})

    pack = {
        'format': 'a11y-evidence-pack/2',
        'lang': language,
        'generated': now,
        'tool': 'a11y-toolkit (github.com/kinti/a11y-toolkit)',
        'summary': summary,
        'effort_pending': pending_effort,
        'criteria': matrix,
        'manual_pending': [m['criterion'] for m in matrix if m['status'] == 'manual-only'],
        'verification': ({'source': 'agent', 'protocol': 'skill manual checklist'}
                         if verified else None),
        'artifacts': artifacts,
        'reviewer': {  # bloque a completar por la persona que firma
            'name': (reviewer or {}).get('name'),
            'credential': (reviewer or {}).get('credential'),
            'review_date': (reviewer or {}).get('review_date'),
            'statement': None,
            'note': tx['reviewer_note'],
        },
        'notes': notes,
        'notice': tx['notice'],
    }
    # the seal excludes sha256 AND the clock ('generated'): re-emitting the
    # same evidence later MUST produce the same sha (re-emission, not a new row)
    pack['sha256'] = _sha256({k: v for k, v in pack.items()
                              if k not in ('sha256', 'generated')})
    return pack


def main(argv):
    ap = argparse.ArgumentParser(description='Evidence pack (verifiable handoff)')
    ap.add_argument('reports', nargs='+', help='audit report JSON files (any mode)')
    ap.add_argument('--snapshot', help='a11y snapshot JSON (optional)')
    ap.add_argument('--reviewer', help='JSON: {"name":…, "credential":…, "review_date":…}')
    ap.add_argument('-o', '--out', default='evidence-pack.json')
    a = ap.parse_args(argv)
    reports = [json.load(open(f, encoding='utf-8')) for f in a.reports]
    snapshot = json.load(open(a.snapshot, encoding='utf-8')) if a.snapshot else None
    reviewer = json.loads(a.reviewer) if a.reviewer else None
    pack = build_pack(reports, snapshot=snapshot, reviewer=reviewer)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    print(json.dumps({'pack': a.out, 'sha256': pack['sha256'],
                      'summary': pack['summary']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
