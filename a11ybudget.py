#!/usr/bin/env python3
"""Presupuesto de accesibilidad — la lección de Google SRE aplicada a WCAG.

La parálisis clásica: la auditoría encuentra 40 fallos, nadie puede arreglarlos
esta semana, así que nadie activa el control. El presupuesto rompe el bloqueo:
se ACEPTA la línea base actual y solo lo NUEVO bloquea. Cada arreglo baja la
base; cada regresión grita.

Fichero de presupuesto (budget.json):

  {
    "url": "https://mysite",
    "senales": ["imgs_alt", "field_label"],       // base aceptada
    "bloqueantes": ["alta", "media"],              // severidades que bloquean
    "max_nuevos": 0,                               // cuántos nuevos se toleran
    "fecha_revision": "2026-12-07"                 // caducidad de la base (opcional)
  }

Genera la base con:  a11y audit --url https://mysite | python3 a11ybudget.py --init
Compara con:         a11y budget --budget budget.json --audit audit.json

Sólo compara claves estables ('senal') y severidades, no textos.
"""

import argparse
import datetime
import json
import sys


def init(auditoria):
    """Informe (o site) → fichero de presupuesto inicial."""
    paginas = auditoria.get('informes') if 'informes' in auditoria else [auditoria]
    senales = sorted({h['senal'] for pg in paginas for h in pg.get('hallazgos', [])})
    return {
        'url': auditoria.get('url', ''),
        'senales': senales,
        'bloqueantes': ['alta', 'media'],
        'max_nuevos': 0,
        'fecha_revision': (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
    }


def comparar(presupuesto, auditoria, hoy=None):
    """Presupuesto vs informe actual → veredicto ok/bloqueado con el detalle."""
    paginas = auditoria.get('informes') if 'informes' in auditoria else [auditoria]
    base = set(presupuesto.get('senales', []))
    bloqueantes = set(presupuesto.get('bloqueantes', ['alta', 'media']))
    actuales = {}
    for pg in paginas:
        for h in pg.get('hallazgos', []):
            actuales.setdefault(h['senal'], []).append(h['severidad'])
    nuevos = sorted(s for s in actuales if s not in base)
    resueltos = sorted(base - set(actuales))
    nuevos_bloqueantes = [s for s in nuevos
                          if any(sev in bloqueantes for sev in actuales[s])]
    max_nuevos = int(presupuesto.get('max_nuevos', 0))
    ok = len(nuevos_bloqueantes) <= max_nuevos
    caducada = False
    fecha = presupuesto.get('fecha_revision')
    if fecha:
        caducada = (hoy or datetime.date.today().isoformat()) > fecha
    return {
        'ok': ok and not caducada,
        'url': auditoria.get('url', presupuesto.get('url', '')),
        'nuevos': nuevos,
        'nuevos_bloqueantes': nuevos_bloqueantes,
        'resueltos': resueltos,
        'resumen': {
            'base': len(base),
            'actuales': len(actuales),
            'nuevos': len(nuevos),
            'resueltos': len(resueltos),
        },
        'base_caducada': caducada,
        'nota': ('ok=false: there are new blocking findings (or the baseline expired). '
                 'ok=true: nothing new vs the accepted baseline — fix baseline items '
                 'and re-run --init to lower it.'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--init', action='store_true',
                    help='genera el presupuesto desde un informe (stdin o --audit)')
    ap.add_argument('--budget', default='budget.json', help='fichero de presupuesto')
    ap.add_argument('--audit', help='informe JSON del auditor')
    ap.add_argument('--url', help='auditar esta URL al vuelo')
    a = ap.parse_args(argv)
    if a.init:
        inform = None
        if not sys.stdin.isatty():
            inform = json.loads(sys.stdin.read())
        elif a.audit:
            with open(a.audit, encoding='utf-8') as f:
                inform = json.load(f)
        if not inform:
            print('necesito el informe por stdin o --audit fichero')
            return 1
        print(json.dumps(init(inform), ensure_ascii=False, indent=1))
        return 0
    if not (a.audit or a.url):
        print('necesito --audit informe.json o --url https://…')
        return 1
    with open(a.budget, encoding='utf-8') as f:
        presupuesto = json.load(f)
    if a.audit:
        with open(a.audit, encoding='utf-8') as f:
            informe = json.load(f)
    else:
        from a11yaudit import audit_url
        informe = audit_url(a.url)
    veredicto = comparar(presupuesto, informe)
    print(json.dumps(veredicto, ensure_ascii=False, indent=1))
    return 0 if veredicto['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
