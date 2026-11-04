#!/usr/bin/env python3
"""La ÚNICA forma de versionar el proyecto: una orden, tres ficheros, asserts.

  python3 scripts/versionar.py 3.9.5            # bump atómico + suites rápidas
  python3 scripts/versionar.py 3.9.5 --tag      # además: commit + tag + push

Sustituye los bumps manuales de pyproject/server/server.json que derivaron
durante 10 releases. Cada sustitución lleva assert en el ancla — la lección
de los parches silenciosos.
"""

import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (histórico) la lista manual RAPIDAS se retiró: el gate descubre TODAS las suites


def bump_fichero(ruta, ancla, nuevo_valor, etiqueta):
    ruta_full = os.path.join(AQUI, ruta)
    s = open(ruta_full, encoding='utf-8').read()
    assert ancla in s, f'ANCLA NO ENCONTRADA en {ruta}: {ancla!r} — nada se tocó'
    s = s.replace(ancla, nuevo_valor, 1)
    open(ruta_full, 'w', encoding='utf-8').write(s)
    print(f'  ✓ {ruta}: {etiqueta}')


def main():
    if len(sys.argv) < 2 or not re.fullmatch(r'\d+\.\d+\.\d+', sys.argv[1] or ''):
        print(__doc__)
        return 1
    nueva = sys.argv[1]
    con_tag = '--tag' in sys.argv

    actual = None
    for lin in open(os.path.join(AQUI, 'pyproject.toml'), encoding='utf-8'):
        m = re.match(r'version = "([\d.]+)"', lin.strip())
        if m:
            actual = m.group(1)
            break
    assert actual, 'no encontré la versión actual en pyproject'
    if nueva == actual:
        print(f'la versión ya es {nueva}: nada que hacer')
        return 0

    print(f'versionando {actual} → {nueva}')
    bump_fichero('pyproject.toml', f'version = "{actual}"', f'version = "{nueva}"', 'versión')
    bump_fichero('a11y_toolkit/server.py', f"VERSION = '{actual}'", f"VERSION = '{nueva}'", 'VERSION')
    sj = os.path.join(AQUI, 'server.json')
    d = json.load(open(sj))
    assert d['version'] == actual, f'server.json estaba en {d["version"]}, no en {actual} — revisa a mano'
    d['version'] = nueva
    for p in d.get('packages', []):
        p['version'] = nueva
    json.dump(d, open(sj, 'w'), indent=2, ensure_ascii=False)
    open(sj, 'a').write('\n')
    print('  ✓ server.json: versión y TODOS los paquetes')
    npj = os.path.join(AQUI, 'npm', 'package.json')
    if os.path.exists(npj):
        d = json.load(open(npj))
        d['version'] = nueva
        json.dump(d, open(npj, 'w'), indent=2)
        open(npj, 'a').write('\n')
        print('  ✓ npm/package.json: versión (lanzador Node)')
    # plugin.json (estándar Agent Plugins) viaja versionado con el resto
    pj = os.path.join(AQUI, 'plugin.json')
    if os.path.exists(pj):
        d = json.load(open(pj))
        d['version'] = nueva
        json.dump(d, open(pj, 'w'), indent=2, ensure_ascii=False)
        open(pj, 'a').write('\n')
        print('  ✓ plugin.json: versión (Agent Plugins)')
    # vscode/package.json viaja con la versión del motor (era 0.1.0 huérfana)
    pv = os.path.join(AQUI, 'vscode', 'package.json')
    if os.path.exists(pv):
        d = json.load(open(pv, encoding='utf-8'))
        if d.get('version') != nueva:
            d['version'] = nueva
            json.dump(d, open(pv, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
            open(pv, 'a', encoding='utf-8').write('\n')
            print('  ✓ vscode/package.json: versión')
    # test_mcp derives its version assertion from server.VERSION: nothing to bump there.

    print('— gate de release: TODAS las suites por descubrimiento (la lista')
    print('  manual omitía 8 suites — test_locate estuvo roto sin que se viera):')
    import glob as _glob
    _todas = sorted(_glob.glob(os.path.join(AQUI, 'tests', 'test_*.py')))
    for t in _todas:
        try:
            r = subprocess.run([sys.executable, t], capture_output=True,
                               timeout=600, cwd=AQUI)
        except subprocess.TimeoutExpired:
            print(f'  ✗ {os.path.basename(t)} — TIMEOUT (>600s)')
            print('SUITE ROJA — no se versiona nada más. Arregla y reintenta.')
            return 2
        estado = '✓' if r.returncode == 0 else '✗'
        print(f'  {estado} {os.path.basename(t)}')
        if r.returncode != 0:
            # el porqué, no solo el qué: cola del output capturado
            tail = (r.stdout or b'')[-600:].decode('utf-8', 'replace')
            print(f'  ── cola de {os.path.basename(t)}:\n{tail}')
            print('SUITE ROJA — no se versiona nada más. Arregla y reintenta.')
            return 2

    # llms.txt incrusta la versión: regenerar tras el bump o el --check del
    # Makefile enrojece al día siguiente (lección v5.17.0: bump sin regen)
    r = subprocess.run([sys.executable, os.path.join(AQUI, 'scripts', 'gen_llms.py')],
                       capture_output=True, timeout=120)
    assert r.returncode == 0, f'llms.txt no regenerado: {r.stderr[-300:]}'
    print('  ✓ llms.txt regenerado con la nueva versión')

    if con_tag:
        r = subprocess.run(['git', 'add', '-A'], cwd=AQUI)
        assert r.returncode == 0
        r = subprocess.run(['git', 'commit', '-q', '-m', f'v{nueva}: versioned via scripts/versionar.py'],
                           cwd=AQUI)
        assert r.returncode == 0
        r = subprocess.run(['git', 'tag', f'v{nueva}'], cwd=AQUI)
        assert r.returncode == 0
        r = subprocess.run(['git', 'push', '-q', 'origin', 'main', f'v{nueva}'], cwd=AQUI)
        assert r.returncode == 0, 'push falló'
        print(f'✓ v{nueva} commiteada, etiquetada y empujada (PyPI publica el tag; '
              f'registro: mcp-publisher publish)')
    else:
        print(f'✓ {nueva} lista en los 4 ficheros. Commitea, etiqueta v{nueva} y empuja.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
