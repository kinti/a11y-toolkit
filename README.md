# a11y-toolkit MCP

Suite de accesibilidad **WCAG 2.2** como servidor MCP (Model Context Protocol)
para agentes de IA — y como CLI. **Cero dependencias** en el núcleo; el cálculo
es local y exacto (luminancia relativa oficial de la especificación).

> **English below** · Herramientas en español orientadas a WCAG 2.2, RD 1112/2018
> y Ley 11/2023 (European Accessibility Act).

## Herramientas (5)

| Herramienta MCP | Qué hace |
|---|---|
| `a11y_contrast_pair` | Ratio de contraste exacto + veredictos por criterio **1.4.3** (AA), **1.4.6** (AAA) y **1.4.11** (no textual). Si falla AA, sugiere el color accesible más cercano. |
| `a11y_contrast_image` | **Texto sobre imagen**: muestrea píxel a píxel el fondo real tras el texto → ratio peor/mediana/p95 y % de área que pasa AA. Lo que ningún verificador de pares hace. |
| `a11y_suggest_color` | Color más cercano a uno dado que alcanza el ratio objetivo. |
| `a11y_generate_declaration` | **Declaración de Accesibilidad** legal en HTML: art. 10 del RD 1112/2018 (sector público) o variante Ley 11/2023/EAA (empresas). |
| `a11y_aria_live_snippet` | Código del monitor de anuncios `aria-live` (inyectable como bookmarklet o `page.evaluate`): registra hora, cortesía, rol y texto. |

Además, en el mismo repo (CLI, no MCP):
- **`declaracion.py`** — generador de declaraciones por línea de comandos.
- **`a11ydiff.py`** — diff de accesibilidad entre builds (snapshots con Playwright: interactivos + nombres accesibles + orden de foco real).

## Instalación como MCP

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "python3",
      "args": ["/ruta/al/repo/server.py"]
    }
  }
}
```

O con [uv](https://docs.astral.sh/uv/) sin clonar:

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/kinti/a11y-toolkit", "a11y-toolkit-mcp"]
    }
  }
}
```

## CLI

```bash
python3 contrast.py pair "#1f2328" "#fbfaf7"
python3 contrast.py image hero.jpg --text "#ffffff" --region 120,40,420,90 --sample 4

python3 declaracion.py --entidad "Nome" --url "https://…" --estado parcial \
  --no-accesible "Mapa sin alternativa textual" --feedback "a@b.gal" --marco eaa --output decl.html

python3 a11ydiff.py snapshot https://miweb --out antes.json   # requiere: pip install playwright && playwright install chromium
python3 a11ydiff.py diff antes.json despues.json

python3 test_contrast.py && python3 test_mcp.py               # tests
```

## Cómo interpretar el modo imagen

- `ratio_peor` — la zona más hostil de la caja del texto.
- `area_pasa_aa_texto_normal_4_5` — % de superficie segura. **Si < 100% y el
  texto cae ahí: velo/overlay, recorte o mover el texto.**
- Para localizar la zona hostil: divide la imagen en cuadrantes con `--region`.

## Seguridad y alcance

Herramienta **local**: se ejecuta en tu máquina con tu usuario. Los argumentos
`path` (imagen) y `output_path` (guardar declaración) leen/escriben rutas
locales — úsalo en clientes MCP de confianza (los tuyos). Nada sale a la red.

## Notas técnicas

- Decodificación de imágenes: Pillow si está disponible; si no, `sips` (macOS);
  PPM siempre (por eso los tests de CI no necesitan dependencias).
- El monitor `aria-live` lleva una lección de diseño documentada en su código:
  el panel NO es una región viva y se excluye a sí mismo del observador — un
  panel `role="log"` casaría con el propio selector y crearía un bucle
  infinito de auto-observación. (Lo sabemos porque nos pasó.)
- Versión web para humanos (misma matemática):
  [jquin.net/lab](https://jquin.net/lab/) — contraste (pares + imagen),
  generador de declaraciones, monitor aria-live y diff entre builds.

## English

An MCP server + CLI for **WCAG 2.2 accessibility work**, in Spanish (legal
output targets Spanish regulation: RD 1112/2018 and Ley 11/2023 / European
Accessibility Act). Five tools: color-pair contrast with per-criterion
verdicts, **text-over-image pixel sampling** (worst/median ratio, % of area
passing AA), nearest passing-color suggestion, legal accessibility-declaration
HTML generator, and an aria-live announcement monitor snippet. Zero-dependency
core (Pillow optional; `sips` on macOS; PPM always). Local-only: nothing is
sent over the network. MIT license. Web versions: [jquin.net/lab](https://jquin.net/lab/).

## Autor

**Jesús Quintana Fernández** ([jquin.net](https://jquin.net/)) — consultor de
SEO técnico, GEO y accesibilidad web desde 2003. MIT © 2026.
