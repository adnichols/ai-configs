---
name: safe-git-index
description: Use when a Git command will mutate the index or when recovering from `.git/index.lock`.
---

# Safe Git Index Operations

Use `git-with-index-lock` for `add`, `commit`, `rm`, `mv`, `restore --staged`, `merge`, `rebase --continue`, `rebase --abort`, `cherry-pick`, `stash`, `apply`, and similar index-mutating commands.

## Resolve the wrapper once

Before the first index mutation in a session:

```bash
ENSURE="$(command -v ensure-git-with-index-lock 2>/dev/null || true)"
if [[ -z "$ENSURE" && -n "${AI_CONFIGS_ROOT:-}" && -x "${AI_CONFIGS_ROOT}/scripts/ensure-git-with-index-lock" ]]; then
  ENSURE="${AI_CONFIGS_ROOT}/scripts/ensure-git-with-index-lock"
fi
if [[ -z "$ENSURE" ]]; then
  TOP="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$TOP" && -x "$TOP/scripts/ensure-git-with-index-lock" ]]; then
    ENSURE="$TOP/scripts/ensure-git-with-index-lock"
  fi
fi
if [[ -n "$ENSURE" ]]; then
  GIT_WL="$("$ENSURE")" || exit 1
else
  for candidate in \
    "$HOME/.local/bin/git-with-index-lock" \
    "$HOME/.agents/scripts/git-with-index-lock" \
    "${AI_CONFIGS_ROOT:+$AI_CONFIGS_ROOT/scripts/git-with-index-lock}" \
    "${TOP:+$TOP/scripts/git-with-index-lock}" \
    "$HOME/code/ai-configs/scripts/git-with-index-lock"
  do
    [[ -n "$candidate" && -x "$candidate" ]] && GIT_WL="$candidate" && break
  done
fi
[[ -n "${GIT_WL:-}" ]] || { echo "git-with-index-lock unavailable" >&2; exit 1; }
```

Keep using the resolved absolute path:

```bash
"$GIT_WL" add <intended-paths>
"$GIT_WL" commit -m "message"
```

Stage explicit intended paths by default. Use `add -A` only when the entire working tree is known to belong to the authorized change.

## Lock recovery

The wrapper waits for a live lock holder and removes a lock only when it is unheld. Do not repeatedly retry raw Git commands. Do not manually remove `.git/index.lock` unless the wrapper is unavailable and `lsof "$(git rev-parse --git-path index.lock)"` confirms no process holds it.

If the resolver or wrapper is unavailable, stop and report the missing helper. Never silently fall back to raw index-mutating Git.
