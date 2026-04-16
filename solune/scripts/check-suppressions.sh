#!/usr/bin/env bash
# check-suppressions.sh — CI guard that ensures all lint/test suppressions
# carry a reason: justification.
#
# Exits 0 if all suppressions are justified, 1 if any lack a reason.
# Run from the repository root: ./solune/scripts/check-suppressions.sh
#
# Patterns checked:
#   Python: # noqa, # type: ignore, # pragma: no cover, # nosec
#   TypeScript/JS: eslint-disable, @ts-expect-error, @ts-ignore
#   Bicep: #disable-next-line
#
# Suppressions that already include "reason:" (case-insensitive) are allowed.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
EXIT_CODE=0

# Patterns to search for (regex)
SUPPRESSION_PATTERNS=(
  '# noqa'
  '# type: ignore'
  '# pragma: no cover'
  '# nosec'
  'eslint-disable'
  '@ts-expect-error'
  '@ts-ignore'
  '#disable-next-line'
)

# File extensions to search
FILE_EXTENSIONS=(
  '*.py'
  '*.ts'
  '*.tsx'
  '*.js'
  '*.jsx'
  '*.bicep'
)

# Directories to exclude
EXCLUDE_DIRS=(
  'node_modules'
  'dist'
  'build'
  '.venv'
  'venv'
  '__pycache__'
  'htmlcov'
  'coverage'
  '.git'
)

build_find_excludes() {
  local excludes=""
  for dir in "${EXCLUDE_DIRS[@]}"; do
    excludes="$excludes -path '*/$dir' -prune -o"
  done
  echo "$excludes"
}

build_find_includes() {
  local includes=""
  local first=true
  for ext in "${FILE_EXTENSIONS[@]}"; do
    if [ "$first" = true ]; then
      includes="-name '$ext'"
      first=false
    else
      includes="$includes -o -name '$ext'"
    fi
  done
  echo "\\( $includes \\)"
}

violations=0

for pattern in "${SUPPRESSION_PATTERNS[@]}"; do
  # Find files with suppressions that do NOT include "reason:" on the same line
  # or the previous line (for multi-line comments).
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    file="${line%%:*}"
    rest="${line#*:}"
    lineno="${rest%%:*}"
    content="${rest#*:}"

    # Check if this line or the preceding comment line contains "reason:"
    if echo "$content" | grep -qi 'reason:'; then
      continue
    fi

    # Check the line above for a reason comment
    prev_lineno=$((lineno - 1))
    if [ "$prev_lineno" -gt 0 ]; then
      prev_line=$(sed -n "${prev_lineno}p" "$file" 2>/dev/null || true)
      if echo "$prev_line" | grep -qi 'reason:'; then
        continue
      fi
    fi

    echo "  ✗ $file:$lineno: suppression without reason: $content"
    violations=$((violations + 1))
  done < <(
    eval "find '$REPO_ROOT' $(build_find_excludes) -type f $(build_find_includes) -print0" \
      | xargs -0 grep -n "$pattern" 2>/dev/null || true
  )
done

if [ "$violations" -gt 0 ]; then
  echo ""
  echo "Found $violations suppression(s) without a reason: justification."
  echo "Add a 'reason:' comment to each suppression, e.g.:"
  echo "  # noqa: B008 — reason: FastAPI Depends() pattern"
  echo "  // eslint-disable-next-line rule -- reason: explanation"
  EXIT_CODE=1
else
  echo "✓ All suppressions carry a reason: justification."
fi

exit $EXIT_CODE
