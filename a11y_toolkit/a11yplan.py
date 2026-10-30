#!/usr/bin/env python3
"""Remediation plan — turn a findings list into an ordered ROUTE.

An inventory of 40 findings overwhelms; nobody answers "in what order?".
Planning matters because fixes change the cost of other fixes: semantic
infrastructure (headings, landmarks, labels) makes later work cheaper, one
design-token decision kills many contrast findings at once, and instances
on a page headed for redesign are wasted minutes. Cross-industry origin:
planning over evolving state (candidate-generation MDPs, arXiv 2607.02115)
— translated here into a deterministic, auditable heuristic. No ML, no
network: batches, declared phases, declared minute assumptions, a root
seal. The human reorders; the plan is evidence, not an oracle.

Phases (in order):
  infrastructure  — structural semantics first (they reprice everything else)
  design-system   — shared-cause decisions (contrast as a system fix)
  instances       — per-instance work, severity high → medium → low
  redesign-zone   — one page accumulating many distinct signals: flagged,
                    moved last, with an explicit note

CLI:
  a11ytoolkit plan --report audit.json [-o plan.json]
  a11ytoolkit plan --report audit.json --from-pack pack.json   # pack effort
"""

import argparse
import hashlib
import json
import sys

# Phase assignment by signal class (declared, not learned).
INFRA_SIGNALS = {'no_h1', 'heading_order', 'landmark', 'bypass_missing',
                 'region_missing', 'field_label', 'button_name', 'link_name',
                 'img_no_alt', 'iframe_title', 'html_lang_missing',
                 'title_missing', 'viewport_zoom_blocked'}
DESIGN_SIGNALS = {'contrast_low', 'contrast_image_fail', 'color_alone',
                  'focus_visibility', 'text_spacing'}
MINUTES_BY_SEVERITY = {'high': [12, 20], 'medium': [5, 10], 'low': [2, 4]}
REDESIGN_SIGNAL_THRESHOLD = 4  # distinct signals on one URL → zone flag

# What each assumption means, printed with the plan (honesty by default).
ASSUMPTIONS_HEURISTIC = {
    'source': 'severity heuristic',
    'minutes': MINUTES_BY_SEVERITY,
    'note': ('per-finding heuristic ranges, NOT measured effort; the pack '
             'effort pricing (a11y_evidence) is the better source when '
             'available'),
}


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))


def _minutes_for(findings, effort_by_criterion=None):
    """Sum of per-finding minute ranges. With pack effort pricing, the
    criterion's MIN/MED/MAX range replaces the severity heuristic."""
    lo = hi = 0
    for f in findings:
        eff = effort_by_criterion.get((f.get('criterion') or '').split(' ')[0])
        if eff and eff.get('minutes'):
            lo += eff['minutes'][0]
            hi += eff['minutes'][1]
        else:
            r = MINUTES_BY_SEVERITY.get(f.get('severity', 'low'), MINUTES_BY_SEVERITY['low'])
            lo += r[0]
            hi += r[1]
    return [lo, hi]


def build_plan(report, pack=None):
    """Report (dict with findings[]) → sealed fix-plan dict. Deterministic:
    same report, same plan. Malformed findings are skipped, never fatal."""
    findings = [f for f in (report.get('findings') or []) if isinstance(f, dict)
                and f.get('signal')]
    effort_by_criterion = {}
    if pack:
        for c in pack.get('criteria', []):
            if c.get('effort', {}).get('minutes'):
                effort_by_criterion[c['criterion'].split(' ')[0]] = c['effort']
    assumptions = dict(ASSUMPTIONS_HEURISTIC)
    if pack:
        assumptions = {'source': 'pack effort',
                       'note': 'minutes from the evidence pack effort pricing'}

    # redesign zones: one URL accumulating many distinct signals
    by_url = {}
    for f in findings:
        u = f.get('url') or report.get('url') or ''
        by_url.setdefault(u, set()).add(f['signal'])
    zones = {u for u, sigs in by_url.items() if len(sigs) >= REDESIGN_SIGNAL_THRESHOLD}

    # batch by signal inside each phase (one signal = one kind of fix)
    by_signal = {}
    for f in findings:
        by_signal.setdefault(f['signal'], []).append(f)

    def phase_of(signal):
        if signal in INFRA_SIGNALS:
            return 'infrastructure'
        if signal in DESIGN_SIGNALS:
            return 'design-system'
        return 'instances'

    sev_rank = {'high': 0, 'medium': 1, 'low': 2}
    batches = []
    infra_signals = sorted(s for s in by_signal if phase_of(s) == 'infrastructure')
    for signal in sorted(by_signal):
        if signal in infra_signals and signal != (infra_signals or [signal])[0]:
            continue  # infrastructure is ONE combined batch (one work session)
        fs = by_signal[signal]
        if signal == (infra_signals or [None])[0] and infra_signals:
            fs = [f for sg in infra_signals for f in by_signal[sg]]
            signal = 'document_structure'
        phase = 'infrastructure' if signal == 'document_structure' else phase_of(signal)
        zone = bool(zones & {f.get('url') or '' for f in fs})
        if phase == 'instances' and zone and len({f.get('url') for f in fs}) == 1 \
                and len(by_url[list(zones & {f.get('url') for f in fs})[0]]) >= REDESIGN_SIGNAL_THRESHOLD:
            phase = 'redesign-zone'
        sev = min((sev_rank.get(f.get('severity', 'low'), 2) for f in fs))
        batch = {
            'title': (f"Fix document structure semantics ({len(fs)} findings)"
                      if signal == 'document_structure' else
                      f"Fix {signal.replace('_', ' ')} ({len(fs)} finding"
                      f"{'s' if len(fs) != 1 else ''})"),
            'phase': phase, 'signal': signal,
            'finding_count': len(fs), 'severity': ('high', 'medium', 'low')[sev],
            'signals': infra_signals if signal == 'document_structure' else [signal],
            'urls': sorted({f.get('url') or '' for f in fs})[:8],
            'criteria': sorted({(f.get('criterion') or '').split(' ')[0] for f in fs}),
            'minutes': _minutes_for(fs, effort_by_criterion),
            'note': ('same kind of fix repeated — fix the pattern once and '
                     're-apply; itemized minutes are the upper bound'
                     if len(fs) > 1 else ''),
        }
        if phase == 'redesign-zone':
            batch['note'] = ('this URL accumulates %d distinct signals — '
                             'consider fixing it in a redesign pass, not '
                             'piecemeal' % len(by_url[list(zones & {f.get('url') for f in fs})[0]]))
        batches.append(batch)

    order = {'infrastructure': 0, 'design-system': 1, 'instances': 2, 'redesign-zone': 3}
    batches.sort(key=lambda b: (order[b['phase']], sev_rank[b['severity']],
                                b['signal']))

    # design-system note when contrast concentrates: one decision, many fixes
    design = [b for b in batches if b['phase'] == 'design-system']
    if design and sum(b['finding_count'] for b in design) >= 3:
        design[0]['note'] = (design[0]['note'] or '') + (
            ' — consider a design-token/theme decision: one change here '
            'typically resolves every finding in this batch').strip(' —')

    cumulative = [0, 0]
    for b in batches:
        cumulative[0] += b['minutes'][0]
        cumulative[1] += b['minutes'][1]
        b['cumulative_minutes'] = list(cumulative)

    itemized = [cumulative[0], cumulative[1]]
    savings = [max(0, itemized[0] // 6), max(0, itemized[1] // 5)]  # declared: 15-20% pattern reuse

    plan = {
        'format': 'a11y-fix-plan/1',
        'source_report': {'url': report.get('url'), 'score': report.get('score'),
                          'mode': report.get('mode'),
                          'findings_total': len(findings)},
        'assumptions': assumptions,
        'batches': batches,
        'total_minutes': list(cumulative),
        'grouping_savings_minutes': savings,
        'grouping_note': ('declared estimate of pattern-reuse savings from '
                          'fixing by batch instead of item by item — an '
                          'optimistic bound, not a promise'),
        'redesign_zones': sorted(zones),
        'note': ('the order is a declared heuristic: infrastructure first '
                 '(it reprices everything else), then design decisions, '
                 'then instances; the human reorders — re-run the seal '
                 'after reordering')
                 + ('' if findings else ' NO FINDINGS in the source report '
                    '— nothing to plan (run the audit first).'),
    }
    plan['sha256'] = hashlib.sha256(
        _canon({k: v for k, v in plan.items() if k != 'sha256'}).encode('utf-8')
    ).hexdigest()
    return plan


def verify_plan(plan):
    expected = hashlib.sha256(
        _canon({k: v for k, v in plan.items() if k != 'sha256'}).encode('utf-8')
    ).hexdigest()
    return expected == plan.get('sha256'), 'root sha256'


def main(argv):
    ap = argparse.ArgumentParser(description='Remediation plan: findings → ordered fix route')
    ap.add_argument('--report', required=True, help='audit report JSON (findings[])')
    ap.add_argument('--from-pack', help='evidence pack JSON: use its effort pricing for minutes')
    ap.add_argument('-o', '--out', default='fix-plan.json')
    a = ap.parse_args(argv)
    report = json.load(open(a.report, encoding='utf-8'))
    pack = json.load(open(a.from_pack, encoding='utf-8')) if a.from_pack else None
    plan = build_plan(report, pack=pack)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    print(json.dumps({'plan': a.out, 'sha256': plan['sha256'],
                      'batches': len(plan['batches']),
                      'total_minutes': plan['total_minutes']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
