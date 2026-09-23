#!/usr/bin/env python3
"""Coverage ledger — accumulated audit knowledge across runs (Cloudflare pattern).

The lesson from Cloudflare's security-audit-skill: no single pass is complete,
and prior runs should inform (not replace) the current one. This module
maintains a persistent ledger of what has been audited, when, and with what
result — so subsequent runs can:

  - Skip unchanged criteria on unchanged pages (carry forward)
  - Re-audit pages whose hash changed
  - Target gaps (criteria never checked on a page)

The ledger is a JSON file you keep next to your project. It integrates with
the evidence pack: a ledger IS the evidence pack accumulated over time.

CLI:
  a11yledger.py record --url https://x --audit report.json [--ledger ledger.json]
  a11yledger.py gaps --url https://x [--ledger ledger.json]
  a11yledger.py summary [--ledger ledger.json]
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def _cargar(ruta='a11y-ledger.json'):
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return {'version': 1, 'entries': {}, 'history': []}


def _guardar(ledger, ruta='a11y-ledger.json'):
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)


def _hash_url(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def record(url, informe, ledger=None, ruta='a11y-ledger.json'):
    """Record an audit result in the ledger."""
    if ledger is None:
        ledger = _cargar(ruta)
    ahora = datetime.now(timezone.utc).isoformat(timespec='seconds')
    clave = _hash_url(url)

    # señales activas y score
    senales = sorted({h['signal'] for h in informe.get('findings', [])})
    score = informe.get('score')

    entrada = {
        'url': url,
        'ultimo_audit': ahora,
        'score': score,
        'previous_score': ledger['entries'].get(clave, {}).get('score'),
        'active_signals': senales,
        'resolved_signals': sorted(
            set(ledger['entries'].get(clave, {}).get('active_signals', [])) - set(senales)
        ),
        'mode': informe.get('mode', 'static'),
        'disprover': informe.get('disprover'),
    }

    ledger['entries'][clave] = entrada
    ledger['history'].append({
        'ts': ahora, 'url': url, 'score': score,
        'change': 'nuevo' if entrada['previous_score'] is None else
                  f"{entrada['previous_score']}→{score}",
        'resolved': len(entrada['resolved_signals']),
    })
    _guardar(ledger, ruta)
    return entrada


def gaps(url, ledger=None, ruta='a11y-ledger.json'):
    """What has never been checked on this URL?"""
    if ledger is None:
        ledger = _cargar(ruta)
    from .a11yaudit import CRIT
    clave = _hash_url(url)
    entrada = ledger['entries'].get(clave)
    if not entrada:
        return {'url': url, 'status': 'nunca_auditado',
                'criteria_without_signal': len(CRIT['en'])}
    auditadas = set(entrada.get('active_signals', []))
    return {
        'url': url,
        'status': 'auditado',
        'ultimo': entrada['ultimo_audit'],
        'score': entrada['score'],
        'resolved_signals': entrada['resolved_signals'],
        'note': ('re-audit this URL if its content changed since '
                 + entrada['ultimo_audit']),
    }


def summary(ledger=None, ruta='a11y-ledger.json'):
    """Summary of the ledger."""
    if ledger is None:
        ledger = _cargar(ruta)
    entradas = ledger['entries']
    if not entradas:
        return {'total_urls': 0, 'note': 'ledger empty — run your first audit'}
    scores = [e.get('score', 0) for e in entradas.values() if e.get('score') is not None]
    return {
        'total_urls': len(entradas),
        'mean_score': round(sum(scores) / len(scores)) if scores else None,
        'score_peor': min(scores) if scores else None,
        'score_mejor': max(scores) if scores else None,
        'total_resueltas': sum(len(e.get('resolved_signals', [])) for e in entradas.values()),
        'recent': ledger['history'][-5:],
    }


def main(argv):
    ap = argparse.ArgumentParser(description='Coverage ledger')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s1 = sub.add_parser('record')
    s1.add_argument('--url', required=True)
    s1.add_argument('--audit', required=True, help='audit report JSON file')
    s1.add_argument('--ledger', default='a11y-ledger.json')
    s2 = sub.add_parser('gaps')
    s2.add_argument('--url', required=True)
    s2.add_argument('--ledger', default='a11y-ledger.json')
    s3 = sub.add_parser('summary')
    s3.add_argument('--ledger', default='a11y-ledger.json')
    a = ap.parse_args(argv)
    if a.cmd == 'record':
        with open(a.audit, encoding='utf-8') as f:
            informe = json.load(f)
        r = record(a.url, informe, ruta=a.ledger)
        print(json.dumps(r, ensure_ascii=False, indent=1))
    elif a.cmd == 'gaps':
        print(json.dumps(gaps(a.url, ruta=a.ledger), ensure_ascii=False, indent=1))
    elif a.cmd == 'summary':
        print(json.dumps(summary(ruta=a.ledger), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
