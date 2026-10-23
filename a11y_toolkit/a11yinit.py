#!/usr/bin/env python3
"""`a11ytoolkit init` — installs the agent hook in the current project.

Writes (or updates, idempotently) an AGENTS.md block that tells coding agents
the one rule that matters: after any UI change, re-audit accessibility before
calling the work done — with the exact commands to do it. Also prints the MCP
config block and the optional skill install step.

Offline by design: no network, no filesystem assumptions beyond AGENTS.md.
"""

import argparse
import json
import os
import sys

MARKER_BEGIN = '<!-- BEGIN a11y-toolkit agent hook -->'
MARKER_END = '<!-- END a11y-toolkit agent hook -->'

BLOCK = f'''{MARKER_BEGIN}

## Accessibility guardrails — a11y-toolkit

After any UI change (HTML, CSS, templates, components, copy that becomes
visible text), run an accessibility audit BEFORE considering the work done.
The audit is part of the change, not an afterthought.

Quick loop (no install needed — uvx runs it from PyPI):

```bash
uvx --from a11y-toolkit a11ytoolkit audit --file path/to/page.html   # static, 0-100 score
uvx --from a11y-toolkit a11ytoolkit audit --url https://localhost:3000
```

Acting on findings:

1. `high` and `medium` findings block the change: apply the remediation each
   finding carries, then re-audit until clear (or document why it stays).
2. Judgment findings (alt text wording, which color to pick) are HUMAN calls:
   propose an option, never invent final copy. The tool marks them as
   `not_applied` with the reason — that is by design.
3. Ask `uvx --from a11y-toolkit a11ytoolkit criterion --signal <id>` when a
   finding's signal needs explaining (it returns the criterion, the official
   W3C Understanding link and the published ACT rule, if any).

If the a11y-toolkit MCP server is connected, prefer the `a11y_*` tools — same
engine, richer output. Before deploys, snapshot + diff catches regressions:

```bash
uvx --from a11y-toolkit a11ytoolkit snapshot https://staging --out before.json
# ...deploy...
uvx --from a11y-toolkit a11ytoolkit diff before.json <(uvx --from a11y-toolkit a11ytoolkit snapshot https://staging)
```

{MARKER_END}
'''

MCP_CONFIG = {
    'mcpServers': {
        'a11y-toolkit': {
            'command': 'uvx',
            'args': ['--from', 'a11y-toolkit', 'a11y-toolkit-mcp'],
        }
    }
}


def merge_block(content):
    """Merge the hook block into existing AGENTS.md content (idempotent)."""
    if MARKER_BEGIN in content:
        start = content.index(MARKER_BEGIN)
        end = content.index(MARKER_END) + len(MARKER_END)
        return content[:start] + BLOCK.strip('\n') + content[end:]
    return (content.rstrip('\n') + '\n\n' if content.strip() else '') + BLOCK.strip('\n') + '\n'


def init(path='.'):
    """Install the agent hook. Returns dict with what happened."""
    filepath = os.path.join(path, 'AGENTS.md')
    previous = open(filepath, encoding='utf-8').read() if os.path.exists(filepath) else ''
    merged = merge_block(previous)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(merged)
    return {'file': filepath, 'already_present': MARKER_BEGIN in previous,
            'created': not previous.strip()}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('path', nargs='?', default='.', help='project directory (default: current)')
    ap.add_argument('--check', action='store_true', help='only report whether the hook is present')
    a = ap.parse_args(argv)
    if a.check:
        target = os.path.join(a.path, 'AGENTS.md')
        presente = os.path.exists(target) and MARKER_BEGIN in open(target, encoding='utf-8').read()
        print(json.dumps({'hook_present': presente, 'file': target}))
        return 0 if presente else 1
    res = init(a.path)
    verbo = 'updated' if res['already_present'] else ('created' if res['created'] else 'installed into')
    print(f"✓ agent hook {verbo}: {res['file']}")
    print('\nMCP config (any MCP client that accepts stdio servers):')
    print(json.dumps(MCP_CONFIG, indent=2))
    print('\nOptional — the agent skill (audit→fix→document→watch loop):')
    print('  curl -fsSL https://raw.githubusercontent.com/kinti/a11y-toolkit/main/skill/install-skill.sh | bash')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

# alias para el dispatcher del hub CLI (convención *_main)
def init_main(argv):
    return main(argv)
