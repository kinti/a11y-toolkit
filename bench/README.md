# Benchmark: a11y-toolkit vs axe-core 4.10 — páginas reales

Metodología: en la MISMA página de Chromium y con el MISMO Playwright se ejecutan
(a) el auditor estático de a11y-toolkit sobre el HTML servido, (b) `a11y_audit_dom`
(renderizado) y (c) axe-core 4.10.3 inyectado. Se comparan los criterios WCAG
reportados por cada uno. Última ejecución: 2026-09-07, v3.5.0 (shadow DOM).

Repítelo: `python3 bench/compara.py <url…>` (necesita /tmp/axe.min.js — descárgalo
de cdn.jsdelivr.net/npm/axe-core).

## Resultados

| Página | Toolkit (est/dom) | Coincide con axe | Solo axe | Solo toolkit | Veredicto del triaje |
|---|---|---|---|---|---|
| example.com | 94 / 94 | 2.4.1 | — | — | acuerdo perfecto |
| **gov.uk** | 98 / **82** | — | 2.4.1 (`region`, 2 nodos) | **1.4.3 REAL** + 1.3.1 + 2.5.8 | **encontramos un fallo real que axe no reporta**: botón "Search GOV.UK", `#1d70b8` sobre `#d2e2f1` a 13px = 3.91:1 < 4.5 (verificado a mano). axe manda contraste a "incomplete"; nosotros lo calculamos |
| es.wikipedia (Portada) | 50 / 64 | 1.1.1, 1.3.1, 4.1.2 | 2.4.1 (`region`) | 1.4.3 (revisar: fondos con imagen), 2.1.1/3.3.2/2.4.4 (del pase estático) | HTML crudo vs DOM con JS: en sitios con mucho JS, usa `a11y_audit_dom` |
| jquin.net | 98 / 100 | — | — | 2.4.4 (aviso baja) | el sitio del autor pasa su propia auditoría |

`region` de axe (contenido FUERA de landmarks) es una comprobación de granularidad
distinta a la nuestra (que existe el mecanismo: main/skip-link), no un falso negativo.

## Falsos positivos que este benchmark destapó (y sus arreglos, v3.4.0)

1. `aria-hidden="true"` sobre controles con `tabindex="-1"` — no son tabulables;
   2.4.7/4.1.2 no aplican. **Arreglado** (estático + DOM).
2. Contenedor oculto tipo **honeypot** (input con `tabindex="-1"` dentro) reportado
   como control oculto. **Arreglado**: solo se reporta si algún descendiente es
   tabulable.
3. **Skip-link oculto** (1×1px con clip) reportado por 2.5.8. **Arreglado**: los
   elementos visualmente ocultos se excluyen del chequeo de tamaño.
4. Un **único enlace genérico** reportado como 2.4.4 — el contexto de la frase suele
   desambiguar. **Arreglado**: solo se reporta con repetición (≥2).
5. Enlaces inline de 20-24px: la **excepción de espaciado** de 2.5.8 no es medible
   sin layout completo; si todos los casos son inline, el hallazgo baja a "baja"
   (revisar) en lugar de "media".

Todos los casos tienen fixture de regresión en `test_dom.py` / `test_audit.py`.

## Límites conocidos y honestos

- axe y nosotros usamos umbrales distintos para "violación" vs "needs review";
  axe devuelve muchos contrastes como *incomplete* (excluidos aquí), nosotros los
  calculamos — de ahí los hallazgos de contraste que axe no lista.
- El pase estático refleja el HTML SERVIDO (antes de JS): en SPAs y sitios muy
  dinámicos es un filtro de primera pasada, no la verdad final.
- **Shadow DOM (v3.5.0)**: el colector atraviesa shadow roots ABIERTOS (tope 20
  raíces, profundidad 6) — contrast, targets, nombres, imágenes, foco y estados.
  Validado con fixture de web component (los 4 fallos interiores detectados con
  rutas `mi-tarjeta ::slotted> …`) y en producción: github.com (5 raíces) y
  m3.material.io (2 raíces) se escanea sin errores. Shadow roots CERRADOS son
  imposibles por diseño del navegador — se declara, no se oculta.
- Regla `list_structure` (1.3.1) añadida: hijos ilegales de `<ul>/<ol>` (regla
  `list` de axe).
