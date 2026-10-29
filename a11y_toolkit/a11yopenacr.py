#!/usr/bin/env python3
"""OpenACR (GSA) generator — the machine-readable ACR for public procurement.

Input: an a11y-evidence-pack/2 (from a11y_evidence / the a11y_evidence MCP
tool) or raw audit reports (the pack is built here). Output: OpenACR YAML
(the GSA open standard born from VPAT 2.4Rev 508; gsa.github.io/openacr)
with the full 55-criterion WCAG 2.2 A/AA matrix — chapters
success_criteria_level_a / _aa, one `web` component per criterion.

Honesty rule (non-negotiable, mirrors the pack and the VPAT): the machine
fills the adherence `notes`, never the level. Every criterion starts at
`not-evaluated` unless an automated fail forces `does-not-support` (or
`partially-supports` for review-level signals). A qualified human sets the
final level via `overrides` — same vocabulary as a11y_generate_vpat
(supports, partially_supports, …); the hyphenated forms of the OpenACR
format itself are accepted too. Every remark references the evidence
pack's sha256 — the same tamper-evidence rule as every document the
engine emits. An ACR is a vendor claim, not a certificate.

The YAML is written by a fixed-schema emitter (stdlib only): JSON string
escaping is valid YAML double-quoted style, so there is no parser
dependency AND no injection — user text (quotes, newlines, colons) can
never break the document structure.

CLI:
  a11yopenacr.py pack.json --product "Acme App" -o openacr.yaml
  a11ytoolkit openacr pack.json --product "Acme App" -o openacr.yaml
"""

import argparse
import datetime
import json
import sys
from . import a11yi18n
from .a11yvpat import LEVELS, _STATUS_TO_LEVEL, _findings_by_code, _wcag_order

TXT = a11yi18n.pair('openacr_txt')


def _t(lang):
    return TXT.get(lang, TXT['en'])


def _q(value):
    """YAML double-quoted scalar: JSON escaping is valid YAML, so user text
    can never break the document structure (fixed schema, no injection)."""
    return json.dumps(str(value), ensure_ascii=False)


def _remarks(row, finding, pack_sha):
    """Remarks por criterio: estado + valor medido + hallazgo + esfuerzo + hash."""
    parts = []
    if row.get('status'):
        parts.append(row['status'])
    if row.get('note'):
        parts.append(row['note'])
    val = row.get('value') or {}
    if val.get('measured') or val.get('example'):
        chunks = []
        if val.get('measured'):
            chunks.append('measured ' + str(val['measured']))
        if val.get('example'):
            chunks.append('e.g. ' + str(val['example']))
        parts.append('; '.join(chunks))
    if finding:
        parts.append('issue: ' + str(finding.get('issue', ''))[:220])
        if finding.get('remediation'):
            parts.append('remediation: ' + str(finding['remediation'])[:220])
    ef = row.get('effort')
    if ef:
        parts.append('remaining human effort: ' + str(ef.get('class'))
                     + ' (' + str(ef.get('minutes')) + ' min)')
    parts.append('evidence pack sha256 ' + pack_sha)
    return ' | '.join(p for p in parts if p)


def generate_openacr(pack=None, reports=None, product='', product_version=None,
                     report_date=None, description=None, author=None, contact=None,
                     methods=None, notes=None, overrides=None, lang='en',
                     output_path=None):
    """Pack (o informes) → OpenACR YAML (GSA) + resumen.

    overrides: {'1.1.1': 'supports', …} — niveles fijados por una persona
    cualificada; se aceptan además las formas con guion del propio formato
    ('partially-supports'). Ganan sobre la derivación automática."""
    t = _t(lang)
    if pack is None:
        if not reports:
            return {'error': t['error_no_pack']}
        from .a11yevidence import build_pack
        pack = build_pack(reports)
    if not isinstance(pack, dict) or 'criteria' not in pack:
        return {'error': t['error_no_pack']}
    overrides = {k: str(v).replace('-', '_') for k, v in (overrides or {}).items()}
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
        wcag_level = cat[0] if cat else 'A'
        rows.append({'code': code, 'name': name, 'level': wcag_level,
                     'adherence': level,
                     'remarks': _remarks(row, by_code.get(code), pack_sha)})

    author = author or {}
    doc_notes = t['notes_draft']
    if (notes or '').strip():
        doc_notes += ' ' + notes.strip()
    methods = methods or t['method_default']

    lines = []
    lines.append('title: ' + _q(product + ' — OpenACR'))
    lines.append('product:')
    lines.append('  name: ' + _q(product))
    if product_version:
        lines.append('  version: ' + _q(product_version))
    if description:
        lines.append('  description: ' + _q(description))
    lines.append('author:')
    lines.append('  name: ' + _q(author.get('name', '')))
    lines.append('  company_name: ' + _q(author.get('company', '')))
    lines.append('  email: ' + _q(author.get('email', '') or (contact or '')))
    if author.get('website'):
        lines.append('  website: ' + _q(author['website']))
    lines.append('report_date: ' + _q(report_date))
    lines.append('last_modified_date: ' + _q(report_date))
    lines.append('version: 1')
    lines.append('notes: ' + _q(doc_notes))
    lines.append('evaluation_methods_used: ' + _q(methods))
    lines.append('legal_disclaimer: ' + _q(t['legal_disclaimer']))
    lines.append('chapters:')
    for chapter, wcag_lvl in (('success_criteria_level_a', 'A'),
                              ('success_criteria_level_aa', 'AA')):
        lines.append('  ' + chapter + ':')
        lines.append('    notes: ' + _q(t['chapter_note']))
        lines.append('    criteria:')
        for f in rows:
            if f['level'] != wcag_lvl:
                continue
            lines.append('      - num: ' + _q(f['code']))
            lines.append('        components:')
            lines.append('          - name: web')
            lines.append('            adherence:')
            lines.append('              level: ' + f['adherence'].replace('_', '-'))
            lines.append('              notes: ' + _q(f['code'] + ' ' + f['name']
                                                   + ' — ' + f['remarks']))

    doc = '\n'.join(lines) + '\n'
    res = {'yaml': doc, 'summary': summary,
           'levels': {f['code']: f['adherence'] for f in rows},
           'pack_sha256': pack_sha, 'format': 'openacr', 'draft': True, 'lang': lang}
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as fh:
            fh.write(doc)
        res['saved_to'] = output_path
    return res


def main(argv):
    ap = argparse.ArgumentParser(description='OpenACR (GSA) YAML from an evidence pack')
    ap.add_argument('pack', nargs='?', help='evidence pack JSON (a11y_evidence output)')
    ap.add_argument('--product', required=True, help='product name')
    ap.add_argument('--reports', nargs='+', help='audit report JSONs (builds the pack) instead of pack')
    ap.add_argument('--product-version', help='product version')
    ap.add_argument('--report-date', help='report date (YYYY-MM-DD, default today)')
    ap.add_argument('--description', help='product description')
    ap.add_argument('--author', help='JSON: {"name":…, "company":…, "email":…, "website":…}')
    ap.add_argument('--contact', help='contact email (author.email fallback)')
    ap.add_argument('--methods', help='evaluation methods used')
    ap.add_argument('--notes', help='additional notes')
    ap.add_argument('--overrides', help='JSON: {"1.1.1": "supports", …}')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    pack = json.load(open(a.pack, encoding='utf-8')) if a.pack else None
    reports = [json.load(open(f, encoding='utf-8')) for f in a.reports] if a.reports else None
    res = generate_openacr(pack=pack, reports=reports, product=a.product,
                           product_version=a.product_version, report_date=a.report_date,
                           description=a.description,
                           author=json.loads(a.author) if a.author else None,
                           contact=a.contact, methods=a.methods, notes=a.notes,
                           overrides=json.loads(a.overrides) if a.overrides else None,
                           lang=a.lang, output_path=a.out)
    if 'error' in res:
        print(res['error'])
        return 1
    print(json.dumps({'summary': res['summary'], 'pack_sha256': res['pack_sha256'],
                      'format': res['format'], 'saved_to': res.get('saved_to'),
                      'draft': res['draft']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
