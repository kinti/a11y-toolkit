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


def plural_category(lang, n):
    """'one' or 'other' per the locale's `_meta.plural` CLDR expression."""
    rule = pack(lang).get('_meta', {}).get('plural', 'n != 1')
    try:
        return 'one' if eval(rule, {'__builtins__': {}}, {'n': n}) else 'other'  # noqa: S307
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
