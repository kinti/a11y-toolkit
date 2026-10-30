#!/usr/bin/env python3
"""Invariantes del lanzador npm (@kinti/a11y-toolkit) — el envoltorio Node
del motor Python. Pina versión (anti-deriva con server.json) y forma."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + (f' — {detail}' if detail and not cond else ''))
    if not cond:
        FAILS.append(name)


def main():
    print('== 1. package.json')
    pkg = json.load(open(os.path.join(ROOT, 'npm', 'package.json')))
    check('nombre scoped @kinti', pkg['name'] == '@kinti/a11y-toolkit')
    server = json.load(open(os.path.join(ROOT, 'server.json')))
    check('versión = server.json (anti-deriva)', pkg['version'] == server['version'],
          f"{pkg['version']} vs {server['version']}")
    check('bins declarados', set(pkg['bin']) == {'a11y-toolkit', 'a11y-toolkit-mcp'})
    check('files cubre bin y lib', {'bin/', 'lib/'} <= set(pkg['files']))

    print('== 2. bins')
    cli = open(os.path.join(ROOT, 'npm', 'bin', 'a11y-toolkit.cjs')).read()
    mcp = open(os.path.join(ROOT, 'npm', 'bin', 'a11y-toolkit-mcp.cjs')).read()
    runner = open(os.path.join(ROOT, 'npm', 'lib', 'runner.cjs')).read()
    check('CLI llama a a11ytoolkit', "run('a11ytoolkit')" in cli)
    check('MCP llama a a11y-toolkit-mcp', "run('a11y-toolkit-mcp')" in mcp)
    check('runner usa uvx --from a11y-toolkit', "'--from'" in runner and "'a11y-toolkit'" in runner)
    check('runner explica cómo instalar uv (sin ENOENT críptico)',
          'astral.sh/uv' in runner and 'ENOENT' in runner)
    check('passthrough de argumentos', 'process.argv.slice(2)' in runner)

    print(f"\n{'ALL OK' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
