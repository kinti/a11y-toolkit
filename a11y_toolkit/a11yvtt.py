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

_RE_TiEMPO = re.compile(
    r'(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{3})')

T = {
    'es': {
        'vtt_malformed': '{n} bloques con línea de tiempos malformada: {ej}.',
        'vtt_malformed_rem': 'Corrige el formato «HH:MM:SS.mmm --> HH:MM:SS.mmm»; un cue roto puede saltarse entero en el lector.',
        'vtt_empty_cue': '{n} cues sin texto: tiempo consumido sin subtítulo.',
        'vtt_empty_cue_rem': 'Elimina los cues vacíos o dales el texto que falta.',
        'vtt_overlap': '{n} solapamientos de tiempo entre cues consecutivos.',
        'vtt_overlap_rem': 'Los cues no deben solaparse: algunos lectores muestran ambos a la vez.',
        'vtt_too_fast': '{n} cues por encima de 21 caracteres/segundo: {ej}.',
        'vtt_too_fast_rem': 'Divide el cue o alarga su tiempo: >21 cps es ilegible (estándar BBC/Netflix).',
        'vtt_no_cues': 'el archivo declara WebVTT pero no contiene cues.',
        'vtt_no_cues_rem': 'Subtitula de verdad: un track vacío no cumple 1.2.2.',
        'vtt_coverage': 'cobertura {pct}% de los {dur}s de media — hay tramos sin subtítulos.',
        'vtt_coverage_rem': 'Subtitula los tramos faltantes o declara el tramo como música/idioma extranjero si aplica.',
        'limits': ('Cribado del CONTENIDO de los subtítulos (1.2.2): no sustituye '
                   'la revisión humana de precisión, identificación de hablantes ni audiodescripción.'),
    },
    'en': {
        'vtt_malformed': '{n} blocks with malformed timing lines: {ej}.',
        'vtt_malformed_rem': 'Fix the "HH:MM:SS.mmm --> HH:MM:SS.mmm" format; a broken cue can be skipped whole by the player.',
        'vtt_empty_cue': '{n} cues with no text: time spent with no caption.',
        'vtt_empty_cue_rem': 'Remove empty cues or add their missing text.',
        'vtt_overlap': '{n} timing overlaps between consecutive cues.',
        'vtt_overlap_rem': 'Cues must not overlap: some players show both at once.',
        'vtt_too_fast': '{n} cues above 21 characters/second: {ej}.',
        'vtt_too_fast_rem': 'Split the cue or extend its time: >21 cps is unreadable (BBC/Netflix standard).',
        'vtt_no_cues': 'the file declares WebVTT but contains no cues.',
        'vtt_no_cues_rem': 'Caption for real: an empty track does not satisfy 1.2.2.',
        'vtt_coverage': '{pct}% coverage of the {dur}s of media — stretches without captions.',
        'vtt_coverage_rem': 'Caption the missing stretches (or mark them as music/foreign language when true).',
        'limits': ('Screening of caption CONTENT (1.2.2): not a substitute for '
                   'human review of accuracy, speaker identification or audio description.'),
    },
}


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
            m = _RE_TiEMPO.search(l)
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

    vacios = [c for c in cues if not c['text']]
    if vacios:
        add('medium', 'vtt_empty_cue', n=len(vacios))

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
