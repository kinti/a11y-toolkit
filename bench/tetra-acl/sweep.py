#!/usr/bin/env python3
"""Calibration sweep: this engine against TetraLogical's known-good components.

The vendored pages (pages/, ISC, see ATTRIBUTION.md) are accessible component
implementations whose upstream repo documents per-criterion expectations and
runs its own Cucumber/Playwright scenarios. Findings our engine emits here are
reviewed one by one and pinned in tests/test_tetra_acl.py; anything NEW firing
on known-good markup must be triaged before it ships.

Static audit always runs. The rendered pass (keyboard walk + 320px reflow)
runs only when Playwright is importable — CI without it degrades to static,
mirroring tests/test_engines.py. Raw output lands in results/<date>.json and
is never edited by hand: the reading lives in README.md.

    python3 bench/tetra-acl/sweep.py
"""
import datetime
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from a11y_toolkit import a11yaudit  # noqa: E402
try:
    from a11y_toolkit.server import VERSION as ENGINE_VERSION
except Exception:  # pragma: no cover — version constant moved
    ENGINE_VERSION = "unknown"

UPSTREAM = {
    "repo": "https://github.com/TetraLogical/accessible-components-library",
    "commit": "214baddf9a0500fd067a37c83583bd288f5a4f72",
    "version": "1.0.0",
    "license": "ISC",
}

try:
    import playwright  # noqa: F401 — probe the real dependency, not our wrapper
    from a11y_toolkit import a11ydom  # noqa: E402
    HAVE_PW = True
except Exception:
    HAVE_PW = False


def static_pass(pages):
    rows = []
    for page in sorted(pages.glob("*/examples/*.html")):
        html = page.read_text(encoding="utf-8")
        report = a11yaudit.audit_html(html, lang="en")
        for f in report.get("findings", []):
            rows.append({
                "component": page.parent.parent.name,
                "page": str(page.relative_to(pages)),
                "signal": f.get("signal"),
                "criterion": (f.get("criterion") or "").split(" ")[0],
                "severity": f.get("severity"),
            })
    return rows


def rendered_pass(pages):
    rows = []
    for page in sorted(pages.glob("*/examples/*.html")):
        url = f"file://{page}"
        entry = {"component": page.parent.parent.name,
                 "page": str(page.relative_to(pages))}
        kb = a11ydom.audit_keyboard(url, max_steps=40, lang="en")
        entry["kbd_score"] = kb.get("score")
        entry["kbd_trap"] = kb.get("trap_detected")
        entry["kbd_stops"] = len(kb.get("tab_stops", []) or [])
        rf = a11ydom.audit_reflow(url, lang="en")
        entry["reflow_scroll"] = rf.get("horizontal_scroll")
        entry["reflow_offenders"] = len(rf.get("offenders", []) or [])
        rows.append(entry)
    return rows


def main():
    pages = HERE / "pages"
    date = datetime.date.today().isoformat()
    result = {
        "meta": {
            "upstream": UPSTREAM,
            "engine": ENGINE_VERSION,
            "date": date,
            "rendered": HAVE_PW,
            "pages": len(list(pages.glob("*/examples/*.html"))),
        },
        "static": static_pass(pages),
    }
    if HAVE_PW:
        result["rendered"] = rendered_pass(pages)
    out = HERE / "results" / f"{date}.json"
    existing = json.loads(out.read_text()) if out.exists() else {}
    if existing and existing.get("meta") == result["meta"]:
        out.write_text(json.dumps(existing, indent=1))  # same day re-run: keep first
    else:
        out.write_text(json.dumps(result, indent=1))
    n = len(result["static"])
    print(f"pages={result['meta']['pages']} static_findings={n} rendered={HAVE_PW} -> {out.name}")


if __name__ == "__main__":
    main()
