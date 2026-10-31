# a11y-toolkit — la capa de accesibilidad para agentes de código con IA

> WCAG 2.2 para tu agente de código — auditar, corregir, documentar y vigilar.
> Cero dependencias, salida es/en.

**English** · [Español](README.es.md)

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![npm](https://img.shields.io/npm/v/%40kinti%2Fa11y-toolkit)](https://www.npmjs.com/package/@kinti/a11y-toolkit)
[![Downloads](https://img.shields.io/pypi/dm/a11y-toolkit)](https://pypistats.org/packages/a11y-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink)](https://github.com/sponsors/kinti)
[![Supply chain](https://img.shields.io/badge/supply%20chain-audited%20by%20Socket-blueviolet)](https://socket.dev/pypi/package/a11y-toolkit/overview)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/kinti/a11y-toolkit/badge)](https://scorecard.dev/viewer/?uri=github.com/kinti/a11y-toolkit)
[![ACT Rules](https://img.shields.io/badge/ACT%20Rules-20%2F20%20consistent-brightgreen)](https://github.com/kinti/a11y-toolkit/blob/main/docs/act-report-summary.md)
[![Releases](https://img.shields.io/badge/releases-OIDC%20provenance%20signed-blue)](.github/workflows/publish.yml)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-blue)](pyproject.toml)
[![Python Versions](https://img.shields.io/pypi/pyversions/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![GitHub Release](https://img.shields.io/github/v/release/kinti/a11y-toolkit)](https://github.com/kinti/a11y-toolkit/releases)

34 herramientas MCP, 6 prompts y una skill que cubren todo el ciclo WCAG 2.2:
auditar, corregir, documentar, vigilar y entregar — y ahora también pruebas de
usabilidad «a ciegas», donde el agente intenta tareas reales percibiendo solo lo
que expone un lector de pantalla. 51 de los 55 criterios A/AA llevan señales
automatizadas (93%), cada hallazgo viaja con una remediación concreta que tu
agente puede aplicar, y las herramientas renderizadas corren en el navegador
que tengas — Chromium, Firefox, WebKit, Chrome o Edge.

El Acto Europeo de Accesibilidad está en vigor desde junio de 2025, las demandas
ADA siguen llegando, y los agentes de IA escriben ya la mayor parte de la web.
Un escaneo no es una defensa: **la máquina encuentra, la persona firma**.

<p align="center">
  <a href="https://madebyhuman.iamjarl.com"><img src="https://madebyhuman.iamjarl.com/badges/loop-white.svg" alt="Human in the Loop — las personas guían y curan el proceso; cada artefacto de conformidad lo firma una persona" height="34"></a>
</p>

<p align="center">
  <img src="docs/demo.gif" alt="a11y-toolkit en acción: auditoría (nota 64), color que aprueba más cercano, re-auditoría (94) — salida real de la herramienta" width="720">
</p>

## Arranque rápido

```bash
# MCP — una línea, cualquier cliente MCP (Claude, Cursor, Codex, Windsurf, …)
claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp

# CLI — el mismo motor, un comando
pip install a11y-toolkit
a11ytoolkit audit --url https://example.com
a11ytoolkit pair "#1f2328" "#fbfaf7"
```

Las auditorías estáticas, el cálculo de contraste, el cribado de PDF/DOCX y el
pack de evidencia corren con **cero dependencias**. Las herramientas renderizadas
(contraste real sobre imágenes, trampas de teclado, reflow, formularios) necesitan
además Playwright:
`pip install playwright && playwright install chromium`.

## Capacidades

| Capacidad | axe-core / Lighthouse / pa11y | a11y-toolkit |
|---|---|---|
| Contraste de texto sobre imágenes y degradados (muestreo por píxeles del fondo real) | No | Sí |
| Borrador VPAT 2.5 (WCAG) desde el pack de evidencia — contraparte US/ADA de la declaración EAA | No | Sí |
| Prueba de errores de formulario: rellena datos inválidos, envía de verdad, juzga qué pasa | No | Sí |
| Trampas de teclado: paseo real con Tab + test de salida con Escape, y navegación disparada por foco/input | No | Sí |
| Auditoría de scroll infinito: supervivencia del foco, anuncios, fin del feed | No | Sí |
| Reflow a 320px y el text-spacing de WCAG, medidos | No | Sí |
| Transcripción de lector de pantalla: lo que oye una persona ciega, linealizado | No | Sí |
| Tooltips que ignoran Escape cazados hovereando de verdad (1.4.13) | No | Sí |
| Declaraciones legales EAA / RD 1112/2018, en español y en inglés | No | Sí |
| Un pack de evidencia que una persona puede firmar — hashes, matriz, bloque de firma vacío | No | Sí |
| Interop ACT Rules: export EARL + informe de consistencia por regla contra los casos oficiales del W3C | No | Sí |
| Vista previa del borrador WCAG 3 — reagrupa hallazgos 2.2 según sus outcomes, sin score inventado | No | Sí |
| El motor se examina a sí mismo: banco de mutantes WCAG con semilla — examen regenerable, kill rate + falsos positivos vía placebos | No | Sí |
| Diagnóstico secuencial: pasa una URL y la evidencia de la página ordena los exámenes (la severidad solo desempata) | No | Sí |
| Cero dependencias en el núcleo, habla es/en, cualquier navegador que tengas | Runtimes pesados | Cero dependencias |

<!-- TOOLS:BEGIN -->
## Las herramientas (34)

Referencia completa — descripciones, argumentos, formas de retorno y
comportamiento — en [docs/tools.md](docs/tools.md). Todas las herramientas
aceptan `lang` (`en`|`es`) salvo indicación; la salida es JSON salvo
indicación. Generada desde `server.TOOLS` por `scripts/gen_readme.py`; esta
traducción puede ir a la zaga del inglés, que es la fuente canónica.

| Herramienta | Categoría | Qué hace |
|---|---|---|
| [`a11y_audit_url`](docs/tools.md#a11y_audit_url) | Auditoría | Auditoría WCAG exprés |
| [`a11y_audit_dom`](docs/tools.md#a11y_audit_dom) | Auditoría | Auditoría WCAG renderizada |
| [`a11y_audit_pdf`](docs/tools.md#a11y_audit_pdf) | Auditoría | Cribado de accesibilidad PDF |
| [`a11y_docx_screen`](docs/tools.md#a11y_docx_screen) | Auditoría | Cribado de accesibilidad DOCX |
| [`a11y_journey_verdict`](docs/tools.md#a11y_journey_verdict) | Pruebas a ciegas | Veredicto de journey a ciegas |
| [`a11y_autofix`](docs/tools.md#a11y_autofix) | Arreglo y contraste | Autocorrecciones seguras y deterministas |
| [`a11y_contrast_pair`](docs/tools.md#a11y_contrast_pair) | Arreglo y contraste | Ratio de contraste + veredictos |
| [`a11y_contrast_image`](docs/tools.md#a11y_contrast_image) | Arreglo y contraste | Contraste de texto sobre imagen |
| [`a11y_contrast_dom`](docs/tools.md#a11y_contrast_dom) | Arreglo y contraste | Muestreo de contraste en elemento vivo |
| [`a11y_suggest_color`](docs/tools.md#a11y_suggest_color) | Arreglo y contraste | Color aprobatorio más cercano |
| [`a11y_generate_declaration`](docs/tools.md#a11y_generate_declaration) | Documentar | Declaración de accesibilidad (EAA/RD 1112) |
| [`a11y_generate_vpat`](docs/tools.md#a11y_generate_vpat) | Documentar | Informe VPAT 2.5 (WCAG) |
| [`a11y_generate_openacr`](docs/tools.md#a11y_generate_openacr) | Documentar | Informe OpenACR YAML (GSA) |
| [`a11y_badge`](docs/tools.md#a11y_badge) | Documentar | Insignia SVG honesta |
| [`a11y_snapshot`](docs/tools.md#a11y_snapshot) | Vigilar (regresiones) | Snapshot de accesibilidad + orden de tab |
| [`a11y_diff`](docs/tools.md#a11y_diff) | Vigilar (regresiones) | Diff de regresión entre snapshots |
| [`a11y_diff_urls`](docs/tools.md#a11y_diff_urls) | Vigilar (regresiones) | Diff staging vs producción |
| [`a11y_aria_live_snippet`](docs/tools.md#a11y_aria_live_snippet) | Vigilar (regresiones) | Snippet monitor aria-live |
| [`a11y_criterion`](docs/tools.md#a11y_criterion) | Conocimiento y contexto | Criterio WCAG explicado |
| [`a11y_html_validate`](docs/tools.md#a11y_html_validate) | Conocimiento y contexto | Validación W3C Nu |
| [`a11y_keyboard`](docs/tools.md#a11y_keyboard) | Interacciones | Detector de trampas de teclado |
| [`a11y_forms`](docs/tools.md#a11y_forms) | Interacciones | Prueba de errores de formulario |
| [`a11y_hover`](docs/tools.md#a11y_hover) | Interacciones | Descartabilidad de tooltips (1.4.13) |
| [`a11y_reflow`](docs/tools.md#a11y_reflow) | Interacciones | Comprobación de reflow a 320px |
| [`a11y_scroll`](docs/tools.md#a11y_scroll) | Interacciones | Auditoría de scroll infinito |
| [`a11y_sr_transcript`](docs/tools.md#a11y_sr_transcript) | Interacciones | Transcripción de lector de pantalla |
| [`a11y_reduced_motion`](docs/tools.md#a11y_reduced_motion) | Interacciones | ¿Respeta prefers-reduced-motion? |
| [`a11y_forced_colors`](docs/tools.md#a11y_forced_colors) | Interacciones | Heurística de supervivencia forced-colors |
| [`a11y_vtt_check`](docs/tools.md#a11y_vtt_check) | Interacciones | Calidad de subtítulos WebVTT |
| [`a11y_evidence`](docs/tools.md#a11y_evidence) | Cobertura y evidencia | Pack de evidencia (entrega verificable) |
| [`a11y_disprove`](docs/tools.md#a11y_disprove) | Cobertura y evidencia | Refutador: re-verifica hallazgos |
| [`a11y_ledger`](docs/tools.md#a11y_ledger) | Cobertura y evidencia | Libro de cobertura (persistente) |
| [`a11y_wcag3_preview`](docs/tools.md#a11y_wcag3_preview) | Cobertura y evidencia | Vista previa borrador WCAG 3 (sin score) |
| [`a11y_route`](docs/tools.md#a11y_route) | Enrutado | Router de herramientas (objetivo o página → pasos) |
<!-- TOOLS:END -->

## Los 6 prompts

- **`audit-page`** (`url*`, `language`): Flujo completo de auditoría de accesibilidad para una URL: herramientas automáticas + qué verificar a mano (teclado, lector de pantalla, zoom). Cada prompt existe en español y en inglés.

- **`fix-contrast`** (`fg*`, `bg*`, `context`): Arreglo de contraste guiado: verifica el par (o la región de texto sobre imagen), obtén el color aprobatorio más cercano, aplícalo al código. Cada prompt existe en español y en inglés.

- **`pre-deploy-check`** (`url*`, `baseline`): Chequeo de regresión pre-deploy: auditoría exprés de la URL más diff de snapshot contra una línea base. Cada prompt existe en español y en inglés.

- **`declaration-eaa`** (`entity*`, `url*`, `status`): Genera una declaración de accesibilidad EAA / RD 1112/2018, pidiendo los campos legales que falten. Cada prompt existe en español y en inglés.

- **`conformance-wcagem`** (`url*`, `tier`, `language`): Escalera de conformidad WCAG-EM guiada para un sitio: cribado exprés → evaluación guiada verificada por el agente sobre una muestra representativa → insumos del informe de conformidad. Cada prompt existe en español y en inglés.

- **`blindfold-task`** (`url*`, `goal*`, `kind`, `language`): Prueba de usabilidad a ciegas — el agente intenta una tarea real percibiendo SOLO el árbol de accesibilidad y actuando solo por nombre accesible y teclado, registrando la fricción por paso; cierra con a11y_journey_verdict. La capacidad que ninguna otra herramienta de accesibilidad tiene: testing no visual por tareas donde el agente ES la persona usuaria del lector de pantalla. Cada prompt existe en español y en inglés.


## Instalación

> mcp-name: io.github.kinti/a11y-toolkit · PyPI: [a11y-toolkit](https://pypi.org/project/a11y-toolkit/) · DOI Zenodo: `10.5281/zenodo.22843722`

Funciona con **cualquier cliente con MCP** — Claude Code/Desktop, Cursor,
Windsurf, VS Code, Codex CLI, OpenCode, ZCode, Zed, Cline, Continue, Kimi
Code… ¿Ecosistema Node? `npx -y @kinti/a11y-toolkit mcp…` — el lanzador npm
ejecuta el mismo motor vía uv ([npm/](npm/)). Los formatos de configuración
verificados de cada cliente, en [docs/clients.md](docs/clients.md). Cómo se
compone con los servidores populares (Playwright, GitHub, Filesystem,
Fetch…) — [docs/interop.md](docs/interop.md). Recetas de principio a fin
(auditar → arreglar → sellar → CI):
[docs/cookbook.md](docs/cookbook.md).

```bash
claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp
```

O con configuración JSON:

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"],
      "timeoutMs": 60000
    }
  }
}
```

Las herramientas renderizadas usan Playwright **si está presente** y aceptan un
parámetro `browser` (`auto`, `chromium`, `firefox`, `webkit`, `chrome`, `msedge`
— autodetecta el primero disponible). Aceptan `auth_state` (ruta al
storage_state de Playwright) para auditar tras login. Todo lo demás funciona
con cero dependencias.

### La skill

```bash
git clone https://github.com/kinti/a11y-toolkit && cd a11y-toolkit
./skills/install-skill.sh     # → ~/.zcode/skills y ~/.claude/skills
```

## Hook de agente — `a11ytoolkit init`

Los agentes que leen `AGENTS.md` por su cuenta reciben la regla que importa —
*tras cualquier cambio de UI, re-audita antes de dar el trabajo por hecho* —
con los comandos exactos:

```bash
cd tu-proyecto
uvx --from a11y-toolkit a11ytoolkit init     # escribe/fusiona el hook en AGENTS.md (idempotente)
```

También imprime el bloque de configuración MCP y el paso opcional de la skill.
`--check` informa de si el hook está presente (exit 1 si no — apto para CI).

## Idiomas — paquetes de locale comunitarios

Todos los mensajes de usuario (hallazgos, remediaciones, textos legales) viven
en [paquetes de locale](a11y_toolkit/locales/) — un JSON por idioma; hoy salen
`es` y `en`. **Añadir un idioma es un PR de un solo fichero**: copia
[`_template.json`](a11y_toolkit/locales/_template.json), traduce conservando los
`{placeholders}`, y `python3 tests/test_locales.py` lo valida mecánicamente
(claves, placeholders, regla de plural, completitud). El mismo modelo comunitario
que los locales de axe-core — con una validación que axe-core no tiene. Guía:
[docs/i18n.md](docs/i18n.md). Los productos derivados pueden superponer su voz
de marca vía overlays sin hacer fork.

## CLI — el mismo motor, un comando

Instálalo con `pip install a11y-toolkit` (o `uv tool install a11y-toolkit`).

```bash
a11ytoolkit audit --changed                     # SOLO lo cambiado desde HEAD (gate de CI)
a11ytoolkit audit --changed --base origin/main  # los cambios de una rama — exit 2 en high/medium
a11ytoolkit audit --url https://example.com --pages 5   # rastreo, sitemap primero
a11ytoolkit pair "#1f2328" "#fbfaf7"                    # contraste
a11ytoolkit image hero.jpg --text "#fff" --region 120,40,420,90
a11ytoolkit forms https://mysite/contact                # errores de formulario
a11ytoolkit kbd https://mysite                          # trampas de teclado + 3.2.1/3.2.2
a11ytoolkit reflow https://mysite                       # reflow 320px
a11ytoolkit scroll https://medium.com/feed              # scroll infinito
a11ytoolkit validate --url https://example.com          # W3C Nu
a11ytoolkit hover https://mysite                        # descartabilidad de tooltips
a11ytoolkit fix --file page.html -o fixed.html          # autofix seguro
a11ytoolkit declaration --entity "Acme" --url https://… --status partial --framework eaa
a11ytoolkit snapshot https://mysite --out before.json   # antes del deploy
a11ytoolkit diff before.json after.json                 # tras el deploy
a11ytoolkit evidence audit.json -o pack.json            # pack de evidencia verificable
a11ytoolkit disprove --url https://mysite               # re-verifica hallazgos
a11ytoolkit budget --budget budget.json --audit audit.json  # solo lo NUEVO bloquea
a11ytoolkit sarif --from-audit audit.json -o a11y.sarif # GitHub code scanning
a11ytoolkit badge --score 92 --out badge.svg            # SVG honesto
a11ytoolkit contrast-dom https://mysite --selector ".hero h1"  # muestreo por píxeles
a11ytoolkit vpat pack.json --product "Acme" -o vpat.html      # borrador VPAT 2.5 (WCAG)
a11ytoolkit openacr pack.json --product "Acme" -o openacr.yaml # OpenACR YAML (GSA)
a11ytoolkit earl --from-audit audit.json -o earl.json          # ACT Rules / EARL
a11ytoolkit wcag3 --from-audit audit.json                      # vista previa WCAG 3 (sin score)
a11ytoolkit route --goal "gate my PR"                          # qué herramientas para la tarea
a11ytoolkit route --file page.html                             # diagnóstico: la página ordena
a11ytoolkit mutants --seed 7 --n 12                            # el autoexamen sellado del motor
a11ytoolkit fingerprints pages/*.html -o templates.json        # gemelas → una auditoría por plantilla
a11ytoolkit corpus verify corpus                               # el corpus congelado, verificado
```

## Cobertura: 51 de 55 criterios WCAG 2.2 A/AA (93%)

| Con señal automatizada | Solo manual (genuinamente humano) |
|---|---|
| 1.1.1, 1.2.2, 1.2.3, 1.2.5, 1.3.1–1.3.5, 1.4.1–1.4.5, 1.4.10–1.4.13, 2.1.1, 2.1.2, 2.1.4, 2.2.1, 2.2.2, 2.4.1–2.4.7, 2.4.11, 2.5.1–2.5.4, 2.5.7, 2.5.8, 3.1.1, 3.1.2, 3.2.1–3.2.4, 3.2.6, 3.3.1–3.3.4, 3.3.8, 4.1.2, 4.1.3 | 1.2.1 (transcripciones de audio), 1.2.4 (subtítulos en directo), 2.3.1 (detección de destellos), 3.3.7 (entrada redundante) |

Los 4 criterios solo-manuales tienen cada uno una entrada de conocimiento
(`a11y_criterion`) que dice al agente exactamente cómo verificarlos a mano.
La frontera se imprime en cada informe.

## El motor detrás de a11y.es

[a11y.es](https://a11y.es) es un servicio de accesibilidad para el mercado
español que ejecuta este motor. El servicio es un código aparte; este
repositorio es el motor.

## Validado contra páginas reales

Comparado mensualmente contra axe-core 4.10 en páginas reales
([metodología y resultados](bench/README.md)). Benchmark de agentes por
tareas en sitios en vivo, incluyendo una muestra estratificada de las páginas
más importantes de España ([método y
resultados](docs/benchmark-agents.md)). Encontró un fallo WCAG real en gov.uk
que axe no reporta (botón azul a 3.91:1, verificado a mano). Sacó de dentro
nuestros propios falsos positivos (skip links ocultos, campos honeypot,
enlaces genéricos de contexto único, accname de image-alt — cada uno con su
fixture de regresión).

También se ejecuta contra los casos de prueba oficiales ACT del W3C:
`scripts/act_report.py` regenera el [informe de implementación
EARL](docs/act-implementation-report.json) — **100% consistente con cada
regla ACT publicada que implementa** (355 casos oficiales, 20/20 reglas,
cero inconsistencias, verificado por release contra el repositorio
w3c/wcag-act-rules; desglose por regla en
[docs/act-report-summary.md](docs/act-report-summary.md)). El catálogo WCAG
2.2 (86 criterios, A/AA/AAA) y el registro de outcomes WCAG 3 se verifican
igualmente contra sus fuentes canónicas de w3.org
(`scripts/wcag22_ingest.py`, `scripts/wcag3_ingest.py`).

## Por qué lo construí

Llevo auditando webs desde 2003. En veinte años las herramientas se hicieron
más rápidas y los fallos siguieron siendo los mismos: el mismo alt ausente,
las mismas trampas de teclado, los mismos formularios que se tragan tu
trabajo. Cuando los agentes de IA empezaron a escribir la mayor parte de la
web, la brecha de auditoría dejó de ser un problema de plantillas y pasó a ser
uno de infraestructura.

Así que construí la herramienta que siempre quise al lado en una auditoría.
No otro escáner — escáneres hay. Un juego de herramientas que hace la mitad
del trabajo, dice exactamente dónde se para, y empaqueta el resto para la
persona que firma. El fallo de gov.uk que has leído arriba no es un caso de
benchmark sintético: este motor lo encontró, y yo lo confirmé con mis propios
ojos antes de escribirlo.

Si te ahorra una tarde, deja una estrella — ayuda de verdad a que el próximo
auditor lo encuentre. Si no, abre un issue y dime qué falta.

## Honestidad, de fábrica

Cada auditoría dice: **la automatización cubre el 93% de los 55 criterios
A/AA** (aproximadamente un tercio de todo WCAG contando AAA y las comprobaciones
genuinamente humanas) **— el resto necesita una persona**.
El prompt `audit-page` y la skill hacen que el agente compruebe lo que puede
(teclado, foco, zoom, errores anunciados) usando [la checklist
manual](skills/a11y-toolkit/references/wcag22-manual-checklist.md). Un filtro,
no un veredicto. El trabajo humano restante está tasado por criterio — MIN 23
(leer y confirmar), MED 19 (verificar en el navegador), MAX 13 (interacción y
juicio reales); [tabla completa](docs/effort-class-table.md). Y el pack de
evidencia es el objeto de entrega para la persona que firma, con transcripción
de lector de pantalla incluida, para que quien revisa vea lo que oye una
persona ciega.

## Seguridad y alcance

Una herramienta **local**: corre en tu máquina como tu usuario.
`a11y_audit_url` acepta solo http/https (nada de `file://` — usa
`--file`/`html` para HTML local). `a11y_html_validate` en modo html envía el
contenido por POST al servicio del W3C (en modo url solo comparte la URL;
vnu autoalojado soportado). `path`/`output_path` leen/escriben rutas locales —
úsalo en clientes MCP en los que confíes.

## Desarrollo

```bash
python3 tests/test_contrast.py && python3 tests/test_audit.py && python3 tests/test_v32.py \
  && python3 tests/test_dom.py && python3 tests/test_cli.py && python3 tests/test_solido.py \
  && python3 tests/test_mcp.py && python3 tests/test_png.py && python3 tests/test_vpat.py \
  && python3 tests/test_act.py
```

`tests/test_dom.py` se auto-omite sin Playwright. `tests/test_solido.py`
obliga a los invariantes de diseño (paridad de catálogos, alineación de
versiones, cobertura de conteos, fuzz de HTML hostil). Releases:
`make release V=X.Y.Z` — bump, gates, tag y push atómicos.

Superficies generadas — no editar a mano: la tabla de herramientas de este
README y [docs/tools.md](docs/tools.md) salen de `server.TOOLS`
(`scripts/gen_readme.py`), y [llms.txt](llms.txt) — el índice de este repo
para agentes, convención llmstxt.org — de la misma fuente
(`scripts/gen_llms.py`). Ambas con `--check` en los gates del Makefile: añadir
una herramienta y olvidarlas tinta la suite.

## Hoja de ruta

Hecho recientemente: auditoría renderizada con shadow DOM y contraste por
estado, prueba de errores de formulario más autofix, trampas de teclado,
scroll infinito, reflow, la integración W3C Nu, SARIF y presupuestos de
error, el pack de evidencia (spec publicada, autoverificable), rastreo por
sitemap, auditoría tras login, autodetección de navegador, la transcripción
de lector de pantalla y el precio del trabajo humano por criterio. La
historia completa vive en el [changelog](CHANGELOG.md).

Siguiente, más o menos en este orden:

- [ ] Interlock de atestación: que la firma de un auditor externo referencie el pack de evidencia por hash (su esquema, mi lado se adapta)
- [ ] Publicar los resultados mensuales del benchmark axe-core desde CI, sobre páginas reales
- [ ] Contrastes de la transcripción de lector contra la salida de NVDA y VoiceOver
- [ ] Más configuraciones de cliente verificadas (JetBrains AI, Gemini CLI), mismo tratamiento que [docs/clients.md](docs/clients.md)

## Autor

**Jesús Quintana Fernández** ([jquin.net](https://jquin.net/)) — consultor
SEO/GEO y profesional de accesibilidad web desde 2003. MIT © 2026.

*Esta traducción acompaña al README en inglés, que es la versión canónica y
la que verifica la suite.*
