#!/bin/bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-review.sh --mode <implementation-review|plan-review|pair> --input <file> [--cwd <dir>] [--output <file>]

Examples:
  run-review.sh --mode implementation-review --input /tmp/review.md --cwd /path/to/repo
  run-review.sh --mode plan-review --input /tmp/plan.md --cwd /path/to/repo --output /tmp/review-output.md

Notes:
  - The wrapper runs Codex in non-interactive exec mode.
  - Keep the outer tool timeout at 300s minimum for blocking runs.
  - For long reviews, launch the outer command asynchronously and wait for completion.
EOF
}

MODE=""
INPUT_PATH=""
TARGET_CWD=""
OUTPUT_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --input)
      INPUT_PATH="${2:-}"
      shift 2
      ;;
    --cwd)
      TARGET_CWD="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_PATH="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$MODE" || -z "$INPUT_PATH" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$INPUT_PATH" ]]; then
  echo "Input file not found: $INPUT_PATH" >&2
  exit 1
fi

if [[ -n "$TARGET_CWD" && ! -d "$TARGET_CWD" ]]; then
  echo "Working directory not found: $TARGET_CWD" >&2
  exit 1
fi

case "$MODE" in
  implementation-review)
    REVIEW_CONTRACT=$'You are performing an implementation review. Review-partner invocation is already active. Do not spawn nested Codex review sessions. Stay read-only. Do not run or invoke tests, test suites, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or any other executable checks intended to validate behavior. You may inspect test code and caller-supplied verification results, but you must not execute them; the calling/coordinating agent exclusively owns test and verification execution. Read-only inspection commands such as git diff, rg, and file reads are allowed. Focus on correctness, edge cases, missed callsites, test gaps, and maintainability. Return concise structured findings with severity labels.'
    ;;
  plan-review)
    REVIEW_CONTRACT=$'You are performing a plan review. Review-partner invocation is already active. Do not spawn nested Codex review sessions. Stay read-only. Do not run or invoke tests, test suites, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or any other executable checks intended to validate behavior. You may inspect test code and caller-supplied verification results, but you must not execute them; the calling/coordinating agent exclusively owns test and verification execution. Read-only inspection commands such as git diff, rg, and file reads are allowed. Focus on missing steps, unsafe assumptions, sequencing risks, verification gaps, migration hazards, and rollback concerns. Return concise structured findings with severity labels.'
    ;;
  pair)
    REVIEW_CONTRACT=$'You are acting as a pairing partner. Review-partner invocation is already active. Do not spawn nested Codex review sessions. Stay read-only unless the user explicitly asks for edits in this inner session. Focus on tradeoffs, debugging next steps, likely failure modes, and simplifications.'
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    usage >&2
    exit 1
    ;;
esac

PROMPT_CONTENT="$(<"$INPUT_PATH")"
if [[ -z "$PROMPT_CONTENT" ]]; then
  echo "Input file is empty: $INPUT_PATH" >&2
  exit 1
fi

WORK_DIR="$PWD"
if [[ -n "$TARGET_CWD" ]]; then
  WORK_DIR="$TARGET_CWD"
fi

if [[ -n "$OUTPUT_PATH" ]]; then
  mkdir -p "$(dirname "$OUTPUT_PATH")"
fi

TMP_OUTPUT="$(mktemp)"
cleanup() {
  rm -f "$TMP_OUTPUT"
}
trap cleanup EXIT

printf '%s' "$PROMPT_CONTENT" |
  env CODEX_REVIEW_PARTNER_ACTIVE=1 codex exec \
    -m gpt-5.6-sol \
    -c 'model_reasoning_effort="high"' \
    -s read-only \
    -C "$WORK_DIR" \
    - | tee "$TMP_OUTPUT"

if [[ -n "$OUTPUT_PATH" ]]; then
  cp "$TMP_OUTPUT" "$OUTPUT_PATH"
fi
