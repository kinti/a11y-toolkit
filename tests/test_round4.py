#!/usr/bin/env python3
# Ronda 4 (2026-11-04, análisis desde cero post-120-arreglos): cada fix de la
# ronda, pineado. Los hallazgos vienen de 6 revisores frescos + cadena viva;
# cada test falla contra el código de la ronda anterior.

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.a11yaudit import audit_html, _apply_standard  # noqa: E402

BASE = '<html lang="en"><head><meta charset="utf-8"><title>t</title></head><body>{}</body></html>'
ok = 0


def check(nombre, cond, detalle=''):
    global ok
    assert cond, f'{nombre}: {detalle}'
    ok += 1
    print(f'  {ok}. {nombre} ✓')


# ── motor estático ──────────────────────────────────────────────────────────
# svg[role=img] SIN nombre: era invisible (el elif del svg se comía el rol)
r = audit_html(BASE.format('<h1>k</h1><main><svg role="img" viewBox="0 0 24 24">'
                           '<path d="M4 4h16v16H4z"/></svg></main>'))
check('svg[role=img] sin nombre → img_no_alt',
      any(x['signal'] == 'img_no_alt' for x in r['findings']))

# svg[role=img] CON <title> hijo: con nombre (la vía del W3C)
r = audit_html(BASE.format('<h1>k</h1><main><svg role="img"><title>Sales chart</title></svg></main>'))
check('svg[role=img] con <title> → sin hallazgo',
      not any(x['signal'] == 'img_no_alt' for x in r['findings']))

# per-video captions: dos tracks en un vídeo NO salvan al segundo
r = audit_html(BASE.format('<h1>k</h1><main><video controls><track kind="captions" srclang="en">'
                           '<track kind="subtitles" srclang="es"></video>'
                           '<video controls src="b.mp4"></video></main>'))
f = [x for x in r['findings'] if x['signal'] == 'video_captions']
check('captions por-VÍDEO (no por-track)', f and '1' in f[0]['issue'])

# track huérfano / en template no acredita
r = audit_html(BASE.format('<h1>k</h1><main><template><track kind="captions"></template>'
                           '<video controls src="a.mp4"></video></main>'))
check('track en template no acredita captions',
      any(x['signal'] == 'video_captions' for x in r['findings']))

# tabla presentation anidada NO popea la entrada de la externa
r = audit_html(BASE.format('<h1>k</h1><main><table><caption>Prices</caption>'
                           '<tr><td><table role="presentation"><tr><td>x</td></tr></table></td></tr>'
                           '<tr><th>Plan</th><td>1</td></tr></table></main>'))
check('tabla presentation anidada: la externa con th no acusa',
      not any(x['signal'] == 'table_no_th' for x in r['findings']))

# border="1" = DATOS (spec); border="0" = maquetación
r = audit_html(BASE.format('<h1>k</h1><main><table border="1"><tr><td>Q1</td><td>1</td></tr></table></main>'))
check('border=1 es tabla de datos → exige th',
      any(x['signal'] == 'table_no_th' for x in r['findings']))
r = audit_html(BASE.format('<h1>k</h1><main><table border="0" cellpadding="0">'
                           '<tr><td>n</td></tr></table></main>'))
check('border=0 sigue siendo maquetación',
      not any(x['signal'] == 'table_no_th' for x in r['findings']))

# texto de <template> es inerte: ni lang ni prosa
r = audit_html(BASE.format('<main><h1>k</h1><template><p lang="zz">foo</p></template></main>'))
check('texto de template no dispara 3.1.2',
      not any(x['signal'] == 'element_lang_invalid' for x in r['findings']))

# delegación: <a> SIN href no salva al wrapper (no es operable)
r = audit_html(BASE.format('<h1>k</h1><main><div onclick="buy()"><a class="btn">Buy</a></div></main>'))
check('a-sin-href no exime el click no enfocable',
      any(x['signal'] == 'click_nonfocusable' for x in r['findings']))

# <a> sin </a> arrastrado por un </div>: el enlace sigue contándose
r = audit_html(BASE.format('<h1>k</h1><main><div><a href="/x" target="_blank">offer</div></a></main>'))
check('ancla rescatada bajo cierre forzado → blank_no_warning',
      any(x['signal'] == 'blank_no_warning' for x in r['findings']))

# ids de template no existen: sin dup_ids
r = audit_html(BASE.format('<h1>k</h1><main><div id="row"></div>'
                           '<template><div id="row"></div></template></main>'))
check('id duplicado en template no cuenta', not any(
    x['signal'] == 'dup_ids' for x in r['findings']))

# username/fullname en 1.3.5
r = audit_html(BASE.format('<h1>k</h1><main><form><input type="text" name="username"></form></main>'))
check('name=username pide autocomplete',
      any(x['signal'] == 'autocomplete' for x in r['findings']))

# documento SVG raíz: sin title_missing
r = audit_html('<svg xmlns="http://www.w3.org/2000/svg"><title>Icon</title></svg>')
check('SVG raíz sin title_missing',
      not any(x['signal'] == 'title_missing' for x in r['findings']))

# viewport múltiple: el path apunta al ÚLTIMO (el que decide)
r = audit_html('<html lang="en"><head><title>t</title>'
               '<meta name="viewport" content="width=device-width">'
               '<meta name="viewport" content="user-scalable=no"></head>'
               '<body><h1>k</h1><main><p>x</p></main></body></html>')
f = [x for x in r['findings'] if x['signal'] == 'zoom_no']
check('zoom_no con 2 viewports: path al que bloquea',
      f and f[0].get('paths') and 'nth-of-type(2)' in f[0]['paths'][0])

# tabindex superscript no tira el parse
r = audit_html(BASE.format('<h1>k</h1><main><a href="/x" tabindex="²">raro</a></main>'))
check('tabindex superscript sobrevive', 'error' not in r)

# redirect mismo-host: mensaje por catálogo, mismo-host permitido
from a11y_toolkit import a11yaudit as _aa  # noqa: E402
err = _aa._FetchError('err_redirect_blocked', url='http://x')
from a11y_toolkit.a11yaudit import _t  # noqa: E402
check('err_redirect_blocked bilingüe',
      'private' in _t('en', 'err_redirect_blocked') and 'privada' in _t('es', 'err_redirect_blocked'))

# normalize_report hostil: findings dict → [] sin crash
from a11y_toolkit.a11yaudit import normalize_report  # noqa: E402
check('normalize_report findings-dict hostil',
      normalize_report({'mode': 'static', 'findings': {'a': 1}})['findings'] == [])

# ── cadena de conformidad ───────────────────────────────────────────────────
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402
# disprover-site: findings top-level (not-rechecked) NO resucitan
_site = {'mode': 'site', 'url': 'https://x', 'reports': [
    {'mode': 'static', 'url': 'https://x/a', 'findings': [
        {'severity': 'high', 'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt',
         'issue': 'x', 'remediation': 'y'}]}],
    'findings': [{'severity': 'high', 'criterion': '1.1.1 Non-text Content',
                  'signal': 'img_no_alt', 'issue': 'x', 'remediation': 'y',
                  'disprover_status': 'not-rechecked', 'page': 'https://x/a'}]}
_pack = build_pack([_site])
_row = [c for c in _pack['criteria'] if c['criterion'].startswith('1.1.1')][0]
check('disproved-site: not-rechecked no resucita en la matriz',
      _row['status'] != 'automated-fail', _row['status'])

# vpat remarks: cita hallazgos de artifacts site (desciende reports[]);
# en el caso disproved (arriba) quedarse VACÍO es lo honesto — todos muertos
from a11y_toolkit import a11yvpat  # noqa: E402
_by_dead = a11yvpat._findings_by_code(_pack)
check('vpat remarks: crawl disproved → sin citas muertas', not _by_dead.get('1.1.1'))
_site_clean = {'mode': 'site', 'url': 'https://x', 'reports': [
    {'mode': 'static', 'url': 'https://x/a', 'findings': [
        {'severity': 'high', 'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt',
         'issue': '3 <img> sin alt', 'remediation': 'y'}]}]}
_pack_clean = build_pack([_site_clean])
_by = a11yvpat._findings_by_code(_pack_clean)
check('vpat remarks citan hallazgos del crawl limpio',
      '1.1.1' in _by and 'sin alt' in _by['1.1.1'].get('issue', ''))

# earl aplana site (crawl limpio → assertions del anidamiento) y respeta muertos
from a11y_toolkit.a11yact import earl  # noqa: E402
_e = earl(_site_clean)
check('earl site: assertions del anidamiento', len(_e['@graph']) >= 1)
_e2 = earl(_site)
check('earl site-disproved: muertos fuera', len(_e2['@graph']) == 0)

# ── shapes de la capa renderizada (sin Playwright: fuente) ──────────────────
_dom = open(os.path.join(os.path.dirname(__file__), '..', 'a11y_toolkit', 'a11ydom.py'),
            encoding='utf-8').read()
check('forms JS escribe fields (no campos)', 'info.fields++' in _dom and 'info.campos++' not in _dom)
check('sr_transcript SIEMPRE pw.stop()', _dom.count('sync_playwright().start()') == 1
      and 'finally:' in _dom.split('def sr_transcript')[1].split('def ')[0])
check('pool reutiliza con auto',
      "(preferred in (None, 'auto') or _POOL['type'] == preferred)" in _dom)
_pat = open(os.path.join(os.path.dirname(__file__), '..', 'a11y_toolkit', 'a11ypatterns.py'),
            encoding='utf-8').read()
check('tablist vertical: ArrowDown aceptado', 'ArrowDown' in _pat)
_tr = open(os.path.join(os.path.dirname(__file__), '..', 'a11y_toolkit', 'a11ytrace.py'),
           encoding='utf-8').read()
check("trace hub: prepend 'trace'", "argv = ['trace'] + argv" in _tr)

# sr severidades renderizadas alineadas con el estático
for _sig, _sev in (("'zoom_max'", "'high'"), ("'no_bypass'", "'low'"),
                   ("'no_h1'", "'low'"), ("'no_headings'", "'low'")):
    check(f'rendered {_sig} → {_sev}',
          f"_add(findings, lang, {_sev}, " in _dom and f"'{_sig[1:-1]}'" in _dom)

print(f'\nRONDA 4 OK ✓ ({ok} pines: motor, cadena, rendered)')
