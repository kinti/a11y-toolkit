#!/usr/bin/env python3
"""Disprover pattern — re-verify findings against the live page and reject those
that don't reproduce.

The Cloudflare security-audit-skill lesson: every finding deserves a fresh
verifier that tries to DISPROVE it, not confirm it. This module does that for
accessibility findings:

  1. Take an audit report
  2. For each finding, re-check the signal against the live page
  3. Findings that reproduce → status: confirmed
  4. Findings that don't → status: rejected + reject_reason

This catches:
  - False positives (the element changed, was fixed, or never existed)
  - Race conditions (page was different when first audited)
  - Rendering differences (element is hidden, removed, or in a different context)

CLI:
  a11ydisprove.py --url https://example.com --file report.json
  a11ydisprove.py --url https://example.com  # audit + disprove in one call
"""

import argparse
import json

import sys

from .a11yaudit import (audit_conditions, audit_conditions_match, audit_url, normalize_signal,
                        page_identity, rendered_conditions_recorded)


def _recheck(url, expected_url, timeout, lang, color_scheme=None, auth_state=None, browser='auto'):
    """Obtain a successful measurement of the same page."""
    if color_scheme is None:
        fresh = audit_url(url, timeout=timeout, lang=lang)
    else:
        from .a11ydom import audit_dom_url
        fresh = audit_dom_url(url, timeout=timeout, lang=lang, color_scheme=color_scheme,
                              auth_state=auth_state, browser=browser)
    if 'error' in fresh:
        return None, fresh['error']
    if page_identity(fresh.get('url')) != page_identity(expected_url):
        return None, ('La reauditoría terminó en una URL distinta de la del informe original.'
                      if lang == 'es' else
                      'The re-audit ended at a different URL from the original report.')
    return fresh, None


def _text(value):
    return value if isinstance(value, str) else ''


def _count(finding):
    count = finding.get('count')
    return count if type(count) is int and count > 0 else None


def _finding_key(finding):
    # el informe es entrada externa: un `signal` o `criterion` numérico no
    # puede tirar la reverificación (revisión 2026-11-25)
    return (normalize_signal(_text(finding.get('signal'))),
            _text(finding.get('criterion')).split(' ', 1)[0])


def _location_evidence(finding):
    """(rutas guardadas, cubren TODAS las instancias). Las rutas de un
    hallazgo con más instancias que rutas son una MUESTRA, no el inventario."""
    stored = finding.get('paths')
    paths = tuple(sorted({path for path in (stored if isinstance(stored, (list, tuple)) else [])
                          if isinstance(path, str)}))
    if paths:
        count = _count(finding)
        return paths, count == len(paths) if count is not None else len(paths) < 5
    return (), False


def _classify_findings(previous, current, lang):
    current = [dict(finding) for finding in current]
    by_key = {}
    for finding in current:
        by_key.setdefault(_finding_key(finding), []).append(finding)
    historical = []
    rejected = ('El hallazgo anterior ya no aparece en la nueva auditoría de la página.'
                if lang == 'es' else
                'The earlier finding no longer appears in the new audit of the page.')
    for old in previous:
        if old.get('status') == 'rejected' or old.get('disprover_status') == 'rejected':
            continue
        key = _finding_key(old)
        candidates = by_key.get(key, [])
        paths, complete = _location_evidence(old)
        locations = [_location_evidence(row) for row in candidates]
        if not candidates or (complete and all(known and not set(paths).intersection(new_paths)
                                                for new_paths, known in locations)):
            historical.append(dict(old, status='rejected', reject_reason=rejected))
        elif len(candidates) == 1:
            # una sola candidata de la misma señal, en la misma página, y sin
            # prueba completa de que los elementos originales ya no fallan: el
            # defecto se reproduce → confirmada. Antes, una MUESTRA de rutas (8
            # instancias, 5 guardadas) no confirmaba nunca y quedaba
            # `not-rechecked` sin haber mirado la evidencia (2026-11-25)
            candidates[0]['status'] = 'confirmed'
        else:
            historical.append(dict(old, disprover_status='not-rechecked'))
    return current, historical


def _unverified(report, reason):
    findings = [dict(h, disprover_status='not-rechecked') for h in report.get('findings', [])]
    return dict(report, findings=findings, disprover={'executed': False, 'reason': reason})


def disprove(url, report=None, timeout=30, lang='en', auth_state=None):
    """Audit a URL and disprove findings, or verify an existing report.

    Return the fresh measurement and the outcomes of prior findings."""
    if report is None:
        if auth_state:
            from .a11ydom import audit_dom_url
            report = audit_dom_url(url, timeout=timeout, lang=lang, auth_state=auth_state)
        else:
            report = audit_url(url, timeout=timeout, lang=lang)
    if not isinstance(report, dict):
        report = {'error': ('El informe no es un objeto JSON de informe de auditoría.'
                            if lang == 'es'
                            else 'The report is not an audit-report JSON object.')}
    if report.get('error'):
        return report
    mode_name = report.get('mode', 'static')
    expected_url = report.get('url') or url
    findings = report.get('findings', [])
    if not isinstance(findings, list) or any(not isinstance(h, dict) for h in findings):
        # el informe es entrada externa (CLI --file / MCP): una lista de
        # hallazgos que no lo es se dice, no se tronca
        message = ('El informe trae una lista de hallazgos inválida: se esperaba una lista de objetos.'
                   if lang == 'es' else
                   'The report carries an invalid findings list: a list of objects was expected.')
        return dict(report, error=message, disprover={'executed': False, 'reason': message})

    if mode_name == 'site':
        # site reports nest findings INSIDE each page: re-checking them against
        # ONE url marked everything 'rejected' and scored 100 on unreviewed
        # evidence. Honest path: not-rechecked per page, with the pointer to
        # re-verify each page properly.
        if not findings:
            findings = [dict(h, page=page.get('url', '')) for page in report.get('reports', [])
                        for h in page.get('findings', [])]
        res = dict(report)
        res['findings'] = [dict(h, disprover_status='not-rechecked') for h in findings]
        res['disprover'] = {'executed': False,
                            'reason': ('site mode: each finding belongs to a page; '
                                       're-verify with a11ydisprove --url <page> '
                                       '--file <that page report>')}
        return res

    if mode_name == 'static':
        if auth_state:
            return _unverified(report, 'El informe estático no admite una sesión de navegador.'
                               if lang == 'es' else
                               'The static report does not support a browser session.')
        fresh, err = _recheck(url, expected_url, timeout, lang)
    elif mode_name == 'rendered':
        conditions = audit_conditions(report)
        if not rendered_conditions_recorded(conditions):
            return _unverified(report, ('El informe no registra todas las condiciones de captura. '
                                       'Vuelve a auditar con a11y_audit_dom.' if lang == 'es' else
                                       'Capture conditions are missing. Re-audit with a11y_audit_dom.'))
        if bool(auth_state) != conditions['authenticated']:
            return _unverified(report, ('La reauditoría necesita el mismo tipo de sesión que la captura. '
                                       'Usa auth_state para una captura con sesión.' if lang == 'es' else
                                       'Re-audit with the same session type as the capture. '
                                       'Use auth_state for an authenticated capture.'))
        scheme = conditions['color_scheme']
        fresh, err = _recheck(url, expected_url, timeout, lang, color_scheme=scheme,
                              auth_state=auth_state, browser=conditions['browser'])
        if not err and not audit_conditions_match(mode_name, conditions, audit_conditions(fresh)):
            return _unverified(report, 'La reauditoría cambió las condiciones de captura.'
                               if lang == 'es' else 'Capture conditions changed during re-audit.')
    else:
        # no re-verifier for this mode: report not-rechecked, never a proxy
        # audit (a keyboard finding must not vanish just because the wrong
        # method ran). `rejected` is reserved for an equivalent check that
        # actually disproves the original finding.
        return _unverified(report, (f'No hay reauditoría para el modo {mode_name!r}.' if lang == 'es'
                                   else f'No re-verifier for mode {mode_name!r}.'))

    if err:
        return dict(report, error=err, disprover={'executed': False, 'reason': err})

    current, historical = _classify_findings(findings, fresh['findings'], lang)
    rejected = [h for h in historical if h.get('status') == 'rejected']
    result = dict(fresh, findings=current + rejected, score_original=report.get('score'))
    result['disprover'] = {
        'executed': True,
        'confirmed': sum(h.get('status') == 'confirmed' for h in current),
        'rejected': len(rejected),
        'previous_findings': historical,
        'note': ('La puntuación y la cobertura corresponden a la nueva auditoría. '
                 'Se conservan los descartes y las coincidencias dudosas para su revisión.'
                 if lang == 'es' else
                 'Score and coverage describe the fresh audit. Rejected findings '
                 'and ambiguous historical matches are retained for review.'),
    }
    return result


def main(argv):
    ap = argparse.ArgumentParser(description='Disprover: re-verify findings against the live page')
    ap.add_argument('--url', required=True, help='URL to audit and disprove')
    ap.add_argument('--file', help='existing report JSON (optional; if absent, audits first)')
    ap.add_argument('--auth-state', help='local Playwright session for the original capture')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=30)
    ap.add_argument('-o', '--out', help='save result JSON here')
    a = ap.parse_args(argv)
    report = None
    if a.file:
        with open(a.file, encoding='utf-8') as f:
            report = json.load(f)
    res = disprove(a.url, report=report, timeout=a.timeout, lang=a.lang, auth_state=a.auth_state)
    if 'error' in res:
        print(json.dumps(res))
        return 1
    output = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(output)
        print(json.dumps({'file': a.out, **res['disprover']}))
    else:
        print(output)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
