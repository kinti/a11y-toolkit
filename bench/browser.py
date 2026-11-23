#!/usr/bin/env python3
"""Shared plumbing for the bench scripts: one browser per run.

The engine's rendered audit keeps a Chromium pool alive for the rest of the
process (its Playwright driver owns a running asyncio loop in the calling
thread). A second `sync_playwright()` session opened in that same thread dies
with "Sync API inside the asyncio loop". The bench scripts therefore never
open a session of their own: they borrow a page from the pool the engine
uses. With the pool off (A11Y_BROWSER_POOL=0) the loan starts a browser for
the page and closes it with it, so both configurations run the same code.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

AXE_VERSION = '4.10.3'
AXE_URL = f'https://cdn.jsdelivr.net/npm/axe-core@{AXE_VERSION}/axe.min.js'
# the MPL binary lives in the user's cache, never inside the repo tree
_CACHE = os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')),
                      'a11y-bench')
AXE_CACHED = os.path.join(_CACHE, 'axe.min.js')
AXE_VENDORED = os.path.join(HERE, 'axe.min.js')     # optional local copy


def axe_file():
    """Path of a local axe-core copy, or None (callers degrade with a notice)."""
    for path in (AXE_VENDORED, AXE_CACHED):
        if os.path.exists(path):
            return path
    return None


def load_axe(download=False):
    """axe-core source. With download=True a missing copy is fetched into the
    user cache (the monthly benchmark needs it); without it, a missing copy
    raises FileNotFoundError and the caller decides how to degrade."""
    path = axe_file()
    if path is None:
        if not download:
            raise FileNotFoundError(
                f'axe-core not found (expected {AXE_VENDORED} or {AXE_CACHED})')
        import urllib.request
        os.makedirs(_CACHE, exist_ok=True)
        urllib.request.urlretrieve(AXE_URL, AXE_CACHED)
        path = AXE_CACHED
    with open(path, encoding='utf-8') as f:
        return f.read()


def borrow_page():
    """(page, close_page) from the engine's browser pool. close_page returns the
    page; the browser stays warm for the next caller and the engine closes it
    when the process ends."""
    from a11y_toolkit.a11ydom import _get_browser, _pooled_page
    return _pooled_page(_get_browser())


def axe_run(page, axe_js):
    """axe-core on the open page: per-rule violations, every failing node's
    target, and how many rules ran. `inapplicable_count` is the proof that axe
    really executed: any page leaves dozens of rules inapplicable."""
    page.evaluate(axe_js)
    return page.evaluate(
        "async () => { const r = await axe.run(document, {resultTypes: ['violations']});"
        " return {violations: r.violations.map(v => ({id: v.id, impact: v.impact,"
        " nodes: v.nodes.length, tags: v.tags.filter(t => t.startsWith('wcag')),"
        " targets: v.nodes.map(n => JSON.stringify(n.target))})),"
        " inapplicable_count: r.inapplicable.length}; }")
