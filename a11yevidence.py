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
    '1.4.12 Text Spacing',
    '1.4.13 Content on Hover or Focus',
    '2.1.4 Character Key Shortcuts',
    '2.3.1 Three Flashes or Below Threshold',
    '2.4.6 Headings and Labels (quality, not structure)',
    '2.5.7 Dragging Movements',
    '3.2.1 On Focus',
    '3.2.2 On Input',
    '3.3.4 Error Prevention (Legal, Financial, Data)',
    '3.3.7 Redundant Entry',
    '4.1.3 Status Messages (beyond scroll-mode observer)',
]

_ESTADOS = ('automated-fail', 'automated-review', 'not-flagged', 'manual-only',
            'agent-verified')


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _sha256(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


def empaquetar(informes, snapshot=None, evaluador=None, notas=None, verificados=None):
    """Informes (lista de dicts JSON) → paquete de evidencia contrafirmable.

    verificados: lista de códigos de criterio ("1.4.1", "3.3.1"…) que un
    agente o una persona han verificado manualmente sobre esta muestra
    (protocolo del checklist del skill). El criterio pasa a estado
    'agent-verified' — salvo que una señal automática diera fail, que
    permanece como fail (el fallo no se borra verificando). La fuente
    (agente/humano, fecha) queda registrada en el bloque verificacion."""
    ahora = datetime.now(timezone.utc).isoformat(timespec='seconds')

    # matriz de criterios: los que tocamos (estado según hallazgos) + manuales
    from a11yaudit import CRIT
    tocados = {}
    for inf in informes:
        for h in inf.get('hallazgos', []):
            crit = h.get('criterio')
            if not crit or not isinstance(crit, str):   # informe malformado: saltar
                continue
            code = crit.split(' ')[0]
            texto = h.get('hallazgo', '') or ''
            texto = texto.lower() if isinstance(texto, str) else ''
            estado = 'automated-review' if (h.get('severidad') == 'baja'
                                            and ('review' in texto or 'revisar' in texto)) \
                else 'automated-fail'
            # el peor estado gana: fail > review
            if tocados.get(code) != 'automated-fail':
                tocados[code] = estado

    verificados = {v.split(' ')[0] for v in (verificados or [])}
    matriz = []
    for code in sorted(CRIT['en']):
        estado = tocados.get(code, 'not-flagged')
        if code in verificados and estado != 'automated-fail':
            estado = 'agent-verified'
        nota = None
        if estado == 'not-flagged':
            nota = 'not-flagged ≠ pass: no automated signal fired on this sample'
        elif estado == 'agent-verified':
            nota = 'verified against this sample per the manual checklist protocol'
        matriz.append({'criterio': CRIT['en'][code], 'estado': estado,
                       'nota': nota})
    manuales_restantes = [m for m in MANUAL_AA if m.split(' ')[0] not in verificados]
    for nombre in manuales_restantes:
        matriz.append({'criterio': nombre, 'estado': 'manual-only',
                       'nota': 'no automated signal exists for this criterion in this toolkit'})
    for code in sorted(verificados):
        if any(code in m for m in MANUAL_AA) and not any(m.startswith(code) for m in manuales_restantes):
            matriz.append({'criterio': next(m for m in MANUAL_AA if m.startswith(code)),
                           'estado': 'agent-verified',
                           'nota': 'verified against this sample per the manual checklist protocol'})

    resumen = {e: sum(1 for m in matriz if m['estado'] == e) for e in _ESTADOS}

    artefactos = []
    for i, inf in enumerate(informes):
        artefactos.append({'tipo': f"informe:{inf.get('modo', 'static')}",
                           'url': inf.get('url'), 'sha256': _sha256(inf),
                           'score': inf.get('score')})
    if snapshot:
        artefactos.append({'tipo': 'snapshot:a11y', 'url': snapshot.get('url'),
                           'sha256': _sha256(snapshot), 'elementos': len(snapshot.get('elementos', []))})

    pack = {
        'formato': 'a11y-evidence-pack/1',
        'generado': ahora,
        'herramienta': 'a11y-toolkit (github.com/kinti/a11y-toolkit)',
        'resumen': resumen,
        'criterios': matriz,
        'manual_pendiente': [m['criterio'] for m in matriz if m['estado'] == 'manual-only'],
        'verificacion': ({'fuente': 'agent', 'protocolo': 'skill manual checklist'}
                         if verificados else None),
        'artefactos': artefactos,
        'evaluador': {  # bloque a completar por la persona que firma
            'nombre': (evaluador or {}).get('nombre'),
            'credencial': (evaluador or {}).get('credencial'),
            'fecha_revision': (evaluador or {}).get('fecha_revision'),
            'declaracion': None,
            'nota': ('any countersignature must reference pack.sha256 and state which '
                     'criteria the human reviewed beyond the automated matrix'),
        },
        'notas': notas,
        'aviso': ('This pack is evidence, not conformance: it says what machines found '
                  'and what remains for a human. A conformance claim requires the firma '
                  'block completed by a qualified person who reviewed the manual list.'),
    }
    pack['sha256'] = _sha256({k: v for k, v in pack.items() if k != 'sha256'})
    return pack


def main(argv):
    ap = argparse.ArgumentParser(description='Evidence pack (countersignature-ready)')
    ap.add_argument('informes', nargs='+', help='audit report JSON files (any mode)')
    ap.add_argument('--snapshot', help='a11y snapshot JSON (optional)')
    ap.add_argument('--evaluador', help='JSON: {"nombre":…, "credencial":…, "fecha_revision":…}')
    ap.add_argument('-o', '--out', default='evidence-pack.json')
    a = ap.parse_args(argv)
    informes = [json.load(open(f, encoding='utf-8')) for f in a.informes]
    snapshot = json.load(open(a.snapshot, encoding='utf-8')) if a.snapshot else None
    evaluador = json.loads(a.evaluador) if a.evaluador else None
    pack = empaquetar(informes, snapshot=snapshot, evaluador=evaluador)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    print(json.dumps({'pack': a.out, 'sha256': pack['sha256'],
                      'resumen': pack['resumen']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
