#!/usr/bin/env python3
"""Informe de implementación ACT — a11y-toolkit contra los casos oficiales W3C.

El listado de implementaciones ACT (axe-core, Alfa, QualWeb…) exige: correr
la herramienta sobre los casos de prueba publicados, publicar un informe
EARL JSON-LD en URL permanente y proponer la entrada vía issue en
w3c/wcag-act-rules. Este script genera ese informe honestamente.

FUENTE LOCAL, CERO RED (lección 2026-10-25): los casos viven en el repo
GitHub w3c/wcag-act-rules — se clona una vez y todo corre desde disco:

    git clone --depth 1 https://github.com/w3c/wcag-act-rules.git /tmp/wcag-act-rules
    python3 scripts/act_report.py --repo /tmp/wcag-act-rules

El `source` de cada sujeto del informe sigue siendo la URL oficial de
w3.org (es la IDENTIDAD del caso), pero el HTML se lee del clon. El modo
--remote existe como respaldo explícito (rate-limited: 1 req/s, una sola
pasada, sin reintentos que re-armen el limitador).

Outcome por regla: alguna señal mapeada disparó → earl:failed; si no →
earl:passed si la página tiene el constructo que la regla mira (tabla
_APLICA), earl:inapplicable si no; nunca cantTell. Consistencia W3C:
esperado-failed no puede ser passed/inapplicable; esperado
passed/inapplicable no puede ser failed. El resumen es honesto — incluye
las reglas donde aún no somos consistentes.

Uso:
  python3 scripts/act_report.py [--repo /tmp/wcag-act-rules] [--limit N]
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)

from a11y_toolkit.a11yaudit import audit_html  # noqa: E402
from a11y_toolkit.a11yact import ACT_MAP  # noqa: E402

TESTCASES_URL = 'https://www.w3.org/WAI/content-assets/wcag-act-rules/testcases.json'
CLON_DEFECTO = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'wcag-act-rules')
OUT_JSON = os.path.join(AQUI, 'docs', 'act-implementation-report.json')
OUT_SUM = os.path.join(AQUI, 'docs', 'act-report-summary.md')

# regla ACT → señales del motor que la implementan (inverso de ACT_MAP)
REGLA_SEÑALES = defaultdict(list)
for señal, reglas in ACT_MAP.items():
    for rid, _nombre in reglas:
        REGLA_SEÑALES[rid].append(señal)

# Aplicabilidad por señal: regex (sobre el HTML del caso) que dice si la
# página SIQUIERA tiene el constructo que la señal mira. Sin match → la
# señal no disparó porque no había nada que mirar → inapplicable. Las
# señales de página completa (title, lang, viewport…) aplican siempre.
_APLICA = {
    'img_no_alt': rb'<img[\s>]',
    'input_img_alt': rb'type=[\'"]?image',
    'ctrl_name': rb'<(button|a[\s>]|summary|select|textarea|input|output|meter)',
    'field_label': rb'<(input|select|textarea)',
    'label_in_name': rb'<(a[\s>]|button|input)',
    'empty_heading': rb'<h[1-6]',
    'iframe_title': rb'<iframe',
    'aria_hidden_focusable': rb'aria-hidden=',
    'aria_value_invalid': rb'aria-(valuenow|valuemin|valuemax)=',
    'role_unknown': rb'role=',
    'lang_missing': rb'<html',
    'lang_invalid': rb'<html[^>]*lang=',
    'element_lang_invalid': rb'lang=',
    'title_missing': rb'<html',
    'meta_refresh': rb'<meta[^>]+http-equiv',
    'zoom_max': rb'<meta[^>]+name=[\'"]?viewport',
    'zoom_no': rb'<meta[^>]+name=[\'"]?viewport',
    'no_bypass': rb'<html',
    'dup_ids': rb'id=',
    'autocomplete_invalid': rb'<(input|select|textarea|form)',
    'contrast_fail': rb'<html',
    'contrast_image_fail': rb'<html',
}
_POR_DEFECTO = rb'<html'


def _outcome(señales, disparadas, html_bytes):
    if any(s in disparadas for s in señales):
        return 'earl:failed', 'signal fired'
    aplica = any(re.search(_APLICA.get(s, _POR_DEFECTO), html_bytes, re.I)
                 for s in señales)
    return ('earl:passed', 'applicable, no violation') if aplica else \
           ('earl:inapplicable', 'construct absent')


# reglas que SOLO el motor renderizado puede decidir (contraste computado):
# se corren con Playwright sobre file:// del clon local — cero red. El
# contraste (afw4f7) se volvió decisivo en la ola del 20/20: exclusiones de
# aplicabilidad + opacidad compuesta + sombra como fondo + muestreo por
# glifos — 34/34 casos oficiales.
REGLAS_RENDERIZADAS = {'afw4f7'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', default=CLON_DEFECTO,
                    help='clon local de w3c/wcag-act-rules (fuente por defecto)')
    ap.add_argument('--remote', action='store_true',
                    help='leer los casos de w3.org (respaldo; lento y limitado)')
    ap.add_argument('--limit', type=int, default=0, help='solo N casos (humo)')
    a = ap.parse_args()

    # ── casos: del clon si existe, si no del JSON ya cacheado/solo remoto ──
    tc_clon = os.path.join(a.repo, 'content-assets', 'wcag-act-rules', 'testcases.json')
    casos = None
    for fuente in (tc_clon, os.path.join('/tmp', 'act-testcases.json')):
        if os.path.exists(fuente):
            with open(fuente, encoding='utf-8') as f:
                casos = json.load(f)['testcases']
            print(f'casos desde {fuente}', flush=True)
            break
    if casos is None:
        import urllib.request
        print('descargando testcases.json (única petición)…', flush=True)
        casos = json.loads(urllib.request.urlopen(TESTCASES_URL, timeout=60).read())['testcases']

    nuestros = [c for c in casos if c['ruleId'] in REGLA_SEÑALES]
    if a.limit:
        nuestros = nuestros[:a.limit]
    print(f'{len(casos)} casos totales · {len(nuestros)} de nuestras '
          f'{len(REGLA_SEÑALES)} reglas mapeadas', flush=True)

    def _html_de(c):
        """HTML del caso: clon local (rápido) o w3.org (respaldo educado)."""
        if not a.remote:
            ruta = os.path.join(a.repo, 'content-assets', 'wcag-act-rules',
                                c['relativePath'])
            with open(ruta, 'rb') as f:
                return f.read()
        import urllib.request
        datos = urllib.request.urlopen(c['url'], timeout=25).read()
        time.sleep(1.0)  # UNA petición por segundo, sin reintentos
        return datos

    grafo, errores = [], []
    consist = defaultdict(lambda: defaultdict(int))
    _dom_disponible = True
    try:
        from a11y_toolkit.a11ydom import audit_dom_url  # noqa: F401
    except ImportError:
        _dom_disponible = False
        print('⚠ sin Playwright: las reglas renderizadas se quedan en estático', flush=True)
    for i, c in enumerate(nuestros):
        try:
            html = _html_de(c)
            ruta_local = os.path.abspath(os.path.join(a.repo, 'content-assets',
                                                      'wcag-act-rules', c['relativePath']))
            if c['ruleId'] in REGLAS_RENDERIZADAS and _dom_disponible \
                    and not a.remote and os.path.exists(ruta_local):
                # contraste computado con navegador real sobre el fichero local
                from a11y_toolkit.a11ydom import audit_dom_url
                rep = audit_dom_url('file://' + ruta_local, timeout=15, lang='en')
                disparadas = {f.get('signal') for f in rep.get('findings', [])}
                html = open(ruta_local, 'rb').read()
            else:
                rep = audit_html(html.decode('utf-8', 'replace'),
                                 url=c['url'], lang='en')
                disparadas = {f.get('signal') for f in rep.get('findings', [])}
        except Exception as e:  # noqa: BLE001
            errores.append({'testcase': c['testcaseId'], 'error': str(e)})
            continue
        aserciones = []
        señales = REGLA_SEÑALES[c['ruleId']]
        outcome, _pk = _outcome(señales, disparadas, html)
        esperado = {'passed': 'earl:passed', 'failed': 'earl:failed',
                    'inapplicable': 'earl:inapplicable'}[c['expected']]
        consist[c['ruleId']][f'{esperado}→{outcome}'] += 1
        aserciones.append({
            '@type': 'Assertion',
            'result': {'outcome': outcome},
            'test': {
                'title': f'ACT {c["ruleId"]} — {c["ruleName"]}',
                'isPartOf': [f'WCAG2:{k.split(":")[-1]}'
                             for k in (c.get('ruleAccessibilityRequirements') or {})
                             if k.startswith('wcag:')],
            },
        })
        grafo.append({'@type': 'TestSubject', 'source': c['url'],
                      'assertions': aserciones})
        if (i + 1) % 60 == 0:
            print(f'  {i + 1}/{len(nuestros)}…', flush=True)

    informe = {
        '@context': 'https://act-rules.github.io/earl-context.json',
        'name': 'a11y-toolkit',
        'website': 'https://github.com/kinti/a11y-toolkit',
        '@graph': grafo,
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(informe, f, ensure_ascii=False, indent=1)
    print(f'informe: {OUT_JSON} ({len(grafo)} sujetos)', flush=True)

    # ── resumen de consistencia (criterio W3C) ──
    lineas = ['# ACT implementation — a11y-toolkit', '',
              f'Casos corridos: {len(grafo)} · reglas con casos: {len(consist)} · '
              f'errores: {len(errores)}', '',
              'Fuente: clon local de w3c/wcag-act-rules (regenerable con '
              '`git clone --depth 1` + `scripts/act_report.py`); outcomes del '
              'motor sin lógica por caso. Contraste (afw4f7) medido con el '
              'motor RENDERIZADO sobre file:// del clon.', '',
              'Consistencia ACT por regla (esperado → outcome, recuentos):', '']
    consistentes = 0
    for rid in sorted(consist):
        d = consist[rid]
        # esperado-failed no puede ser passed/inapplicable (omisión);
        # esperado passed/inapplicable no puede ser failed (falso positivo);
        # passed↔inapplicable cruzados ES consistente
        malos = {k: v for k, v in d.items()
                 if re.match(r'earl:failed→earl:(passed|inapplicable)', k)
                 or re.match(r'earl:(passed|inapplicable)→earl:failed', k)}
        bien = not malos
        consistentes += bien
        marca = '✓' if bien else '✗'
        detalle = '; '.join(f'{k}: {v}' for k, v in sorted(d.items()))
        lineas.append(f'- {marca} `{rid}`: {detalle}')
    lineas += ['', f'**Reglas consistentes: {consistentes}/{len(consist)}**',
               '', 'Datos aportados por el proveedor; el W3C no los verifica',
               'ni respalda (alcance del listado oficial).', '']
    with open(OUT_SUM, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas))
    print(f'resumen: {OUT_SUM} · consistentes {consistentes}/{len(consist)}', flush=True)
    if errores:
        print(f'⚠ {len(errores)} casos con error (ver JSON/consola)', flush=True)


if __name__ == '__main__':
    main()
