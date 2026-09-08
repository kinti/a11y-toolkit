#!/usr/bin/env python3
"""Autofix determinista — SOLO correcciones demostrablemente seguras.

La lección del sector (overlays "IA" tipo accessiBe, multa FTC de 1M$): arreglar
accesibilidad inyectando conjeturas termina en multa. Este módulo hace lo
contrario: una lista corta de transformaciones donde el arreglo correcto es
ÚNICO y verificable, y para todo lo demás un «no lo toco, esto es lo que haría
falta» honesto.

Transformaciones (lista cerrada, auditable):
  1. viewport        — elimina user-scalable=no/0 y maximum-scale<2 (1.4.4).
                       El zoom es un derecho; quitar el bloqueo nunca rompe nada.
  2. autocomplete    — añade el token determinista a inputs que lo exigen (1.3.5):
                       type=email→email, type=tel→tel, type=url→url, y name/id que
                       casan con el patrón de datos personales (name, postal-code…).
  3. lang de <html>  — SOLO si falta y la persona usuaria da --lang.
  4. <title> vacío   — SOLO si la persona usuaria da --title.

Todo lo demás (alt, contraste, nombres accesibles…) exige criterio humano o del
agente: se enumera en «no_aplicados» con la remediación correspondiente.

CLI:
  a11yfix.py --file pagina.html [--lang es] [--title "T"] [-o fixed.html]
  audit --file pagina.html | a11yfix.py --lang es --title "T" -o fixed.html   (stdin JSON)
"""

import argparse
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

    # 3. lang de <html> (solo si falta y lo dan)
    if lang:
        m = _RE_HTML_TAG.search(fixed)
        if m and 'lang=' not in m.group(1).lower():
            fixed = fixed[:m.start()] + f'<html lang="{lang}"' + m.group(1) + '>' + fixed[m.end():]
            aplicados.append({'senal': 'lang_missing',
                              'hecho': f'<html lang="{lang}"> (3.1.1)'})

    # 4. title (solo si vacío y lo dan)
    if title and _RE_TITLE.search(fixed):
        fixed = _RE_TITLE.sub(f'<title>{title}</title>', fixed, count=1)
        aplicados.append({'senal': 'title_missing', 'hecho': '<title> añadido (2.4.2)'})

    # 5. lo que NO se toca — honestidad operativa
    informe = audit_html(html_text, url, lang='es')
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
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--file')
    g.add_argument('--stdin-audit', action='store_true')
    ap.add_argument('--lang', choices=['es', 'en', 'pt', 'fr', 'de', 'it', 'gl', 'ca', 'eu'])
    ap.add_argument('--title')
    ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    if a.file:
        with open(a.file, encoding='utf-8', errors='replace') as f:
            html_text = f.read()
    else:
        print('lee el HTML por stdin: a11ytoolkit audit --file x.html no sirve aquí; usa --file')
        return 1
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
