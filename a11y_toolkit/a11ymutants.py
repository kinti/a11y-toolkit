#!/usr/bin/env python3
"""a11y_mutants — the engine's sealed exam (WCAG mutation testing).

Cross-industry translation: mutation testing — inject known defects into a
working program and count what the test suite kills — applied to
accessibility evaluation. The generator builds a CLEAN page that varies
with the seed, injects ONE violation per mutant (each operator derived
from the toolkit's own signal→criterion map), and keeps the sealed answer
log (operator + expected signal + criterion). Same seed = same exam, to
compare auditors fairly; fresh seed = an exam nobody has memorized.

Placebo control pages (clean, no violation injected) catch false
positives: any finding on them is a false positive by construction.

This is a self-exam, not a tool (D17): the engine that publishes its own
kill rate is an engine that can be measured. CLI:

  a11ymutants.py --seed 7 --n 12 [--out exam-dir]
"""

import argparse
import json
import os
import random
import re
import sys

from .a11yaudit import audit_html, normalize_signal

# ── página limpia regenerable ──────────────────────────────────────────────
# La estructura es siempre accesible; el contenido varía por semilla (títulos,
# nº de imágenes, textos). El test clava los placebos a CERO hallazgos: si
# alguien rompe una plantilla limpia, la suite se tiñe.
_WORDS = {
    'title': ['Quarterly accessibility report', 'Service dashboard guide',
              'Inclusion handbook for editors', 'Regional transit study',
              'Public library annual review', 'Water quality summary'],
    'h1': ['Accessibility report', 'Service overview', 'Editorial handbook',
           'Transit study', 'Annual review', 'Water quality summary'],
    'h2': ['Key findings', 'Methodology', 'Recommendations', 'Data summary',
           'Next steps', 'Background', 'Annexes'],
    'alt': ['Bar chart comparing audit scores by quarter',
            'Map of stations audited this year',
            'Team reviewing a document together',
            'Cover of the printed handbook',
            'Flow diagram of the review process',
            'Photo of the reading room'],
    'nav': ['Findings', 'Method', 'Data', 'Contact', 'About', 'Archive'],
    'btn': ['Download the full report', 'Start the survey', 'Show details',
            'Print this page', 'Export as CSV'],
    'field': [('Report title', 'report'), ('Your reference', 'reference'),
              ('Notes', 'notes'), ('Keywords', 'keywords'),
              ('Project code', 'project')],
    'li': ['Plain language summaries for every finding',
           'Keyboard-only walkthrough of the checkout flow',
           'Contrast measurements with the exact ratios',
           'Captions reviewed against the audio track',
           'Focus order verified on every dialog',
           'Forms submitted empty to judge the error messages'],
    'iframe': ['Monthly satisfaction chart', 'Station occupancy map',
               'Feedback form summary', 'Reading room calendar'],
    'para': ['This report summarizes the quarterly review and lists the '
             'corrective actions already shipped by each team.',
             'Every number in this page was measured twice and cross-checked '
             'against the raw data set before publication.',
             'The review followed the published methodology and was verified '
             'by a second reader before the editor approved it.'],
}

# el input de email es el objetivo del operador autocomplete_removed: su name
# ("email") es dato personal a ojos del motor y su autocomplete lo mantiene
# limpio mientras no se lo quiten
_EMAIL_FIELD = ('<label for="field-b">Work email</label>\n'
                '<input id="field-b" name="email" type="email" autocomplete="email">')


def base_page(rng):
    """Página limpia (cero hallazgos) con ranuras donde operan los mutantes."""
    n_imgs = rng.randint(3, 5)
    n_btns = rng.randint(2, 4)
    n_links = rng.randint(3, 5)
    n_lis = rng.randint(3, 5)
    f1, n1 = rng.choice(_WORDS['field'])
    f2, n2 = rng.choice(_WORDS['field'])
    nav = '\n'.join(f'<li><a href="/{w.lower()}">{w}</a></li>'
                    for w in rng.sample(_WORDS['nav'], n_links))
    imgs = '\n'.join(f'<img src="figure-{i}.png" alt="{rng.choice(_WORDS["alt"])}">'
                     for i in range(1, n_imgs + 1))
    btns = '\n'.join(f'<button type="button" id="act-{i}">{rng.choice(_WORDS["btn"])}'
                     f'</button>' for i in range(1, n_btns + 1))
    lis = '\n'.join(f'<li>{rng.choice(_WORDS["li"])}</li>' for _ in range(n_lis))
    h2s = rng.sample(_WORDS['h2'], 3)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{rng.choice(_WORDS['title'])}</title>
</head>
<body>
<a href="#main" class="skip">Skip to content</a>
<header>
<nav aria-label="Primary">
<ul>
{nav}
</ul>
</nav>
</header>
<main id="main">
<h1>{rng.choice(_WORDS['h1'])}</h1>
<p>{rng.choice(_WORDS['para'])}</p>
<h2>{h2s[0]}</h2>
{imgs}
<h2>{h2s[1]}</h2>
<p>{rng.choice(_WORDS['para'])}</p>
<ul>
{lis}
</ul>
<h2>{h2s[2]}</h2>
{btns}
<label for="field-a">{f1}</label>
<input id="field-a" name="{n1}" type="text">
{_EMAIL_FIELD}
<label for="field-c">{f2}</label>
<input id="field-c" name="{n2}" type="text">
<iframe src="panel-1.html" title="{rng.choice(_WORDS['iframe'])}"></iframe>
</main>
</body>
</html>'''


# ── utilidades de cirugía ──────────────────────────────────────────────────
def _pick(pattern, html, rng):
    """El k-ésimo match (k al azar): el mismo operador cae en objetivo distinto."""
    ms = list(re.finditer(pattern, html))
    if not ms:
        return None
    return ms[rng.randrange(len(ms))]


def _splice(html, m, new):
    return html[:m.start()] + new + html[m.end():]


def _src(tag_str):
    s = re.search(r'src="([^"]*)"', tag_str)
    return s.group(1) if s else '?'


# ── operadores: cada uno inyecta UNA violación con respuesta sellada ───────
# Señal y criterio salen del mapa del propio motor (test de integridad).
OPERATORS = []


def _op(name, signal, criterion, apply):
    OPERATORS.append({'op': name, 'signal': signal, 'criterion': criterion,
                      'apply': apply})


def _img_alt_removed(html, rng):
    m = _pick(r'<img\b[^>]*>', html, rng)
    return _splice(html, m, re.sub(r'\s+alt="[^"]*"', '', m.group(0), count=1)), \
        f'alt removed from <img src="{_src(m.group(0))}">'


def _button_name_removed(html, rng):
    m = _pick(r'<button type="button"[^>]*>[^<]*</button>', html, rng)
    return _splice(html, m, re.sub(r'>[^<]*</button>', '></button>',
                                    m.group(0), count=1)), 'text removed from a button'


def _field_label_removed(html, rng):
    m = _pick(r'<label for="field-[ac]">[^<]*</label>\s*', html, rng)
    target = m.group(0).split('"')[1]   # field-a / field-c
    return html[:m.start()] + html[m.end():], f'label removed from input {target}'


def _lang_missing(html, rng):
    return html.replace('<html lang="en">', '<html>', 1), 'lang attribute removed'


def _lang_invalid(html, rng):
    return html.replace('<html lang="en">', '<html lang="xyz">', 1), 'lang="xyz"'


def _title_emptied(html, rng):
    m = re.search(r'<title>[^<]*</title>', html)
    return _splice(html, m, '<title></title>'), 'title emptied'


def _zoom_locked(html, rng):
    return html.replace('<meta charset="utf-8">',
                        '<meta charset="utf-8">\n'
                        '<meta name="viewport" content="width=device-width, '
                        'user-scalable=no">', 1), 'viewport user-scalable=no'


def _refresh_injected(html, rng):
    secs = rng.randint(2, 30)
    return html.replace('<meta charset="utf-8">',
                        f'<meta charset="utf-8">\n'
                        f'<meta http-equiv="refresh" content="{secs}">', 1), \
        f'meta refresh {secs}s'


def _tabindex_positive(html, rng):
    m = _pick(r'<a href="/[^"]*">', html, rng)
    return _splice(html, m, m.group(0)[:-1] + f' tabindex="{rng.randint(2, 9)}">'), \
        'positive tabindex on a nav link'


def _iframe_title_removed(html, rng):
    m = _pick(r'<iframe\b[^>]*>', html, rng)
    return _splice(html, m, re.sub(r'\s+title="[^"]*"', '', m.group(0), count=1)), \
        f'title removed from <iframe src="{_src(m.group(0))}">'


def _video_no_track(html, rng):
    k = rng.randint(1, 9)
    return html.replace('</main>',
                        f'<video controls width="480" height="270" '
                        f'src="clip-{k}.mp4"></video>\n</main>', 1), \
        f'<video src="clip-{k}.mp4"> without captions track'


def _div_onclick(html, rng):
    return html.replace('</main>',
                        '<div onclick="togglePanel()">Show the interactive '
                        'panel</div>\n</main>', 1), 'onclick on a non-focusable div'


def _blank_unwarned(html, rng):
    k = rng.randint(1, 9)
    return html.replace('</main>',
                        f'<p>See the <a href="https://example.org/data/{k}" '
                        f'target="_blank">open data set</a> behind these '
                        f'numbers.</p>\n</main>', 1), \
        f'target=_blank link without new-window warning'


def _autocomplete_removed(html, rng):
    return html.replace(' autocomplete="email"', '', 1), \
        'autocomplete="email" removed from the email input'


def _heading_skip(html, rng):
    m = _pick(r'<h2>[^<]*</h2>', html, rng)
    return _splice(html, m, m.group(0).replace('<h2>', '<h4>', 1)
                   .replace('</h2>', '</h4>', 1)), \
        f'{m.group(0)[:44]}… demoted to h4'


def _id_duplicated(html, rng):
    # el 2º botón roba el id del 1º (n_btns ≥ 2 garantizado en base_page)
    return html.replace('id="act-2"', 'id="act-1"', 1), \
        'button id act-2 duplicated as act-1'


def _aria_ref_broken(html, rng):
    m = _pick(r'<button type="button" id="act-\d+">', html, rng)
    return _splice(html, m, m.group(0)[:-1] + ' aria-labelledby="missing-ref">'), \
        'aria-labelledby points to a non-existent id'


def _list_item_div(html, rng):
    # solo los <li> de TEXTO (los del nav llevan <a>): div como hijo directo
    # de <ul> rompe la estructura de lista
    m = _pick(r'<li>(?=[A-Z])[^<]*</li>', html, rng)
    return _splice(html, m, m.group(0).replace('<li>', '<div>', 1)
                   .replace('</li>', '</div>', 1)), \
        f'{m.group(0)[:44]}… became a div inside the ul'


_op('img_alt_removed', 'img_no_alt', '1.1.1', _img_alt_removed)
_op('button_name_removed', 'ctrl_name', '4.1.2', _button_name_removed)
_op('field_label_removed', 'field_label', '3.3.2', _field_label_removed)
_op('lang_missing', 'lang_missing', '3.1.1', _lang_missing)
_op('lang_invalid', 'lang_invalid', '3.1.1', _lang_invalid)
_op('title_emptied', 'title_missing', '2.4.2', _title_emptied)
_op('zoom_locked', 'zoom_no', '1.4.4', _zoom_locked)
_op('refresh_injected', 'meta_refresh', '2.2.1', _refresh_injected)
_op('tabindex_positive', 'tabindex_pos', '2.4.3', _tabindex_positive)
_op('iframe_title_removed', 'iframe_title', '4.1.2', _iframe_title_removed)
_op('video_no_track', 'video_captions', '1.2.2', _video_no_track)
_op('div_onclick', 'click_nonfocusable', '2.1.1', _div_onclick)
_op('blank_unwarned', 'blank_no_warning', '3.2.5', _blank_unwarned)
_op('autocomplete_removed', 'autocomplete', '1.3.5', _autocomplete_removed)
_op('heading_skip', 'heading_skips', '1.3.1', _heading_skip)
_op('id_duplicated', 'dup_ids', '4.1.2', _id_duplicated)
_op('aria_ref_broken', 'aria_ref_missing', '4.1.2', _aria_ref_broken)
_op('list_item_div', 'list_structure', '1.3.1', _list_item_div)


# ── examen ─────────────────────────────────────────────────────────────────
_NOTE_EXAM = {
    'es': ('Un hallazgo sobre una página placebo es un falso positivo por '
           'construcción. El sobre sellado (operador/señal/criterio) se '
           'abre solo después de puntuar.'),
    'en': ('Findings on placebo control pages are false positives by '
           'construction. Sealed answers (operator/signal/criterion) open '
           'only after scoring.'),
}
def generate(seed=7, n=12):
    """Examen determinista: n mutantes (operadores al azar sobre páginas
    distintas por semilla) + placebos de control."""
    rng = random.Random(seed)
    ops = list(OPERATORS)
    if n <= len(ops):
        chosen = rng.sample(ops, max(n, 0))
    else:
        chosen = []
        while len(chosen) < n:
            shuffled = ops[:]
            rng.shuffle(shuffled)
            chosen += shuffled
        chosen = chosen[:n]
    # semillas hijas por ENTEROS (no str): estables entre procesos y versiones
    mutants = []
    for i, op in enumerate(chosen):
        prng = random.Random(seed * 1000003 + 7 * i + 13)
        html = base_page(prng)
        html2, detail = op['apply'](html, prng)
        mutants.append({'id': f'm{seed}-{i}', 'html': html2,
                        'sealed': {'operator': op['op'], 'signal': op['signal'],
                                   'criterion': op['criterion'], 'detail': detail}})
    # placebos de control: páginas limpias del mismo generador
    controls = []
    for j in range(max(1, n // 6)):
        prng = random.Random(seed * 999331 + 101 * j + 7)
        controls.append({'id': f'p{seed}-{j}', 'html': base_page(prng),
                         'sealed': {'operator': 'placebo', 'signal': None,
                                    'criterion': None,
                                    'detail': 'no violation injected'}})
    return {'seed': seed, 'n': n, 'mutants': mutants, 'control_pages': controls}


def run_exam(seed=7, n=12, engine=None, lang='en'):
    """Corre el examen contra un evaluador (por defecto, el propio motor) y
    abre el sobre SOLO después de puntuar: kill rate + falsos positivos.
    El evaluador externo puede firmar (html) o (html, lang=): el examen se
    adapta a su firma — medir a otros es el punto del módulo."""
    import inspect
    eng = engine or audit_html
    _takes_lang = 'lang' in inspect.signature(eng).parameters

    def _call(h):
        return eng(h, lang='en') if _takes_lang else eng(h)
    exam = generate(seed, n)
    killed, missed, fps, per_op = [], [], [], {}
    for m in exam['mutants']:
        rep = _call(m['html'])
        sigs = ({normalize_signal(h.get('signal', ''))
                 for h in rep.get('findings', [])}
                if isinstance(rep, dict) else set())
        op = m['sealed']['operator']
        per_op.setdefault(op, {'total': 0, 'killed': 0})
        per_op[op]['total'] += 1
        if m['sealed']['signal'] in sigs:
            killed.append(m['id'])
            per_op[op]['killed'] += 1
        else:
            missed.append({'id': m['id'], **m['sealed'], 'found_instead': sorted(sigs)})
    for p in exam['control_pages']:
        rep = _call(p['html'])
        for h in (rep.get('findings', []) if isinstance(rep, dict) else []):
            fps.append({'control_page': p['id'],
                        'signal': normalize_signal(h.get('signal', ''))})
    total = len(exam['mutants'])
    return {
        'mode': 'mutant-exam', 'seed': seed, 'mutants': total,
        'control_pages': len(exam['control_pages']),
        'killed': len(killed), 'missed': len(missed),
        'missed_detail': missed,
        'kill_rate': round(len(killed) / total, 4) if total else None,
        'false_positives': fps,
        'per_operator': per_op,
        'note': _NOTE_EXAM['es' if lang == 'es' else 'en'],
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seed', type=int, default=7, help='exam id (same seed, same exam)')
    ap.add_argument('--n', type=int, default=12, help='number of mutants')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--out', help='directory: writes each page + answers.json '
                                  '(sealed log) for external examiners')
    a = ap.parse_args(argv)
    report = run_exam(a.seed, a.n, lang=a.lang)
    if a.out:
        exam = generate(a.seed, a.n)
        os.makedirs(a.out, exist_ok=True)
        for item in exam['mutants'] + exam['control_pages']:
            with open(os.path.join(a.out, item['id'] + '.html'), 'w',
                      encoding='utf-8') as f:
                f.write(item['html'])
        with open(os.path.join(a.out, 'answers.json'), 'w', encoding='utf-8') as f:
            json.dump({'seed': a.seed,
                       'sealed': [dict(i['sealed'], id=i['id'])
                                  for i in exam['mutants']]}, f, indent=1)
        report['out'] = a.out
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
