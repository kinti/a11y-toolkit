#!/usr/bin/env python3
"""Locale packs — community-editable message catalogs, zero dependencies.

The engine's user-facing messages live in `locales/<lang>.json` (one file per
language, namespaced by module), NOT in Python code. Anyone can add a language:
copy `locales/_template.json` → `<lang>.json`, translate the values, and the
validation test (`tests/test_locales.py`) mechanically checks the result —
same keys as English, same `{placeholders}`, a working CLDR plural rule.

Design (documented in docs/i18n.md):
- **Fallback chain**: a missing key in a pack falls back to English, so a
  half-translated locale degrades gracefully instead of crashing.
- **Plural rules**: `_meta.plural` is a CLDR-style expression over `n`
  (True → "one", False → "other"). Entries MAY be `{"one": ..., "other": ...}`
  dicts; `plural_entry()` resolves them.
- **Overlays**: downstream products (e.g. a hosted service) layer their own
  pack ON TOP of the base via `use_overlay(path)` — deep-merged, overlay wins.
  Brand voice without forking the engine.
"""

import ast
import json
import os
import re

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')
_PACKS = {}          # lang → pack dict (with overlays applied)
_OVERLAYS = []       # paths to overlay packs (applied on load)
_ARGS = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')


def available():
    """Locale codes present as locale packs (en always present)."""
    codes = {f[:-5] for f in os.listdir(_LOCALES_DIR)
               if f.endswith('.json') and not f.startswith('_')}
    return sorted(codes | {'en'})


def _deep_merge(base, overlay):
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load(lang):
    path = os.path.join(_LOCALES_DIR, f'{lang}.json')
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def pack(lang):
    """The full pack for `lang` (cached, overlays applied, en-fallback filled)."""
    if lang not in _PACKS:
        base = _load(lang) or {}
        en = _load('en') or {}
        merged = _deep_merge(en, base) if lang != 'en' else en
        for ov in _OVERLAYS:
            # overlay: {"<lang>": {"<namespace>": {...}}} — la capa gana siempre
            layer = json.load(open(ov, encoding='utf-8'))
            merged = _deep_merge(merged, layer.get(lang, {}))
        _PACKS[lang] = merged
    return _PACKS[lang]


def use_overlay(path):
    """Register an overlay pack (applies to every subsequently loaded pack)."""
    global _PACKS
    _OVERLAYS.append(path)
    _PACKS = {}  # invalidate cache


def pair(namespace):
    """Namespace catalog in the `{'es': ..., 'en': ...}` shape the engine uses."""
    return {lang: pack(lang).get(namespace, {}) for lang in ('es', 'en')}


# ── reglas plurales CLDR SIN eval ───────────────────────────────────────────
# Un locale pack es DATO (community-editable por diseño, y use_overlay() puede
# capar encima un pack de un tercero): dato jamás se convierte en código. La
# gramática CLDR es comparaciones y módulos sobre n — se evalúa con un AST de
# lista blanca; cualquier constructo fuera de esa gramática levanta ValueError.
_CLDR_COMPARE = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
                 ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
                 ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}
_CLDR_BINOP = {ast.Mod: lambda a, b: a % b, ast.Add: lambda a, b: a + b,
               ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b}


def eval_plural_rule(rule, n):
    """Evalúa 'n != 1', 'n % 10 == 1 and n % 100 != 11'… SIN eval dinámico.

    Lista blanca AST: BoolOp(And/Or), Not, Compare (== != < <= > >=),
    BinOp (% + - *), enteros/flotantes y el nombre `n`. TODO lo demás
    (llamadas, atributos, subíndices, imports…) → ValueError."""
    if not isinstance(rule, str) or not rule or len(rule) > 120:
        raise ValueError('plural rule must be a short non-empty string')
    tree = ast.parse(rule, mode='eval')

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            vals = (ev(v) for v in node.values)
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand)
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op, comp in zip(node.ops, node.comparators):
                fn = _CLDR_COMPARE.get(type(op))
                if fn is None:
                    raise ValueError('operator not in the CLDR subset')
                right = ev(comp)
                if not fn(left, right):
                    return False
                left = right          # encadenadas: a < b < c
            return True
        if isinstance(node, ast.BinOp) and type(node.op) in _CLDR_BINOP:
            return _CLDR_BINOP[type(node.op)](ev(node.left), ev(node.right))
        if (isinstance(node, ast.Constant)
                and isinstance(node.value, (int, float))
                and not isinstance(node.value, bool)):
            return node.value
        if isinstance(node, ast.Name) and node.id == 'n':
            return n
        raise ValueError('construct not in the CLDR subset: %s'
                         % type(node).__name__)

    result = ev(tree)
    if not isinstance(result, bool):
        raise ValueError('plural rule must be a predicate (a comparison), '
                         'not a bare value')
    return result


def plural_category(lang, n):
    """'one' or 'other' per the locale's `_meta.plural` CLDR expression."""
    rule = pack(lang).get('_meta', {}).get('plural', 'n != 1')
    try:
        return 'one' if eval_plural_rule(rule, n) else 'other'
    except Exception:
        return 'other'


def plural_entry(value, lang, n):
    """Resolve a `{"one": ..., "other": ...}` entry; plain strings pass through."""
    if isinstance(value, dict) and {'one', 'other'} & set(value):
        return value.get(plural_category(lang, n), value.get('other', ''))
    return value


def placeholders(text):
    """Named `{args}` a message expects — used by the validation test."""
    return set(_ARGS.findall(text or ''))
