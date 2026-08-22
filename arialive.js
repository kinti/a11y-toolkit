/* Monitor de anuncios aria-live · v1.0 · jquin.net/lab
 * Inyectable como bookmarklet o vía Playwright (page.evaluate).
 * Registra cada anuncio de regiones dinámicas (aria-live, role=alert/status/
 * log) con hora, cortesía, rol y texto — lo que un lector de pantalla
 * "diría", visible en pantalla. Sin dependencias.
 */
(function () {
  'use strict';
  if (window.__ariaLiveMonitor) { window.__ariaLiveMonitor(); return; }
  var SEL = '[aria-live],[role=alert],[role=status],[role=log],[role=marquee],[role=timer]';
  var log = [];
  var observados = new WeakSet();

  var css = document.createElement('style');
  css.textContent = '.alm-panel{position:fixed;bottom:12px;right:12px;z-index:2147483647;' +
    'width:min(420px,90vw);max-height:45vh;overflow:auto;background:#111;color:#fff;' +
    'font:12px/1.5 ui-monospace,monospace;border:2px solid #ffd33d;border-radius:8px;padding:8px}' +
    '.alm-panel button{background:#ffd33d;color:#111;border:0;border-radius:4px;padding:3px 8px;' +
    'font:inherit;cursor:pointer;margin-left:6px}' +
    '.alm-e{padding:4px 6px;border-bottom:1px solid #333;white-space:pre-wrap}' +
    '.alm-t{color:#ffd33d}.alm-e b{color:#8ec2f5}';
  document.head.appendChild(css);

  var panel = document.createElement('div');
  panel.className = 'alm-panel';
  // Sin role="log" a propósito: una región viva casaría con nuestro propio
  // selector y crearía un bucle de auto-observación infinito.
  panel.setAttribute('aria-label', 'Monitor de anuncios aria-live');
  panel.innerHTML = '<div><span class="alm-t">aria-live monitor</span>' +
    '<button type="button" data-alm="copy">Copiar</button>' +
    '<button type="button" data-alm="close">Cerrar</button></div><div data-alm="log"></div>';
  document.body.appendChild(panel);
  var cont = panel.querySelector('[data-alm=log]');

  function desc(el) {
    var d = el.tagName.toLowerCase();
    if (el.id) d += '#' + el.id;
    else if (el.className && typeof el.className === 'string')
      d += '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.');
    return d;
  }

  function anota(el, razon) {
    var rol = el.getAttribute('role') || '(sin role)';
    var cortesia = el.getAttribute('aria-live') ||
      ({ alert: 'assertive', status: 'polite', log: 'polite',
         marquee: 'off', timer: 'off' })[el.getAttribute('role')] || 'polite';
    var texto = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 220);
    var hora = new Date().toTimeString().slice(0, 8);
    log.push(hora + ' [' + cortesia + '] ' + rol + ' · ' + desc(el) + ' · ' + texto);
    var fila = document.createElement('div');
    fila.className = 'alm-e';
    fila.innerHTML = '<span class="alm-t">' + hora + '</span> [' + cortesia + '] <b>' + rol +
      '</b> · ' + desc(el) + (razon ? ' <i>(' + razon + ')</i>' : '') + '<br>' + texto;
    cont.appendChild(fila);
    panel.scrollTop = panel.scrollHeight;
  }

  function vigila(el) {
    if (!el || observados.has(el) || el.nodeType !== 1) return;
    // Nunca monitorizar nuestro propio panel (bucle de auto-observación).
    if (el.closest && el.closest('.alm-panel')) return;
    if (!el.matches(SEL)) return;
    observados.add(el);
    if (el.getAttribute('role') === 'alert') anota(el, 'insertado');
    new MutationObserver(function () {
      anota(el, null);
    }).observe(el, { childList: true, characterData: true, subtree: true });
  }

  document.querySelectorAll(SEL).forEach(function (el) { vigila(el); });

  new MutationObserver(function (muts) {
    muts.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        vigila(n);
        if (n.querySelectorAll) n.querySelectorAll(SEL).forEach(vigila);
      });
    });
  }).observe(document.body, { childList: true, subtree: true });

  panel.addEventListener('click', function (ev) {
    var b = ev.target.closest('button');
    if (!b) return;
    if (b.dataset.alm === 'close') { panel.remove(); css.remove(); delete window.__ariaLiveMonitor; }
    if (b.dataset.alm === 'copy' && navigator.clipboard)
      navigator.clipboard.writeText(log.join('\n'));
  });

  window.__ariaLiveMonitor = function () { panel.remove(); css.remove(); delete window.__ariaLiveMonitor; };
})();
