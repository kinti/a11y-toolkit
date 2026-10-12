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
  a11yvpat.py pack.json --producto "Acme App" --contact a11y@acme.example \
      --overrides '{"1.1.1": "does_not_support", "1.2.2": "not_applicable"}' \
      -o vpat.html
"""

import argparse
import datetime
import html
import json
import sys

NIVELES = {
    'es': {
        'supports': 'Lo soporta',
        'partially_supports': 'Lo soporta parcialmente',
        'does_not_support': 'No lo soporta',
        'not_applicable': 'No aplica',
        'not_evaluated': 'No evaluado',
    },
    'en': {
        'supports': 'Supports',
        'partially_supports': 'Partially Supports',
        'does_not_support': 'Does Not Support',
        'not_applicable': 'Not Applicable',
        'not_evaluated': 'Not Evaluated',
    },
}

_ESTADO_A_NIVEL = {
    'automated-fail': 'does_not_support',
    'automated-review': 'partially_supports',
    # not-flagged ≠ pass; agent-verified no es una firma humana
    'not-flagged': 'not_evaluated',
    'not-run': 'not_evaluated',
    'manual-only': 'not_evaluated',
    'agent-verified': 'not_evaluated',
}

TXT = {
    'es': {
        'titulo': 'Informe de conformidad de accesibilidad VPAT® 2.5 — edición WCAG',
        'seccion_estandar': 'Pautas/estándares aplicables',
        'estandar': ('<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                     '(niveles A y AA) — Recomendación W3C de octubre de 2023.'),
        'producto': 'Nombre del producto', 'version': 'Versión',
        'fecha': 'Fecha del informe', 'descripcion': 'Descripción del producto',
        'contacto': 'Información de contacto', 'metodos': 'Métodos de evaluación utilizados',
        'notas': 'Notas', 'credencial': 'Credencial',
        'metodo_defecto': ('Cribado automatizado con a11y-toolkit (auditoría estática y, cuando '
                           'está disponible, renderizada con contraste computado y muestreo de '
                           'píxeles); revisión manual pendiente.'),
        'leyenda_titulo': 'Definiciones de los niveles de conformidad (extracto del VPAT®)',
        'leyenda': [
            ('Supports', 'El producto tiene al menos un método que cumple el criterio sin defectos conocidos.'),
            ('Partially Supports', 'Alguna funcionalidad del producto no cumple el criterio.'),
            ('Does Not Support', 'La mayor parte de la funcionalidad del producto no cumple el criterio.'),
            ('Not Applicable', 'El criterio no es relevante para el producto.'),
            ('Not Evaluated', 'El producto aún no ha sido evaluado frente al criterio; el nivel está pendiente de una persona cualificada.'),
        ],
        'tabla_caption': 'Tabla 1: Criterios de conformidad WCAG 2.2 (A/AA)',
        'col_criterio': 'Criterio', 'col_nivel': 'Nivel de conformidad',
        'col_comentarios': 'Comentarios y explicaciones',
        'firma_titulo': 'Firma y evidencia',
        'firma': ('Este documento es un <strong>BORRADOR</strong> generado por cribado '
                  'automatizado. Los niveles marcados «No evaluado» deben ser fijados por una '
                  'persona cualificada tras la revisión; la declaración de firma debe '
                  'referenciar el hash del paquete de evidencia:'),
        'firma_vacia': 'Bloque de firma sin completar: nombre, credencial y fecha pendientes.',
        'nota_iti': ('VPAT® es una marca registrada del Information Technology Industry Council '
                     '(ITI). Este documento es un andamiaje de autodeclaración del proveedor, '
                     'generado por a11y-toolkit; no constituye certificación alguna.'),
        'error_sin_pack': 'necesitas un pack (a11y_evidence) o reports (informes de auditoría)',
        'error_nivel': 'nivel desconocido en overrides: {n} (usa supports, partially_supports, does_not_support, not_applicable, not_evaluated)',
        'draft': 'BORRADOR — niveles pendientes de persona cualificada',
    },
    'en': {
        'titulo': 'VPAT® 2.5 Accessibility Conformance Report — WCAG edition',
        'seccion_estandar': 'Applicable Standards/Guidelines',
        'estandar': ('<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                     '(Levels A and AA) — W3C Recommendation, October 2023.'),
        'producto': 'Product name', 'version': 'Version',
        'fecha': 'Report date', 'descripcion': 'Product description',
        'contacto': 'Contact information', 'metodos': 'Evaluation methods used',
        'notas': 'Notes', 'credencial': 'Credential',
        'metodo_defecto': ('Automated screening with a11y-toolkit (static audit and, when '
                           'available, rendered audit with computed contrast and pixel '
                           'sampling); manual review pending.'),
        'leyenda_titulo': 'Conformance level definitions (excerpt from the VPAT®)',
        'leyenda': [
            ('Supports', 'The product has at least one method that meets the criterion without known defects.'),
            ('Partially Supports', 'Some functionality of the product does not meet the criterion.'),
            ('Does Not Support', 'The majority of product functionality does not meet the criterion.'),
            ('Not Applicable', 'The criterion is not relevant to the product.'),
            ('Not Evaluated', 'The product has not yet been evaluated against the criterion; the level is pending a qualified person.'),
        ],
        'tabla_caption': 'Table 1: WCAG 2.2 (A/AA) conformance criteria',
        'col_criterio': 'Criteria', 'col_nivel': 'Conformance level',
        'col_comentarios': 'Remarks and explanations',
        'firma_titulo': 'Signature and evidence',
        'firma': ('This document is a <strong>DRAFT</strong> generated by automated '
                  'screening. Levels marked "Not Evaluated" must be set by a qualified '
                  'person after review; the signature statement must reference the '
                  'evidence pack hash:'),
        'firma_vacia': 'Empty signature block: name, credential and date pending.',
        'nota_iti': ('VPAT® is a registered trademark of the Information Technology Industry '
                     'Council (ITI). This document is a vendor self-declaration scaffold '
                     'generated by a11y-toolkit; it is not a certification.'),
        'error_sin_pack': 'need a pack (a11y_evidence) or reports (audit report objects)',
        'error_nivel': 'unknown level in overrides: {n} (use supports, partially_supports, does_not_support, not_applicable, not_evaluated)',
        'draft': 'DRAFT — levels pending a qualified person',
    },
}


def _t(lang):
    return TXT.get(lang, TXT['en'])


def _hallazgos_por_codigo(pack):
    """Código de criterio → primer hallazgo con issue+remediation (de los artefactos)."""
    por_codigo = {}
    for art in pack.get('artifacts', []):
        body = art.get('body') or {}
        for h in body.get('findings', []):
            code = (h.get('criterion') or '').split(' ')[0]
            if code and code not in por_codigo:
                por_codigo[code] = h
    return por_codigo


def _comentario(t, fila, hallazgo, nivel, pack_sha):
    """Remarks auto por fila: estado + valor medido + esfuerzo + hallazgo + hash."""
    partes = []
    estado = fila.get('status')
    if estado == 'automated-fail':
        partes.append(t['draft'] + ' — ' + 'automated-fail')
    elif estado == 'automated-review':
        partes.append('automated-review')
    else:
        partes.append(estado)
    nota = fila.get('note')
    if nota:
        partes.append(nota)
    val = fila.get('value')
    if val:
        trozos = []
        if val.get('measured'):
            trozos.append(f"measured {val['measured']}")
        if val.get('example'):
            trozos.append(f"e.g. {val['example']}")
        if trozos:
            partes.append('; '.join(trozos))
    if hallazgo:
        partes.append(f"issue: {hallazgo.get('issue', '')[:220]}")
        if hallazgo.get('remediation'):
            partes.append(f"remediation: {hallazgo['remediation'][:220]}")
    ef = fila.get('effort')
    if ef:
        partes.append(f"remaining human effort: {ef['class']} ({ef['minutes']} min)")
    partes.append(f"evidence pack sha256 {pack_sha}")
    return ' | '.join(p for p in partes if p)


def _orden_wcag(code):
    try:
        return tuple(int(p) for p in code.split('.'))
    except ValueError:
        return (99, 0, 0)


def generar_vpat(pack=None, reports=None, producto='', version_producto=None,
                 fecha=None, descripcion=None, contacto=None, metodos=None,
                 notas=None, overrides=None, evaluador=None, lang='en',
                 verificados=None, output_path=None):
    """Pack (o informes) → HTML VPAT 2.5 accesible + resumen.

    overrides: {'1.1.1': 'supports', …} — niveles fijados por una persona
    cualificada; ganan sobre la derivación automática."""
    t = _t(lang)
    if pack is None:
        if not reports:
            return {'error': t['error_sin_pack']}
        from .a11yevidence import empaquetar
        pack = empaquetar(reports, verificados=verificados,
                          evaluador=evaluador)
    if not isinstance(pack, dict) or 'criteria' not in pack:
        return {'error': t['error_sin_pack']}
    overrides = overrides or {}
    for code, nivel in overrides.items():
        if nivel not in NIVELES[lang]:
            return {'error': t['error_nivel'].format(n=nivel)}

    from .a11ycrit import _C as _CAT
    pack_sha = pack.get('sha256', '')
    por_codigo = _hallazgos_por_codigo(pack)
    fecha = fecha or datetime.date.today().isoformat()

    filas = []
    resumen = {n: 0 for n in NIVELES[lang]}
    for fila in sorted(pack['criteria'], key=lambda r: _orden_wcag(r['criterion'].split(' ')[0])):
        code = fila['criterion'].split(' ')[0]
        nivel = _ESTADO_A_NIVEL.get(fila.get('status'), 'not_evaluated')
        nivel = overrides.get(code, nivel)
        resumen[nivel] += 1
        cat = _CAT.get(code)
        nombre = cat[1][lang][0] if cat else fila['criterion']
        nivel_wcag = cat[0] if cat else ''
        hallazgo = por_codigo.get(code)
        filas.append({
            'code': code, 'name': nombre, 'level': nivel_wcag,
            'conformance': nivel,
            'remarks': _comentario(t, fila, hallazgo, nivel, pack_sha),
        })

    e = html.escape
    metodos = metodos or t['metodo_defecto']
    filas_html = []
    for f in filas:
        filas_html.append(
            '<tr><th scope="row">' + e(f['code']) + ' ' + e(f['name'])
            + (' <span class="lvl">(Level ' + e(f['level']) + ')</span>' if f['level'] else '')
            + '</th><td><strong>' + e(NIVELES[lang][f['conformance']]) + '</strong></td>'
            + '<td>' + e(f['remarks']) + '</td></tr>')
    leyenda = ''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k, v in t['leyenda'])

    doc = (
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{e(t["titulo"])} — {e(producto)}</title>\n'
        '<style>body{max-width:60rem;margin:2rem auto;padding:0 1rem;'
        'font:1rem/1.6 system-ui,sans-serif} table{border-collapse:collapse;width:100%}'
        ' th,td{border:1px solid #888;padding:.5rem;vertical-align:top;text-align:left}'
        ' thead th{background:#f0f0f0} .lvl{color:#555;font-size:.85em}'
        ' code{background:#f5f5f5;padding:.1rem .3rem}</style>\n</head>\n<body>\n'
        f'<h1>{e(t["titulo"])}</h1>\n'
        f'<p><strong>{e(producto)}</strong>'
        + (f' — {t["version"]}: {e(version_producto)}' if version_producto else '')
        + f' — {t["fecha"]}: <time datetime="{e(fecha)}">{e(fecha)}</time></p>\n'
        + (f'<p><strong>{t["descripcion"]}:</strong> {e(descripcion)}</p>\n' if descripcion else '')
        + (f'<p><strong>{t["contacto"]}:</strong> {e(contacto)}</p>\n' if contacto else '')
        + f'<h2>{t["seccion_estandar"]}</h2>\n<p>{t["estandar"]}</p>\n'
        + f'<h2>{t["metodos"]}</h2>\n<p>{e(metodos)}</p>\n'
        + (f'<h2>{t["notas"]}</h2>\n<p>{e(notas)}</p>\n' if notas else '')
        + f'<details>\n<summary>{t["leyenda_titulo"]}</summary>\n<dl>{leyenda}</dl>\n</details>\n'
        + f'<table>\n<caption>{t["tabla_caption"]}</caption>\n'
        + '<thead><tr><th scope="col">' + t['col_criterio'] + '</th><th scope="col">'
        + t['col_nivel'] + '</th><th scope="col">' + t['col_comentarios']
        + '</th></tr></thead>\n<tbody>\n' + '\n'.join(filas_html) + '\n</tbody>\n</table>\n'
        + f'<h2>{t["firma_titulo"]}</h2>\n<p>{t["firma"]} <code>{e(pack_sha)}</code></p>\n'
        + '<p><em>' + t['firma_vacia'] + '</em></p>\n'
        + (f'<p>{t["producto"]}: {e((evaluador or {}).get("name", "________________"))} — '
           f'{t["credencial"]}: {e((evaluador or {}).get("credential", "________________"))} — '
           f'{t["fecha"]}: {e((evaluador or {}).get("review_date", "________________"))}</p>\n'
           if evaluador else '')
        + f'<footer><p><small>{t["nota_iti"]}</small></p></footer>\n</body>\n</html>'
    )
    res = {'html': doc, 'summary': resumen, 'levels': {f['code']: f['conformance'] for f in filas},
           'pack_sha256': pack_sha, 'draft': True, 'lang': lang}
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc)
        res['guardado_en'] = output_path
    return res


def main(argv):
    ap = argparse.ArgumentParser(description='VPAT 2.5 (WCAG edition) from an evidence pack')
    ap.add_argument('pack', nargs='?', help='evidence pack JSON (a11y_evidence output)')
    ap.add_argument('--producto', required=True, help='product name')
    ap.add_argument('--informes', nargs='+', help='audit report JSONs (builds the pack) instead of pack')
    ap.add_argument('--fecha', help='report date (YYYY-MM-DD, default today)')
    ap.add_argument('--descripcion', help='product description')
    ap.add_argument('--contacto', help='contact information')
    ap.add_argument('--metodos', help='evaluation methods used')
    ap.add_argument('--notas', help='notes')
    ap.add_argument('--overrides', help='JSON: {"1.1.1": "does_not_support", …}')
    ap.add_argument('--evaluador', help='JSON: {"name":…, "credential":…, "review_date":…}')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    pack = json.load(open(a.pack, encoding='utf-8')) if a.pack else None
    reports = [json.load(open(f, encoding='utf-8')) for f in a.informes] if a.informes else None
    res = generar_vpat(pack=pack, reports=reports, producto=a.producto, fecha=a.fecha,
                       descripcion=a.descripcion, contacto=a.contacto, metodos=a.metodos,
                       notas=a.notas, overrides=json.loads(a.overrides) if a.overrides else None,
                       evaluador=json.loads(a.evaluador) if a.evaluador else None,
                       lang=a.lang, output_path=a.out)
    if 'error' in res:
        print(res['error'])
        return 1
    print(json.dumps({'summary': res['summary'], 'pack_sha256': res['pack_sha256'],
                      'guardado_en': res.get('guardado_en'),
                      'draft': res['draft']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
