#!/usr/bin/env python3
"""Deterministic autofix — ONLY provably safe corrections.

The industry lesson (overlay vendors, the accessiBe FTC fine): fixing
accessibility by injecting guesses ends in fines. This module does the
opposite: a short closed list of transformations where the correct fix is
UNIQUE and verifiable, and for everything else an honest "not touched —
here is what it would take".

Transformations (closed, auditable list):
  1. viewport        — removes user-scalable=no/0 and maximum-scale<2 (1.4.4).
  2. autocomplete    — adds the deterministic token to inputs that require it
                       (1.3.5): type=email→email, tel→tel, url→url, and name/id
                       matching the personal-data pattern (name, postal-code…).
  3. <html> lang     — ONLY if missing and the caller provides --lang.
  4. empty <title>   — ONLY if the caller provides --title.

Everything else (alt, contrast, accessible names…) requires human or agent
judgment: listed under "no_aplicados" with the remediation.

CLI:
  a11yfix.py --file page.html [--lang es] [--title "T"] [-o fixed.html]
"""

import argparse
import html as _html
import json
import re
import sys

from .a11yaudit import audit_html, _PERSONAL_DATA

from . import a11yi18n
# token autocomplete por type de input (determinista por especificación)
_TOKEN_BY_TYPE = {'email': 'email', 'tel': 'tel', 'url': 'url'}
# token por pista de name/id (mismas pistas que usa el auditor 1.3.5)
_TOKEN_BY_HINT = [
    (re.compile(r'postal|zip|cp\b', re.I), 'postal-code'),
    (re.compile(r'street|direccion|address|calle', re.I), 'street-address'),
    (re.compile(r'ciudad|city', re.I), 'address-level2'),
    (re.compile(r'country|pais', re.I), 'country-name'),
    (re.compile(r'organi[sz]ation|company|empresa', re.I), 'organization'),
    (re.compile(r'phone|telefono|tel\b', re.I), 'tel'),
    (re.compile(r'email|correo', re.I), 'email'),
    (re.compile(r'(?:^|[\W_])(?:full)?name|nombre', re.I), 'name'),
]

_RE_FORM = re.compile(r'<form\b[^>]*>', re.I)
_RE_TAG_Q = r'(?:[^>\"\']|\"[^\"]*\"|\'[^\']*\')*'
_RE_FIELD = re.compile(r'<input' + _RE_TAG_Q + r'>|<(select|textarea)' + _RE_TAG_Q + r'>.*?</\1\s*>', re.I | re.S)
_RE_SCRIPTS = re.compile(r'<script\b.*?</script>', re.S | re.I)
_RE_FORM_BLOCK = re.compile(r'<form\b.*?</form>', re.S | re.I)

_PHRASES = a11yi18n.pair('fix')  # locales/<lang>.json — community-editable

_JS_PHRASES = """<script>
(function(){
  var F = {req:%(req)s,email:%(email)s,url:%(url)s,num:%(num)s,between:%(between)s,short:%(short)s,pattern:%(pattern)s};
  function sug(el){var v=el.validity;if(!v)return '';
    if(v.valueMissing)return F.req;
    if(v.typeMismatch){if(el.type==='email')return F.email;if(el.type==='url')return F.url;if(el.type==='number')return F.num;}
    if(v.rangeUnderflow||v.rangeOverflow)return F.between.replace('%%a',el.min).replace('%%b',el.max);
    if(v.tooShort)return F.short.replace('%%n',el.minLength);
    if(v.patternMismatch)return el.pattern?F.pattern.replace('%%p',el.pattern):F.req;
    return '';}
  document.querySelectorAll('form[data-a11yfx]').forEach(function(f){
    f.noValidate=true;
    f.addEventListener('submit',function(ev){
      var first=null;
      f.querySelectorAll('input,select,textarea').forEach(function(el){
        var id=el.getAttribute('data-a11yfx-err'),msg=id?document.getElementById(id):null;
        if(!el.checkValidity()){var t=sug(el)||el.validationMessage||'';
          el.setAttribute('aria-invalid','true');
          if(msg){msg.hidden=false;msg.textContent=t;}
          if(!first)first=el;
        }else{el.removeAttribute('aria-invalid');if(msg){msg.hidden=true;msg.textContent='';}}
      });
      if(first){ev.preventDefault();first.focus();}
    });
    f.addEventListener('input',function(ev){var el=ev.target;if(!el.getAttribute)return;
      var id=el.getAttribute('data-a11yfx-err');if(!id)return;
      if(el.checkValidity()){el.removeAttribute('aria-invalid');var m=document.getElementById(id);
        if(m){m.hidden=true;m.textContent='';}}
    });
  });
})();
</script>"""

_RE_INPUT = re.compile(r'<input' + _RE_TAG_Q + r'>', re.I)
_RE_VIEWPORT = re.compile(r'(<meta\s[^>]*name=["\']viewport["\'][^>]*content=["\'])([^"\']*)(["\'])', re.I)
_RE_HTML_TAG = re.compile(r'<html\b([^>]*)>', re.I)
_RE_TITLE = re.compile(r'<title>\s*</title>', re.I)


def _attrs(tag_html):
    out = {}
    for m in re.finditer(
            r'([\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag_html):
        dbl, sgl, bare = m.group(2), m.group(3), m.group(4)
        out[m.group(1)] = dbl if dbl is not None else (sgl if sgl is not None else bare)
    return out


def _clean_viewport(content):
    parts = [p.strip() for p in content.split(',') if p.strip()]
    removed = []
    clean = []
    for p in parts:
        if re.match(r'user-scalable\s*=\s*(no|0)', p, re.I):
            removed.append(p)
            continue
        m = re.match(r'maximum-scale\s*=\s*([\d.]+)', p, re.I)
        if m and float(m.group(1)) < 2:
            removed.append(p)
            continue
        clean.append(p)
    return ', '.join(clean), removed


def autofix(html_text, lang=None, title=None, url='(html)', form_errors=True):
    """Aplica los arreglos seguros. Devuelve fixed_html + aplicados + no_aplicados."""
    applied = []
    fixed = html_text

    # 0. máscara REAL: el contenido de script/style/textarea y los comentarios
    #    no son marcado — ninguna regex de transformación debe verlo. Sin este
    #    paso, el "no toco scripts" era falso (revisión externa, ronda 2).
    _masks = []

    def _mask(text):
        def _pon(m):
            tok = '\x00A11YFXMASK%d\x00' % len(_masks)
            _masks.append((tok, m.group(0)))
            return tok
        text = re.sub(r'<script\b[^>]*>.*?</script\s*>', _pon, text, flags=re.I | re.S)
        text = re.sub(r'<style\b[^>]*>.*?</style\s*>', _pon, text, flags=re.I | re.S)
        # textarea NO se enmascara: la capa de error se inserta tras su cierre
        # (5.2.1) y el contenido queda intacto; ocultarlo quitaría el 3.3.1
        text = re.sub(r'<!--.*?-->', _pon, text, flags=re.S)
        return text

    def _unmask(text):
        for tok, original in _masks:
            text = text.replace(tok, original)
        return text

    fixed = _mask(fixed)

    # 1. viewport: zoom sin bloqueos (1.4.4)
    m = _RE_VIEWPORT.search(fixed)
    if m and (re.search(r'user-scalable\s*=\s*(no|0)', m.group(2), re.I)
              or re.search(r'maximum-scale\s*=\s*([\d.]+)', m.group(2), re.I)):
        clean, removed = _clean_viewport(m.group(2))
        if clean:
            fixed = fixed[:m.start()] + m.group(1) + clean + m.group(3) + fixed[m.end():]
        else:
            # eliminar el meta COMPLETO: escanear el final de etiqueta
            # respetando comillas (un `>` dentro de value= no cierra el tag)
            end = m.end()
            q = None
            while end < len(fixed):
                ch = fixed[end]
                if q:
                    if ch == q:
                        q = None
                elif ch in ('"', "'"):
                    q = ch
                elif ch == '>':
                    break
                end += 1
            fixed = fixed[:m.start()] + (fixed[end + 1:] if end < len(fixed) else '')
        applied.append({'signal': 'zoom_no',
                          'fix': f'viewport without {", ".join(removed)} (1.4.4: zoom no longer blocked)'})

    # 2. autocomplete determinista (1.3.5)
    n_ac = 0

    def _input_fix(mtag):
        nonlocal n_ac
        tag = mtag.group(0)
        if 'autocomplete' in tag.lower():
            return tag
        a = _attrs(tag)
        kind = (a.get('type') or 'text').lower()
        token = _TOKEN_BY_TYPE.get(kind)
        if not token:
            hint = (a.get('name') or '') + ' ' + (a.get('id') or '')
            if kind in ('search', 'password'):
                return tag
            for rx, tok in _TOKEN_BY_HINT:
                if rx.search(hint):
                    token = tok
                    break
        if not token:
            return tag
        n_ac += 1
        return tag[:-1].rstrip() + f' autocomplete="{token}">'
    fixed = _RE_INPUT.sub(_input_fix, fixed)
    if n_ac:
        applied.append({'signal': 'autocomplete',
                          'fix': f'{n_ac} inputs with their autocomplete token (1.3.5)'})

    # 3. lang de <html> (solo si falta y lo dan); BCP-47 validado y escapado:
    #    este toolkit ESCRIBE HTML, no puede ser vector de inyección
    if lang and re.fullmatch(r'[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*', lang.strip()):
        m = _RE_HTML_TAG.search(fixed)
        if m and 'lang=' not in m.group(1).lower():
            fixed = fixed[:m.start()] + f'<html lang="{_html.escape(lang.strip())}"' + m.group(1) + '>' + fixed[m.end():]
            applied.append({'signal': 'lang_missing',
                              'fix': f'<html lang="{lang.strip()}"> added (3.1.1)'})

    # 4. title (solo si vacío y lo dan); escapado por la misma razón
    if title and _RE_TITLE.search(fixed):
        fixed = _RE_TITLE.sub(lambda _m: f'<title>{_html.escape(title)}</title>', fixed, count=1)
        applied.append({'signal': 'title_missing', 'fix': '<title> added (2.4.2)'})

    # 4b. form errors: accessible error layer (3.3.1 + 3.3.3 from attributes)
    if form_errors and 'a11yfx' not in fixed:
        scripts = _RE_SCRIPTS.findall(fixed)
        if not any(('aria-invalid' in s or 'setCustomValidity' in s) for s in scripts):
            import json as _json
            state = {'forms': 0, 'fields': 0}

            def _input_type(tag):
                m = re.search(r'type=["\']([\w-]+)', tag, re.I)
                return m.group(1).lower() if m else ''

            def _validable(tag):
                kind = _input_type(tag)
                if re.search(r'\b(required|pattern|minlength)\b|\bmin\s*=', tag, re.I):
                    return True
                return kind in ('email', 'url', 'number', 'tel', 'date', 'time',
                                'datetime-local', 'month', 'week')

            def _process_field(elem):
                if 'data-a11yfx-err' in elem or not _validable(elem):
                    return elem
                state['fields'] += 1
                fid = "a11yfx-e-%d-%d" % (state['forms'], state['fields'])
                opening = re.match(r'<[a-zA-Z]+(?:[^>"\']|"[^"]*"|\'[^\']*\')*>', elem).group(0)
                mdb = re.search(r'aria-describedby=["\']([^"\']*)["\']', opening, re.I)
                if mdb:  # merge, preserving the existing reference
                    new = 'aria-describedby="%s %s"' % (mdb.group(1), fid)
                    opening = opening[:mdb.start()] + new + opening[mdb.end():]
                    opening = opening[:-1] + ' data-a11yfx-err="%s">' % fid
                else:
                    opening = opening[:-1] + ' data-a11yfx-err="%s" aria-describedby="%s">' % (fid, fid)
                layer = '\n<p class="a11yfx-err" id="%s" hidden></p>' % fid
                if opening.lower().startswith(('<textarea', '<select')):
                    # content-bearing element: the layer goes AFTER the close,
                    # never inside (inside would become its value — a real
                    # data-corruption regression, caught in external review)
                    return elem.replace(re.match(r'<[^>]*>', elem).group(0), opening, 1) + layer
                return opening + layer

            def _own_handling(atrs_form):
                m = re.search(r'onsubmit=["\']([^"\']*)', atrs_form, re.I)
                if not m:
                    return False
                body = m.group(1).strip().lower()
                # a pure navigation guard is NOT error handling — common fixture/SPA pattern
                return body not in ('return false', 'return!1', 'return !1')

            def _process_block(mb):
                block = mb.group(0)
                opening = re.match(r'<form\b[^>]*>', block, re.I).group(0)
                if 'data-a11yfx' in opening or _own_handling(opening):
                    return block  # custom error handling present: never fight it
                state['forms'] += 1
                rest = block[len(opening):]
                rest = _RE_FIELD.sub(lambda mc: _process_field(mc.group(0)), rest)
                return opening[:-1] + ' data-a11yfx>' + rest

            fixed = _RE_FORM_BLOCK.sub(_process_block, fixed)
            if state['fields']:
                fr = _PHRASES.get(lang, _PHRASES['en'])
                js = _JS_PHRASES % {k: _json.dumps(v) for k, v in fr.items()}
                fixed = fixed.replace('</body>', js + '\n</body>', 1)
                applied.append({'signal': 'form_error_missing',
                                  'fix': f"accessible error layer on {state['forms']} form(s), "
                                           f"{state['fields']} field(s) — 3.3.1 identification + "
                                           f"3.3.3 attribute-derived suggestions"})

    # 5. lo que NO se toca — honestidad operativa
    report = audit_html(html_text, url, lang='en')
    do_not_touch = {
        'img_no_alt': 'we cannot know if the image is decorative: alt="" vs descriptive is a human call',
        'ctrl_name': 'the accessible name requires knowing what the control does',
        'field_label': 'the label text is dictated by the content',
        'contrast_fail': 'picking the new color is a design decision (use a11y_suggest_color)',
        'target_small': 'needs a layout redesign',
        'list_structure': 'rebuilding the markup requires understanding the structure',
    }
    already = {a['signal'] for a in applied}
    not_applied = []
    seen = set()
    for h in report.get('findings', []):
        signal = h['signal']
        if signal in do_not_touch and signal not in seen and signal not in already:
            seen.add(signal)
            not_applied.append({'signal': signal, 'criterion': h['criterion'],
                                 'why_not': do_not_touch[signal],
                                 'remediation': h['remediation']})

    fixed = _unmask(fixed)
    return {'fixed_html': fixed, 'applied': applied, 'not_applied': not_applied}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--file', required=True)
    ap.add_argument('--lang', choices=['es', 'en', 'pt', 'fr', 'de', 'it', 'gl', 'ca', 'eu'])
    ap.add_argument('--title')
    ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    with open(a.file, encoding='utf-8', errors='replace') as f:
        html_text = f.read()
    res = autofix(html_text, lang=a.lang, title=a.title, url=a.file)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(res['fixed_html'])
        print(json.dumps({'file': a.out, 'applied': res['applied'],
                          'not_applied': res['not_applied']}, ensure_ascii=False, indent=1))
    else:
        print(res['fixed_html'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
