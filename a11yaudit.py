#!/usr/bin/env python3
"""Auditoría exprés de accesibilidad sobre HTML (heurísticas WCAG, sin dependencias).

a11y_audit_url / audit_html revisan señales automáticas de las que derivan
criterios concretos de WCAG 2.2: imágenes sin alternativa (1.1.1), controles
sin nombre accesible (4.1.2), campos sin etiqueta (3.3.2), idioma (3.1.1),
título (2.4.2), salto de encabezados (1.3.1), zoom bloqueado (1.4.4),
tabindex positivos (2.4.3), iframes sin título (4.1.2).

La automatización cubre ~un tercio de WCAG: la revisión manual sigue siendo
insustituible. Esta herramienta es filtro, no veredicto.

CLI:
  a11yaudit.py --url https://example.com
  a11yaudit.py --file pagina.html
"""

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

MAX_HTML = 3_000_000

# Campos de formulario que necesitan etiqueta visible o nombre accesible
_CAMPOS = {'text', 'email', 'tel', 'url', 'search', 'password', 'number',
           'date', 'time', 'datetime-local', 'month', 'week'}


class _Auditor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs_sin_alt = []
        self.sitios = {}          # tag → lista de (nombre, atributos) de controles sin nombre
        self.campos_sin_label = []
        self.iframes_sin_title = []
        self.lang = None
        self.title = ''
        self._en_title = False
        self.headings = []        # (nivel, texto)
        self._nivel_h = None
        self._texto_h = []
        self.tabindex_positivos = []
        self.viewport = None
        self.elementos = 0
        # Pila de controles interactivos (a/button/summary) para recoger su
        # texto interno, que es la fuente más habitual de nombre accesible.
        self._ctrl = []
        self._label_depth = 0
        self._labels_for = set()

    def _cierra_control(self, tag):
        if not self._ctrl:
            return
        c = self._ctrl[-1]
        if c['tag'] != tag:
            return
        self._ctrl.pop()
        a = c['attrs']
        texto = ' '.join(c['texto']).strip()
        if not (texto or a.get('aria-label') or a.get('aria-labelledby')
                or a.get('title') or a.get('alt')):
            # el nombre del control puede venir también de una imagen interna
            if not c.get('img_interna'):
                self.sitios.setdefault(tag, []).append(a)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.elementos += 1
        if tag == 'html':
            self.lang = (a.get('lang') or '').strip()
        elif tag == 'title':
            self._en_title = True
        elif tag == 'meta' and a.get('name', '').lower() == 'viewport':
            self.viewport = a.get('content', '')
        elif tag == 'img':
            if 'alt' not in a:
                self.imgs_sin_alt.append(a.get('src', '')[:100])
            if self._ctrl and a.get('alt', '').strip():
                self._ctrl[-1]['img_interna'] = True
        elif tag == 'iframe':
            if not (a.get('title') or a.get('aria-label')):
                self.iframes_sin_title.append((a.get('src') or '')[:100])
        elif tag in ('a', 'button', 'summary'):
            # Enlace no interactivo (ancla pura sin href): no se audita.
            if tag == 'a' and not (a.get('href') or '').strip():
                pass
            else:
                self._ctrl.append({'tag': tag, 'attrs': a, 'texto': [], 'img_interna': False})
        elif tag == 'input':
            tipo = (a.get('type') or 'text').lower()
            if tipo in ('submit', 'button', 'reset'):
                if not (a.get('value') or a.get('aria-label') or a.get('alt')):
                    self.sitios.setdefault('input:' + tipo, []).append(a)
            elif tipo in _CAMPOS:
                tiene_nombre = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
                if not tiene_nombre and self._label_depth == 0:
                    self.campos_sin_label.append((tipo, a.get('name', '')[:60], a.get('id')))
        elif tag == 'label':
            self._label_depth += 1
            if a.get('for'):
                self._labels_for.add(a['for'])
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._nivel_h = int(tag[1])
            self._texto_h = []
        ti = a.get('tabindex')
        if ti and ti.isdigit() and int(ti) > 0:
            self.tabindex_positivos.append((tag, int(ti)))

    def handle_endtag(self, tag):
        if tag == 'title':
            self._en_title = False
        elif tag == 'label':
            self._label_depth = max(0, self._label_depth - 1)
        elif tag in ('a', 'button', 'summary'):
            self._cierra_control(tag)
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self._nivel_h:
            self.headings.append((self._nivel_h, ' '.join(self._texto_h).strip()[:80]))
            self._nivel_h = None

    def handle_data(self, data):
        if self._en_title:
            self.title += data
        else:
            # Un texto puede pertenecer a la vez a un enlace dentro de un
            # encabezado (<h2><a>Guías</a></h2>): alimenta a ambos.
            if self._ctrl:
                self._ctrl[-1]['texto'].append(data)
            if self._nivel_h is not None:
                self._texto_h.append(data)


def audit_html(html_text, url='(html)'):
    """Analiza una cadena HTML y devuelve el informe de hallazgos."""
    p = _Auditor()
    try:
        p.feed(html_text[:MAX_HTML])
        p.close()
    except Exception as e:  # noqa: BLE001
        return {'error': f'HTML no parseable: {e}'}

    # Campos cuyo id sí tiene un <label for> explícito en otro punto: fuera.
    p.campos_sin_label = [c for c in p.campos_sin_label if c[2] not in p._labels_for]

    hallazgos = []

    def add(severidad, criterio, descripcion, ejemplos=None):
        h = {'severidad': severidad, 'criterio': criterio, 'hallazgo': descripcion}
        if ejemplos:
            h['ejemplos'] = ejemplos[:5]
        hallazgos.append(h)

    if p.imgs_sin_alt:
        add('alta', '1.1.1 Contenido no textual',
            f'{len(p.imgs_sin_alt)} <img> sin atributo alt (ni siquiera alt="").',
            p.imgs_sin_alt)
    for tag, controles in p.sitios.items():
        add('alta', '4.1.2 Nombre, función, valor',
            f'{len(controles)} <{tag}> sin nombre accesible (sin texto, aria-label ni title).')
    if p.campos_sin_label:
        add('alta', '3.3.2 Etiquetas o instrucciones',
            f'{len(p.campos_sin_label)} campos de formulario sin <label> asociado ni nombre accesible.',
            [f'input type={t} name={n or "(sin name)"}' for t, n, _i in p.campos_sin_label])
    if not p.lang:
        add('media', '3.1.1 Idioma de la página', 'El elemento <html> no declara lang.')
    if not p.title.strip():
        add('media', '2.4.2 Página con título', 'La página no tiene <title> con contenido.')
    if p.iframes_sin_title:
        add('media', '4.1.2 Nombre, función, valor',
            f'{len(p.iframes_sin_title)} <iframe> sin title accesible.', p.iframes_sin_title)
    if p.viewport and re.search(r'user-scalable\s*=\s*(no|0)', p.viewport, re.I):
        add('alta', '1.4.4 Cambio de tamaño del texto',
            'El viewport bloquea el zoom del usuario (user-scalable=no/0).')
    elif p.viewport and (m := re.search(r'maximum-scale\s*=\s*([\d.]+)', p.viewport, re.I)) \
            and float(m.group(1)) < 2:
        add('media', '1.4.4 Cambio de tamaño del texto',
            f'El viewport limita el zoom (maximum-scale={m.group(1)}; se recomienda no limitar o ≥2).')
    if p.tabindex_positivos:
        add('media', '2.4.3 Orden del foco',
            f'{len(p.tabindex_positivos)} elementos con tabindex positivo (modifica el orden natural).',
            [f'{t}[tabindex={i}]' for t, i in p.tabindex_positivos])

    niveles = [n for n, _ in p.headings]
    if niveles:
        if 1 not in niveles:
            add('media', '1.3.1 Estructura e información',
                'No hay ningún <h1> en la página.')
        prev = 0
        saltos = []
        for n in niveles:
            if prev and n > prev + 1:
                saltos.append(f'h{prev}→h{n}')
            prev = n
        if saltos:
            add('baja', '1.3.1 Estructura e información',
                f'Saltos de nivel en encabezados: {", ".join(saltos[:5])}.')
    else:
        add('media', '1.3.1 Estructura e información',
            'La página no tiene encabezados (h1–h6).')

    severidad_orden = {'alta': 0, 'media': 1, 'baja': 2}
    hallazgos.sort(key=lambda h: severidad_orden[h['severidad']])
    resumen = {s: sum(1 for h in hallazgos if h['severidad'] == s)
               for s in ('alta', 'media', 'baja')}
    return {
        'url': url,
        'elementos_analizados': p.elementos,
        'resumen': resumen,
        'hallazgos': hallazgos,
        'limites': ('Automatización ≈ un tercio de WCAG: esto es un filtro exprés, no sustituye '
                    'revisión manual (teclado, lector de pantalla, contraste real, refrán de '
                    'auditoría).'),
    }


def audit_url(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'a11y-toolkit/2.2 (WCAG audit)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        datos = r.read(MAX_HTML + 1)
        if len(datos) > MAX_HTML:
            return {'error': f'HTML > {MAX_HTML // 1000000} MB, demasiado grande'}
        charset = 'utf-8'
        m = re.search(rb'charset=["\']?([\w-]+)', datos[:2048])
        if m:
            charset = m.group(1).decode('ascii', 'ignore')
        try:
            html_text = datos.decode(charset, 'replace')
        except LookupError:
            html_text = datos.decode('utf-8', 'replace')
    return audit_html(html_text, url)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url')
    g.add_argument('--file')
    a = ap.parse_args(argv)
    if a.url:
        try:
            res = audit_url(a.url)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({'error': f'no se pudo descargar: {e}'}))
            return 1
    else:
        res = audit_html(open(a.file, encoding='utf-8', errors='replace').read(), a.file)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
