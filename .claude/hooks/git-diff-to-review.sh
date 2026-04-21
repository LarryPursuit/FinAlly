#!/usr/bin/env bash
# Writes uncommitted + last-commit diff snapshot to planning/REVIEW.md (Stop hook).
set -euo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-.}"
cd "$ROOT"
mkdir -p planning
{
  printf '# Change snapshot (Stop hook)\n\n'
  printf 'Generated: %s\n\n' "$(date -u +%Y-%m-%dT%H:%MZ)"
  printf '## git diff (vs HEAD)\n\n'
  git diff HEAD || true
  printf '\n## git status\n\n'
  git status -sb || true
} > planning/REVIEW.md
