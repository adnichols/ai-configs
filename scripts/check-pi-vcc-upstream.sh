#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENDORED_DIR_REL="./_pi/packages/pi-vcc"
VENDORED_DIR="$REPO_ROOT/_pi/packages/pi-vcc"
README_PATH="$VENDORED_DIR/README.md"
PACKAGE_JSON="$VENDORED_DIR/package.json"
UPSTREAM_REPO_URL="https://github.com/sting8k/pi-vcc.git"
VERBOSE=0

# Path-level intentional manifest against the reviewed upstream commit recorded
# in _pi/packages/pi-vcc/README.md. Entries include both local fork patches and
# deliberately skipped upstream changes; any unlisted path drift fails.
EXPECTED_LOCAL_DIFFS=(
  ".gitignore|repo-local ignore set differs from upstream package repo"
  "README.md|vendored README documents local fork contract and reviewed uptake"
  "demo.gif|upstream demo asset intentionally not vendored"
  "index.ts|preserve @earendil-works import/local registration behavior"
  "package.json|preserve local package name/version and peer dependency ranges"
  "src/commands/pi-vcc.ts|preserve __PI_VCC_MANUAL_BYPASS__ command marker"
  "src/commands/vcc-recall.ts|preserve local recall command behavior"
  "src/core/brief.ts|preserve redaction/tool-error policy plus bashExecution uptake"
  "src/core/build-sections.ts|preserve local tool-error outstanding-context behavior plus local intent wiring"
  "src/core/compact-args.ts|adapt upstream keep parsing to local manual bypass marker"
  "src/core/content.ts|preserve local content handling"
  "src/core/filter-noise.ts|skip upstream broad noise-cleanup churn"
  "src/core/format.ts|approved TUI wrapping uptake with local output contract"
  "src/core/lineage.ts|skip upstream active-lineage recall feature"
  "src/core/load-messages.ts|preserve local session loading behavior"
  "src/core/normalize.ts|approved bashExecution uptake plus local thinking/tool-error handling"
  "src/core/protected-tools.ts|local protected tool-result retention policy shared by pruning and summary rendering"
  "src/core/prune.ts|local deterministic summary-only pruning stage"
  "src/core/recall-scope.ts|skip upstream recall-scope feature"
  "src/core/redact.ts|preserve local redaction despite upstream removal"
  "src/core/render-entries.ts|approved explicit bashExecution typing/rendering"
  "src/core/report.ts|approved report recall-hit searchEntries argument fix"
  "src/core/search-entries.ts|approved explicit bashExecution search handling"
  "src/core/settings.ts|skip upstream settings scaffold"
  "src/core/summarize.ts|approved wrapping uptake while preserving final redaction/local continuation summary contract"
  "src/details.ts|preserve local compaction details"
  "src/extract/commits.ts|omit upstream commit extraction from local summaries"
  "src/extract/files.ts|preserve local file extraction behavior"
  "src/extract/goals.ts|preserve local goal extraction behavior"
  "src/extract/preferences.ts|preserve local preference extraction behavior"
  "src/hooks/before-compact.ts|preserve local compaction cut, continuation, marker behavior, intent parsing, and overflow fallback"
  "src/sections.ts|preserve local summary contract with intent additions"
  "src/tools/recall.ts|preserve local recall tool behavior"
  "src/types.ts|approved bashExecution typing plus local block shape"
  "tests/before-compact-hook.test.ts|skip upstream settings/hook test surface"
  "tests/before-compact.test.ts|preserve local compaction invariant tests"
  "tests/brief.test.ts|approved bashExecution test plus local redaction/tool-error tests"
  "tests/build-sections.test.ts|preserve local section/tool-error tests"
  "tests/compile.test.ts|approved wrapping tests plus local final redaction, intent, and pruning tests"
  "tests/extract-goals.test.ts|preserve local extraction tests"
  "tests/filter-noise.test.ts|skip upstream broad noise-cleanup churn"
  "tests/fixtures.ts|preserve local test fixtures"
  "tests/format.test.ts|approved wrapping tests plus local section contract"
  "tests/lineage.test.ts|skip upstream active-lineage recall tests"
  "tests/load-messages.test.ts|skip upstream load-message tests not in local package"
  "tests/normalize.test.ts|approved bashExecution test plus local thinking/tool-error tests"
  "tests/pi-vcc-command.test.ts|skip upstream command harness because local command behavior is covered in package tests"
  "tests/report.test.ts|approved report recall-hit and bashExecution report metrics tests"
  "tests/recall-expand.test.ts|skip upstream recall expansion test surface"
  "tests/recall-scope.test.ts|skip upstream recall-scope test surface"
  "tests/recall-tool-scope.test.ts|skip upstream recall-scope test surface"
  "tests/render-entries.test.ts|approved explicit bashExecution rendering tests"
  "tests/search-entries.test.ts|approved bashExecution search tests plus local search behavior"
  "tests/support/load-session.ts|preserve local real-session fixture loading"
)

for arg in "$@"; do
  case "$arg" in
    --verbose|-v)
      VERBOSE=1
      ;;
    --summary)
      ;;
    *)
      echo "Usage: $0 [--verbose]" >&2
      exit 1
      ;;
  esac
done

if [ ! -d "$VENDORED_DIR" ]; then
  echo "Vendored pi-vcc directory not found: $VENDORED_DIR_REL" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required" >&2
  exit 1
fi

LOCAL_PACKAGE_VERSION="$(python3 - "$PACKAGE_JSON" <<'PY'
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    print(json.load(f)['version'])
PY
)"

read_reviewed_metadata() {
  python3 - "$README_PATH" <<'PY'
import re, sys
text = open(sys.argv[1], 'r', encoding='utf-8').read()
version = re.search(r'^- Reviewed upstream version: `([^`]+)`$', text, re.M)
commit = re.search(r'^- Reviewed upstream commit: `([0-9a-f]{7,40})`$', text, re.M)
print(version.group(1) if version else '')
print(commit.group(1) if commit else '')
PY
}

REVIEWED_METADATA="$(read_reviewed_metadata)"
REVIEWED_UPSTREAM_VERSION="$(printf '%s\n' "$REVIEWED_METADATA" | sed -n '1p')"
REVIEWED_UPSTREAM_COMMIT="$(printf '%s\n' "$REVIEWED_METADATA" | sed -n '2p')"

NPM_LATEST_VERSION="$(npm view @sting8k/pi-vcc version 2>/dev/null || true)"
UPSTREAM_HEAD="$(git ls-remote "$UPSTREAM_REPO_URL" refs/heads/master | awk '{print $1}')"

printf 'pi-vcc upstream check\n'
printf 'vendored path: %s\n' "$VENDORED_DIR_REL"
printf 'local package version: %s\n' "$LOCAL_PACKAGE_VERSION"
printf 'reviewed upstream version: %s\n' "${REVIEWED_UPSTREAM_VERSION:-<missing from README>}"
printf 'reviewed upstream commit: %s\n' "${REVIEWED_UPSTREAM_COMMIT:-<missing from README>}"
printf 'npm latest version: %s\n' "${NPM_LATEST_VERSION:-<unavailable>}"
printf 'upstream master head: %s\n' "${UPSTREAM_HEAD:-<unavailable>}"

STALE=0
if [ -z "$REVIEWED_UPSTREAM_VERSION" ] || [ -z "$REVIEWED_UPSTREAM_COMMIT" ]; then
  printf 'version status: reviewed upstream metadata missing\n'
  printf 'commit status: reviewed upstream metadata missing\n'
  STALE=1
else
  if [ -z "$NPM_LATEST_VERSION" ]; then
    printf 'version status: unknown (npm latest unavailable)\n'
  elif [ "$NPM_LATEST_VERSION" != "$REVIEWED_UPSTREAM_VERSION" ]; then
    printf 'version status: RE-REVIEW REQUIRED (reviewed %s, npm latest %s)\n' "$REVIEWED_UPSTREAM_VERSION" "$NPM_LATEST_VERSION"
    STALE=1
  else
    printf 'version status: reviewed upstream version matches npm latest\n'
  fi

  if [ -z "$UPSTREAM_HEAD" ]; then
    printf 'commit status: unknown (upstream head unavailable)\n'
  elif [ "$UPSTREAM_HEAD" != "$REVIEWED_UPSTREAM_COMMIT" ]; then
    printf 'commit status: RE-REVIEW REQUIRED (reviewed %s, upstream %s)\n' "$REVIEWED_UPSTREAM_COMMIT" "$UPSTREAM_HEAD"
    STALE=1
  else
    printf 'commit status: reviewed upstream commit matches upstream head\n'
  fi
fi

if [ "$STALE" -ne 0 ]; then
  printf 'drift status: not checked because reviewed upstream metadata is stale or missing\n'
  exit 2
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

git init -q "$TMP_DIR/upstream"
git -C "$TMP_DIR/upstream" remote add origin "$UPSTREAM_REPO_URL"
git -C "$TMP_DIR/upstream" fetch --depth 1 origin "$REVIEWED_UPSTREAM_COMMIT" >/dev/null 2>&1
git -C "$TMP_DIR/upstream" checkout -q --detach FETCH_HEAD

NORMALIZED_DIFFS="$(python3 - "$TMP_DIR/upstream" "$VENDORED_DIR" <<'PY'
from pathlib import Path
import os, sys

upstream = Path(sys.argv[1])
vendored = Path(sys.argv[2])
ignore_dirs = {'.git', 'node_modules'}
ignore_files = {'package-lock.json'}

def collect(root: Path):
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        base = Path(dirpath)
        for filename in filenames:
            if filename in ignore_files:
                continue
            path = base / filename
            rel = path.relative_to(root).as_posix()
            files[rel] = path
    return files

left = collect(upstream)
right = collect(vendored)
all_paths = sorted(set(left) | set(right))
diffs = []
for rel in all_paths:
    l = left.get(rel)
    r = right.get(rel)
    if l is None or r is None:
        diffs.append(rel)
        continue
    if l.read_bytes() != r.read_bytes():
        diffs.append(rel)
print('\n'.join(diffs))
PY
)"

EXPECTED_DIFFS_TEXT="$(printf '%s\n' "${EXPECTED_LOCAL_DIFFS[@]}" | awk -F'|' '{print $1}' | sort -u)"
UNEXPECTED_DIFFS="$({
  comm -23 \
    <(printf '%s\n' "$NORMALIZED_DIFFS" | sed '/^$/d' | sort -u) \
    <(printf '%s\n' "$EXPECTED_DIFFS_TEXT" | sed '/^$/d' | sort -u)
} || true)"
MISSING_EXPECTED_DIFFS="$({
  comm -23 \
    <(printf '%s\n' "$EXPECTED_DIFFS_TEXT" | sed '/^$/d' | sort -u) \
    <(printf '%s\n' "$NORMALIZED_DIFFS" | sed '/^$/d' | sort -u)
} || true)"

DRIFT_COUNT="$(printf '%s\n' "$NORMALIZED_DIFFS" | sed '/^$/d' | wc -l | tr -d ' ')"
UNEXPECTED_COUNT="$(printf '%s\n' "$UNEXPECTED_DIFFS" | sed '/^$/d' | wc -l | tr -d ' ')"
MISSING_COUNT="$(printf '%s\n' "$MISSING_EXPECTED_DIFFS" | sed '/^$/d' | wc -l | tr -d ' ')"

if [ -z "$NORMALIZED_DIFFS" ]; then
  printf 'drift status: no local diffs vs reviewed upstream commit\n'
elif [ -n "$UNEXPECTED_DIFFS" ]; then
  printf 'drift status: unexpected local diffs present\n'
elif [ -n "$MISSING_EXPECTED_DIFFS" ]; then
  printf 'drift status: intentional diff manifest contains stale paths\n'
else
  printf 'drift status: only intentional diffs present (%s paths)\n' "$DRIFT_COUNT"
fi

if [ "$UNEXPECTED_COUNT" -gt 0 ]; then
  printf 'unexpected diff count: %s\n' "$UNEXPECTED_COUNT"
fi

if [ "$MISSING_COUNT" -gt 0 ]; then
  printf 'missing expected diff count: %s\n' "$MISSING_COUNT"
fi

if [ "$VERBOSE" -eq 1 ]; then
  printf '\nlocal drift vs reviewed upstream commit:\n'
  if [ -z "$NORMALIZED_DIFFS" ]; then
    printf '  none\n'
  else
    while IFS= read -r item; do
      [ -n "$item" ] || continue
      printf '  %s\n' "$item"
    done <<EOF
$NORMALIZED_DIFFS
EOF
  fi

  printf '\nintentional diff manifest:\n'
  while IFS='|' read -r path reason; do
    [ -n "$path" ] || continue
    printf '  %s — %s\n' "$path" "$reason"
  done <<EOF
$(printf '%s\n' "${EXPECTED_LOCAL_DIFFS[@]}" | sort -u)
EOF

  if [ -n "$UNEXPECTED_DIFFS" ]; then
    printf '\nunexpected diffs:\n'
    while IFS= read -r item; do
      [ -n "$item" ] || continue
      printf '  %s\n' "$item"
    done <<EOF
$UNEXPECTED_DIFFS
EOF
  fi

  if [ -n "$MISSING_EXPECTED_DIFFS" ]; then
    printf '\nmanifest entries without current diffs:\n'
    while IFS= read -r item; do
      [ -n "$item" ] || continue
      printf '  %s\n' "$item"
    done <<EOF
$MISSING_EXPECTED_DIFFS
EOF
  fi
elif [ "$UNEXPECTED_COUNT" -gt 0 ] || [ "$MISSING_COUNT" -gt 0 ]; then
  printf 'review details with: ./scripts/check-pi-vcc-upstream.sh --verbose\n'
fi

if [ -n "$UNEXPECTED_DIFFS" ]; then
  exit 1
fi

if [ -n "$MISSING_EXPECTED_DIFFS" ]; then
  exit 1
fi
