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

    print('== 1b. autocontenido END-TO-END (empaqueta y ejecuta como el workflow)')
    import shutil, subprocess
    shutil.copytree(os.path.join(ROOT, 'a11y_toolkit'), os.path.join(ROOT, 'npm', 'a11y_toolkit'),
                    ignore=shutil.ignore_patterns('__pycache__'), dirs_exist_ok=True)
    try:
        r = subprocess.run(['node', os.path.join(ROOT, 'npm', 'bin', 'a11y-toolkit.cjs'),
                            'pair', '#767676', '#ffffff'],
                           capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0 and '"ratio"' in r.stdout
        check('bin Node → motor interno (pair real, sin uv ni red)', ok,
              (r.stderr or r.stdout)[:150])
    finally:
        shutil.rmtree(os.path.join(ROOT, 'npm', 'a11y_toolkit'), ignore_errors=True)

    print('== 2. bins')
    cli = open(os.path.join(ROOT, 'npm', 'bin', 'a11y-toolkit.cjs')).read()
    mcp = open(os.path.join(ROOT, 'npm', 'bin', 'a11y-toolkit-mcp.cjs')).read()
    runner = open(os.path.join(ROOT, 'npm', 'lib', 'runner.cjs')).read()
    check('CLI ejecuta el módulo del motor', "run('a11y_toolkit.a11y')" in cli)
    check('MCP ejecuta el módulo del servidor', "run('a11y_toolkit.server')" in mcp)
    check('runner ejecuta el motor INTERNO (python3 -m, sin red)',
          "'-m'" in runner and 'a11y_toolkit' in runner and 'PYTHONPATH' in runner)
    check('fallback uvx pineado (origen package.json)',
          'a11y-toolkit==${VERSION}' in runner and "require('../package.json').version" in runner)
    check('sin python3 ni uv: mensaje con la línea de instalación',
          'astral.sh/uv' in runner and 'ENOENT' in runner)
    check('runner explica cómo instalar uv (sin ENOENT críptico)',
          'astral.sh/uv' in runner and 'ENOENT' in runner)
    check('passthrough de argumentos', 'process.argv.slice(2)' in runner)

    print(f"\n{'ALL OK' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
