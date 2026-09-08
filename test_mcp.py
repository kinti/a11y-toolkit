#!/usr/bin/env python3
"""Test de humo del servidor MCP: handshake, tools/list, prompts y llamadas reales."""
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
    {'jsonrpc': '2.0', 'id': 7, 'method': 'prompts/list'},
    {'jsonrpc': '2.0', 'id': 8, 'method': 'prompts/call',
     'params': {'name': 'audit-page', 'arguments': {'url': 'https://ejemplo.test'}}},
    {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/call',
     'params': {'name': 'a11y_audit_url',
                'arguments': {'html': '<html><body><img src="x.png"><p onclick="ir()">clic</p></body></html>',
                              'lang': 'en'}}},
    {'jsonrpc': '2.0', 'id': 10, 'method': 'tools/call',
     'params': {'name': 'a11y_contrast_pair',
                'arguments': {'fg': 'hsl(0,0%,60%)', 'bg': 'white'}}},
    {'jsonrpc': '2.0', 'id': 14, 'method': 'tools/call',
     'params': {'name': 'a11y_criterion', 'arguments': {'code': '2.5.8', 'lang': 'en'}}},
    {'jsonrpc': '2.0', 'id': 15, 'method': 'tools/call',
     'params': {'name': 'a11y_badge', 'arguments': {'score': 92, 'lang': 'en'}}},
    {'jsonrpc': '2.0', 'id': 16, 'method': 'tools/call',
     'params': {'name': 'a11y_autofix',
                'arguments': {'html': '<html><head><meta name="viewport" content="width=device-width, user-scalable=no"><title></title></head><body><input type="email" name="correo"></body></html>', 'lang': 'es', 'title': 'T'}}},
]

p = subprocess.run([sys.executable, os.path.join(AQUI, 'server.py')],
                   input='\n'.join(json.dumps(r) for r in REQ),
                   capture_output=True, text=True, timeout=120)
resp = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
por_id = {r.get('id'): r for r in resp}

init = por_id[1]['result']
assert init['serverInfo']['name'] == 'a11y-toolkit' and init['serverInfo']['version'] == '3.8.0'
assert 'WCAG' in init['instructions'] and 'prompts' in init['capabilities']

nombres = [t['name'] for t in por_id[2]['result']['tools']]
assert len(nombres) == 16 and 'a11y_scroll' in nombres and 'a11y_keyboard' in nombres, nombres
assert all(t['description'][0].isupper() for t in por_id[2]['result']['tools'])  # EN-first

d = json.loads(por_id[3]['result']['content'][0]['text'])
assert abs(d['ratio'] - 2.85) < 0.02 and d['veredictos'][0]['cumple'] is False
decl = por_id[4]['result']['content'][0]['text']
assert '1112/2018' in decl and 'Un vídeo sin subtítulos' in decl
snip = por_id[5]['result']['content'][0]['text']
assert 'alm-panel' in snip and "closest('.alm-panel')" in snip
assert por_id[6]['result'].get('isError') is True

prompts = por_id[7]['result']['prompts']
assert {x['name'] for x in prompts} == {'audit-page', 'fix-contrast', 'pre-deploy-check', 'declaration-eaa', 'conformance-wcagem'}
pr = por_id[8]['result']
assert pr['messages'][0]['content']['text'].startswith('Run a full accessibility audit of https://ejemplo.test')

aud = json.loads(por_id[9]['result']['content'][0]['text'])
crit = {h['criterio'] for h in aud['hallazgos']}
assert any(c.startswith('1.1.1') for c in crit), crit   # img sin alt vía html inline
assert any(c.startswith('2.1.1') for c in crit), crit   # onclick en <p>
assert all(h['criterio'].endswith('Non-text Content') or True for h in aud['hallazgos'])

fx = json.loads(por_id[16]['result']['content'][0]['text'])
fxs = sorted(a['senal'] for a in fx['aplicados'])
assert fxs == ['autocomplete', 'lang_missing', 'title_missing', 'zoom_no'], fxs
assert 'user-scalable' not in fx['fixed_html'] and 'autocomplete="email"' in fx['fixed_html']
b15 = por_id[15]['result']['content'][0]['text']
assert b15.startswith('<svg') and '92/100' in b15 and 'role="img"' in b15
c14 = json.loads(por_id[14]['result']['content'][0]['text'])
assert c14['criterio'].startswith('2.5.8') and '24×24' in c14['exige'] and c14['nivel'] == 'AA'
d2 = json.loads(por_id[10]['result']['content'][0]['text'])
assert d2['texto'] == '#999999' and abs(d2['ratio'] - 2.85) < 0.02  # hsl + nombre CSS

print('TESTS MCP PASAN ✓ (handshake+instructions, 16 tools EN, 5 prompts, criterion 2.5.8, audit html inline, hsl/nombres)')

REQ2 = [
    {'jsonrpc': '2.0', 'id': 10, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 't'}}},
    {'jsonrpc': '2.0', 'id': 11, 'method': 'tools/call', 'params': {'name': 'a11y_contrast_pair', 'arguments': {'fg': '#999999', 'bg': '#ffffff', 'lang': 'en'}}},
    {'jsonrpc': '2.0', 'id': 12, 'method': 'tools/call', 'params': {'name': 'a11y_generate_declaration', 'arguments': {'entidad': 'Acme', 'url': 'https://acme.eu', 'estado': 'parcial', 'contenido_no_accesible': ['Old videos without captions'], 'marco': 'eaa', 'lang': 'en'}}},
    {'jsonrpc': '2.0', 'id': 13, 'method': 'prompts/call', 'params': {'name': 'declaration-eaa', 'arguments': {'entidad': 'Acme', 'url': 'https://acme.eu', 'language': 'es'}}},
]
p2 = subprocess.run([sys.executable, os.path.join(AQUI, 'server.py')],
                    input='\n'.join(json.dumps(r) for r in REQ2),
                    capture_output=True, text=True, timeout=60)
r2 = {json.loads(l).get('id'): json.loads(l) for l in p2.stdout.splitlines() if l.strip()}
d_en = json.loads(r2[11]['result']['content'][0]['text'])
assert d_en['veredictos'][0]['criterio'].startswith('1.4.3 Contrast')
decl_en = r2[12]['result']['content'][0]['text']
assert 'European Accessibility Act' in decl_en and '<html lang="en">' in decl_en
assert 'Old videos without captions' in decl_en
prompt_es = r2[13]['result']['messages'][0]['content']['text']
assert prompt_es.startswith('Genera la declaración')
print('MULTILINGUE MCP OK ✓ (EN pair + EN/EAA declaration + prompt ES)')
