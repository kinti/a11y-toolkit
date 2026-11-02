#!/usr/bin/env python3
"""The guided wizard — the Canadian pattern, inverted, in the terminal.

2-3 questions a person CAN answer (what are you building, which standard
applies to your market, the 508 product questions when that standard is
chosen) configure everything the engine already knows how to do: the
audit runs with the right standard, the scope artifact carries the
machine proposals, and — when the market or contract demands it — the
tender annex is generated in the chosen language.

Everything the wizard does is also available as individual commands
(audit --standard …, scope --solicitation …): the wizard composes, it
does not hide. Interactive by design; a piped stdin works too (tests,
CI) and an exhausted stdin aborts gracefully with the non-interactive
commands as the message.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yaudit import audit_html, audit_url  # noqa: E402
from a11y_toolkit.a11yscope import build_scope, solicitation  # noqa: E402


def _t(key):
    from .a11yi18n import pack
    return pack(_LANG).get('wiz', {}).get(key) or key


def _ask(prompt, valid=None, default=None):
    """input() con validación: reintenta hasta respuesta válida; en EOF
    aborta con la salida no-interactiva como mensaje (el wizard compone
    comandos que existen)."""
    while True:
        try:
            ans = input(prompt).strip()
        except EOFError:
            print(_t('wiz_abort'))
            sys.exit(1)
        if not ans and default is not None:
            return default
        if valid is None:
            return ans
        if ans in valid:
            return ans
        print('  ' + '/'.join(valid) + '?')


_YESNO = ('y', 'Y', 's', 'S', 'si', 'sí', 'SI', 'yes', 'YES', 'Yes',
             'n', 'N', 'no', 'NO', 'No')
_YES = ('y', 'Y', 's', 'S', 'si', 'sí', 'SI', 'yes', 'YES', 'Yes')
_NO = ('n', 'N', 'no', 'NO', 'No')

_LANG = 'en'


def main(argv):
    global _LANG
    ap = argparse.ArgumentParser(
        description='Guided wizard: 2-3 questions → standard, audit, scope '
                    'and tender annex. Also non-interactive commands exist.')
    ap.add_argument('--url', help='page to audit (skipped from the questions if given)')
    ap.add_argument('--file', help='local html to audit')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('-o', '--out', default='scope.json',
                    help='where the scope artifact is written (default scope.json)')
    a = ap.parse_args(argv)
    _LANG = a.lang

    # Q0: qué auditar (flag o pregunta)
    url = (a.url or '').strip()
    if not url and not a.file:
        url = _ask(_t('wiz_need_url') + ' URL: ', valid=None)

    # Q1: qué estás construyendo
    tgt = _ask(_t('wiz_q_target'), valid={'1', '2', '3', '4'})
    if tgt == '4':
        raw = _ask(_t('wiz_q_multi'))
        targets = [x.strip() for x in raw.split(',') if x.strip() in ('web', 'documents', 'software')] \
            or ['web']
        target = targets[0]
    else:
        target = {'1': 'web', '2': 'documents', '3': 'software'}[tgt]
        targets = [target]

    # Q2: qué norma
    std_map = {'1': 'wcag22', '2': 'en301549', '3': '508', '4': 'rgaa'}
    std = std_map[_ask(_t('wiz_q_std'), valid={'1', '2', '3', '4'})]

    # Q3: preguntas de producto (solo 508: el árbol GSA ya modelado)
    answers = {}
    if std == '508':
        answers['508:public_facing'] = {
            'answer': 'yes' if _ask(_t('wiz_q_public'), valid=_YESNO) in _YES else 'no'}
        answers['508:official_comm'] = {
            'answer': 'yes' if _ask(_t('wiz_q_official'), valid=_YESNO) in _YES else 'no'}
        if target == 'software':
            answers['508:authoring_tool'] = {
                'answer': 'yes' if _ask(_t('wiz_q_authoring'), valid=_YESNO) in _YES else 'no'}

    # auditoría con el estándar elegido
    std_arg = std if std in ('en301549', 'rgaa') else None
    if url:
        report = audit_url(url, timeout=30, lang=a.lang, standard=std_arg, target=targets[0])
    else:
        report = audit_html(open(a.file, encoding='utf-8', errors='replace').read()[:2_000_000],
                            url=a.file, lang=a.lang, standard=std_arg, target=targets[0])
    if 'error' in report:
        print(json.dumps(report, ensure_ascii=False))
        return 1

    scope = build_scope([report], standard=std, target=target,
                        answers=answers or None, lang=a.lang, targets=targets)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(scope, f, ensure_ascii=False, indent=1)

    # anexo opcional (el artefacto de contrato)
    annex = '—'
    if _ask(_t('wiz_q_annex'), valid=_YESNO, default='n') in _YES:
        annex_lang = _ask(_t('wiz_annex_lang'), valid={'es', 'en'}, default=a.lang)
        text = solicitation(scope, lang=annex_lang)
        # el anexo cae JUNTO al alcance: un solo entregable, un solo sitio
        annex = os.path.join(os.path.dirname(os.path.abspath(a.out)),
                             'anexo_' + ('pligo' if annex_lang == 'es' else 'tender') + '.txt')
        with open(annex, 'w', encoding='utf-8') as f:
            f.write(text + '\n')

    print(_t('wiz_done').format(scope=a.out, annex=annex, score=report.get('score'),
                                ins=scope['counters']['in_scope'],
                                pro=scope['counters']['proposed_excluded']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
