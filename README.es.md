# a11y-toolkit

**Comprobaciones de accesibilidad WCAG 2.2 para agentes de programación, equipos de desarrollo y CI.**

Un chequeo automático encuentra una parte de los problemas de accesibilidad y
ahí se queda. a11y-toolkit sigue: audita un archivo HTML o una página web,
averigua cómo corregir cada hallazgo y comprueba qué ha cambiado antes de
publicar. Cuando una persona tenga que revisar el resultado, exporta un
paquete de evidencias verificable con los hallazgos y las comprobaciones
pendientes.

Gratis para usarlo por tu cuenta bajo licencia MIT. Lo construyó [Jesús
Quintana Fernández](https://jquin.net/), que audita webs desde 2003, y
[a11y.es](https://a11y.es) lo usa en su servicio de monitorización de
accesibilidad.

[English](README.md) · [Español](README.es.md)

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![npm](https://img.shields.io/npm/v/%40kinti%2Fa11y-toolkit)](https://www.npmjs.com/package/@kinti/a11y-toolkit)
[![Downloads](https://img.shields.io/pypi/dm/a11y-toolkit)](https://pypistats.org/packages/a11y-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink)](https://github.com/sponsors/kinti)
[![Socket score](https://socket.dev/api/badge/pypi/package/a11y-toolkit)](https://socket.dev/pypi/package/a11y-toolkit/overview)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/kinti/a11y-toolkit/badge)](https://scorecard.dev/viewer/?uri=github.com/kinti/a11y-toolkit)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16107/badge)](https://www.bestpractices.dev/en/projects/16107)
[![ACT Rules](https://img.shields.io/badge/ACT%20Rules-134%2F134%20fallos%20detectados-brightgreen)](https://github.com/kinti/a11y-toolkit/blob/main/docs/act-report-summary.md)
[![Releases](https://img.shields.io/badge/releases-OIDC%20provenance%20signed-blue)](.github/workflows/publish.yml)
[![Dependencies](https://img.shields.io/badge/core%20dependencies-zero-blue)](pyproject.toml)
[![Python Versions](https://img.shields.io/pypi/pyversions/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![GitHub Release](https://img.shields.io/github/v/release/kinti/a11y-toolkit)](https://github.com/kinti/a11y-toolkit/releases)

<p align="center">
  <a href="https://madebyhuman.iamjarl.com"><img src="https://madebyhuman.iamjarl.com/badges/loop-white.svg" alt="Human in the Loop — revisión humana" height="34"></a>
</p>

Python 3.9+ · Cero dependencias en el núcleo · Cero telemetría · Resultados en español e inglés

## Inicio rápido

### Prueba la CLI

Mide el contraste entre dos colores con `uvx`. La relación esperada es
**4,54:1**. [Guía de uv](https://docs.astral.sh/uv/guides/tools/)

```sh
uvx --from a11y-toolkit a11ytoolkit pair "#767676" "#ffffff"
```

Instala la CLI con `uv tool install a11y-toolkit` o ejecuta
`python -m pip install a11y-toolkit` en el entorno Python de tu proyecto.
Después, audita una página pública o añade `--file page.html` para auditar
un archivo HTML local. Usa `--lang es` para recibir el informe en español.

```sh
a11ytoolkit audit --url https://example.com
```

Cada hallazgo incluye el criterio WCAG, la gravedad y cómo corregirlo.
Consulta `not_measured` para ver qué criterios quedan pendientes en esta
auditoría. Ejecuta `a11ytoolkit route --url https://example.com` para ver
qué comprobaciones conviene hacer después. El CLI escribe en UTF-8 en todas
las plataformas, así que un informe enviado a un archivo o a otro comando
(`> informe.json`) sigue siendo válido en Windows.

<details>
<summary>Ver una auditoría, una corrección de contraste y la comprobación final</summary>

![La auditoría detecta una imagen sin texto alternativo y un campo sin etiqueta. El chequeo de contraste propone un color más oscuro y la nueva auditoría, ya con las correcciones, muestra la mejora.](docs/demo.gif)

</details>

### Conecta tu agente de programación

> mcp-name: io.github.kinti/a11y-toolkit

Registra un servidor MCP por **stdio** con el comando y los argumentos
indicados. Usa el formato de configuración de tu cliente. [Guía de instalación por cliente](docs/clients.md)

```text
command: uvx
args: --from a11y-toolkit a11y-toolkit-mcp
```

Para usar el lanzador de npm, ejecuta
`npx -y -p @kinti/a11y-toolkit a11y-toolkit-mcp`. Incluye el motor y
utiliza un intérprete local de Python 3.9+. [Opciones de instalación](llms-install.md)

Una vez conectado, pide al agente que llame a `a11y_contrast_pair` con
`#767676` sobre `#ffffff`. La relación de contraste esperada es **4,54:1**.

### Activa las comprobaciones con navegador

Usa el mismo entorno Python para Playwright y para la CLI o el servidor
MCP. Instala Chromium para las pruebas con navegador y Pillow para
decodificar imágenes al medir el contraste por píxeles.

```sh
python -m pip install a11y-toolkit playwright pillow
python -m playwright install chromium
a11ytoolkit dom https://example.com
```

La CLI no tiene opción de navegador: usa el primero que encuentre. Para
elegir uno, pasa `browser` a las herramientas MCP. Si tu cliente MCP usa un
entorno aislado de `uvx`, configúralo para que
ejecute `a11y-toolkit-mcp` desde el entorno donde instalaste Playwright.
Las comprobaciones con navegador también funcionan con Firefox, WebKit,
Chrome y Edge si están instalados.

El contenido de un `<details>` cerrado ya no se acusa como sin nombre ni sin
foco. `a11y_snapshot` puede ejecutarse justo después de una auditoría de
navegador en la misma sesión, y `a11y_contrast_dom` devuelve un timeout de
carga como objeto de error. Si `load` agota el timeout pero el DOM está
completo, `a11y_audit_dom` audita la página renderizada y la anota en
`page_errors`; sube `timeout` en sitios lentos. Los hallazgos renderizados
traen `count`, el total de instancias (los ejemplos siguen limitados a 6).

## Del hallazgo a la corrección verificada

### Localiza el problema y vuelve a comprobarlo

Ejecuta estos comandos sobre el mismo archivo HTML. La copia anotada
marca los elementos que el informe puede localizar en el código original, y
`marks.json` indica la ruta de cada elemento marcado.

```sh
a11ytoolkit audit --file page.html > audit.json
a11ytoolkit annotate page.html --report audit.json -o annotated.html --marks marks.json
```

Aplica la corrección en `page.html` y repite la auditoría. El comando
`a11ytoolkit pair "#767676" "#ffffff"` mide el contraste entre ambos
colores e indica los umbrales aplicables. Usa el navegador para comprobar
texto sobre imágenes o degradados.

### Bloquea regresiones en CI

Audita la página que quieres vigilar. El presupuesto registra los
hallazgos que ya has aceptado. Guárdalo en Git para que CI pueda usarlo
como referencia.

```sh
a11ytoolkit budget --init --audit audit.json > budget.json
```

Después de un cambio, audita de nuevo el **mismo** archivo y compara el
resultado con el presupuesto guardado.

```sh
a11ytoolkit audit --file page.html > next.json
a11ytoolkit budget --budget budget.json --audit next.json
```

| Código de salida | Resultado |
| --- | --- |
| `0` | Los cambios medidos están dentro del presupuesto. |
| `1` | Falló la captura o los informes no se pudieron comparar. |
| `2` | Al menos un hallazgo superó el presupuesto. |

Para comparar capturas web, mantén el mismo navegador, esquema de color
y tipo de sesión. Para revisar el HTML que cambió en una rama de Git,
usa `a11ytoolkit audit --changed --base origin/main`. Para comparar el
orden del foco en un recorrido con guion, usa `trace`. [Ejemplos de CI y teclado](docs/cookbook.md)

```sh
a11ytoolkit trace https://mysite --script journey.json --capture-dialog-state -o after.json
a11ytoolkit trace diff before.json after.json --gate-dialog-state
```

`--capture-dialog-state` registra, después de cada paso, si hay un diálogo
abierto y si el foco está dentro. `trace diff --gate-dialog-state` compara ese
estado cuando ambos recorridos lo llevan.

El presupuesto empareja instancias por `stable_paths` (id, `data-testid`,
nombre ARIA) antes que por rutas posicionales. En un rastreo, las URLs
fallidas no gastan el cupo de páginas; el rastreo se detiene cuando los
fallos llegan al doble del cupo y el informe lo indica con
`failed_pages_capped`.

`a11ytoolkit init` también instala una barrera al guardar en
`.claude/settings.json`. `guard` falla cerrado: un guardado que el motor no
puede auditar (más de 3 MB, no parseable) devuelve `decision: "error"` y
exit 1 en vez de `allow`; `A11Y_GATE=off` salta el hook y `--lang es`
responde en español. `fix` devuelve `error` cuando falla su auditoría
final. Para volver a comprobar un informe, `a11y_disprove` revisa cada
hallazgo anterior en la página real; con menos rutas guardadas que
instancias, solo confirma una señal que sigue en la misma página y solo
descarta con prueba completa.

### Entrega la evidencia para revisión

```sh
a11ytoolkit evidence next.json -o evidence-pack.json
```

El paquete incluye los informes originales, una matriz de 55 criterios y
las comprobaciones que quedan pendientes en la muestra. Desde una copia
local del repositorio, ejecuta
`python3 scripts/verify_pack.py /path/to/evidence-pack.json` para comprobar
el sello SHA-256 y los informes incluidos. La persona que audita puede
revisar el paquete y emitir el dictamen de conformidad. [Formato y verificador](docs/evidence-pack-schema.md)

## Prueba una tarea real a ciegas

Los escáneres comprueban de qué está hecha una página. Esto comprueba qué
puede hacer una persona con ella. Tu agente de programación intenta una tarea
real («suscribirse al boletín», «restablecer la contraseña») percibiendo solo
el árbol de accesibilidad, que es lo que expone un lector de pantalla, y
actuando solo por nombre accesible y teclado. Cada dificultad que encuentra se
registra contra un criterio WCAG.

<details>
<summary>Ver cómo un agente intenta suscribirse a un boletín y desiste</summary>

![Un agente de programación intenta suscribirse a un boletín percibiendo solo el árbol de accesibilidad, anota una dificultad en cada obstáculo y a11y_journey_verdict devuelve un veredicto de tarea bloqueada con cada hallazgo, su criterio y su corrección.](docs/blindfold.gif)

</details>

La página de demostración está hecha para fallar, y el veredicto que se ve es
salida real de ese recorrido.

Pide a tu agente que ejecute el prompt `blindfold-task` con una URL y la
tarea. Al terminar, cierra con `a11y_journey_verdict`, que convierte el
registro de dificultades en un veredicto determinista: `pass`, `partial`,
`fail` o `blocked`, con una puntuación y cada hallazgo con su criterio y su
corrección. Para puntuar un registro a mano, ejecuta
`python3 -m a11y_toolkit.a11yjourney friction.json`. El veredicto es un
informe como las auditorías, así que `a11y_evidence` lo acepta y la lista de
dificultades llega a quien revisa.

Un `pass` significa que una tarea se pudo completar sin vista, por un agente
de IA, en una página. Es evidencia de usabilidad. No es una declaración de
conformidad ni sustituye la prueba con una persona usuaria de lector de
pantalla. El [ejemplo desarrollado](docs/journey-example.md) muestra el ciclo
completo, sobre una página de prueba con fallos y sobre dos sitios reales.

## Elige la comprobación adecuada

| Si necesitas… | Empieza por… |
| --- | --- |
| Auditar una página, un HTML local o un sitio pequeño | `audit --url`, `audit --file` o `audit --url … --pages 5` |
| Comprobar contraste, foco o tamaño de elementos interactivos en el navegador | `dom` o `contrast-dom` |
| Recorrer la página con el teclado o comprobar la redistribución a 320 píxeles CSS | `kbd`, `trace` o `reflow` |
| Observar cómo se anuncian los errores, qué aparece al pasar el puntero o cómo funciona el desplazamiento infinito | `forms`, `hover`, `scroll` o `patterns` |
| Saber si una tarea se puede completar sin ver la página | prompt `blindfold-task` y después `a11y_journey_verdict` |
| Inspeccionar qué expone el navegador a las tecnologías de apoyo | Herramienta MCP `a11y_sr_transcript` o prompt `blindfold-task` |
| Revisar la estructura de documentos o los subtítulos | `pdf`, `python -m a11y_toolkit.a11ydocx` o `vtt` |
| Preparar una revisión humana o exportar resultados a otras herramientas | `evidence`, `scope`, `sarif`, `earl`, `vpat` u `openacr` |

Las pruebas de formularios pueden enviar datos. Ejecútalas en un sitio
de pruebas o en un entorno preparado para recibir esos envíos.
[Ejemplos y opciones de los comandos](docs/cookbook.md)

## Cobertura y validación

**48 de los 55 criterios A/AA de WCAG 2.2 cuentan con al menos una señal
automatizada (87 %)** en los modos de comprobación disponibles. Una señal
cubre una condición concreta dentro de un criterio. Cuenta cualquier señal,
incluso las parciales: un criterio entra en este recuento en cuanto se
comprueba una de sus condiciones, y eso no dice nada sobre las demás. La
muestra, las pruebas ejecutadas y la revisión manual determinan qué puede
concluir quien evalúa la conformidad. El paquete de evidencias lo detalla
criterio
por criterio. [Lista de comprobación manual](skills/a11y-toolkit/references/wcag22-manual-checklist.md) · [Estándares y correspondencias](docs/standards-coverage.md)

| Evidencia | Qué mide |
| --- | --- |
| [Informe de implementación ACT](docs/act-report-summary.md) | Se detectaron los 134 fallos esperados en 355 casos de 20 reglas. Coincidieron exactamente 273 de los 355 resultados (77 %). El resto difirió entre `passed` e `inapplicable`. |
| [Corpus congelado](corpus/README.md) | El toolkit detectó los 18 fallos introducidos y evaluó los tres controles sin alertas. Los casos proceden de su propio banco de mutaciones. Otros motores pueden enviar sus resultados al mismo evaluador. |
| [Comparación con axe-core en páginas reales](bench/README.md) | Se comparan cuatro páginas públicas mediante una auditoría estática, una renderizada y una pasada de axe. Las diferencias señalan casos para revisión manual. Los resultados originales y el método de validación son públicos. |

La transcripción se obtiene del árbol de accesibilidad del navegador.
Comprueba la salida hablada con un lector de pantalla.
[Comprobación con lectores de pantalla](docs/sr-crosscheck.md)

## Herramientas MCP y prompts

El proyecto incluye 37 herramientas MCP, 5 prompts y una skill para
repetir auditorías y revisiones. La CLI incluye además comandos para
comprobar regresiones y evaluar entregas sobre el corpus.
[Skill para agentes](skills/a11y-toolkit/SKILL.md) · [Índice de documentación para agentes](llms.txt)

<details>
<summary>Consultar el catálogo de 37 herramientas</summary>

<!-- TOOLS:BEGIN -->
## Las herramientas (37)

La referencia completa incluye las descripciones, los argumentos y el
formato de respuesta. Salvo que se indique lo contrario, las herramientas
aceptan `lang` (`en` o `es`) y devuelven JSON. [Referencia MCP](docs/tools.md)

| Herramienta | Categoría | Qué hace |
|---|---|---|
| [`a11y_audit_url`](docs/tools.md#a11y_audit_url) | Auditoría | Auditoría WCAG exprés |
| [`a11y_audit_dom`](docs/tools.md#a11y_audit_dom) | Auditoría | Auditoría WCAG renderizada |
| [`a11y_audit_pdf`](docs/tools.md#a11y_audit_pdf) | Auditoría | Revisión estructural de PDF |
| [`a11y_docx_screen`](docs/tools.md#a11y_docx_screen) | Auditoría | Revisión estructural de DOCX |
| [`a11y_locate`](docs/tools.md#a11y_locate) | Localizar | Localiza un elemento por su nombre accesible |
| [`a11y_journey_verdict`](docs/tools.md#a11y_journey_verdict) | Pruebas a ciegas | Evalúa las dificultades de un recorrido sin visión |
| [`a11y_autofix`](docs/tools.md#a11y_autofix) | Corrección y contraste | Autocorrecciones seguras y deterministas |
| [`a11y_patches`](docs/tools.md#a11y_patches) | Corrección y contraste | Registro de correcciones sellado con SHA-256 |
| [`a11y_contrast_pair`](docs/tools.md#a11y_contrast_pair) | Corrección y contraste | Relación de contraste y resultado por criterio |
| [`a11y_contrast_image`](docs/tools.md#a11y_contrast_image) | Corrección y contraste | Contraste de texto sobre imagen |
| [`a11y_contrast_dom`](docs/tools.md#a11y_contrast_dom) | Corrección y contraste | Mide el contraste del elemento renderizado |
| [`a11y_suggest_color`](docs/tools.md#a11y_suggest_color) | Corrección y contraste | Color más cercano que cumple el contraste |
| [`a11y_generate_declaration`](docs/tools.md#a11y_generate_declaration) | Documentar | Borrador de declaración de accesibilidad |
| [`a11y_generate_vpat`](docs/tools.md#a11y_generate_vpat) | Documentar | Borrador de informe VPAT 2.5 (WCAG) |
| [`a11y_generate_openacr`](docs/tools.md#a11y_generate_openacr) | Documentar | Borrador de informe OpenACR en YAML |
| [`a11y_badge`](docs/tools.md#a11y_badge) | Documentar | Insignia SVG con la puntuación y su alcance |
| [`a11y_snapshot`](docs/tools.md#a11y_snapshot) | Regresiones | Captura de accesibilidad y orden de tabulación |
| [`a11y_diff`](docs/tools.md#a11y_diff) | Regresiones | Compara dos capturas de accesibilidad |
| [`a11y_diff_urls`](docs/tools.md#a11y_diff_urls) | Regresiones | Compara la accesibilidad de dos URL |
| [`a11y_aria_live_snippet`](docs/tools.md#a11y_aria_live_snippet) | Regresiones | Script de seguimiento de mensajes `aria-live` |
| [`a11y_criterion`](docs/tools.md#a11y_criterion) | Referencia y validación | Criterio WCAG explicado |
| [`a11y_html_validate`](docs/tools.md#a11y_html_validate) | Referencia y validación | Validación W3C Nu |
| [`a11y_keyboard`](docs/tools.md#a11y_keyboard) | Interacciones | Trampas de teclado y destino de los enlaces de salto |
| [`a11y_forms`](docs/tools.md#a11y_forms) | Interacciones | Prueba de errores de formulario |
| [`a11y_hover`](docs/tools.md#a11y_hover) | Interacciones | Comprueba si los mensajes emergentes se pueden cerrar (1.4.13) |
| [`a11y_reflow`](docs/tools.md#a11y_reflow) | Interacciones | Comprueba la redistribución a 320 píxeles CSS |
| [`a11y_scroll`](docs/tools.md#a11y_scroll) | Interacciones | Auditoría de desplazamiento infinito (pasiva por defecto; con interactive=true pulsa solo el control que indiques) |
| [`a11y_sr_transcript`](docs/tools.md#a11y_sr_transcript) | Interacciones | Transcripción del árbol de accesibilidad del navegador |
| [`a11y_reduced_motion`](docs/tools.md#a11y_reduced_motion) | Interacciones | Comprueba la preferencia `prefers-reduced-motion` |
| [`a11y_forced_colors`](docs/tools.md#a11y_forced_colors) | Interacciones | Detecta posibles problemas con los colores forzados |
| [`a11y_vtt_check`](docs/tools.md#a11y_vtt_check) | Interacciones | Calidad de subtítulos WebVTT |
| [`a11y_evidence`](docs/tools.md#a11y_evidence) | Cobertura y evidencia | Paquete de evidencias verificable |
| [`a11y_disprove`](docs/tools.md#a11y_disprove) | Cobertura y evidencia | Vuelve a comprobar los hallazgos de una auditoría |
| [`a11y_ledger`](docs/tools.md#a11y_ledger) | Cobertura y evidencia | Mantiene un registro de cobertura entre auditorías |
| [`a11y_wcag3_preview`](docs/tools.md#a11y_wcag3_preview) | Cobertura y evidencia | Vista previa del borrador WCAG 3 (sin puntuación) |
| [`a11y_scope`](docs/tools.md#a11y_scope) | Cobertura y evidencia | Propone el alcance y la aplicabilidad para revisión |
| [`a11y_route`](docs/tools.md#a11y_route) | Diagnóstico | Propone comprobaciones según el objetivo o la página |
<!-- TOOLS:END -->

</details>

### Los 5 prompts

| Prompt | Para qué sirve |
| --- | --- |
| `audit-page` | Audita una página y planifica las pruebas con teclado, lector de pantalla y zoom. |
| `fix-contrast` | Encuentra y aplica un color de texto que cumple el contraste sobre el fondo medido. |
| `pre-deploy-check` | Audita una URL y la compara con una captura de accesibilidad guardada. |
| `declaration-eaa` | Prepara un borrador de declaración de accesibilidad para revisión humana. |
| `blindfold-task` | Intenta completar una tarea con nombres accesibles y acciones de teclado, y registra las dificultades de cada paso. |

## Datos y seguridad

El toolkit se ejecuta con los permisos de tu usuario. Los argumentos de
archivo permiten leer o escribir en las rutas a las que tiene acceso ese
usuario. Las comprobaciones de URL y las del navegador se conectan a las
páginas que indiques. La validación HTML opcional con Nu envía la URL o
el HTML al validador configurado. Guarda en local los archivos de sesión
del navegador que contienen datos de autenticación.
[Política de seguridad y canal privado](SECURITY.md)

## Contribuye

Ejecuta `make test` desde la raíz del repositorio. Instala Playwright y
Chromium para ejecutar las pruebas con navegador. El catálogo de
herramientas y el índice para agentes se generan a partir de las
definiciones MCP. CI comprueba que estén sincronizados.
[Arquitectura](docs/ARCHITECTURE.md) · [Historial de cambios](CHANGELOG.md)

Puedes corregir un fallo, mejorar un ejemplo o añadir un idioma.
Comprueba los paquetes de traducción con `python3 tests/test_locales.py`.
[Guía de traducción](docs/i18n.md) ·
[Tareas para empezar](https://github.com/kinti/a11y-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3A%22good%20first%20issue%22) ·
[Debates](https://github.com/kinti/a11y-toolkit/discussions)

## Sobre el proyecto

Audito webs desde 2003. Construí este toolkit para que quien corrige un
problema pueda encontrarlo y quien revisa la corrección pueda comprobar
la evidencia. Si algún resultado te sorprende, comparte la página más
sencilla que permita reproducirlo. [Jesús Quintana Fernández](https://jquin.net/) ·
[Comunicar un problema](https://github.com/kinti/a11y-toolkit/issues/new/choose)

a11y.es usa este motor en su servicio de monitorización de accesibilidad. [a11y.es](https://a11y.es)

El código se distribuye bajo licencia MIT. Las distribuciones modificadas
usan nombre e identidad propios. [Licencia](LICENSE)
