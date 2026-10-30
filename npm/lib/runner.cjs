#!/usr/bin/env node
/* Shared launcher: runs the a11y-toolkit engine through uv (uvx).
 * The engine is Python (stdlib-only); this wrapper only opens the Node
 * door. If uv is missing, we say exactly how to get it — no cryptic
 * spawn errors. */
const { spawn } = require('child_process');

const UVX = process.platform === 'win32' ? 'uvx.exe' : 'uvx';
// Pin de versión: el launcher SIEMPRE ejecuta la versión del motor con la
// que se publicó (la de este package.json, que versionar bumbea con cada
// release). Reproducible y auditable: nada de "descarga la última" en
// tiempo de ejecución.
const VERSION = require('../package.json').version;

function run(entry) {
  const args = ['--from', `a11y-toolkit==${VERSION}`, entry, ...process.argv.slice(2)];
  const child = spawn(UVX, args, { stdio: 'inherit' });
  child.on('error', (e) => {
    if (e.code === 'ENOENT') {
      console.error('a11y-toolkit: "uvx" (uv) is not installed.');
      console.error('');
      console.error('The engine is Python; this launcher runs it via uv. Install uv (one line):');
      console.error('  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh');
      console.error('  macOS (brew): brew install uv');
      console.error('  Windows (PowerShell): powershell -c "irm https://astral.sh/uv/install.ps1 | iex"');
      console.error('  or:  pip install uv');
      console.error('');
      console.error('Then run this command again. https://github.com/kinti/a11y-toolkit');
      process.exit(1);
    }
    throw e;
  });
  child.on('close', (code) => process.exit(code === null ? 1 : code));
}

module.exports = { run };
