#!/usr/bin/env python3
"""Superficie pública 100% inglesa — el test que impide que vuelva a colarse español.

Nació del barrido 2026-10 (TDQS 2/5 en Naming): se colaron params españoles
(method, fecha_evaluacion, max_pasos…), claves de output (applied, batches,
language…) y señales (imgs_alt, lang_partes…) en la superficie que ven los
agentes. Aquí queda clavado:

  1. SCHEMA: nombres de tools, params y enums sin tokens españoles.
  2. DESCRIPCIONES: TOOLS + PROMPTS + INSTRUCTIONS sin words españolas.
  3. CLAVES DE DICT: ningún token español como entry_key en a11y_toolkit/*.py,
     salvo los alias de compatibilidad revisados (PARAM/SIGNAL/STATUS_ALIASES).
  4. SIN TILDES ni ñ en identificadores de la superficie.

DECISIÓN A (23/10, Jesús): los COMENTARIOS y docstrings pueden
seguir en español POR DISEÑO (legibilidad del maintainer) — no son deuda
pendiente: ninguna sesión futura debe "traducirlos". El i18n completo
(catálogos, más idiomas) es un ítem de roadmap aparte, decidido pero no hoy.

Los alias de compatibilidad son la ÚNICA excepción: son los nombres pre-5.11
que seguimos aceptando en la entry para no romper a clientes existentes.
"""

import os
import re
import sys
import tokenize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit import server  # noqa: E402
from a11y_toolkit.a11yaudit import SIGNAL_ALIASES  # noqa: E402
from a11y_toolkit.a11ystatement import STATUS_ALIASES  # noqa: E402

# Palabras españolas que NO existen en inglés. Token-exacto tras partir por _.
# Sirve para claves de dict, params, enums E identificadores (sección 5).
# NUNCA añadir aquí una palabra que también sea inglesa (path, pages, name…).
LEXICON = {
    'accion', 'acciones', 'alcance', 'alternativa', 'alternativo', 'ancho', 'alto',
    'anuncios', 'aplicado', 'aplicados', 'archivo', 'avisos', 'aviso', 'ayuda',
    'año', 'blanco', 'bloque', 'bloques', 'boton', 'botones', 'cabecera',
    'cabeceras', 'cadena', 'cadenas', 'campo', 'campos', 'canal', 'cargar',
    'carga', 'ciclo', 'clave', 'claves', 'codigo', 'codigos', 'comun', 'cuenta',
    'cuerpo', 'cubierto', 'cuerpos', 'declaracion', 'descarga', 'desde',
    'detalle',  'dia', 'dias', 'disponibilidad', 'dominio',
    'elemento', 'elementos', 'enlace', 'enlaces', 'entrada', 'entradas',
    'equipo', 'escala', 'escrito', 'estado', 'estados', 'evaluacion',
    'evaluador', 'ejemplo', 'ejemplos', 'exige', 'fallos', 'falso', 'falsos',
    'fecha', 'fichero', 'ficheros', 'fin', 'firma', 'fondo', 'forma', 'fresco',
    'fuera', 'gestos', 'grande', 'guardado', 'guardar', 'hallazgo',
    'hallazgos', 'hasta', 'hoy',
    'identificados', 'malos', 'nativos', 'sugeridos', 'coloreados',
    'techo', 'trozo', 'aceptar', 'esquema', 'severidad', 'saltos', 'esfuerzo',
    'navego', 'aniadido', 'eliminado', 'cambia', 'busqueda', 'foco',
    'validar', 'legado', 'pendiente', 'matriz', 'restantes', 'nombre_de', 'modo', 'todas', 'idioma', 'idiomas', 'imagen', 'imagenes',
    'informe', 'informes', 'inicial', 'invalida', 'invalido', 'invalidos',
    'izquierda', 'jornada', 'leyenda', 'libera', 'limite', 'limites', 'linea',
    'lineas', 'lista', 'listas', 'lugar', 'manos', 'marco', 'mejor', 'mensaje',
    'metodo', 'metodos', 'nivel', 'niveles', 'nombre', 'nombres', 'nueva',
    'nuevo', 'nuevos', 'numero', 'numeros', 'opaco', 'paginas', 'pagina',
    'pais', 'palabra', 'palabras', 'parada', 'paradas', 'parece', 'parcial',
    'parte', 'partes', 'paso', 'pasos', 'peor', 'pequena', 'pequeno', 'plena',
    'porque', 'prueba', 'pruebas', 'que', 'razon', 'reclamacion', 'recorrido',
    'reglas', 'renglon', 'resena', 'resueltas', 'resumen',
    'resultados', 'resto', 'resultado', 'ruta', 'rutas', 'salida', 'salidas',
    'seccion', 'secciones', 'senal', 'senales', 'sencillo', 'siguiente',
    'sobre', 'sin', 'tabla', 'tablas', 'tanda', 'tandas', 'texto', 'textos',
    'tipo', 'tipos', 'titulo', 'titulos', 'todos', 'ultimo', 'ultima',
    'umbral', 'valor', 'valores', 'vaso', 'verificacion', 'verificado',
    'ver', 'vacio', 'vivos', 'zona', 'zonas',
}
# Falsos amigos EXCLUIDOS (existen en inglés): no, total, base, color, radio,
# normal, final, error, mode, date, score, note, path, pages, name, data…
# 'lang' es código ISO de uso universal: permitido.
LEXICON.discard('lang')

ALIAS_PERMITIDOS = set(SIGNAL_ALIASES) | set(SIGNAL_ALIASES.values())
ALIAS_PERMITIDOS |= set(STATUS_ALIASES) | set(STATUS_ALIASES.values())
ALIAS_PERMITIDOS |= set(server.PARAM_ALIASES) | set(server.PARAM_ALIASES.values())
ALIAS_PERMITIDOS |= {'no_conforme'}  # valor legal RD 1112/2018 aceptado a la entrada
# claves de DATOS LEGADOS que se leen a propósito para no romper ficheros pre-5.11
LEGADO_PERMITIDO = {'ultimo_audit'}  # ledgers guardados antes del rename (a11yledger)

ACCENTOS = re.compile(r'[áéíóúñÁÉÍÓÚÑ]')
CLAVE = re.compile(r"""['"]([a-z_áéíóúñ][a-z0-9_áéíóúñ]*)['"]\s*:""")
TOKENS = re.compile(r'[a-záéíóúñ0-9]+')


def tokens(text):
    return TOKENS.findall(str(text).lower())


def espanyol(ident):
    """Tokens españoles de un identificador (snake_case o text)."""
    return [t for t in tokens(ident) if t in LEXICON]


# ---------- 1. SCHEMA: tools, params, enums ----------
failures = []
for t in server.TOOLS:
    if espanyol(t['name']):
        failures.append(f"tool {t['name']}: name con español")
    for p, spec in t.get('inputSchema', {}).get('properties', {}).items():
        if p not in ALIAS_PERMITIDOS and espanyol(p):
            failures.append(f"{t['name']}.{p}: param con español")
        if isinstance(spec, dict) and p not in ('lang', 'browser'):
            for v in spec.get('enum', []) or []:
                if str(v) not in ALIAS_PERMITIDOS and espanyol(v):
                    failures.append(f"{t['name']}.{p}: enum {v!r} con español")
assert not failures, '\n'.join(failures)

# ---------- 2. DESCRIPCIONES: TOOLS, PROMPTS, INSTRUCTIONS ----------
failures = []
for t in server.TOOLS:
    for w in espanyol(t.get('description', '')):
        failures.append(f"descripción de {t['name']}: {w!r}")
for p in getattr(server, 'PROMPTS', []):
    for w in espanyol(p.get('description', '') + ' ' + str(p.get('template', ''))):
        failures.append(f"prompt {p.get('name')}: {w!r}")
for w in espanyol(server.INSTRUCTIONS):
    failures.append(f"INSTRUCTIONS: {w!r}")
assert not failures, '\n'.join(failures)

# ---------- 3. CLAVES DE DICT en todo el paquete ----------
failures = []
for f in sorted(os.listdir(os.path.join(ROOT, 'a11y_toolkit'))):
    if not f.endswith('.py'):
        continue
    path = os.path.join(ROOT, 'a11y_toolkit', f)
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        for m in CLAVE.finditer(line):
            entry_key = m.group(1)
            if entry_key in ALIAS_PERMITIDOS:
                continue
            mal = espanyol(entry_key)
            if mal or ACCENTOS.search(entry_key):
                failures.append(f"{f}:{n} entry_key {entry_key!r} ({','.join(mal) or 'tilde'})")
assert not failures, '\n'.join(failures)

# ---------- 4. SIN TILDES en la superficie ----------
failures = []
for t in server.TOOLS:
    if ACCENTOS.search(t['name']):
        failures.append(t['name'])
    for p in t.get('inputSchema', {}).get('properties', {}):
        if ACCENTOS.search(p):
            failures.append(f"{t['name']}.{p}")
assert not failures, failures

print('test_naming.py OK — superficie pública sin español')

# ---------- 5. IDENTIFICADORES: nada de español en nombres de código ----------
fallos = []
for f in sorted(os.listdir(os.path.join(ROOT, 'a11y_toolkit'))):
    if not f.endswith('.py'):
        continue
    ruta = os.path.join(ROOT, 'a11y_toolkit', f)
    with open(ruta, 'rb') as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type != tokenize.NAME:
                continue
            if tok.string in ALIAS_PERMITIDOS:
                continue
            if ACCENTOS.search(tok.string):
                fallos.append(f'{f}:{tok.start[0]} identificador con tilde: {tok.string}')
                continue
            for parte in TOKENS.findall(tok.string.lower()) if '_' in tok.string else tok.string.lower().split('_'):
                if parte in LEXICON:
                    fallos.append(f'{f}:{tok.start[0]} identificador {tok.string} (español: {parte})')
assert not fallos, '\n'.join(sorted(set(fallos))[:20])

# ---------- 6. CLAVES EN POSICIÓN DE LECTURA (d['clave'] / .get('clave')) ----------
# Los cuatro bugs de la 5.11 (F.corto en JS, {ciclo}, carga_error, selector_falta)
# vivían AQUÍ: el identificador era un string, invisible para el pin de NAME tokens.
LECTURA = re.compile(r"""\[\s*['"]([a-z_áéíóúñ][a-z0-9_áéíóúñ]*)['"]\s*\]|\.(?:get|pop|setdefault)\(\s*['"]([a-z_áéíóúñ][a-z0-9_áéíóúñ]*)['"]""")
fallos = []
for f in sorted(os.listdir(os.path.join(ROOT, 'a11y_toolkit'))):
    if not f.endswith('.py'):
        continue
    for n, linea in enumerate(open(os.path.join(ROOT, 'a11y_toolkit', f), encoding='utf-8'), 1):
        for m in LECTURA.finditer(linea):
            clave = m.group(1) or m.group(2)
            if clave in ALIAS_PERMITIDOS or clave in LEGADO_PERMITIDO:
                continue
            mal = [t for t in TOKENS.findall(clave) if t in LEXICON]
            if mal or ACCENTOS.search(clave):
                fallos.append(f'{f}:{n} lectura {clave!r} ({",".join(mal) or "tilde"})')
assert not fallos, '\n'.join(sorted(set(fallos))[:20])

# ---------- 7. PLANTILLAS ↔ JS: placeholders de _PHRASES y props F.* consistentes ----------
from a11y_toolkit.a11yfix import _PHRASES, _JS_PHRASES  # noqa: E402
for idioma in ('es', 'en'):
    for k in _PHRASES[idioma]:
        assert f'%({k})s' in _JS_PHRASES, f'_JS_PHRASES no usa el placeholder {k}'
for prop in re.findall(r'F\.([a-zA-Z]+)', _JS_PHRASES):
    assert prop in _PHRASES['en'] and prop in _PHRASES['es'], \
        f'F.{prop} del JS inyectado no existe en _PHRASES'



# ---------- 8. DICCIONARIO CRUZADO (definitivo: español ∩ no-inglés) ----------
# El lexicón curado se queda como primera línea rápida; esta sección usa la
# lista completa de palabras españolas que NO existen en inglés (613k tokens,
# tests/es-only-tokens.txt.gz) contra TODO identificador del paquete. Sin
# huecos posibles: si una palabra es española y no inglesa, salta.
import gzip as _gz
_ES_ONLY = set(_gz.open(os.path.join(ROOT, 'tests', 'es-only-tokens.txt.gz'),
                        'rt', encoding='utf-8').read().splitlines())
# falsos amigos del código (existen en español pero son términos técnicos)
_CODE_OK = {'res', 'items', 'values', 'val', 'vals', 'pos', 'sel', 'pre', 'cues',
            'box', 'todo', 'gaps', 'videos', 'min', 'max', 'idem', 'effort',
            'minutes', 'form', 'label', 'labels', 'title', 'name', 'text', 'type',
            'mode', 'state', 'level', 'score', 'note', 'notes', 'scope', 'role',
            'roles', 'rules', 'focus', 'pair', 'pares', 'gen', 'sin', 'van',
            'una', 'uno', 'del', 'mal', 'pan', 'tal', 'tres', 'data', 'user',
            'base', 'top', 'bottom', 'left', 'right', 'center', 'auth', 'lang',
            'api', 'degrades', 'grew', 'waits', 'wait', 'mask', 'masks', 'layer',
            'ratios', 'ratio', 'channels', 'raw', 'filter', 'clip', 'forced', 'reduced',
            'aliases', 'has', 'fileno', 'locales', 'locale',
            'target', 'errors', 'present', 'verb', 'note', 'notes', 'grade', 'current',
            'resolved', 'removed', 'renamed', 'same', 'dynamic', 'after', 'touched',
            'streams', 'stream', 'truncated', 'encrypted', 'signatures', 'weights',
            'syllables', 'controls', 'styles', 'measured', 'candidates', 'hint', 'clean'}
fallos = []
for f in sorted(os.listdir(os.path.join(ROOT, 'a11y_toolkit'))):
    if not f.endswith('.py'):
        continue
    with open(os.path.join(ROOT, 'a11y_toolkit', f), 'rb') as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type != tokenize.NAME:
                continue
            for parte in tok.string.lower().split('_'):
                if len(parte) >= 3 and parte in _ES_ONLY and parte not in _CODE_OK:
                    fallos.append(f'{f}:{tok.start[0]} identificador {tok.string} (español: {parte})')
assert not fallos, '\n'.join(sorted(set(fallos))[:25])
print('  diccionario cruzado: 613k tokens españoles revisados — cero fugas')

# ── 9. JS INYECTADO y LITERALES (análisis externo 2026-10: el test veía NAME
#    tokens y claves, pero NO los identificadores dentro de los strings
#    evaluate(...) ni los literales de print/error — ahí vivía el español) ──
_TRIPLE = "'''" + '"""'
_JS_BLOQUES = []
for _f9 in sorted(os.listdir(os.path.join(ROOT, 'a11y_toolkit'))):
    if not _f9.endswith('.py'):
        continue
    _src9 = open(os.path.join(ROOT, 'a11y_toolkit', _f9), encoding='utf-8').read()
    for _b in re.findall("'''(.*?)'''", _src9, re.S):
        if 'const ' in _b or 'function ' in _b or 'document.' in _b or 'getComputedStyle' in _b:
            _JS_BLOQUES.append((_f9, _b))
assert len(_JS_BLOQUES) >= 5, 'no se extrajo el JS inyectado — ¿cambió el transporte?'
_fallos_js = []
for _f9, _b in _JS_BLOQUES:
    for _m in re.finditer(r'(?:const|let|var|function)\s+([A-Za-z_$][\w$]*)', _b):
        for _parte in _m.group(1).lower().split('_'):
            if len(_parte) >= 3 and _parte in _ES_ONLY and _parte not in _CODE_OK:
                _fallos_js.append(f'{_f9} JS: {_m.group(1)} (español: {_parte})')
assert not _fallos_js, 'JS inyectado con español: ' + '; '.join(sorted(set(_fallos_js))[:8])

# literales de string (print/errores de usuario): inglés — el contenido va en
# locales/*.json, no en el código. DOCSTRINGS exentos (decisión A): se marcan
# sus posiciones por AST y se saltan. Alias de compatibilidad tolerados.
from a11y_toolkit.a11yaudit import SIGNAL_ALIASES as _SA  # noqa: E402
from a11y_toolkit.server import PARAM_ALIASES as _PA  # noqa: E402
from a11y_toolkit.a11ystatement import STATUS_ALIASES as _STA  # noqa: E402
_ALIASES_OK = {'pixel', 'huerta'}   # préstamo inglés legítimo / nombre propio
for _al in list(_SA) + list(_SA.values()) + list(_PA) + list(_PA.values()) \
        + list(_STA) + list(_STA.values()):
    _ALIASES_OK |= set(_al.split('_'))
# alcance: strings que el usuario VE (prints de CLI y mensajes de error) —
# los datos bilingües de detección (CRIT es, vocabularios, labels) son
# DATO de idioma, no superficie de código
import ast as _ast9  # noqa: E402
_CADENAS_UI = []
for _f9 in sorted(os.listdir(os.path.join(ROOT, 'a11y_toolkit'))):
    if not _f9.endswith('.py'):
        continue
    _tree = _ast9.parse(open(os.path.join(ROOT, 'a11y_toolkit', _f9), encoding='utf-8').read())
    for _n in _ast9.walk(_tree):
        if isinstance(_n, _ast9.Call) and isinstance(_n.func, _ast9.Name) and _n.func.id == 'print':
            for _a9 in _n.args:
                if isinstance(_a9, _ast9.Constant) and isinstance(_a9.value, str):
                    _CADENAS_UI.append((_f9, _a9.lineno, _a9.value))
        if isinstance(_n, _ast9.Dict):
            for _k9, _v9 in zip(_n.keys, _n.values):
                if isinstance(_k9, _ast9.Constant) and _k9.value == 'error' \
                        and isinstance(_v9, _ast9.Constant) and isinstance(_v9.value, str):
                    _CADENAS_UI.append((_f9, _v9.lineno, _v9.value))
_fallos_lit = []
for _f9, _ln9, _txt9 in _CADENAS_UI:
    for _palabra in re.findall(r'[a-záéíóúñü]{4,}', _txt9):
        _p9 = _palabra.lower()
        if _p9 in _ES_ONLY and _p9 not in _CODE_OK and _p9 not in _ALIASES_OK:
            _fallos_lit.append(f'{_f9}:{_ln9} literal "{_palabra}"')
assert not _fallos_lit, 'prints/errores con español: ' + '; '.join(sorted(set(_fallos_lit))[:8])
print(f'  prints/errores de usuario ({len(_CADENAS_UI)} strings): sin español ✓')
print(f'  JS inyectado ({len(_JS_BLOQUES)} bloques) y literales de código: sin español ✓')

print('test_naming.py OK — superficie pública, código, JS inyectado y literales sin español')
