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
RAPIDAS = ['tests/test_contrast.py', 'tests/test_audit.py', 'tests/test_v32.py', 'tests/test_solido.py']


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
    d['packages'][0]['version'] = nueva
    json.dump(d, open(sj, 'w'), indent=2, ensure_ascii=False)
    open(sj, 'a').write('\n')
    print('  ✓ server.json: versión y paquete')
    # test_mcp derives its version assertion from server.VERSION: nothing to bump there.

    print('— suites rápidas:')
    for t in RAPIDAS:
        r = subprocess.run([sys.executable, os.path.join(AQUI, t)],
                           capture_output=True, timeout=300)
        estado = '✓' if r.returncode == 0 else '✗'
        print(f'  {estado} {t}')
        if r.returncode != 0:
            print('SUITE ROJA — no se versiona nada más. Arregla y reintenta.')
            return 2

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
