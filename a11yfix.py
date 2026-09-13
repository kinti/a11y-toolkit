#!/usr/bin/env python3
"""Deterministic autofix — ONLY provably safe corrections.

The industry lesson (overlay vendors, the accessiBe FTC fine): fixing
accessibility by injecting guesses ends in fines. This module does the
opposite: a short closed list of transformations where the correct fix is
UNIQUE and verifiable, and for everything else an honest "not touched —
here is what it would take".

Transformations (closed, auditable list):
  1. viewport        — removes user-scalable=no/0 and maximum-scale<2 (1.4.4).
  2. autocomplete    — adds the deterministic token to inputs that require it
                       (1.3.5): type=email→email, tel→tel, url→url, and name/id
                       matching the personal-data pattern (name, postal-code…).
  3. <html> lang     — ONLY if missing and the caller provides --lang.
  4. empty <title>   — ONLY if the caller provides --title.

Everything else (alt, contrast, accessible names…) requires human or agent
judgment: listed under "no_aplicados" with the remediation.

CLI:
  a11yfix.py --file page.html [--lang es] [--title "T"] [-o fixed.html]
"""

import argparse
import html as _html
import json
import re
import sys

from a11yaudit import audit_html, _DATO_PERSONAL

# token autocomplete por type de input (determinista por especificación)
_TOKEN_POR_TYPE = {'email': 'email', 'tel': 'tel', 'url': 'url'}
# token por pista de name/id (mismas pistas que usa el auditor 1.3.5)
_TOKEN_POR_PISTA = [
    (re.compile(r'postal|zip|cp\b', re.I), 'postal-code'),
    (re.compile(r'street|direccion|address|calle', re.I), 'street-address'),
    (re.compile(r'ciudad|city', re.I), 'address-level2'),
    (re.compile(r'country|pais', re.I), 'country-name'),
    (re.compile(r'organi[sz]ation|company|empresa', re.I), 'organization'),
    (re.compile(r'phone|telefono|tel\b', re.I), 'tel'),
    (re.compile(r'email|correo', re.I), 'email'),
    (re.compile(r'(?:^|[\W_])(?:full)?name|nombre', re.I), 'name'),
]

_RE_INPUT = re.compile(r'<input\b[^>]*>', re.I)
_RE_VIEWPORT = re.compile(r'(<meta\s[^>]*name=["\']viewport["\'][^>]*content=["\'])([^"\']*)(["\'])', re.I)
_RE_HTML_TAG = re.compile(r'<html\b([^>]*)>', re.I)
_RE_TITLE = re.compile(r'<title>\s*</title>', re.I)


def _attrs(tag_html):
    pares = re.findall(r'([\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag_html)
    return {k: next(v for v in vals if v != '') for k, *vals in
            ((k, a, b, c) for k, a, b, c in pares)}


def _viewport_limpio(content):
    partes = [p.strip() for p in content.split(',') if p.strip()]
    fuera = []
    limpias = []
    for p in partes:
        if re.match(r'user-scalable\s*=\s*(no|0)', p, re.I):
            fuera.append(p)
            continue
        m = re.match(r'maximum-scale\s*=\s*([\d.]+)', p, re.I)
        if m and float(m.group(1)) < 2:
            fuera.append(p)
            continue
        limpias.append(p)
    return ', '.join(limpias), fuera


def autofix(html_text, lang=None, title=None, url='(html)'):
    """Aplica los arreglos seguros. Devuelve fixed_html + aplicados + no_aplicados."""
    aplicados = []
    fixed = html_text

    # 1. viewport: zoom sin bloqueos (1.4.4)
    m = _RE_VIEWPORT.search(fixed)
    if m and (re.search(r'user-scalable\s*=\s*(no|0)', m.group(2), re.I)
              or re.search(r'maximum-scale\s*=\s*([\d.]+)', m.group(2), re.I)):
        limpio, fuera = _viewport_limpio(m.group(2))
        if limpio:
            fixed = fixed[:m.start()] + m.group(1) + limpio + m.group(3) + fixed[m.end():]
        else:
            fixed = fixed[:m.start()] + fixed[m.end():]
        aplicados.append({'senal': 'zoom_no',
                          'hecho': f'viewport sin {", ".join(fuera)} (1.4.4: el zoom no se bloquea)'})

    # 2. autocomplete determinista (1.3.5)
    n_ac = 0

    def _input_fix(mtag):
        nonlocal n_ac
        tag = mtag.group(0)
        if 'autocomplete' in tag.lower():
            return tag
        a = _attrs(tag)
        tipo = (a.get('type') or 'text').lower()
        token = _TOKEN_POR_TYPE.get(tipo)
        if not token:
            pista = (a.get('name') or '') + ' ' + (a.get('id') or '')
            if tipo in ('search', 'password'):
                return tag
            for rx, tok in _TOKEN_POR_PISTA:
                if rx.search(pista):
                    token = tok
                    break
        if not token:
            return tag
        n_ac += 1
        return tag[:-1].rstrip() + f' autocomplete="{token}">'
    fixed = _RE_INPUT.sub(_input_fix, fixed)
    if n_ac:
        aplicados.append({'senal': 'autocomplete',
                          'hecho': f'{n_ac} inputs con su token autocomplete (1.3.5)'})

    # 3. lang de <html> (solo si falta y lo dan); BCP-47 validado y escapado:
    #    este toolkit ESCRIBE HTML, no puede ser vector de inyección
    if lang and re.fullmatch(r'[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*', lang.strip()):
        m = _RE_HTML_TAG.search(fixed)
        if m and 'lang=' not in m.group(1).lower():
            fixed = fixed[:m.start()] + f'<html lang="{_html.escape(lang.strip())}"' + m.group(1) + '>' + fixed[m.end():]
            aplicados.append({'senal': 'lang_missing',
                              'hecho': f'<html lang="{lang.strip()}"> (3.1.1)'})

    # 4. title (solo si vacío y lo dan); escapado por la misma razón
    if title and _RE_TITLE.search(fixed):
        fixed = _RE_TITLE.sub(lambda _m: f'<title>{_html.escape(title)}</title>', fixed, count=1)
        aplicados.append({'senal': 'title_missing', 'hecho': '<title> añadido (2.4.2)'})

    # 5. lo que NO se toca — honestidad operativa
    informe = audit_html(html_text, url, lang='en')
    no_toca = {
        'imgs_alt': 'no sabemos si la imagen es decorativa: alt="" o descriptivo lo decide alguien',
        'ctrl_name': 'el nombre accesible exige saber qué hace el control',
        'field_label': 'el texto de la etiqueta lo dicta el contenido',
        'contrast_fail': 'elegir el color nuevo es una decisión de diseño (usa a11y_suggest_color)',
        'target_small': 'rediseño de layout',
        'list_structure': 'rehacer el marcado exige entender la estructura',
    }
    ya = {a['senal'] for a in aplicados}
    no_aplicados = []
    vistos = set()
    for h in informe.get('hallazgos', []):
        senal = h['senal']
        if senal in no_toca and senal not in vistos and senal not in ya:
            vistos.add(senal)
            no_aplicados.append({'senal': senal, 'criterio': h['criterio'],
                                 'por_que_no': no_toca[senal],
                                 'remediacion': h['remediacion']})

    return {'fixed_html': fixed, 'aplicados': aplicados, 'no_aplicados': no_aplicados}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--file', required=True)
    ap.add_argument('--lang', choices=['es', 'en', 'pt', 'fr', 'de', 'it', 'gl', 'ca', 'eu'])
    ap.add_argument('--title')
    ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    with open(a.file, encoding='utf-8', errors='replace') as f:
        html_text = f.read()
    res = autofix(html_text, lang=a.lang, title=a.title, url=a.file)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(res['fixed_html'])
        print(json.dumps({'fichero': a.out, 'aplicados': res['aplicados'],
                          'no_aplicados': res['no_aplicados']}, ensure_ascii=False, indent=1))
    else:
        print(res['fixed_html'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
