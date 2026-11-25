#!/usr/bin/env python3
"""a11y gate — the write-time guard, pure logic.

Contract: only NEW (or grown) high/medium findings refuse the write; known
findings and low severity warn; non-user-facing paths never judge; an
unreadable hook payload fails OPEN, a save the engine cannot audit fails
CLOSED; the refusal carries criterion + how-to-fix."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit.a11ygate import (verdict, payload_to_write,  # noqa: E402
                                   is_user_facing, guard_hook)

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(('ok  ' if cond else 'FAIL') + ' ' + name)


CLEAN = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
         '<title>Ok</title></head><body><main><h1>Ok</h1>'
         '<img src="a.png" alt="Chart of monthly sales">'
         '<button>Send</button></main></body></html>')
BROKEN = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
          '<title>Ok</title></head><body><main><h1>Ok</h1>'
          '<img src="a.png">'
          '<button></button></main></body></html>')
BROKEN2 = BROKEN.replace('<img src="a.png">', '<img src="a.png"><img src="b.png">')

# ── the core semantics ──────────────────────────────────────────────────────
v = verdict('', CLEAN, 'page.html')
check('clean NEW file → allow', v['decision'] == 'allow'
      and not v['blocked'])

v = verdict('', BROKEN, 'page.html')
check('new file with failures → block', v['decision'] == 'block')
check('blocked carries criterion + how-to-fix',
      all('criterion' in b and b.get('remediation') for b in v['blocked']))

v = verdict(BROKEN, BROKEN, 'page.html')
check('identical save → allow (known warns)', v['decision'] == 'allow'
      and any('known finding kind(s)' in w for w in v['warnings']))

v = verdict(BROKEN, BROKEN2, 'page.html')
check('same kinds (engine aggregates by kind) → allow + known warning',
      v['decision'] == 'allow'
      and any('known finding kind(s)' in w for w in v['warnings']))

v = verdict(CLEAN, BROKEN, 'page.html')
check('regression vs HEAD → block', v['decision'] == 'block'
      and v['before'] == 0 and v['after'] > 0)

# ── severity discipline ─────────────────────────────────────────────────────
LOW_ONLY = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>Ok</title></head><body><main><h1>Ok</h1>'
            '<p>Serving the needs of the many users everywhere today</p>'
            '</main></body></html>')
LINKED = CLEAN.replace('</main>',
    '<a href="/x">more</a><a href="/y">more</a></main>')
v = verdict(CLEAN, LINKED, 'page.html')
check('new low kind (same_name_links) → allow with warning',
      v['decision'] == 'allow'
      and any('low-severity' in w for w in v['warnings']))

# ── the path filter ─────────────────────────────────────────────────────────
check('html is user-facing', is_user_facing('src/pages/index.html'))
check('jsx is user-facing', is_user_facing('src/App.tsx'))
check('config file is NOT', not is_user_facing('config/settings.json'))
check('readme is NOT', not is_user_facing('docs/README.md'))

# ── payload mapping (Claude Code protocol) ──────────────────────────────────
path, content = payload_to_write({'tool_name': 'Write',
                                  'tool_input': {'file_path': 'a.html',
                                                 'content': '<x>'}})
check('Write payload → path+content', path == 'a.html' and content == '<x>')
path, content = payload_to_write({'tool_name': 'Edit',
                                  'tool_input': {'file_path': 'a.html'}})
check('Edit without disk file → content None', content is None)
check('unknown tool → None', payload_to_write(
    {'tool_name': 'Bash', 'tool_input': {'command': 'ls'}})[1] is None)

# ── the hook protocol fails OPEN ────────────────────────────────────────────
code, err = guard_hook('not json at all')
check('unparseable payload → fail-open (exit 0)', code == 0
      and 'fail-open' in err)
code, err = guard_hook(json.dumps({'tool_name': 'Write',
                                   'tool_input': {'file_path': 'x.py',
                                                  'content': 'garbage'}}))
check('non-user-facing suffix → allow silently', code == 0)

# ── canonical package import path agrees ──────────────────────────────
from a11y_toolkit import a11ygate  # noqa: E402
check('import paths agree', a11ygate.is_user_facing is is_user_facing)

# revisión externa 2026-11-22: un settings.json ILEGIBLE se machacaba partiendo
# de {} (permisos de Claude incluidos). Ahora: error y el original intacto.
import tempfile as _tf, os as _os, json as _json
from a11y_toolkit import a11yinit as _ini
_d = _tf.mkdtemp()
_os.makedirs(_os.path.join(_d, '.claude'))
_sp = _os.path.join(_d, '.claude', 'settings.json')
open(_sp, 'w').write('{"permissions": {"allow": ["Bash"]}, ROT')
_r = _ini.install_gate(_d)
results.append(('init: config ilegible → error y original intacto',
                bool(_r.get('error')) and 'ROT' in open(_sp).read()))
open(_sp, 'w').write('{}')
_r2 = _ini.install_gate(_d)
_cfg = _json.load(open(_sp))
results.append(('init: config válida → gate instalado atómicamente',
                _r2.get('gate') == 'installed'
                and any('a11ytoolkit' in h.get('command', '')
                        for e in _cfg['hooks']['PreToolUse'] for h in e['hooks'])
                and not _os.path.exists(_sp + '.a11y-tmp')))

# the command init installs is a command the CLI dispatches.
# 2026-11-25: settings.json ran `a11ytoolkit guard-hook`, the dispatcher only
# knew `guard`, so every save (clean or not) got «Unknown subcommand» + exit 2
# and the client refused it. Whole chain: installed command, dispatcher, stdin
# JSON, inside a real Git repository (the gate compares the save with HEAD).
import contextlib as _ctx, io as _io, shlex as _shlex  # noqa: E402
import subprocess as _sp, sys as _sys  # noqa: E402
from a11y_toolkit import a11y as _cli  # noqa: E402

_d2 = _tf.mkdtemp()
_page2 = _os.path.join(_d2, 'page.html')
with open(_page2, 'w', encoding='utf-8') as _f:
    _f.write(CLEAN)


def _git2(*args):
    return _sp.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com',
                    '-c', 'commit.gpgsign=false', *args], cwd=_d2, capture_output=True)


_git2('init', '-q')
_git2('add', 'page.html')
_git2('commit', '-qm', 'base')


def _installed_hook(new_html):
    """Run the command exactly as `init` writes it, with a Write payload."""
    payload = _json.dumps({'tool_name': 'Write', 'tool_input': {
        'file_path': _page2, 'content': new_html}})
    out, err = _io.StringIO(), _io.StringIO()
    old_stdin, old_cwd = _sys.stdin, _os.getcwd()
    try:
        _os.chdir(_d2)                    # old_version() reads HEAD from the cwd
        _sys.stdin = _io.StringIO(payload)
        with _ctx.redirect_stderr(err), _ctx.redirect_stdout(out):
            code = _cli.main(_shlex.split(_ini.GATE_CMD)[1:])
    finally:
        _sys.stdin = old_stdin
        _os.chdir(old_cwd)
    return code, out.getvalue() + err.getvalue()


def _hook_check(name, result, want_code, needle):
    good = result[0] == want_code and needle in result[1] \
        and 'Unknown subcommand' not in result[1]
    if not good:
        print('     the hook answered:', repr(result[1][-200:]))
    check(name, good)


clean = _installed_hook(CLEAN.replace('<h1>Ok</h1>', '<h1>Ok</h1><p>More</p>'))
_hook_check('installed command (`%s`): a clean save runs, exit 0' % _ini.GATE_CMD,
            clean, 0, '')
broken = _installed_hook(BROKEN)
_hook_check('installed command: a save with a NEW finding is refused, exit 2',
            broken, 2, 'save refused')
_os.environ['A11Y_GATE'] = 'off'
try:
    off = _installed_hook(BROKEN)
finally:
    _os.environ.pop('A11Y_GATE', None)
_hook_check('A11Y_GATE=off: the installed command lets the save through', off, 0, '')
check('A11Y_GATE=off answers nothing', not off[1])

fails = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(fails)}/{len(results)} checks")
sys.exit(1 if fails else 0)
