#!/usr/bin/env python3
"""a11y gate — the write-time guard, pure logic.

Contract: only NEW (or grown) high/medium findings refuse the write; known
findings and low severity warn; non-user-facing paths never judge; the
hook protocol fails OPEN; the refusal carries criterion + how-to-fix."""

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

fails = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(fails)}/{len(results)} checks")
sys.exit(1 if fails else 0)
