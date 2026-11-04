#!/usr/bin/env python3
"""a11y_trace — the behavioral trace: what a keyboard user LIVES, step by step.

The deterministic core of the journey-replay idea family (replayable journeys,
screen-reader release gates, behavioral debugging): one walk of the page
recording, PER TAB STEP, the focused element's stable signature (the same
key doctrine as the snapshot), the aria-live announcements the step
triggered, and the url — plus the accessibility tree at the end.
`trace diff` compares two traces: FOCUS BEHAVIOR IS THE GATE (a forked or
lost tab sequence blocks, exit 2); announcements are reported, not gated
(content changes legitimately between builds — a collapsed announcement
layer is flagged informationally).

Honesty: this captures the accessibility-tree / live-region layer — what a
screen reader would have AVAILABLE, not the synthesized speech of NVDA/JAWS
(real AT is a different beast; the agent-side complement is
a11y_journey_verdict). The collector is SILENT (no panel injected): a trace
must not mutate the page it measures.

CLI (infrastructure, not a tool — D17, like corpus/mutants/engines):
  a11ytrace.py https://web [--steps 25] [-o trace.json]      # needs Playwright
  a11ytrace.py https://web --script journey.json -o t.json   # scripted real journey
  a11ytrace.py diff before.json after.json                   # exit 0 ok / 2 divergences

Script file: a JSON list of actions — {"kind":"click","selector":"#pay"},
{"kind":"fill","selector":"#email","value":"…"}, {"kind":"select",…},
{"kind":"press","key":"Enter"}, {"kind":"wait","ms":300}, {"kind":"goto","url":…}.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from . import a11ydiff

# Silent live-region collector: accumulates announcements and exposes a
# drain() so each trace step reads EXACTLY the announcements it triggered.
# Same selector set as the arialive monitor, but no DOM panel — the trace
# must not mutate the page it measures.
_COLLECTOR = r'''() => {
  if (window.__a11yTraceDrain) return window.__a11yTraceDrain();
  const SEL = '[aria-live],[role=alert],[role=status],[role=log],[role=marquee],[role=timer]';
  const seen = new WeakSet(); const log = [];
  const politeness = el => el.getAttribute('aria-live') ||
    ({ alert: 'assertive', status: 'polite', log: 'polite',
       marquee: 'off', timer: 'off' })[el.getAttribute('role')] || 'polite';
  const target = el => el.id ? '#' + el.id
    : (el.className && typeof el.className === 'string'
       ? el.tagName.toLowerCase() + '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.')
       : el.tagName.toLowerCase());
  const push = (el, reason) => {
    if (log.length >= 500) return;
    log.push({ politeness: politeness(el),
               role: el.getAttribute('role') || 'aria-live',
               target: target(el),
               text: ((el.innerText || el.textContent || '').trim()
                      .replace(/\s+/g, ' ')).slice(0, 220),
               reason: reason || 'update' });
  };
  const watch = el => {
    if (!el || el.nodeType !== 1 || seen.has(el)) return;
    if (!el.matches || !el.matches(SEL)) return;
    seen.add(el);
    if (el.getAttribute('role') === 'alert') push(el, 'inserted');
    new MutationObserver(() => push(el))
      .observe(el, { childList: true, characterData: true, subtree: true });
  };
  document.querySelectorAll(SEL).forEach(watch);
  new MutationObserver(muts => muts.forEach(m => m.addedNodes.forEach(n => {
    if (n.nodeType !== 1) return;
    watch(n);
    if (n.querySelectorAll) n.querySelectorAll(SEL).forEach(watch);
  }))).observe(document.body, { childList: true, subtree: true });
  window.__a11yTraceDrain = () => log.splice(0);
  return [];
}'''

# Drenaje defensivo: un `goto` destruye window.__a11yTraceDrain (navegación =
# contexto nuevo); pedirlo sin guardia tronaría el paso entero. La expresión
# es estática (nada del page entra aquí) y devuelve [] cuando el recolector
# aún no existe — el paso se graba, simplemente sin anuncios de ese instante.
_DRAIN = '() => window.__a11yTraceDrain ? window.__a11yTraceDrain() : []'


def _run_script_action(page, act):
    """One scripted action → (label, ok). Selector-valued actions target CSS."""
    kind = act.get('kind', '')
    sel = act.get('selector') or act.get('target') or ''
    if kind == 'click':
        loc = page.locator(sel).first
        loc.click(timeout=5000)
        return f'click:{sel}', True
    if kind == 'fill':
        page.locator(sel).first.fill(str(act.get('value', '')), timeout=5000)
        return f'fill:{sel}', True
    if kind == 'select':
        page.locator(sel).first.select_option(str(act.get('value', '')), timeout=5000)
        return f'select:{sel}', True
    if kind == 'press':
        page.keyboard.press(act.get('key', 'Enter'))
        return f'press:{act.get("key", "Enter")}', True
    if kind == 'wait':
        page.wait_for_timeout(int(act.get('ms', 300)))
        return f'wait:{act.get("ms", 300)}', True
    if kind == 'goto':
        page.goto(act.get('url', ''), wait_until='load', timeout=30000)
        # la navegación destruye el recolector (contexto nuevo): re-inyectarlo
        # o el drain de ESTE paso y de los siguientes tronaría/volvería vacío
        page.evaluate(_COLLECTOR)
        return f'goto:{act.get("url", "")}', True
    return f'unknown:{kind or sel}', False


def _run_script(page, script):
    """Scripted actions → (walk, navigations). Factored out of trace() so the
    loop is testable against a fake page (no Playwright needed)."""
    walk = []
    navigations = 0
    url_now = page.url
    for i, act in enumerate(script):
        if not isinstance(act, dict):
            continue
        try:
            label, _ok = _run_script_action(page, act)
        except Exception as e:  # noqa: BLE001 — a failed action is a recorded step too
            label = f'{act.get("kind", "?")}:{act.get("selector") or act.get("key") or ""}'
            label += f' (failed: {str(e)[:60]})'
        page.wait_for_timeout(200)
        info = page.evaluate(a11ydiff.FOCUS_KEY_JS)
        anns = page.evaluate(_DRAIN)
        if page.url != url_now:
            navigations += 1
            url_now = page.url
        walk.append({'step': i + 1, 'action': label, 'focus': info,
                     'announcements': anns, 'url': page.url})
    return walk, navigations


def trace(url, steps=25, output=None, auth_state=None, timeout=45, script=None, browser='auto'):
    """One url → the behavioral trace (replayable JSON).

    script: optional list of scripted actions (click/fill/select/press/wait/
    goto, each with a CSS selector where applicable) — a REAL journey instead
    of the keyboard walk. Each action becomes a recorded step; the announcement
    collector and the focus signature stay identical, so trace diff works the
    same over scripted traces."""
    from playwright.sync_api import sync_playwright
    from .a11ydom import _get_browser
    with sync_playwright() as p:
        nav = _get_browser(p, preferred=browser)
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': f'could not load: {e}'}
        page.wait_for_timeout(400)
        page.evaluate(_COLLECTOR)

        walk = []
        navigations = 0
        url_now = page.url
        if script:
            ended_by = 'script_done'
            walk, navigations = _run_script(page, script)
        else:
            ended_by = 'step_cap'
            for i in range(steps):
                page.keyboard.press('Tab')
                info = page.evaluate(a11ydiff.FOCUS_KEY_JS)
                if info is None:
                    ended_by = 'no_more_focusables'
                    break
                page.wait_for_timeout(150)   # let the observers flush
                anns = page.evaluate(_DRAIN)
                if page.url != url_now:
                    navigations += 1
                    url_now = page.url
                walk.append({'step': i + 1, 'focus': info,
                             'announcements': anns, 'url': page.url})

        tree = None
        try:
            tree = page.locator('body').aria_snapshot()
            if len(tree) > 60_000:
                tree = tree[:60_000] + '\n… (truncated)'
        except Exception:  # noqa: BLE001
            tree = None
        nav.close()

    data = {'mode': 'trace', 'url': url,
            'ts': datetime.now(timezone.utc).isoformat(),
            'steps': walk,
            'summary': {'steps_taken': len(walk),
                        'announcements': sum(len(s.get('announcements') or [])
                                             for s in walk),
                        'navigations': navigations,
                        'ended_by': ended_by}}
    if tree is not None:
        data['tree'] = tree
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def trace_diff(a, b):
    """Two traces → verdict. Focus behavior gates; announcements inform."""
    fa = [s.get('focus') for s in a.get('steps', [])]
    fb = [s.get('focus') for s in b.get('steps', [])]
    set_a, set_b = set(fa), set(fb)
    common_a = [x for x in fa if x in set_b]
    common_b = [x for x in fb if x in set_a]
    lost = [x for x in fa if x not in set_b]
    gained = [x for x in fb if x not in set_a]
    reordered = common_a != common_b
    first_divergence = next((i for i, (x, y) in enumerate(zip(common_a, common_b))
                             if x != y), None)
    ann_a = sum(len(s.get('announcements', [])) for s in a.get('steps', []))
    ann_b = sum(len(s.get('announcements', [])) for s in b.get('steps', []))
    collapsed = ann_a > 0 and ann_b == 0
    ok = not (lost or reordered)
    return {
        'ok': ok,
        'summary': {'steps': {'before': len(fa), 'after': len(fb)},
                    'focus_lost': len(lost), 'focus_gained': len(gained),
                    'reordered': reordered,
                    'announcements': {'before': ann_a, 'after': ann_b,
                                      'collapsed': collapsed}},
        'focus': {'before': fa, 'after': fb, 'lost': lost, 'gained': gained,
                  'first_divergence': first_divergence},
        'note': ('focus behavior is the gate: a lost or forked tab sequence '
                 'blocks (exit 2). Announcement counts are reported, not '
                 'gated — content changes legitimately between builds; a '
                 'collapsed layer (had announcements, now zero) is flagged '
                 'informationally'),
    }


def main(argv):
    # el hub del CLI pasa el argv SIN el subcomando (['url', …]): el parser
    # exige trace|diff — prepend 'trace' cuando el primer token no es subcmd
    if argv and argv[0] not in ('trace', 'diff') and not argv[0].startswith('-'):
        argv = ['trace'] + argv
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s1 = sub.add_parser('trace')
    s1.add_argument('url')
    s1.add_argument('--steps', type=int, default=25)
    s1.add_argument('--script', help='JSON file: scripted journey (click/fill/select/press/wait/goto)')
    s1.add_argument('--auth-state', help='Playwright storage_state JSON (session)')
    s1.add_argument('--timeout', type=int, default=45)
    s1.add_argument('-o', '--out', default='trace.json')
    s2 = sub.add_parser('diff')
    s2.add_argument('a')
    s2.add_argument('b')
    a = p.parse_args(argv)

    if a.cmd == 'trace':
        script = None
        if a.script:
            try:
                with open(a.script, encoding='utf-8') as f:
                    script = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(json.dumps({'error': f'bad script file: {e}'}))
                return 1
        try:
            d = trace(a.url, steps=a.steps, output=a.out, auth_state=a.auth_state,
                      timeout=a.timeout, script=script)
        except ImportError:
            print(json.dumps({'error': 'Playwright not installed: pip install '
                                       'playwright && playwright install chromium'}))
            return 1
        if 'error' in d:
            print(json.dumps(d, ensure_ascii=False))
            return 1
        print(json.dumps({'url': d['url'], 'summary': d['summary'],
                          'out': a.out}, ensure_ascii=False, indent=1))
        return 0
    with open(a.a, encoding='utf-8') as f:
        ja = json.load(f)
    with open(a.b, encoding='utf-8') as f:
        jb = json.load(f)
    verdict = trace_diff(ja, jb)
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return 0 if verdict['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
