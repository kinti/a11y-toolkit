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
  a11yledger.py recurrence [--ledger ledger.json]
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


import tempfile

from .a11yaudit import normalize_signal  # noqa: E402  (compat 5.10)

# per-path lock: always multi-thread; multi-process on POSIX (fcntl).
# Without it, two concurrent writes left a truncated JSON (external review
# 2026-10) — schedulers and interactive writers coexist here.
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
                e['resolutions'] = {normalize_signal(k): v for k, v in (e.get('resolutions') or {}).items()}
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
    prev = ledger['entries'].get(entry_key, {})

    # resoluciones PERSISTENTES (señal→{resolved_on, seen_count}): antes se
    # recalculaban solo contra el audit anterior y la resolución se olvidaba
    # tras UN audit limpio más (la evidencia de cuándo se arregló se evaporaba).
    # Ahora: señal ausente del último audit pero presente en el historial
    # sigue «resolved» con su resolved_on ORIGINAL.
    resolutions = {normalize_signal(s): (dict(v) if isinstance(v, dict)
                                         else {'resolved_on': v, 'seen_count': 1})
                   for s, v in (prev.get('resolutions') or {}).items()}
    if not resolutions and prev.get('resolved_signals'):
        # ledger legado sin dict: sembrar desde la lista (fecha más antigua
        # disponible = el último audit registrado antes de esta llamada)
        resolutions = {s: {'resolved_on': prev.get('last_audit')
                           or prev.get('ultimo_audit'), 'seen_count': 1}
                       for s in prev['resolved_signals']}
    for s in signals:            # volvió a estar activa → la resolución caduca
        resolutions.pop(s, None)
    ever_seen = set(resolutions) | set(prev.get('active_signals', []))
    for s in ever_seen - set(signals):
        if s in resolutions:     # sigue ausente: la resolución original aguanta
            resolutions[s]['seen_count'] = int(resolutions[s].get('seen_count', 1)) + 1
        else:
            resolutions[s] = {'resolved_on': now, 'seen_count': 1}

    entry = {
        'url': url,
        'last_audit': now,
        'score': score,
        'previous_score': prev.get('score'),
        'active_signals': signals,
        'resolved_signals': sorted(resolutions),
        'resolutions': resolutions,
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
    """What has never been checked on this URL?

    For an audited URL the ledger knows every signal that EVER fired on it
    (active now or resolved in history): mapped through the signal→criterion
    table that is the complement against the A/AA catalog — the honest
    target list for the next pass. A signal we cannot map (unknown id) is
    skipped, never guessed."""
    if ledger is None:
        ledger = _load(path)
    from .a11yaudit import CRIT
    entry_key = _hash_url(url)
    entry = ledger['entries'].get(entry_key)
    if not entry:
        return {'url': url, 'status': 'never_audited',
                'criteria_without_signal': len(CRIT['en'])}
    from .a11ycrit import _C, _SIGNAL_CRIT  # read-only: el mapa señal→criterio
    ever_signaled = set(entry.get('active_signals', [])) \
        | set(entry.get('resolutions') or {})
    checked = {_SIGNAL_CRIT[s] for s in ever_signaled if s in _SIGNAL_CRIT}
    aa = {code for code, v in _C.items() if v[0] in ('A', 'AA')}
    return {
        'url': url,
        'status': 'audited',
        'last_audit': entry.get('last_audit') or entry.get('ultimo_audit'),
        'score': entry['score'],
        'resolved_signals': entry.get('resolved_signals', []),
        'criteria_with_signal': sorted(checked),
        'criteria_without_signal': sorted(aa - checked),
        'note': ('re-audit this URL if its content changed since '
                 + (entry.get('last_audit') or entry.get('ultimo_audit'))
                 + '. criteria_without_signal = A/AA criteria with no engine '
                   'signal (active or resolved) ever recorded here — many are '
                   'manual-only by nature; they are targets, not failures'),
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


def recurrence(ledger=None, path='a11y-ledger.json'):
    """Chronic signals across urls + hot urls + review queue.

    The deterministic core of "predictive guardrails" — no ML: the ledger
    itself IS the model. A signal active on many urls, or resolved somewhere
    and still active elsewhere, is CHRONIC: it comes back with every build,
    and a template-level fix beats page-by-page whack-a-mole."""
    if ledger is None:
        ledger = _load(path)
    entries = ledger['entries']
    if not entries:
        return {'total_urls': 0, 'note': 'ledger empty — record audits first'}
    active, resolved = {}, {}
    for e in entries.values():
        for s in e.get('active_signals', []):
            active.setdefault(s, []).append(e.get('url', ''))
        for s in e.get('resolved_signals', []):
            resolved.setdefault(s, []).append(e.get('url', ''))
    chronic = sorted(
        ({'signal': s, 'active_on': len(urls),
          'resolved_on': len(resolved.get(s, [])),
          'recurring': s in resolved and s in active}
         for s, urls in active.items()),
        key=lambda x: (-x['active_on'], -x['resolved_on'], x['signal']))[:10]
    urls_ranked = sorted(
        ({'url': e.get('url', ''), 'score': e.get('score'),
          'active_signals': len(e.get('active_signals', []))}
         for e in entries.values()),
        key=lambda x: (x['score'] if x['score'] is not None else 101,
                       -x['active_signals'], x['url']))
    return {
        'total_urls': len(entries),
        'signals_chronic': chronic,
        'hot_urls': urls_ranked[:5],
        'note': ('deterministic: chronic = active on many urls, or resolved '
                 'somewhere and still active elsewhere (recurring). The review '
                 'queue starts at hot_urls — fix at the template level, '
                 're-audit, and the chronic row drops out'),
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
    s4 = sub.add_parser('recurrence')
    s4.add_argument('--ledger', default='a11y-ledger.json')
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
    elif a.cmd == 'recurrence':
        print(json.dumps(recurrence(path=a.ledger), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
