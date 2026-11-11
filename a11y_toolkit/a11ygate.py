#!/usr/bin/env python3
"""a11y gate — the write-time guard: stop accessibility failures at birth.

The audit-after-the-fact model has a fixed flaw: it arrives after the code
was saved. This gate lives where failures are BORN — in the AI client's
write path. `a11ytoolkit init` installs a client hook (Claude Code
PreToolUse) so every save of a user-facing file runs the audit against the
git HEAD version: only NEW high/medium findings refuse the write; low
severity and known issues are warnings. The AI holding the pen has the
remediation and the element right there — the fix happens in the same
second the failure would have been born.

Honesty, as everywhere: the gate audits what the engine sees (part of
WCAG) — a filter, not a conformance verdict, and it says so in every
refusal. A11Y_GATE=off disables it; --hook fails open (a gate that crashes
a developer's flow gets uninstalled — refusing on OUR error helps nobody).

Output:
  verdict(old, new, path) -> {decision, blocked[], warnings[], counts...}
  guard_hook(payload)     -> (exit_code, stderr)   # Claude Code protocol

CLI:
  a11ytoolkit guard --file index.html          # human verdict, exit 2 = block
  a11ytoolkit guard --hook                     # stdin JSON -> exit protocol
"""

import argparse
import json
import re
import subprocess
import sys

from .a11yaudit import audit_html, normalize_signal

USER_SUFFIXES = ('.html', '.htm', '.css', '.jsx', '.tsx', '.vue', '.svelte',
                 '.astro', '.ejs', '.hbs', '.mustache', '.erb', '.twig',
                 '.liquid', '.jinja', '.jinja2', '.php')
BLOCKING = {'high', 'medium'}
_SEV_ORDER = {'high': 0, 'medium': 1, 'low': 2}
_LIST_CAP = 6
_FOOT = ('the gate audits what the engine sees — a filter, not a '
         'conformance verdict · disable: A11Y_GATE=off')


def is_user_facing(path):
    return bool(path) and path.lower().endswith(USER_SUFFIXES)


def _counts(findings):
    """(normalized signal, criterion code) → occurrences."""
    out = {}
    for h in findings:
        key = (normalize_signal(h.get('signal', '')),
               (h.get('criterion') or '').split(' ')[0])
        out[key] = out.get(key, 0) + 1
    return out


def old_version(path, project='.'):
    """The file's content at git HEAD ('' when untracked, new, or no git —
    a gate must never crash a developer's flow on missing plumbing)."""
    try:
        rel = subprocess.run(['git', 'ls-files', '--', path], cwd=project,
                             capture_output=True, text=True, timeout=10)
        if rel.returncode != 0 or not rel.stdout.strip():
            return ''
        shown = subprocess.run(['git', 'show', f'HEAD:{path}'], cwd=project,
                               capture_output=True, text=True, timeout=10)
        return shown.stdout if shown.returncode == 0 else ''
    except Exception:  # noqa: BLE001 — fail open, always
        return ''


def verdict(old_content, new_content, path='(file)'):
    """Compare findings in OLD (git HEAD) vs NEW (the save in flight).

    The engine aggregates findings by KIND (one 'img without alt' finding
    covers N images), so the gate works on KINDS, like the budget module:
    a NEW kind with high/medium severity refuses the save; new LOW kinds
    and kinds already in HEAD are warnings. Returns {decision, blocked[],
    warnings[], known, before, after, score}."""
    old = audit_html((old_content or '')[:3_000_000], url=f'(old) {path}')
    new = audit_html((new_content or '')[:3_000_000], url=f'(new) {path}')
    if 'error' in old or 'error' in new:
        return {'decision': 'allow', 'path': path,
                'note': 'unparseable content — the gate does not judge '
                        'what the engine cannot parse'}

    before = _counts(old.get('findings', []))
    after = _counts(new.get('findings', []))
    blocked, warnings = [], []
    for h in new.get('findings', []):
        key = (normalize_signal(h.get('signal', '')),
               (h.get('criterion') or '').split(' ')[0])
        if key in before:
            continue
        sev = h.get('severity', 'low')
        if sev in BLOCKING:
            blocked.append(h)
        else:
            warnings.append(f"new low-severity finding: "
                            f"{h.get('criterion', '?').split(' ')[0]} "
                            f"{h.get('signal', '?')}")
    known = len(before)
    if known:
        warnings.append(f'{known} known finding kind(s) in this file — '
                        f'not blocking (fix and re-run audit to lower)')
    blocked.sort(key=lambda h: (_SEV_ORDER.get(h.get('severity'), 3),
                                h.get('signal', '')))
    decision = 'block' if blocked else 'allow'
    return {'decision': decision, 'path': path, 'blocked': blocked,
            'warnings': warnings, 'known': known,
            'before': sum(before.values()), 'after': sum(after.values()),
            'score': new.get('score')}


def _fmt_blocked(blocked):
    out = []
    for h in blocked[:_LIST_CAP]:
        out.append(f"  - [{h.get('severity')}] {h.get('criterion', '?')} "
                   f"{h.get('signal', '?')}: "
                   f"{(h.get('issue') or '')[:110]}")
        rem = (h.get('remediation') or '')[:150]
        if rem:
            out.append(f"      how to fix: {rem}")
    more = len(blocked) - _LIST_CAP
    if more > 0:
        out.append(f'  … and {more} more')
    return '\n'.join(out)


def _fmt_verdict(v):
    lines = [f"[a11y gate] {len(v['blocked'])} NEW accessibility finding(s) "
             f"in {v['path']} — save refused"]
    lines.append(_fmt_blocked(v['blocked']))
    for w in v.get('warnings', []):
        lines.append(f'  note: {w}')
    lines.append(_FOOT)
    return '\n'.join(lines)


def payload_to_write(payload):
    """Claude Code PreToolUse payload → (path, new_content or None).

    Write carries the full content; Edit/MultiEdit carry fragments — apply
    them to the on-disk version (which PreToolUse sees before the write)."""
    if not isinstance(payload, dict):
        return None, None
    tool = payload.get('tool_name', '')
    tin = payload.get('tool_input') or {}
    path = tin.get('file_path') or ''
    if tool == 'Write':
        return path, tin.get('content')
    if tool in ('Edit', 'MultiEdit'):
        try:
            content = open(path, encoding='utf-8', errors='replace').read()
        except Exception:  # noqa: BLE001
            return path, None
        edits = tin.get('edits') if tool == 'MultiEdit' else [tin]
        for e in edits or []:
            if not isinstance(e, dict):
                continue
            old, new = e.get('old_string'), e.get('new_string')
            if old is None:
                continue
            content = content.replace(old, new) if new is not None \
                else content.replace(old, '')
        return path, content
    return path, None


def guard_hook(payload_text):
    """stdin JSON → (exit_code, stderr) under the Claude Code protocol:
    exit 2 blocks the write and feeds stderr back to the model; exit 0
    allows (stderr is a transcript note). Fails OPEN on unreadable input —
    a gate that errors the developer's flow gets uninstalled."""
    try:
        payload = json.loads(payload_text or '')
    except Exception:  # noqa: BLE001
        return 0, '[a11y gate] unreadable hook payload — allowing (fail-open)'
    path, content = payload_to_write(payload)
    if not path or content is None:
        return 0, ''
    if not is_user_facing(path):
        return 0, ''
    v = verdict(old_version(path), content, path)
    if v['decision'] == 'block':
        return 2, _fmt_verdict(v)
    if v.get('warnings'):
        return 0, '\n'.join(f'[a11y gate] {w}' for w in v['warnings'])
    return 0, ''


def main(argv):
    ap = argparse.ArgumentParser(
        description='Write-time gate: refuse saves that introduce NEW '
                    'high/medium accessibility findings')
    ap.add_argument('--hook', action='store_true',
                    help='read the client hook JSON payload from stdin')
    ap.add_argument('--file', help='audit this file directly')
    a = ap.parse_args(argv)
    if a.hook:
        text = sys.stdin.read()
        code, err = guard_hook(text)
        if err:
            print(err, file=sys.stderr)
        return code
    if a.file:
        content = open(a.file, encoding='utf-8', errors='replace').read()
        v = verdict(old_version(a.file), content, a.file)
        print(json.dumps({k: v[k] for k in ('decision', 'path', 'known',
                                            'before', 'after', 'score')},
                         ensure_ascii=False, indent=1))
        for w in v.get('warnings', []):
            print('note:', w)
        if v['decision'] == 'block':
            print(_fmt_verdict(v), file=sys.stderr)
            return 2
        return 0
    ap.print_usage()
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
