#!/usr/bin/env python3
"""VPAT 2.5 (WCAG edition) generator — the US counterpart of the EAA declaration.

Input: an a11y-evidence-pack/2 (from a11y_evidence / a11y_evidence MCP tool)
or raw audit reports (the pack is built here). Output: an accessible HTML
VPAT with the full 55-criterion WCAG 2.2 A/AA table.

Honesty rule (non-negotiable, mirrors the pack): the machine fills Remarks,
never the Conformance Level. Every row starts at 'Not Evaluated' unless an
automated fail forces 'Does Not Support' (or 'Partially Supports' for
review-level signals). A qualified human sets the final level via `overrides`
and signs; until then the document is a DRAFT and says so. The signature
statement must reference the evidence pack's sha256 — same tamper-evidence
rule as the pack itself. VPAT is a vendor self-declaration, not a certificate.

CLI:
  a11yvpat.py pack.json --product "Acme App" --contact a11y@acme.example \
      --overrides '{"1.1.1": "does_not_support", "1.2.2": "not_applicable"}' \
      -o vpat.html
"""

import argparse
import datetime
import html
import json
import sys
from . import a11yi18n

LEVELS = a11yi18n.pair('vpat_levels')  # locales/<lang>.json — community-editable

_STATUS_TO_LEVEL = {
    'automated-fail': 'does_not_support',
    'automated-review': 'partially_supports',
    # not-flagged ≠ pass; agent-verified no es una firma humana
    'not-flagged': 'not_evaluated',
    'not-run': 'not_evaluated',
    'manual-only': 'not_evaluated',
    'agent-verified': 'not_evaluated',
}

TXT = a11yi18n.pair('vpat_txt')  # locales/<lang>.json — community-editable


def _t(lang):
    return TXT.get(lang, TXT['en'])


def _findings_by_code(pack):
    """Código de criterio → primer hallazgo con issue+remediation (de los artefactos)."""
    by_code = {}
    for art in pack.get('artifacts', []):
        body = art.get('body') or {}
        for h in body.get('findings', []):
            code = (h.get('criterion') or '').split(' ')[0]
            if code and code not in by_code:
                by_code[code] = h
    return by_code


def _remarks(t, row, finding, level, pack_sha):
    """Remarks auto por fila: estado + valor medido + esfuerzo + hallazgo + hash."""
    parts = []
    state = row.get('status')
    if state == 'automated-fail':
        parts.append(t['draft'] + ' — ' + 'automated-fail')
    elif state == 'automated-review':
        parts.append('automated-review')
    else:
        parts.append(state)
    note = row.get('note')
    if note:
        parts.append(note)
    val = row.get('value')
    if val:
        chunks = []
        if val.get('measured'):
            chunks.append(f"measured {val['measured']}")
        if val.get('example'):
            chunks.append(f"e.g. {val['example']}")
        if chunks:
            parts.append('; '.join(chunks))
    if finding:
        parts.append(f"issue: {finding.get('issue', '')[:220]}")
        if finding.get('remediation'):
            parts.append(f"remediation: {finding['remediation'][:220]}")
    ef = row.get('effort')
    if ef:
        parts.append(f"remaining human effort: {ef['class']} ({ef['minutes']} min)")
    parts.append(f"evidence pack sha256 {pack_sha}")
    return ' | '.join(p for p in parts if p)


def _wcag_order(code):
    try:
        return tuple(int(p) for p in code.split('.'))
    except ValueError:
        return (99, 0, 0)


def generate_vpat(pack=None, reports=None, product='', product_version=None,
                 report_date=None, description=None, contact=None, methods=None,
                 notes=None, overrides=None, reviewer=None, lang='en',
                 verified=None, output_path=None):
    """Pack (o informes) → HTML VPAT 2.5 accesible + resumen.

    overrides: {'1.1.1': 'supports', …} — niveles fijados por una persona
    cualificada; ganan sobre la derivación automática."""
    t = _t(lang)
    if pack is None:
        if not reports:
            return {'error': t['error_no_pack']}
        from .a11yevidence import build_pack
        pack = build_pack(reports, verified=verified,
                          reviewer=reviewer)
    if not isinstance(pack, dict) or 'criteria' not in pack:
        return {'error': t['error_no_pack']}
    overrides = overrides or {}
    for code, level in overrides.items():
        if level not in LEVELS[lang]:
            return {'error': t['error_level'].format(n=level)}

    from .a11ycrit import _C as _CAT
    pack_sha = pack.get('sha256', '')
    by_code = _findings_by_code(pack)
    report_date = report_date or datetime.date.today().isoformat()

    rows = []
    summary = {n: 0 for n in LEVELS[lang]}
    for row in sorted(pack['criteria'], key=lambda r: _wcag_order(r['criterion'].split(' ')[0])):
        code = row['criterion'].split(' ')[0]
        level = _STATUS_TO_LEVEL.get(row.get('status'), 'not_evaluated')
        level = overrides.get(code, level)
        summary[level] += 1
        cat = _CAT.get(code)
        name = cat[1][lang][0] if cat else row['criterion']
        wcag_level = cat[0] if cat else ''
        finding = by_code.get(code)
        rows.append({
            'code': code, 'name': name, 'level': wcag_level,
            'conformance': level,
            'remarks': _remarks(t, row, finding, level, pack_sha),
        })

    e = html.escape
    methods = methods or t['method_default']
    rows_html = []
    for f in rows:
        rows_html.append(
            '<tr><th scope="row">' + e(f['code']) + ' ' + e(f['name'])
            + (' <span class="lvl">(Level ' + e(f['level']) + ')</span>' if f['level'] else '')
            + '</th><td><strong>' + e(LEVELS[lang][f['conformance']]) + '</strong></td>'
            + '<td>' + e(f['remarks']) + '</td></tr>')
    legend = ''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k, v in t['legend'])

    doc = (
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{e(t["title"])} — {e(product)}</title>\n'
        # self-contained signable document: FIXED colors, not the system theme
        # (dark mode painted light text on light header gray — contrast ~1:1),
        # and long hashes must wrap instead of stretching the page (1.4.10).
        '<style>:root{color-scheme:light}body{max-width:60rem;margin:2rem auto;'
        'padding:0 1rem;color:#161A16;background:#fff;'
        'font:1rem/1.6 system-ui,sans-serif} table{border-collapse:collapse;width:100%}'
        ' th,td{border:1px solid #888;padding:.5rem;vertical-align:top;text-align:left}'
        ' thead th{background:#f0f0f0;color:#161A16} .lvl{color:#555;font-size:.85em}'
        ' code{background:#f5f5f5;padding:.1rem .3rem;overflow-wrap:anywhere}'
        ' p,dd,dt,th,td,li{overflow-wrap:anywhere}'
        ' .table-scroll{overflow-x:auto}'
        ' @media (max-width:40rem){body{margin:1rem auto} th,td{padding:.35rem}}'
        '</style>\n</head>\n<body>\n<main>\n'
        f'<h1>{e(t["title"])}</h1>\n'
        f'<p><strong>{e(product)}</strong>'
        + (f' — {t["version"]}: {e(product_version)}' if product_version else '')
        + f' — {t["date"]}: <time datetime="{e(report_date)}">{e(report_date)}</time></p>\n'
        + (f'<p><strong>{t["description"]}:</strong> {e(description)}</p>\n' if description else '')
        + (f'<p><strong>{t["contact"]}:</strong> {e(contact)}</p>\n' if contact else '')
        + f'<h2>{t["standards_section"]}</h2>\n<p>{t["standard"]}</p>\n'
        + f'<h2>{t["methods"]}</h2>\n<p>{e(methods)}</p>\n'
        + (f'<h2>{t["notes"]}</h2>\n<p>{e(notes)}</p>\n' if notes else '')
        + f'<details>\n<summary>{t["legend_title"]}</summary>\n<dl>{legend}</dl>\n</details>\n'
        # the criteria table is wide: scrolling lives HERE, keyboard-focusable,
        # so the PAGE does not overflow (WCAG 1.4.10)
        + '<div class="table-scroll" tabindex="0" role="group">\n'
        + f'<table>\n<caption>{t["table_caption"]}</caption>\n'
        + '<thead><tr><th scope="col">' + t['col_criteria'] + '</th><th scope="col">'
        + t['col_level'] + '</th><th scope="col">' + t['col_remarks']
        + '</th></tr></thead>\n<tbody>\n' + '\n'.join(rows_html) + '\n</tbody>\n</table>\n</div>\n'
        + f'<h2>{t["signature_title"]}</h2>\n<p>{t["signature"]} <code>{e(pack_sha)}</code></p>\n'
        + '<p><em>' + t['signature_empty'] + '</em></p>\n'
        + (f'<p>{t["product"]}: {e((reviewer or {}).get("name", "________________"))} — '
           f'{t["credential"]}: {e((reviewer or {}).get("credential", "________________"))} — '
           f'{t["date"]}: {e((reviewer or {}).get("review_date", "________________"))}</p>\n'
           if reviewer else '')
        + f'</main>\n<footer><p><small>{t["iti_note"]}</small></p></footer>\n</body>\n</html>'
    )
    res = {'html': doc, 'summary': summary, 'levels': {f['code']: f['conformance'] for f in rows},
           'pack_sha256': pack_sha, 'draft': True, 'lang': lang}
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc)
        res['saved_to'] = output_path
    return res


def main(argv):
    ap = argparse.ArgumentParser(description='VPAT 2.5 (WCAG edition) from an evidence pack')
    ap.add_argument('pack', nargs='?', help='evidence pack JSON (a11y_evidence output)')
    ap.add_argument('--product', required=True, help='product name')
    ap.add_argument('--reports', nargs='+', help='audit report JSONs (builds the pack) instead of pack')
    ap.add_argument('--report-date', help='report date (YYYY-MM-DD, default today)')
    ap.add_argument('--description', help='product description')
    ap.add_argument('--contact', help='contact information')
    ap.add_argument('--methods', help='evaluation methods used')
    ap.add_argument('--notes', help='notes')
    ap.add_argument('--overrides', help='JSON: {"1.1.1": "does_not_support", …}')
    ap.add_argument('--reviewer', help='JSON: {"name":…, "credential":…, "review_date":…}')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    pack = json.load(open(a.pack, encoding='utf-8')) if a.pack else None
    reports = [json.load(open(f, encoding='utf-8')) for f in a.reports] if a.reports else None
    res = generate_vpat(pack=pack, reports=reports, product=a.product, report_date=a.report_date,
                       description=a.description, contact=a.contact, methods=a.methods,
                       notes=a.notes, overrides=json.loads(a.overrides) if a.overrides else None,
                       reviewer=json.loads(a.reviewer) if a.reviewer else None,
                       lang=a.lang, output_path=a.out)
    if 'error' in res:
        print(res['error'])
        return 1
    print(json.dumps({'summary': res['summary'], 'pack_sha256': res['pack_sha256'],
                      'saved_to': res.get('saved_to'),
                      'draft': res['draft']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
