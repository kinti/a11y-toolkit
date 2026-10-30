#!/usr/bin/env node
/* Launcher: runs the SELF-CONTAINED engine that ships inside this package
 * (a11y_toolkit/, pure-stdlib Python). No downloads at runtime when a
 * python3 (>=3.9) exists; falls back to a version-pinned uvx when it does
 * not. Zero install, zero network, reproducible by construction. */
const { spawn, spawnSync } = require('child_process');
const path = require('path');

const ENGINE = path.join(__dirname, '..');          // where a11y_toolkit/ lives
const PY = process.platform === 'win32' ? 'python' : 'python3';
const UVX = process.platform === 'win32' ? 'uvx.exe' : 'uvx';
const VERSION = require('../package.json').version;  // pinned fallback, same release

function pythonOk() {
  try {
    const r = spawnSync(PY, ['-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)']);
    return r.status === 0;
  } catch { return false; }
}

function run(entry) {
  const args = process.argv.slice(2);
  if (pythonOk()) {
    const child = spawn(PY, ['-m', entry, ...args],
                        { stdio: 'inherit', env: { ...process.env, PYTHONPATH: ENGINE } });
    child.on('close', (c) => process.exit(c === null ? 1 : c));
    return;
  }
  const SCRIPTS = { 'a11y_toolkit.a11y': 'a11ytoolkit', 'a11y_toolkit.server': 'a11y-toolkit-mcp' };
  const child = spawn(UVX, ['--from', `a11y-toolkit==${VERSION}`, SCRIPTS[entry] || entry], { stdio: 'inherit' });
  child.on('error', (e) => {
    if (e.code === 'ENOENT') {
      console.error('a11y-toolkit: needs python3 (>=3.9) or uv.');
      console.error('  uv (one line): curl -LsSf https://astral.sh/uv/install.sh | sh');
      console.error('  or python3:    https://www.python.org/downloads/');
      console.error('https://github.com/kinti/a11y-toolkit');
      process.exit(1);
    }
    throw e;
  });
  child.on('close', (c) => process.exit(c === null ? 1 : c));
}

module.exports = { run };
