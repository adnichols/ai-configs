Commit all changes in the repo and push the changes up to github

Use `git-with-index-lock` for index-mutating steps (`add`, `commit`) instead of raw `git`.

Bootstrap when missing (new host / no PATH entry):

```bash
ENSURE="$(command -v ensure-git-with-index-lock 2>/dev/null || true)"
if [[ -z "$ENSURE" && -n "${AI_CONFIGS_ROOT:-}" && -x "${AI_CONFIGS_ROOT}/scripts/ensure-git-with-index-lock" ]]; then
  ENSURE="${AI_CONFIGS_ROOT}/scripts/ensure-git-with-index-lock"
fi
TOP="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ENSURE" && -n "$TOP" && -x "$TOP/scripts/ensure-git-with-index-lock" ]]; then
  ENSURE="$TOP/scripts/ensure-git-with-index-lock"
fi
if [[ -z "$ENSURE" ]]; then
  echo "git-with-index-lock bootstrap unavailable: set AI_CONFIGS_ROOT or run ai-configs install.sh" >&2
  exit 1
fi
GIT_WL="$("$ENSURE")" || exit 1
"$GIT_WL" add -A
"$GIT_WL" commit -m "$COMMIT_SUBJECT"
```

Do not silently fall back to raw index-mutating `git`.
