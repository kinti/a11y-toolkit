#!/usr/bin/env python3
"""Evidence pack — the machine→human handoff object (countersignature-ready).

The design lesson comes from outside: an agent can produce a thorough audit
and still not produce a conformance statement, because conformance needs a
named person behind it, reachable later by a supervising authority. This
module builds the vendor-neutral bridge: a tamper-evident bundle of what the
machines found, what remains for a human, and an empty signature block whose
statement references the pack's own hash.

No third parties, no network, no claim of conformance: the pack IS the thing
any qualified human (the maintainer, a marketplace auditor, a regulator-facing
consultant) reviews and countersigns.

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

_ESTADOS = ('automated-fail', 'automated-review', 'not-flagged', 'manual-only',
            'agent-verified', 'not-run')


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _sha256(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


def empaquetar(informes, snapshot=None, evaluador=None, notas=None, verificados=None, sr_transcript=None):
    """Informes (lista de dicts JSON) → paquete de evidencia contrafirmable.

    verificados: lista de códigos de criterio ("1.4.1", "3.3.1"…) que un
    agente o una persona han verificado manualmente sobre esta muestra
    (protocolo del checklist del skill). El criterio pasa a estado
    'agent-verified' — salvo que una señal automática diera fail, que
    permanece como fail (el fallo no se borra verificando). La fuente
    (agente/humano, fecha) queda registrada en el bloque verificacion."""
    ahora = datetime.now(timezone.utc).isoformat(timespec='seconds')

    # matriz de criterios: los que tocamos (estado según hallazgos) + manuales
    from .a11ycrit import _C as _CAT, effort
    codes_aa = sorted(k for k, v in _CAT.items() if v[0] in ('A', 'AA'))
    modos_incluidos = {inf.get('mode', 'static') for inf in informes}
    tocados = {}
    for inf in informes:
        for h in inf.get('findings', []):
            crit = h.get('criterion')
            if not crit or not isinstance(crit, str):   # informe malformado: saltar
                continue
            code = crit.split(' ')[0]
            texto = h.get('issue', '') or ''
            texto = texto.lower() if isinstance(texto, str) else ''
            estado = 'automated-review' if (h.get('severity') == 'low'
                                            and ('review' in texto or 'revisar' in texto)) \
                else 'automated-fail'
            # el peor estado gana: fail > review
            if tocados.get(code) != 'automated-fail':
                tocados[code] = estado

    verificados = {v.split(' ')[0] for v in (verificados or [])}
    # extraer valores medidos clave de los hallazgos (ratio, ejemplos)
    valores = {}
    for inf in informes:
        for h in inf.get('findings', []):
            code = (h.get('criterion') or '').split(' ')[0]
            if code not in valores:
                val = {}
                if 'ratio' in h.get('issue', '').lower() or ':' in h.get('issue', ''):
                    import re as _re
                    m = _re.search(r'([\d.]+):1', h.get('issue', ''))
                    if m:
                        val['measured'] = f'{m.group(1)}:1'
                ej = h.get('examples', [])
                if ej:
                    val['example'] = str(ej[0])[:80]
                if val:
                    valores[code] = val

    # criterios que requieren modo rendered (si solo corrió static, su estado
    # real es not-run, no not-flagged: la herramienta SÍ tiene señal pero el
    # modo que la produce no se incluyó)
    _RENDERED_ONLY = {'1.4.3', '1.4.12', '1.4.1', '1.3.2', '2.2.2', '2.5.8',
                      '2.4.7', '2.4.11', '3.2.1', '3.2.2'}

    verificados_set = {v.split(' ')[0] for v in (verificados or [])}

    matriz = []
    _manual_codes = {m.split(' ')[0] for m in MANUAL_AA}
    for code in codes_aa:
        if code in _manual_codes:
            continue  # covered by the manual-only rows appended below
        estado = tocados.get(code, 'not-flagged')

        # not-run: el criterio requiere rendered y este pack no lo incluye
        if estado == 'not-flagged' and code in _RENDERED_ONLY and 'rendered' not in modos_incluidos:
            estado = 'not-run'

        # verificados: promueve not-flagged/not-run/manual-only → agent-verified
        # (pero automated-fail permanece: un fallo no se borra verificando)
        if code in verificados_set and estado != 'automated-fail':
            estado = 'agent-verified'

        nota = None
        if estado == 'not-flagged':
            nota = 'not-flagged ≠ pass: no automated signal fired on this sample'
        elif estado == 'not-run':
            nota = ('requires rendered mode (a11y_audit_dom) — this pack only '
                    'includes the static audit, so no signal was tried')
        elif estado == 'agent-verified':
            nota = 'verified against this sample per the manual checklist protocol'

        entrada = {'criterion': f"{code} {_CAT[code][1]['en'][0]}", 'status': estado, 'note': nota}
        ef = effort(code)
        if ef:
            # human-effort class: what the HUMAN still does after the machine's
            # best signal (pricing input for review marketplaces)
            entrada['effort'] = {'class': ef['class'], 'minutes': ef['minutes'],
                                   'why': ef['why']}
        if code in valores:
            entrada['value'] = valores[code]
        matriz.append(entrada)
    manuales_restantes = [m for m in MANUAL_AA if m.split(' ')[0] not in verificados]
    # los not-run son adicionalmente "pendientes" (la máquina no miró)
    for nombre in manuales_restantes:
        fila = {'criterion': nombre, 'status': 'manual-only',
                'note': 'no automated signal exists for this criterion in this toolkit'}
        ef = effort(nombre.split(' ')[0])
        if ef:
            fila['effort'] = {'class': ef['class'], 'minutes': ef['minutes'],
                                'why': ef['why']}
        matriz.append(fila)
    for code in sorted(verificados):
        if any(code in m for m in MANUAL_AA) and not any(m.startswith(code) for m in manuales_restantes):
            nombre = next(m for m in MANUAL_AA if m.startswith(code))
            fila = {'criterion': nombre, 'status': 'agent-verified',
                    'note': 'verified against this sample per the manual checklist protocol'}
            ef = effort(code)
            if ef:
                fila['effort'] = {'class': ef['class'], 'minutes': ef['minutes'],
                                    'why': ef['why']}
            matriz.append(fila)

    resumen = {e: sum(1 for m in matriz if m['status'] == e) for e in _ESTADOS}

    # remaining human review, in minutes: MIN/MED/MAX per class summed over
    # every row a human still has to touch (everything except agent-verified).
    # This is the quote input for a review marketplace: agent output in,
    # priced human scope out.
    _MIN = {'MIN': (1, 3), 'MED': (5, 10), 'MAX': (15, 30)}
    pend = {}
    for m in matriz:
        if m['status'] == 'agent-verified':
            continue
        ef = m.get('effort')
        if ef:
            lo, hi = _MIN[ef['class']]
            pend.setdefault(ef['class'], [0, 0])
            pend[ef['class']][0] += lo
            pend[ef['class']][1] += hi
    esfuerzo_pendiente = {
        'by_class': {k: {'criteria': sum(1 for m in matriz
                                           if m['status'] != 'agent-verified'
                                           and m.get('effort', {}).get('class') == k),
                          'minutes': v}
                      for k, v in sorted(pend.items())},
        'total_minutes': [sum(v[0] for v in pend.values()), sum(v[1] for v in pend.values())],
        'note': ('human review remaining after the machine, per class '
                 '(MIN 1-3, MED 5-10, MAX 15-30 min per criterion)'),
    }

    artefactos = []
    for i, inf in enumerate(informes):
        artefactos.append({'type': f"report:{inf.get('mode', 'static')}",
                           'url': inf.get('url'), 'sha256': _sha256(inf),
                           'score': inf.get('score'),
                           'body': inf})  # embedded: pack self-verifying
    if snapshot:
        artefactos.append({'type': 'snapshot:a11y', 'url': snapshot.get('url'),
                           'sha256': _sha256(snapshot), 'elements': len(snapshot.get('elements', []))})
    if sr_transcript:
        artefactos.append({'type': 'sr_transcript', 'url': sr_transcript.get('url'),
                           'sha256': _sha256(sr_transcript), 'announcements': sr_transcript.get('total', 0),
                           'linearized': sr_transcript.get('announcements', [])[:50]})

    pack = {
        'format': 'a11y-evidence-pack/2',
        'generated': ahora,
        'tool': 'a11y-toolkit (github.com/kinti/a11y-toolkit)',
        'summary': resumen,
        'effort_pending': esfuerzo_pendiente,
        'criteria': matriz,
        'manual_pending': [m['criterion'] for m in matriz if m['status'] == 'manual-only'],
        'verification': ({'source': 'agent', 'protocol': 'skill manual checklist'}
                         if verificados else None),
        'artifacts': artefactos,
        'reviewer': {  # bloque a completar por la persona que firma
            'name': (evaluador or {}).get('name'),
            'credential': (evaluador or {}).get('credential'),
            'review_date': (evaluador or {}).get('review_date'),
            'statement': None,
            'note': ('any countersignature must reference pack.sha256 and state which '
                     'criteria the human reviewed beyond the automated matrix'),
        },
        'notes': notas,
        'notice': ('This pack is evidence, not conformance: it says what machines found '
                  'and what remains for a human. A conformance claim requires the firma '
                  'block completed by a qualified person who reviewed the manual list.'),
    }
    pack['sha256'] = _sha256({k: v for k, v in pack.items() if k != 'sha256'})
    return pack


def main(argv):
    ap = argparse.ArgumentParser(description='Evidence pack (countersignature-ready)')
    ap.add_argument('reports', nargs='+', help='audit report JSON files (any mode)')
    ap.add_argument('--snapshot', help='a11y snapshot JSON (optional)')
    ap.add_argument('--evaluador', help='JSON: {"name":…, "credential":…, "review_date":…}')
    ap.add_argument('-o', '--out', default='evidence-pack.json')
    a = ap.parse_args(argv)
    informes = [json.load(open(f, encoding='utf-8')) for f in a.reports]
    snapshot = json.load(open(a.snapshot, encoding='utf-8')) if a.snapshot else None
    evaluador = json.loads(a.evaluador) if a.evaluador else None
    pack = empaquetar(informes, snapshot=snapshot, evaluador=evaluador)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    print(json.dumps({'pack': a.out, 'sha256': pack['sha256'],
                      'summary': pack['summary']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
