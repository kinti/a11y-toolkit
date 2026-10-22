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


import tempfile

from .a11yaudit import normalize_signal  # noqa: E402  (compat 5.10)

# lock por ruta: multi-hilo siempre; multi-proceso en POSIX (fcntl). El
# SaaS programa auditorías mientras el panel escribe — sin esto, dos
# escrituras simultáneas dejaban un JSON truncado (revisión externa 2026-10).
_LOCKS = {}

from contextlib import contextmanager


@contextmanager
def _lock(path):
    import threading
    lk = _LOCKS.setdefault(os.path.abspath(path), threading.Lock())
    with lk:
        fd = None
        try:
            try:
                import fcntl
                fd = open(os.path.abspath(path) + '.lock', 'w')
                fcntl.flock(fd, fcntl.LOCK_EX)
            except ImportError:
                pass  # Windows: solo lock de hilo (documentado)
            yield
        finally:
            if fd:
                fd.close()  # libera el flock


def _load(path='a11y-ledger.json'):
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                ledger = json.load(f)
            for e in ledger.get('entries', {}).values():
                e['active_signals'] = sorted(normalize_signal(x) for x in e.get('active_signals', []))
                e['resolved_signals'] = sorted(normalize_signal(x) for x in e.get('resolved_signals', []))
            # renames de claves 5.11.0 (por si un proceso antiguo reescribe después)
            e['last_audit'] = e.pop('ultimo_audit') if 'ultimo_audit' in e else e.get('last_audit')
            return ledger
        except json.JSONDecodeError:
            # corrupto (crash a mitad de escritura de una versión anterior):
            # no arrastrar la corrupción — aislar y empezar limpio
            os.replace(path, path + '.corrupto-' + datetime.now(timezone.utc)
                       .strftime('%Y%m%dT%H%M%SZ'))
            return {'version': 1, 'entries': {}, 'history': []}
    return {'version': 1, 'entries': {}, 'history': []}


def _save(ledger, path='a11y-ledger.json'):
    # escritura atómica: tempfile EN EL MISMO DIRECTORIO + os.replace —
    # un crash a mitad nunca deja el fichero a medias
    d = os.path.dirname(os.path.abspath(path)) or '.'
    temporal = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=d,
                                         delete=False, suffix='.tmp') as f:
            temporal = f.name
            json.dump(ledger, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, path)
    except BaseException:
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)
        raise


def record(url, report, ledger=None, path='a11y-ledger.json'):
    """Record an audit result in the ledger (thread/process safe)."""
    with _lock(path):
        return _record(url, report, ledger=ledger, path=path)


def _hash_url(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _record(url, report, ledger=None, path='a11y-ledger.json'):
    if ledger is None:
        ledger = _load(path)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    entry_key = _hash_url(url)

    # señales activas y score
    signals = sorted({normalize_signal(h.get('signal', '')) for h in report.get('findings', [])})
    score = report.get('score')

    entry = {
        'url': url,
        'last_audit': now,
        'score': score,
        'previous_score': ledger['entries'].get(entry_key, {}).get('score'),
        'active_signals': signals,
        'resolved_signals': sorted(
            set(ledger['entries'].get(entry_key, {}).get('active_signals', [])) - set(signals)
        ),
        'mode': report.get('mode', 'static'),
        'disprover': report.get('disprover'),
    }

    ledger['entries'][entry_key] = entry
    ledger['history'].append({
        'ts': now, 'url': url, 'score': score,
        'change': 'new' if entry['previous_score'] is None else
                  f"{entry['previous_score']}→{score}",
        'resolved': len(entry['resolved_signals']),
    })
    _save(ledger, path)
    return entry


def gaps(url, ledger=None, path='a11y-ledger.json'):
    """What has never been checked on this URL?"""
    if ledger is None:
        ledger = _load(path)
    from .a11yaudit import CRIT
    entry_key = _hash_url(url)
    entry = ledger['entries'].get(entry_key)
    if not entry:
        return {'url': url, 'status': 'never_audited',
                'criteria_without_signal': len(CRIT['en'])}
    auditadas = set(entry.get('active_signals', []))
    return {
        'url': url,
        'status': 'audited',
        'last_audit': entry.get('last_audit') or entry.get('ultimo_audit'),
        'score': entry['score'],
        'resolved_signals': entry.get('resolved_signals', []),
        'note': ('re-audit this URL if its content changed since '
                 + (entry.get('last_audit') or entry.get('ultimo_audit'))),
    }


def summary(ledger=None, path='a11y-ledger.json'):
    """Summary of the ledger."""
    if ledger is None:
        ledger = _load(path)
    entries = ledger['entries']
    if not entries:
        return {'total_urls': 0, 'note': 'ledger empty — run your first audit'}
    scores = [e.get('score', 0) for e in entries.values() if e.get('score') is not None]
    return {
        'total_urls': len(entries),
        'mean_score': round(sum(scores) / len(scores)) if scores else None,
        'worst_score': min(scores) if scores else None,
        'best_score': max(scores) if scores else None,
        'total_resolved': sum(len(e.get('resolved_signals', [])) for e in entries.values()),
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
            report = json.load(f)
        r = record(a.url, report, path=a.ledger)
        print(json.dumps(r, ensure_ascii=False, indent=1))
    elif a.cmd == 'gaps':
        print(json.dumps(gaps(a.url, path=a.ledger), ensure_ascii=False, indent=1))
    elif a.cmd == 'summary':
        print(json.dumps(summary(path=a.ledger), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
