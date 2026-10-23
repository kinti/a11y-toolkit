#!/usr/bin/env python3
"""WebVTT caption quality (1.2.2) — the substance, not just the presence.

Everyone (axe included) stops at "<track> exists". This parses the actual
.vtt file and judges the captions people get: malformed cues, empty text,
overlaps, impossible reading speeds (>21 chars/second — BBC/Netflix
subtitling standards), and coverage vs the media duration when given.

Zero dependencies. Fetch goes through the shared _descarga guard
(http/https only, size-capped).

CLI:
  a11yvtt.py https://site/captions.vtt [--duration 640]
"""

import argparse
import json
import re
import sys
from . import a11yi18n

_RE_TIME = re.compile(
    r'(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{3})')

T = a11yi18n.pair('vtt')  # locales/<lang>.json — community-editable


def _t(lang, key):
    return T.get(lang, T['en'])[key]


def _seconds(h, m, s, ms):
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def vtt_check(url, duration=None, lang='en'):
    """Descarga y juzga un .vtt — el contenido de 1.2.2, no su mera presencia."""
    from .a11yaudit import _fetch, compute_score, CRIT
    data = _fetch(url, timeout=30, truncate_at=2_000_000)
    if isinstance(data, dict) and 'error' in data:
        return data
    if isinstance(data, bytes):
        text = data.decode('utf-8', errors='replace')
    else:
        text = str(data)

    findings = []

    def add(sev, key, **fmt):
        findings.append({'severity': sev, 'criterion': CRIT.get(lang, CRIT['es']).get('1.2.2', '1.2.2'),
                          'signal': key, 'issue': _t(lang, key).format(**fmt),
                          'remediation': _t(lang, key + '_rem').format(**fmt)})

    if not text.lstrip().startswith('WEBVTT'):
        return {'error': 'no declara WEBVTT (¿es un .srt u otro formato?)',
                'primeros_bytes': text[:40]}

    blocks = [b for b in re.split(r'\n\s*\n', text) if b.strip()]
    cues, malformed = [], []
    for b in blocks[1:]:  # el primero es la cabecera
        lines = [l for l in b.splitlines() if l.strip()]
        m = None
        for i, l in enumerate(lines):
            m = _RE_TIME.search(l)
            if m:
                body = '\n'.join(lines[i + 1:]).strip()
                break
        if not m:
            if '-->' in b:
                malformed.append(lines[0][:30])
            continue
        start = _seconds(*m.groups()[:4])
        end = _seconds(*m.groups()[4:])
        cues.append({'start': start, 'end': end, 'text': body})

    if malformed:
        add('high', 'vtt_malformed', n=len(malformed), ej=', '.join(malformed[:3]))
    if not cues:
        add('high', 'vtt_no_cues')
        return _report(url, findings, 0, 0, lang, duration, cues)

    empties = [c for c in cues if not c['text']]
    if empties:
        add('medium', 'vtt_empty_cue', n=len(empties))

    overlaps = sum(1 for a, b in zip(cues, cues[1:]) if b['start'] < a['end'])
    if overlaps:
        add('low', 'vtt_overlap', n=overlaps)

    too_fast = [{'t': c['text'][:30], 'cps': round(len(c['text']) / max(c['end'] - c['start'], 0.1), 1)}
               for c in cues if not c['text'].startswith('<') and c['text']
               and len(c['text']) / max(c['end'] - c['start'], 0.1) > 21]
    if too_fast:
        add('medium', 'vtt_too_fast', n=len(too_fast),
            ej=', '.join(f"{r['t']}… ({r['cps']}cps)" for r in too_fast[:3]))

    if duration:
        covered = sum(max(0.0, min(c['end'], duration) - c['start']) for c in cues if c['start'] < duration)
        pct = round(100 * covered / max(duration, 1), 1)
        if pct < 95:
            add('medium', 'vtt_coverage', pct=pct, dur=round(duration))

    n_char = sum(len(c['text']) for c in cues)
    return _report(url, findings, len(cues), n_char, lang, duration, cues)


def _report(url, findings, n_cues, n_char, lang, duration, cues):
    from .a11yaudit import compute_score
    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    return {
        'mode': 'vtt', 'url': url,
        'duration': duration,
        'cues': n_cues, 'characters': n_char,
        'captioned_seconds': round(sum(c['end'] - c['start'] for c in cues), 1) if cues else 0,
        'score': compute_score(findings),
        'findings': findings,
        'summary': {s: sum(1 for h in findings if h['severity'] == s)
                    for s in ('high', 'medium', 'low')},
        'limits': _t(lang, 'limits'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url', help='.vtt URL')
    ap.add_argument('--duration', type=float, help='media duration in seconds (coverage check)')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    print(json.dumps(vtt_check(a.url, duration=a.duration, lang=a.lang),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
