#!/usr/bin/env python3
"""Arranque AISLADO del motor interno del paquete npm (@kinti/a11y-toolkit).

El lanzador ejecuta `python -I _bootstrap.py <entrada> <args…>`: -I (modo
aislado) saca el directorio de trabajo de sys.path — un módulo homónimo del
proyecto auditado (que VS Code invoca desde la raíz del workspace) jamás
gana a la hora de importarse — e ignora PYTHONPATH. El motor se carga aquí
por RUTA ABSOLUTA del paquete que viaja dentro de este npm.

Entradas: a11y_toolkit.a11y (CLI) y a11y_toolkit.server (servidor MCP).
"""
import os
import sys

_ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ENGINE)

_ENTRY = {
    'a11y_toolkit.a11y': 'main',
    'a11y_toolkit.server': 'main',
}


def _run(entry, args):
    if entry not in _ENTRY:
        print(f'unknown entry: {entry}', file=sys.stderr)
        return 2
    module = __import__(entry, fromlist=[_ENTRY[entry]])
    return getattr(module, _ENTRY[entry])(args)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: _bootstrap.py <entry> [args…]', file=sys.stderr)
        sys.exit(2)
    sys.exit(_run(sys.argv[1], sys.argv[2:]))
