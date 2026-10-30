// a11y-toolkit for VS Code — v0.1 skeleton.
// Runs the self-contained engine via npx (the npm package ships the Python
// inside; only python3 must exist on the machine) and surfaces findings in
// the Problems panel. No settings, no telemetry.
const vscode = require('vscode');
const { spawn } = require('child_process');

const NPM_PKG = '@kinti/a11y-toolkit';

function runEngine(args) {
  return new Promise((resolve) => {
    const p = spawn('npx', ['-y', NPM_PKG, ...args], { cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath });
    let out = '', err = '';
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (err += d));
    p.on('close', (code) => resolve({ code, out, err }));
    p.on('error', (e) => resolve({ code: 1, out: '', err: String(e) }));
  });
}

function auditToDiagnostics(doc, report, collection) {
  const diags = [];
  for (const f of report.findings || []) {
    const line = Math.max(0, (f.line || 1) - 1);
    const sev = f.severity === 'high' ? vscode.DiagnosticSeverity.Error
              : f.severity === 'medium' ? vscode.DiagnosticSeverity.Warning
              : vscode.DiagnosticSeverity.Information;
    const d = new vscode.Diagnostic(new vscode.Range(line, 0, line, 200),
      `${f.criterion} — ${f.issue} (${f.signal}) · fix: ${f.remediation}`, sev);
    d.source = 'a11y-toolkit';
    diags.push(d);
  }
  collection.set(doc.uri, diags);
  const s = report.score != null ? ` · score ${report.score}/100` : '';
  vscode.window.setStatusBarMessage(
    `a11y: ${diags.length} findings${s} — automation ≈1/3 of WCAG; the rest needs you`, 8000);
}

function activate(context) {
  const collection = vscode.languages.createDiagnosticCollection('a11y-toolkit');
  const auditFile = vscode.commands.registerCommand('a11y.auditFile', async () => {
    const doc = vscode.window.activeTextEditor?.document;
    if (!doc || !/\.(html?|vue|astro)$/i.test(doc.fileName)) {
      vscode.window.showWarningMessage('a11y: open an HTML file to audit.');
      return;
    }
    await doc.save();
    const { code, out, err } = await runEngine(['audit', '--file', doc.fileName]);
    if (code !== 0) { vscode.window.showErrorMessage(`a11y: ${err.slice(0, 200)}`); return; }
    try { auditToDiagnostics(doc, JSON.parse(out), collection); }
    catch { vscode.window.showErrorMessage('a11y: unparsable report — is python3 (>=3.9) installed?'); }
  });
  const auditChanged = vscode.commands.registerCommand('a11y.auditChanged', async () => {
    const { code, out, err } = await runEngine(['audit', '--changed']);
    if (code !== 0) { vscode.window.showErrorMessage(`a11y: ${err.slice(0, 200)}`); return; }
    try {
      const r = JSON.parse(out);
      const n = (r.reports || [r]).reduce((a, x) => a + (x.findings?.length || 0), 0);
      vscode.window.showInformationMessage(
        `a11y: ${n} findings in what this branch touched (exit gate: ${r.verdict || code}).`);
    } catch { vscode.window.showErrorMessage('a11y: unparsable report.'); }
  });
  context.subscriptions.push(collection, auditFile, auditChanged);
}

module.exports = { activate };
