#!/usr/bin/env python3
"""Ciclo de vida del pool de navegador — el P1 de la revisión externa 2026-11-22.

El «Event loop is closed»: sr_transcript paraba SU driver Playwright en el
finally dejando el browser en el pool; la llamada siguiente heredaba un objeto
huérfano (is_connected() rancio) y moría. Desde el arreglo, el POOL posee el
driver — browser y playwright mueren juntos — y las auditorías solo cierran su
página/contexto. Este test hace lo que hacía el revisor: varias llamadas en un
ÚNICO proceso, la primera con auth_state.

Se auto-omite si Playwright no está instalado (mismo criterio que test_dom).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_pool_lifecycle: Playwright no instalado')
    sys.exit(0)

FIXTURE = '''<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Pool</title></head><body><main><h1>Pool</h1>
<p style="color:#999;background:#fff">contraste flojo</p>
<button>ok</button></main></body></html>'''
_path = os.path.join('/tmp', 'a11y_pool_fixture.html')
with open(_path, 'w', encoding='utf-8') as f:
    f.write(FIXTURE)
URL = 'file://' + _path

# storage_state válido (vacío): new_context lo acepta — el punto es ejercer
# la ruta CON contexto que dejaba el browser huérfano
_state = os.path.join('/tmp', 'a11y_pool_state.json')
with open(_state, 'w', encoding='utf-8') as f:
    f.write(json.dumps({'cookies': [], 'origins': []}))

from a11y_toolkit import a11ydom  # noqa: E402

# 1) sr_transcript CON auth_state: en el código viejo, su finally paraba el
# driver y dejaba el browser del pool huérfano
r1 = a11ydom.sr_transcript(URL, auth_state=_state)
assert not any('Event loop' in str(v) for v in (r1.get('error'), r1)), r1

# 2) la llamada siguiente (la que el revisor veía morir): MISMO proceso
try:
    r2 = a11ydom.audit_dom_url(URL, auth_state=_state)
except Exception as e:  # noqa: BLE001
    raise AssertionError(f'segunda llamada murió: {e}') from e
assert 'error' not in r2, r2.get('error')
assert r2['mode'] == 'rendered'

# 3) tercera sin auth_state: reutiliza el MISMO browser del pool (caliente)
r3 = a11ydom.audit_dom_url(URL)
assert 'error' not in r3, r3.get('error')
assert r3 is not r2

# 4) reflow con auth_state (P2 de la misma revisión: el parámetro existía y
# se ignoraba) — con sesión debe cargar, no devolver el error de la cookie
r4 = a11ydom.audit_reflow(URL, auth_state=_state)
assert 'error' not in r4, r4.get('error')
assert r4['mode'] == 'reflow'

# 5) el pool sigue vivo y COHERENTE: mismo browser, driver y browser juntos
assert a11ydom._POOL['browser'] is not None and a11ydom._POOL['playwright'] is not None
assert a11ydom._POOL['browser'].is_connected()
a11ydom._close_pool()
assert a11ydom._POOL['browser'] is None and a11ydom._POOL['playwright'] is None

# 6) tras cerrar, el pool renace limpio (una llamada más)
r5 = a11ydom.audit_dom_url(URL)
assert 'error' not in r5, r5.get('error')
a11ydom._close_pool()

print('POOL LIFECYCLE OK ✓ (sr-transcript+auth → dom+auth → dom → reflow+auth → recliclado)')
