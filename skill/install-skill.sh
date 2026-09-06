#!/usr/bin/env bash
# Installs the a11y-toolkit skill into the user's agent skill directories.
set -euo pipefail
ORIGEN="$(cd "$(dirname "$0")" && pwd)"
DESTINOS=("$HOME/.zcode/skills" "$HOME/.claude/skills")
for d in "${DESTINOS[@]}"; do
  if [ -d "$(dirname "$d")" ]; then
    mkdir -p "$d"
    rm -rf "$d/a11y-toolkit"
    cp -R "$ORIGEN/a11y-toolkit" "$d/a11y-toolkit"
    echo "✓ instalado en $d/a11y-toolkit"
  fi
done
