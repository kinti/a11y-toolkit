#!/usr/bin/env python3
"""Test de humo del servidor MCP: handshake, tools/list y una llamada real."""
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REQ = [
    {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
     'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                'clientInfo': {'name': 'test'}}},
    {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
    {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
     'params': {'name': 'a11y_contrast_pair',
                'arguments': {'fg': '#999999', 'bg': '#ffffff'}}},
    {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call',
     'params': {'name': 'a11y_generate_declaration',
                'arguments': {'entidad': 'T', 'url': 'https://t.example',
                              'estado': 'parcial',
                              'contenido_no_accesible': ['Un vídeo sin subtítulos']}}},
    {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call',
     'params': {'name': 'a11y_aria_live_snippet', 'arguments': {}}},
    {'jsonrpc': '2.0', 'id': 6, 'method': 'tools/call',
     'params': {'name': 'a11y_contrast_image',
                'arguments': {'path': '/no/existe.jpg', 'text_color': '#fff'}}},
]

p = subprocess.run([sys.executable, os.path.join(AQUI, 'server.py')],
                   input='\n'.join(json.dumps(r) for r in REQ),
                   capture_output=True, text=True, timeout=60)
resp = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
por_id = {r.get('id'): r for r in resp}

assert por_id[1]['result']['serverInfo']['name'] == 'a11y-toolkit'
nombres = [t['name'] for t in por_id[2]['result']['tools']]
assert len(nombres) == 5, nombres
d = json.loads(por_id[3]['result']['content'][0]['text'])
assert abs(d['ratio'] - 2.85) < 0.02 and d['veredictos'][0]['cumple'] is False
decl = por_id[4]['result']['content'][0]['text']
assert '1112/2018' in decl and 'Un vídeo sin subtítulos' in decl
snip = por_id[5]['result']['content'][0]['text']
assert 'alm-panel' in snip and "closest('.alm-panel')" in snip
assert por_id[6]['result'].get('isError') is True

print('TESTS MCP PASAN ✓ (handshake, 5 herramientas, errores con isError)')
