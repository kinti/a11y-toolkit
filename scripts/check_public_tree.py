#!/usr/bin/env python3
"""Check the exact staged content before publishing the public engine."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


_PATH_MARKERS = ('drafts/', 'internal/', '.draft.md', '.local.md', 'competencia',
                 'competitor', 'backlog', 'estrategia', 'zcodeignore')
_OPERATIONAL_CONTENT = re.compile(
    rb'-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----'
    rb'|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'
    rb'|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'
    rb'|\bssh\s+-i\s+/(?:root|home/[^\s/]+)/\.ssh/')


def _git(*args):
    return subprocess.check_output(['git', *args])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='check the full staged tree')
    args = parser.parse_args(argv)
    os.chdir(os.fsdecode(_git('rev-parse', '--show-toplevel').strip()))
    common = Path(os.fsdecode(_git('rev-parse', '--git-common-dir').strip()))
    private_terms = common / 'a11y-internal-terms.txt'
    terms = [b'a11y-' + b'drafts']
    if private_terms.is_file():
        terms.extend(term for line in private_terms.read_bytes().lower().splitlines()
                     if (term := line.strip()) and not term.startswith(b'#'))

    paths = (_git('ls-files', '-z', '--cached') if args.all else
             _git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'))
    refused = []
    for name in paths.split(b'\0'):
        if not name:
            continue
        path = os.fsdecode(name)
        low_path = path.lower()
        if (any(marker in low_path for marker in _PATH_MARKERS)
                or re.fullmatch(r'blog-.*\.png', low_path)
                or Path(low_path).name in {'.env', 'storage_state.json'}):
            refused.append((path, 'internal path or working artifact'))
            continue
        data = _git('show', f':{path}')
        if _OPERATIONAL_CONTENT.search(data):
            refused.append((path, 'credential or host-specific deployment instruction'))
        elif not path.startswith(('bench/tetra-acl/', 'bench/results/')):
            lower = data.lower()
            if any(term in lower for term in terms):
                refused.append((path, 'internal terminology'))

    for path, reason in refused:
        print(f'Public tree check refused {path!r} ({reason})', file=sys.stderr)
    return 1 if refused else 0


if __name__ == '__main__':
    raise SystemExit(main())
