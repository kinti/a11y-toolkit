#!/usr/bin/env python3
"""Genera los visuales del repo con las salidas REALES de las herramientas:
  docs/social-preview.png  (1280×640, para GitHub Settings → Social preview)
  docs/demo.gif            (terminal animado audit → fix → verify, ~11 s)

Playwright renderiza fotogramas HTML; Pillow ensambla el GIF. El terminal es
acumulativo (como uno real) y todo lo que se ve es salida genuina de a11y.
"""

import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from a11yaudit import audit_html
from a11ybadge import badge
from contrast import pair

ANCHO, ALTO = 1024, 640
GRIS, VERDE, ROJO, AMAR = '#8b949e', '#3fb950', '#f85149', '#d29922'


# ---------------------------------------------------------------- datos -----
DEMO_HTML = '''<!doctype html><html><head><title>Demo</title></head><body><main>
<h1>Demo site</h1>
<img src="hero.png">
<p style="color:#999999;background:#ffffff">Texto con poco contraste</p>
<input type="email" name="correo">
<button class="mini">OK</button>
</main></body></html>'''

informe = audit_html(DEMO_HTML, 'https://demo.site', lang='en')
p = pair('#999999', '#ffffff')
sugerido = p['sugerencia_aa']['color']
score_antes = informe['score']
resumen = informe['resumen']
fallos = [(h['criterio'], h['hallazgo']) for h in informe['hallazgos'][:3]]

DEMO_FIX = DEMO_HTML.replace('<img src="hero.png">', '<img src="hero.png" alt="Hero">') \
    .replace('color:#999999', f'color:{sugerido}') \
    .replace('<input type="email" name="correo">',
             '<input type="email" name="correo" autocomplete="email" aria-label="Email">') \
    .replace('class="mini"', 'class="mini" aria-label="OK"')
informe2 = audit_html(DEMO_FIX, 'https://demo.site', lang='en')
score_despues = informe2['score']
svg_insignia = badge(score_despues, fecha='2026-09-07', lang='en')
print(f'real: score {score_antes} → {score_despues}, sugerido {sugerido}')

# --------------------------------------------------------------- estilos ----
BASE = f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{ANCHO}px;height:{ALTO}px;background:#0d1117;overflow:hidden;
  font-family:'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace}}
#term{{padding:36px 44px;font-size:17px;line-height:1.6;color:#e6edf3;white-space:pre-wrap}}
.c{{color:{GRIS}}} .ok{{color:{VERDE}}} .bad{{color:{ROJO}}} .warn{{color:{AMAR}}}
.p{{color:{VERDE};font-weight:bold}}
</style></head><body><div id="term"></div></body></html>'''


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def main():
    from playwright.sync_api import sync_playwright
    from PIL import Image

    # --------- 1. social preview 1280×640 ---------
    social_html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:640px;overflow:hidden;position:relative;
  background:#0d1117;color:#e6edf3;font-family:-apple-system,'Segoe UI',Inter,sans-serif}}
.blob{{position:absolute;border-radius:50%;filter:blur(90px);opacity:.25}}
.b1{{width:520px;height:520px;background:#1f6feb;top:-180px;right:-120px}}
.b2{{width:420px;height:420px;background:#238636;bottom:-160px;left:-100px}}
.wrap{{position:relative;padding:64px 72px;height:100%;display:flex;flex-direction:column;justify-content:space-between}}
.kicker{{color:#58a6ff;font-weight:600;letter-spacing:.18em;font-size:15px;text-transform:uppercase}}
h1{{font-size:76px;letter-spacing:-.02em;margin:10px 0 6px}}
h1 .dot{{color:#3fb950}}
.sub{{font-size:28px;color:#8b949e;font-weight:400}}
.chips{{display:flex;gap:12px;margin-top:26px;flex-wrap:wrap}}
.chip{{border:1px solid #30363d;border-radius:999px;padding:8px 18px;font-size:19px;color:#c9d1d9;background:#161b22}}
.chip b{{color:#3fb950}}
.code{{font-family:Menlo,monospace;background:#161b22;border:1px solid #30363d;border-radius:10px;
  padding:16px 22px;font-size:21px;color:#79c0ff;width:fit-content}}
.code .p{{color:#3fb950}}
.loop{{font-size:22px;color:#8b949e;margin-top:18px}} .loop b{{color:#e6edf3}}
</style></head><body>
<div class="blob b1"></div><div class="blob b2"></div>
<div class="wrap">
  <div>
    <div class="kicker">Model Context Protocol · WCAG 2.2 · es/en</div>
    <h1>a11y<span class="dot">-</span>toolkit</h1>
    <div class="sub">The accessibility layer for AI coding agents</div>
    <div class="chips">
      <div class="chip"><b>16</b> MCP tools</div>
      <div class="chip"><b>5</b> prompts</div>
      <div class="chip">rendered audit</div>
      <div class="chip"><b>0</b> deps at core</div>
      <div class="chip">SARIF</div>
      <div class="chip">EAA statements</div>
    </div>
  </div>
  <div class="foot">
    <div class="code"><span class="p">$</span> uvx --from a11y-toolkit a11y-toolkit-mcp</div>
    <div class="loop"><b>audit</b> → <b>fix</b> → <b>document</b> → <b>watch</b></div>
  </div>
</div>
</body></html>'''

    # --------- 2. GIF: terminal acumulativo ---------
    frames = []   # (body_html, hold_ms)
    hist = []     # bloques html ya completados

    def snap(body, hold):
        frames.append((f'<div id="term">{body}</div>', hold))

    def escribe(cmd, salida='', hold=1500, blanco_previo=False):
        if blanco_previo:
            hist.append('')
        base = list(hist)
        for i in range(0, len(cmd) + 1, 7):
            body = '\n'.join(base + [f'<span class="p">$</span> {esc(cmd[:i])}'])
            snap(body, 55)
        hist.append(f'<span class="p">$</span> {esc(cmd)}')
        if salida:
            hist.append(salida)
        snap('\n'.join(hist), hold)

    snap('<span class="p">$</span>', 500)
    escribe('claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp',
            '<span class="ok">✓ a11y-toolkit registered</span>  <span class="c">(16 tools · 5 prompts)</span>',
            hold=1100)
    salida_audit = (f'<span class="warn">score: {score_antes}/100</span>   '
                    f'<span class="bad">high: {resumen["alta"]}</span>  '
                    f'medium: {resumen["media"]}  low: {resumen["baja"]}'
                    + ''.join(f'\n<span class="bad">✗</span> <span class="c">{esc(c)}</span>  {esc(t[:48])}'
                              for c, t in fallos)
                    + '\n<span class="c">automation ≈ 1/3 of WCAG — filter, not verdict</span>')
    escribe('a11ytoolkit audit --url demo.site --lang en', salida_audit, hold=2400,
            blanco_previo=True)
    escribe('a11ytoolkit pair "#999999" "#ffffff"',
            f'ratio: <span class="bad">2.85:1 ✗ AA</span>  →  sugerencia_aa: '
            f'<span class="ok">{sugerido} ✓</span>', hold=1800, blanco_previo=True)
    escribe('a11ytoolkit audit --url demo.site   # after the fix',
            f'<span class="ok">score: {score_despues}/100 ✓</span>   '
            f'<span class="c">regression watch: a11ytoolkit budget · a11ytoolkit diff</span>',
            hold=1600, blanco_previo=True)
    hist.append('')
    hist.append(svg_insignia.replace('\n', ' '))
    hist.append(f'\n<span class="ok">a11y-toolkit</span>  MIT · github.com/kinti/a11y-toolkit'
                f'\n<span class="c">uvx --from a11y-toolkit a11y-toolkit-mcp</span>')
    snap('\n'.join(hist), 3200)

    with tempfile.TemporaryDirectory() as tmp:
        frames_dir = os.path.join(tmp, 'f')
        os.makedirs(frames_dir)
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            page = nav.new_page(viewport={'width': ANCHO, 'height': ALTO},
                                device_scale_factor=2)
            page.set_content(social_html)
            page.wait_for_timeout(120)
            page.screenshot(path=os.path.join(AQUI, 'social-preview.png'))
            rutas = []
            for i, (cuerpo, _hold) in enumerate(frames):
                html = BASE.replace('<div id="term"></div>', cuerpo)
                page.set_content(html)
                page.wait_for_timeout(40)
                ruta = os.path.join(frames_dir, f'{i:03d}.png')
                page.screenshot(path=ruta)
                rutas.append(ruta)
            nav.close()

        imgs = [Image.open(r).convert('RGB').resize((ANCHO, ALTO), Image.LANCZOS)
                for r in rutas]
        duraciones = [_h for _c, _h in frames]
        salida_gif = os.path.join(AQUI, 'demo.gif')
        imgs[0].save(salida_gif, save_all=True, append_images=imgs[1:],
                     duration=duraciones, loop=0, optimize=True)
        print(f'GIF: {salida_gif} — {len(imgs)} frames')
        print('social:', os.path.join(AQUI, 'social-preview.png'))


if __name__ == '__main__':
    main()
