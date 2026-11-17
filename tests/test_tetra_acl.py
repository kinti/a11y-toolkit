#!/usr/bin/env python3
"""Calibration bench bench/tetra-acl: known-good components (TetraLogical, ISC).

Invariant: the static findings on these vendored pages may only be the
reviewed page-context signals (the upstream examples are heading-less
fragments). Any NEW signal on known-good markup must fail the suite until a
human triages it — the engine either learned something real (extend the
allowlist with a comment) or grew a false positive (fix the engine).

The rendered half (keyboard walk + 320px reflow) runs only when Playwright is
importable, mirroring tests/test_engines.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from a11y_toolkit import a11yaudit  # noqa: E402

PAGES = os.path.join(ROOT, "bench", "tetra-acl", "pages")

# ── 1. the panel exists and is whole ────────────────────────────────────────
comps = sorted(os.listdir(PAGES))
assert comps == ["accordion", "breadcrumbs", "dialog", "disclosure",
                 "pagination", "tabs", "text-input", "textarea"], comps
htmls = []
for c in comps:
    ex = os.path.join(PAGES, c, "examples")
    for name in sorted(os.listdir(ex)):
        if name.endswith(".html"):
            htmls.append(os.path.join(ex, name))
assert len(htmls) == 16, f"el panel cambió sin re-triaje: {len(htmls)} páginas"
print(f"1. panel entero: 8 componentes, {len(htmls)} páginas ✓")

# ── 2. estático: solo los señales revisados (contexto de página, no componente) ──
ALLOWED = {("no_headings", "1.3.1"), ("no_h1", "1.3.1")}
extra = []
n_findings = 0
for path in htmls:
    report = a11yaudit.audit_html(open(path, encoding="utf-8").read(), lang="en")
    for f in report.get("findings", []):
        n_findings += 1
        key = (f.get("signal"), (f.get("criterion") or "").split(" ")[0])
        if key not in ALLOWED:
            extra.append((os.path.relpath(path, PAGES), key))
assert not extra, f"señal NUEVA sobre markup conocido-bueno — triar antes de subir: {extra[:5]}"
print(f"2. estático: {n_findings} hallazgos, todos dentro de los revisados {sorted(ALLOWED)} ✓")

# ── 3. rendered (skip honesto sin Playwright) ──────────────────────────────
try:
    import playwright  # noqa: F401 — probe the real dependency, not our wrapper
    from a11y_toolkit import a11ydom  # noqa: F401
    HAVE_PW = True
except Exception:
    HAVE_PW = False
if not HAVE_PW:
    print("3. SKIP rendered: Playwright no instalado (igual que test_engines)")
else:
    for path in htmls:
        url = "file://" + path
        kb = a11ydom.audit_keyboard(url, max_steps=40, lang="en")
        assert not kb.get("trap_detected"), f"trampa de teclado en conocido-bueno: {path}"
        assert kb.get("score", 0) == 100, f"keyboard score <100 en conocido-bueno: {path} → {kb.get('score')}"
        rf = a11ydom.audit_reflow(url, lang="en")
        assert not rf.get("horizontal_scroll"), f"scroll horizontal a 320px en conocido-bueno: {path}"
    print(f"3. rendered: {len(htmls)}/{len(htmls)} páginas sin trampa, score 100, sin scroll a 320px ✓")

print("TETRA-ACL OK ✓ (calibración contra componentes conocido-buenos dentro de lo revisado)")
