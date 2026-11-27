#!/usr/bin/env python3
"""Generates the repo visuals using REAL tool output:
  docs/social-preview.png  (1280×640, for GitHub Settings → Social preview)
  docs/demo.gif            (animated terminal: audit → fix → verify, ~11 s)
  docs/blindfold.gif       (animated terminal: a blindfold journey → its verdict)
  docs/visuals.json        (counts the visuals were generated with; test_solido
                            compares them with server.TOOLS, so a stale GIF
                            turns the suite red)

Playwright renders HTML frames; Pillow assembles the GIF. The terminal is
cumulative (like a real one) and everything shown is genuine a11y output.
The blindfold walk is the record of a real run (JOURNEY_STEPS); its verdict
is not stored, a11yjourney.verdict() recomputes it on every run.
"""

import datetime
import json
import os
import sys
import tempfile
import textwrap

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from a11y_toolkit import server as _server
from a11y_toolkit.a11yaudit import audit_html
from a11y_toolkit.a11ybadge import badge
from a11y_toolkit.a11yjourney import verdict as journey_verdict
from a11y_toolkit.contrast import pair

ANCHO, ALTO = 1024, 640
COLORES = 64   # colores por fotograma en los GIF
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
sugerido = p['aa_suggestion']['color']
score_antes = informe['score']
summary = informe['summary']
fallos = [(h['criterion'], h['issue']) for h in informe['findings'][:3]]

DEMO_FIX = DEMO_HTML.replace('<img src="hero.png">', '<img src="hero.png" alt="Hero">') \
    .replace('color:#999999', f'color:{sugerido}') \
    .replace('<input type="email" name="correo">',
             '<input type="email" name="correo" autocomplete="email" aria-label="Email">') \
    .replace('class="mini"', 'class="mini" aria-label="OK"')
informe2 = audit_html(DEMO_FIX, 'https://demo.site', lang='en')
score_despues = informe2['score']
svg_insignia = badge(score_despues, date=datetime.date.today().isoformat(), lang='en')
print(f'real: score {score_antes} → {score_despues}, sugerido {sugerido}')

# ------------------------------------------------ pruebas a ciegas (ciegas) --
# Registro de una pasada REAL (27-nov-2026): la tarea se intentó sobre
# SIGNUP_DEMO (página de demostración hecha para fallar, servida en local),
# percibiendo SOLO el árbol de accesibilidad y actuando por nombre accesible y
# teclado, como manda el prompt blindfold-task. Cada «perceived» es lo que la
# instantánea de accesibilidad mostró en ese paso; una fricción se anota la
# primera vez que ocurre, no en cada reintento. El veredicto NO está guardado:
# verdict() lo recalcula en cada ejecución con las reglas vigentes.
SIGNUP_DEMO = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Acme Weekly</title>
<style>
body{margin:0;background:#f6f8fa;color:#14171a;font-family:system-ui,sans-serif}
.top{padding:18px 32px;border-bottom:1px solid #d8dee4;font-weight:700}
.card{max-width:460px;margin:48px auto;background:#fff;border:1px solid #d8dee4;border-radius:10px;padding:28px}
.brand{font-size:28px;margin:0 0 4px}
.kicker{color:#57606a;font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;margin-bottom:14px}
input{width:100%;padding:10px 12px;border:1px solid #8c959f;border-radius:6px;font-size:15px}
button{margin-top:12px;font-size:18px;padding:6px 14px}
.error{color:#cf222e;margin-top:10px}
</style>
</head>
<body>
<div class="top">Acme</div>
<div class="card">
<h1 class="brand">Acme Weekly</h1>
<div class="kicker">Latest issue</div>
<p>One email every Friday: what shipped in design systems, and why it matters.</p>
<form id="signup" novalidate>
<input type="email" name="email" placeholder="Your email">
<button type="submit">&#8594;</button>
</form>
</div>
<script>
document.getElementById('signup').addEventListener('submit', function (e) {
  e.preventDefault();
  var box = document.createElement('div');
  box.className = 'error';
  box.textContent = 'Please enter a valid email address.';
  this.appendChild(box);
});
</script>
</body>
</html>'''

JOURNEY_TASK = {'goal': 'Subscribe to the Acme Weekly newsletter', 'kind': 'sign-up'}
JOURNEY_URL = 'demo page authored to fail (SIGNUP_DEMO)'
JOURNEY_STEPS = [
    {'action': 'read',
     'perceived': 'heading "Acme Weekly" (level 1); no landmarks, every container is generic',
     'friction': [{'pattern': 'journey_landmark_missing'}]},
    {'action': 'type', 'target': 'textbox "Your email"',
     'perceived': 'no description, no required state in the tree',
     'friction': [{'pattern': 'journey_no_instruction'}]},
    {'action': 'click', 'target': 'button "→"',
     'perceived': 'its whole name is an arrow; after submit a generic node reports the error, '
                  'no alert, focus unmoved',
     'friction': [{'pattern': 'journey_unnamed_control'},
                  {'pattern': 'journey_error_silent'},
                  {'pattern': 'journey_status_silent'}]},
    {'action': 'type + click', 'target': 'textbox "Your email", button "→"',
     'perceived': 'valid-format address: same silent failure, a second identical error node'},
    {'action': 'type + Enter', 'target': 'textbox "Your email"',
     'perceived': 'same silent failure, a third identical error node'},
]
JOURNEY_OUTCOME = {
    'completed': False, 'gave_up': True, 'workaround_used': False,
    'notes': 'Three reasonable attempts (one malformed address, two valid-format addresses, '
             'the last one submitted with Enter). The tree only ever gained one more silent '
             'error node.',
}
journey = journey_verdict(JOURNEY_TASK, JOURNEY_STEPS, JOURNEY_OUTCOME, url=JOURNEY_URL)
assert 'error' not in journey, journey   # un registro inválido nunca llega al GIF


# --------------------------------------------------------------- estilos ----
def base(fuente=17):
    """Hoja del terminal. El GIF de pruebas a ciegas usa un punto menos para
    que quepan más líneas."""
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{ANCHO}px;height:{ALTO}px;background:#0d1117;overflow:hidden;
  font-family:'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace}}
#term{{padding:36px 44px;font-size:{fuente}px;line-height:1.6;color:#e6edf3;white-space:pre-wrap}}
.c{{color:{GRIS}}} .ok{{color:{VERDE}}} .bad{{color:{ROJO}}} .warn{{color:{AMAR}}}
.p{{color:{VERDE};font-weight:bold}}
</style></head><body><div id="term"></div></body></html>'''


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def recorta(t, n=48):
    """Corta un mensaje en el último espacio que cabe: los catálogos cambian
    de redacción y un corte a mitad de palabra parece un fallo."""
    return t if len(t) <= n else t[:n].rsplit(' ', 1)[0] + '…'


# --------------------------------------------------------------- terminal ----
def terminal(scroll=0, paso=7):
    """Terminal acumulativo: cada orden se teclea y su salida queda en pantalla.
    scroll > 0 = líneas visibles; lo más antiguo sube, como en una consola.
    paso = caracteres por fotograma mientras se teclea."""
    frames, hist = [], []

    def snap(lineas, hold):
        visible = lineas[-scroll:] if scroll else lineas
        frames.append((f'<div id="term">{chr(10).join(visible)}</div>', hold))

    def escribe(cmd, salida='', hold=1500, blanco_previo=False):
        if blanco_previo:
            hist.append('')
        base_previa = list(hist)
        for i in range(0, len(cmd) + 1, paso):
            snap(base_previa + [f'<span class="p">$</span> {esc(cmd[:i])}'], 55)
        hist.append(f'<span class="p">$</span> {esc(cmd)}')
        if salida:
            hist.extend(salida.split('\n'))
        snap(list(hist), hold)

    return frames, hist, snap, escribe


def demo_frames():
    """GIF de portada: registro del servidor MCP, auditoría, corrección de
    contraste y nueva auditoría. Todo es salida real calculada arriba."""
    frames, hist, snap, escribe = terminal()

    snap(['<span class="p">$</span>'], 500)
    escribe('claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp',
            f'<span class="ok">✓ a11y-toolkit registered</span>  '
            f'<span class="c">({len(_server.TOOLS)} tools · {len(_server._PROMPTS)} prompts)</span>',
            hold=1100)
    salida_audit = (f'<span class="warn">score: {score_antes}/100</span>   '
                    f'<span class="bad">high: {summary["high"]}</span>  '
                    f'medium: {summary["medium"]}  low: {summary["low"]}'
                    + ''.join(f'\n<span class="bad">✗</span> <span class="c">{esc(c)}</span>  {esc(recorta(t))}'
                              for c, t in fallos)
                    + '\n<span class="c">automation ≈ 1/3 of WCAG — filter, not verdict</span>')
    escribe('a11ytoolkit audit --url demo.site --lang en', salida_audit, hold=2400,
            blanco_previo=True)
    escribe('a11ytoolkit pair "#999999" "#ffffff"',
            f'ratio: <span class="bad">{p["ratio"]:.2f}:1 ✗ AA</span>  →  aa_suggestion: '
            f'<span class="ok">{sugerido} ✓</span>', hold=1800, blanco_previo=True)
    escribe('a11ytoolkit audit --url demo.site   # after the fix',
            f'<span class="ok">score: {score_despues}/100 ✓</span>   '
            f'<span class="c">regression watch: a11ytoolkit budget · a11ytoolkit diff</span>',
            hold=1600, blanco_previo=True)
    hist.append('')
    hist.append(svg_insignia.replace('\n', ' '))
    hist.append(f'\n<span class="ok">a11y-toolkit</span>  MIT · github.com/kinti/a11y-toolkit'
                f'\n<span class="c">uvx --from a11y-toolkit a11y-toolkit-mcp</span>')
    snap(list(hist), 3200)
    return frames


def blindfold_frames():
    """GIF de pruebas a ciegas: la tarea, lo que el árbol mostró en cada paso
    y el veredicto real. La pantalla desplaza: al final queda el veredicto."""
    frames, hist, snap, escribe = terminal(scroll=21, paso=12)

    escribe(f'blindfold-task "{JOURNEY_TASK["goal"]}" --url demo.page',
            '<span class="ok">✓ agent on it</span>\n'
            '  <span class="c">perceives: the accessibility tree only · '
            'acts: accessible name and keyboard</span>',
            hold=1600)

    por_paso = {}
    for f in journey['findings']:
        por_paso.setdefault(f['step'], []).append(f)
    hist.append('')
    for n, paso in enumerate(JOURNEY_STEPS, 1):
        bloque = [f'<span class="ok">{n} {esc(paso["action"].upper())}</span>'
                  + (f'   <span class="c">{esc(paso["target"])}</span>' if paso.get('target') else '')]
        bloque += [f'   <span class="c">{esc(parte)}</span>'
                   for parte in paso['perceived'].split('; ')]
        bloque += [f'   <span class="bad">✗ {f["criterion"]} {f["severity"]:<6}</span>  {esc(f["signal"])}'
                   for f in por_paso.get(n - 1, [])]
        hist.extend(bloque)
        snap(list(hist), 850)
    if journey['outcome']['gave_up']:
        intentos = sum(1 for s in JOURNEY_STEPS if 'click' in s['action'] or 'Enter' in s['action'])
        hist.append(f'<span class="warn">GAVE UP</span>   {intentos} reasonable attempts, no way forward')
        snap(list(hist), 1000)

    # el veredicto sale de una sola vez, como la salida real de la CLI
    orden = {'high': 0, 'medium': 1, 'low': 2}
    lista = sorted(journey['findings'], key=lambda f: (orden[f['severity']], f['step']))
    sumario = journey['summary']
    clase = {'pass': 'ok', 'partial': 'warn'}.get(journey['verdict'], 'bad')
    salida = [f'<span class="{clase}">verdict: {journey["verdict"]}</span>   '
              f'<span class="warn">score: {journey["score"]}/100</span>   '
              f'high: {sumario["high"]}  medium: {sumario["medium"]}  low: {sumario["low"]}',
              f'<span class="c">task: "{esc(JOURNEY_TASK["goal"])}" · '
              f'{"gave up" if journey["outcome"]["gave_up"] else "done"} after {journey["steps_count"]} steps</span>',
              '']
    for f in lista:
        salida.append(f'<span class="bad">✗ {f["criterion"]}  {f["severity"]:<6}</span> {esc(f["signal"])}')
        salida.append('   ' + esc(f['issue']))
        if f['severity'] == 'high':      # la corrección solo en las altas: caben
            salida += [f'<span class="c">{esc(linea)}</span>'
                       for linea in textwrap.wrap('→ ' + f['remediation'], width=95,
                                                  initial_indent='   ', subsequent_indent='   ')]
    escribe('python3 -m a11y_toolkit.a11yjourney friction.json', '\n'.join(salida),
            hold=1700, blanco_previo=True)

    color = {'pass': '#238636', 'partial': '#9e6a03'}.get(journey['verdict'], '#b62324')
    criterios = {f['criterion'] for f in lista}
    hist.append('')
    hist.append(f'<span style="background:{color};color:#fff;border-radius:4px;padding:1px 8px">'
                f'{journey["verdict"]} · {journey["score"]}/100</span>  '
                f'<span class="c">{len(lista)} findings on {len(criterios)} criteria · '
                f'usability evidence, never conformance</span>')
    hist.append('<span class="ok">a11y-toolkit</span>  blindfold testing · MIT · '
                'github.com/kinti/a11y-toolkit')
    hist.append('<span class="c">the agent tries the task without seeing the page; '
                'the toolkit prices the walk</span>')
    snap(list(hist), 3600)
    return frames


def guarda_gif(page, tmp, hoja, frames, salida):
    """Renderiza cada fotograma con Playwright y los une con Pillow."""
    from PIL import Image
    carpeta = tempfile.mkdtemp(dir=tmp)
    rutas = []
    for i, (cuerpo, _hold) in enumerate(frames):
        page.set_content(hoja.replace('<div id="term"></div>', cuerpo))
        page.wait_for_timeout(40)
        ruta = os.path.join(carpeta, f'{i:03d}.png')
        page.screenshot(path=ruta)
        rutas.append(ruta)

    # 64 colores por fotograma: el texto conserva el antialias y el GIF pesa
    # bastante menos que con la paleta por defecto de 256
    imgs = [Image.open(r).convert('RGB').resize((ANCHO, ALTO), Image.LANCZOS)
            .quantize(colors=COLORES, method=Image.Quantize.MEDIANCUT)
            for r in rutas]
    duraciones = [_h for _c, _h in frames]
    imgs[0].save(salida, save_all=True, append_images=imgs[1:],
                 duration=duraciones, loop=0, optimize=True)
    print(f'GIF: {salida} — {len(imgs)} frames')


def main():
    from playwright.sync_api import sync_playwright

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
      <div class="chip"><b>{len(_server.TOOLS)}</b> MCP tools</div>
      <div class="chip"><b>{len(_server._PROMPTS)}</b> prompts</div>
      <div class="chip">rendered audit</div>
      <div class="chip">blindfold testing</div>
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

    # --------- 2. GIFs: terminal acumulativo ---------
    with tempfile.TemporaryDirectory() as tmp:
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            # la tarjeta social mide 1280 de ancho: con el viewport del GIF
            # (1024) la captura perdía el cuarto derecho
            social = nav.new_page(viewport={'width': 1280, 'height': 640},
                                   device_scale_factor=2)
            social.set_content(social_html)
            social.wait_for_timeout(120)
            social.screenshot(path=os.path.join(AQUI, 'social-preview.png'))
            social.close()
            page = nav.new_page(viewport={'width': ANCHO, 'height': ALTO},
                                device_scale_factor=2)
            guarda_gif(page, tmp, base(), demo_frames(), os.path.join(AQUI, 'demo.gif'))
            guarda_gif(page, tmp, base(16), blindfold_frames(), os.path.join(AQUI, 'blindfold.gif'))
            nav.close()
    print('social:', os.path.join(AQUI, 'social-preview.png'))

    # el conteo va dentro de los píxeles del GIF: este rastro deja que
    # test_solido exija `make visual` cuando cambia el número de tools
    with open(os.path.join(AQUI, 'visuals.json'), 'w', encoding='utf-8') as f:
        json.dump({'tools': len(_server.TOOLS), 'prompts': len(_server._PROMPTS)},
                  f, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()
