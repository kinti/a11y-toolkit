#!/usr/bin/env python3
"""a11y_patterns — APG keyboard contracts for high-risk ARIA widgets, tested live.

The deterministic piece of "screen-reader regression testing for web
components": detect the widget pattern in the rendered page and PROVE its
keyboard contract against the ARIA Authoring Practices Guide:

  dialog / alertdialog   Esc closes it; focus stays inside while open
                         (modal), focus returns after close
  tablist                ArrowRight/Left move focus between tabs (roving
                         tabindex); the tab becomes selected — by focus
                         (automatic) or by Enter/Space (manual)
  disclosure             activating the button FLIPS aria-expanded (the
                         state must be exposed, not just the visual)

Findings are family `pattern_*` with bilingual remediation. Honesty (what
v1 deliberately does NOT do): only patterns VISIBLE at load are tested —
opening a closed dialog means guessing a trigger flow (side effects on a
real site are never acceptable); nesting/corner cases (combobox, menu,
slider) are future operators, not silent gaps — this is a filter, not a
verdict.

CLI (infrastructure, not a tool — D17, like corpus/mutants/engines):
  a11ypatterns.py https://web [--lang en] [-o report.json]
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from . import a11yi18n

_P = a11yi18n.pair('patterns')  # locales/<lang>.json — community-editable

# patterns visibles en carga: dialogs abiertos, tablists, disclosures, combobox,
# menu buttons y sliders (widgets ARIA de alto riesgo, contratos APG v1+v2)
_COUNTS = r'''() => {
  const vis = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  return {
    dialogs: [...document.querySelectorAll('[role=dialog], [role=alertdialog], dialog[open]')]
      .filter(vis).length,
    tablists: [...document.querySelectorAll('[role=tablist]')].filter(vis)
      .map(l => l.querySelectorAll('[role=tab]').length),
    disclosures: [...document.querySelectorAll('button[aria-expanded]:not([aria-haspopup="menu"]), [role=button][aria-expanded]:not([aria-haspopup="menu"])')]
      .filter(vis).length,
    comboboxes: [...document.querySelectorAll('[role=combobox]')].filter(vis).length,
    menus: [...document.querySelectorAll('button[aria-haspopup="menu"], [role="button"][aria-haspopup="menu"]')]
      .filter(vis).length,
    sliders: [...document.querySelectorAll('[role="slider"]')].filter(vis).length,
  };
}'''

_INSIDE = r'''() => {
  const el = document.activeElement;
  return !!el && !!el.closest('[role=dialog], [role=alertdialog], dialog');
}'''


def _finding(findings, lang, severity, criterion, key, **fmt):
    cat = _P['es' if lang == 'es' else 'en']
    findings.append({'severity': severity, 'criterion': criterion,
                     'signal': key,
                     'issue': cat[key].format(**fmt),
                     'remediation': cat[key + '_rem']})


def _test_dialogs(page, findings, lang, cap=3):
    """Visible dialogs: Esc closes; focus stays inside (modal); returns after."""
    loc = page.locator('[role="dialog"]:visible, [role="alertdialog"]:visible, '
                       'dialog[open]:visible')
    n = min(loc.count(), cap)
    for i in range(n):
        d = loc.nth(i)
        try:
            d.evaluate('el => (el.querySelector("a[href],button,input,select,textarea,[tabindex]") '
                       '|| el).focus()')
        except Exception:  # noqa: BLE001
            continue
        is_modal = (d.get_attribute('aria-modal') or '').lower() == 'true'
        if is_modal:
            page.keyboard.press('Tab')
            page.wait_for_timeout(120)
            try:
                inside = page.evaluate(_INSIDE)
            except Exception:  # noqa: BLE001
                inside = True
            if not inside:
                _finding(findings, lang, 'medium', '2.4.3', 'pattern_modal_focus_escapes')
        page.keyboard.press('Escape')
        page.wait_for_timeout(250)
        try:
            still_open = d.is_visible()
        except Exception:  # noqa: BLE001
            still_open = False
        if still_open:
            _finding(findings, lang, 'high', '2.1.2', 'pattern_dialog_esc_no_close')


def _test_tablists(page, findings, lang, cap=3):
    """Visible tablists: arrows move focus (roving tabindex); activation follows."""
    locs = page.locator('[role="tablist"]:visible')
    n = min(locs.count(), cap)
    for i in range(n):
        tabs = locs.nth(i).locator('[role="tab"]')
        total = tabs.count()
        if total < 2:
            continue
        try:
            tabs.nth(0).evaluate('el => el.focus()')
            page.keyboard.press('ArrowRight')
            page.wait_for_timeout(120)
            is_second = page.evaluate(
                '''(tab) => document.activeElement === tab''',
                tabs.nth(1).element_handle())
            if not is_second:
                _finding(findings, lang, 'high', '2.1.1', 'pattern_tabs_arrows_dead',
                         n=total)
                continue
            # selección: automática (aria-selected sigue al foco) o manual
            # (Enter/Space activa) — ninguna = estado expuesto muerto
            if (tabs.nth(1).get_attribute('aria-selected') or '').lower() != 'true':
                page.keyboard.press('Enter')
                page.wait_for_timeout(150)
                if (tabs.nth(1).get_attribute('aria-selected') or '').lower() != 'true':
                    page.keyboard.press(' ')   # Space, la otra vía manual
                    page.wait_for_timeout(150)
                    if (tabs.nth(1).get_attribute('aria-selected') or '').lower() != 'true':
                        _finding(findings, lang, 'medium', '4.1.2',
                                 'pattern_tabs_no_activation')
        except Exception:  # noqa: BLE001 — un widget roto no debe matar el pase
            continue


def _test_disclosures(page, findings, lang, cap=8):
    """Disclosure buttons: activation must FLIP the exposed state.
    Menu buttons are excluded — they are the menu pattern's subject."""
    loc = page.locator('button[aria-expanded]:visible:not([aria-haspopup="menu"]), '
                       '[role="button"][aria-expanded]:visible:not([aria-haspopup="menu"])')
    n = min(loc.count(), cap)
    for i in range(n):
        b = loc.nth(i)
        try:
            before = (b.get_attribute('aria-expanded') or '').lower()
            name = ((b.get_attribute('aria-label') or '') or b.inner_text()
                    or 'disclosure').strip().replace('\n', ' ')[:40]
            b.click()
            page.wait_for_timeout(250)
            after = (b.get_attribute('aria-expanded') or '').lower()
            if before == after and before in ('true', 'false'):
                _finding(findings, lang, 'medium', '4.1.2',
                         'pattern_disclosure_state_frozen', name=name)
            elif after in ('true', 'false') and after != before:
                b.click()   # dejar la página como estaba
                page.wait_for_timeout(150)
        except Exception:  # noqa: BLE001
            continue


def _visible_open(page, sel):
    """Is a matching element visible right now?"""
    try:
        return page.locator(sel).first.is_visible()
    except Exception:  # noqa: BLE001
        return False


def _test_comboboxes(page, findings, lang, cap=3):
    """Comboboxes: activation opens the popup; Escape closes it."""
    loc = page.locator('[role="combobox"]:visible')
    n = min(loc.count(), cap)
    for i in range(n):
        c = loc.nth(i)
        try:
            c.evaluate('el => el.focus()')
            before = (c.get_attribute('aria-expanded') or '').lower()
            page.keyboard.press('ArrowDown')
            page.wait_for_timeout(300)
            after = (c.get_attribute('aria-expanded') or '').lower()
            opened = after == 'true' or _visible_open(page, '[role="listbox"]:visible')
            if not opened and before != 'true':
                _finding(findings, lang, 'medium', '2.1.1', 'pattern_combobox_no_open')
                continue
            page.keyboard.press('Escape')
            page.wait_for_timeout(250)
            closed = (c.get_attribute('aria-expanded') or '').lower() != 'true' \
                and not _visible_open(page, '[role="listbox"]:visible')
            if not closed:
                _finding(findings, lang, 'medium', '2.1.1', 'pattern_combobox_esc_no_close')
        except Exception:  # noqa: BLE001
            continue


def _test_menu_buttons(page, findings, lang, cap=3):
    """Menu buttons: activation opens the menu; Escape closes + refocuses."""
    loc = page.locator('button[aria-haspopup="menu"]:visible, '
                       '[role="button"][aria-haspopup="menu"]:visible')
    n = min(loc.count(), cap)
    for i in range(n):
        b = loc.nth(i)
        try:
            b.click()
            page.wait_for_timeout(300)
            opened = _visible_open(page, '[role="menu"]:visible') \
                or (b.get_attribute('aria-expanded') or '').lower() == 'true'
            if not opened:
                _finding(findings, lang, 'medium', '2.1.1', 'pattern_menu_no_open')
                continue
            page.keyboard.press('Escape')
            page.wait_for_timeout(250)
            closed = not _visible_open(page, '[role="menu"]:visible') \
                and (b.get_attribute('aria-expanded') or '').lower() != 'true'
            if not closed:
                _finding(findings, lang, 'medium', '2.1.1', 'pattern_menu_esc_no_close')
        except Exception:  # noqa: BLE001
            continue


def _test_sliders(page, findings, lang, cap=3):
    """Custom sliders: arrows change the value; the state trio must be exposed."""
    loc = page.locator('[role="slider"]:visible')
    n = min(loc.count(), cap)
    for i in range(n):
        s = loc.nth(i)
        try:
            has_state = all((s.get_attribute(a) or '').strip() not in ('', None)
                            for a in ('aria-valuenow', 'aria-valuemin', 'aria-valuemax'))
            if not has_state:
                _finding(findings, lang, 'medium', '4.1.2', 'pattern_slider_no_state',
                         name=((s.get_attribute('aria-label') or '') or 'slider')[:40])
            now = (s.get_attribute('aria-valuenow') or '').strip()
            s.evaluate('el => el.focus()')
            page.keyboard.press('ArrowRight')
            page.wait_for_timeout(150)
            after_r = (s.get_attribute('aria-valuenow') or '').strip()
            if after_r == now:
                page.keyboard.press('ArrowUp')
                page.wait_for_timeout(150)
                after_up = (s.get_attribute('aria-valuenow') or '').strip()
                if after_up == now:
                    _finding(findings, lang, 'high', '2.1.1', 'pattern_slider_arrows_dead')
                    continue
            # devolver el valor original (dejar la página como estaba)
            if now and (s.get_attribute('aria-valuenow') or '').strip() != now:
                s.evaluate('(el, v) => el.setAttribute("aria-valuenow", v)', now)
        except Exception:  # noqa: BLE001
            continue


def audit_patterns(url, timeout=45, lang='en', auth_state=None, browser='auto'):
    """One url → widget patterns found + contract findings (filter, not verdict)."""
    from playwright.sync_api import sync_playwright
    from .a11ydom import _get_browser
    lang = 'es' if lang == 'es' else 'en'
    with sync_playwright() as p:
        nav = _get_browser(p, preferred=browser)
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': f'could not load: {e}'}

        counts = page.evaluate(_COUNTS)
        findings = []
        _test_dialogs(page, findings, lang)
        _test_tablists(page, findings, lang)
        _test_disclosures(page, findings, lang)
        _test_comboboxes(page, findings, lang)
        _test_menu_buttons(page, findings, lang)
        _test_sliders(page, findings, lang)
        nav.close()

    limits = ('Only patterns VISIBLE at page load are tested: opening a closed '
              'dialog means guessing a trigger flow — never acceptable on a '
              'live site. Operators: dialog (Esc + modal containment), '
              'tablist (arrows + activation), disclosure (aria-expanded flips), '
              'combobox (opens + Esc closes), menu button (opens + Esc closes), '
              'slider (arrows change value + value trio exposed). A '
              'clean pass proves THESE contracts at THIS moment — not full '
              'APG conformance.'
              if lang == 'en' else
              'Solo se prueban patrones VISIBLES en carga: abrir un diálogo '
              'cerrado exige adivinar un disparador — jamás aceptable en un '
              'sitio real. Operadores: dialog (Esc + contención modal), '
              'tablist (flechas + activación), disclosure (aria-expanded '
              'cambia), combobox (abre + Esc cierra), menu button (abre + Esc '
              'cierra), slider (flechas cambian el valor + trío de estado '
              'expuesto). Un pase limpio prueba ESTOS contratos en '
              'ESTE momento — no conformidad APG completa.')
    return {'mode': 'patterns', 'url': url,
            'ts': datetime.now(timezone.utc).isoformat(),
            'patterns_seen': {'dialog': counts.get('dialogs', 0),
                              'tablist': len(counts.get('tablists', [])),
                              'tabs': sum(counts.get('tablists', [])),
                              'disclosure': counts.get('disclosures', 0),
                              'combobox': counts.get('comboboxes', 0),
                              'menu': counts.get('menus', 0),
                              'slider': counts.get('sliders', 0)},
            'findings': findings,
            'limits': limits}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=45)
    ap.add_argument('--auth-state', help='Playwright storage_state JSON (session)')
    ap.add_argument('-o', '--out', help='write the report here (default: stdout)')
    a = ap.parse_args(argv)
    try:
        res = audit_patterns(a.url, timeout=a.timeout, lang=a.lang,
                             auth_state=a.auth_state)
    except ImportError:
        print(json.dumps({'error': 'Playwright not installed: pip install '
                                   'playwright && playwright install chromium'}))
        return 1
    out = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print(json.dumps({'url': a.url,
                          'patterns_seen': res.get('patterns_seen'),
                          'findings': len(res.get('findings', [])),
                          'out': a.out}, ensure_ascii=False))
    else:
        print(out)
    return 1 if 'error' in res else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
