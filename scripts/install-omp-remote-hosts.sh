#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOSTS="${OMP_REMOTE_HOSTS:-dever thump}"
REMOTE_BRANCH="${OMP_REMOTE_BRANCH:-$(git -C "$REPO_ROOT" branch --show-current)}"
REMOTE_REPO_PATH="${OMP_REMOTE_REPO_PATH:-}"
STRICT="${OMP_CONFIG_STRICT_REMOTE:-1}"

while (($#)); do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --best-effort) STRICT=0; shift ;;
    --hosts)
      [[ $# -ge 2 ]] || { echo "--hosts requires a space-separated host list" >&2; exit 2; }
      REMOTE_HOSTS="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || { echo "--branch requires a branch name" >&2; exit 2; }
      REMOTE_BRANCH="$2"
      shift 2
      ;;
    --repo-path)
      [[ $# -ge 2 ]] || { echo "--repo-path requires a remote checkout path" >&2; exit 2; }
      REMOTE_REPO_PATH="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--strict|--best-effort] [--hosts <list>] [--branch <name>] [--repo-path <path>]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$REMOTE_BRANCH" ]] || {
  echo "Cannot deploy OMP remotely without a checked-out local Git branch." >&2
  exit 2
}

if [[ "${OMP_CONFIG_SKIP_REMOTE:-0}" == 1 ]]; then
  echo "Remote OMP config deployment skipped by environment."
  exit 0
fi

hosts=()
for raw_host in $REMOTE_HOSTS; do
  host="${raw_host#"${raw_host%%[![:space:]]*}"}"
  host="${host%"${host##*[![:space:]]}"}"
  [[ -n "$host" ]] || continue
  duplicate=false
  for existing in "${hosts[@]:-}"; do
    [[ "$existing" == "$host" ]] && duplicate=true
  done
  [[ "$duplicate" == true ]] || hosts+=("$host")
done

failures=()
for host in "${hosts[@]}"; do
  echo "Pulling and installing OMP config on $host..."
  if ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
    env "OMP_REMOTE_BRANCH=$REMOTE_BRANCH" "OMP_REMOTE_REPO_PATH=$REMOTE_REPO_PATH" bash -s <<'REMOTE_INSTALL'
set -euo pipefail

repo_path="${OMP_REMOTE_REPO_PATH:-$HOME/code/ai-configs}"
cd -- "$repo_path"

current_branch="$(git branch --show-current)"
if [[ "$current_branch" != "$OMP_REMOTE_BRANCH" ]]; then
  echo "Remote checkout is on '$current_branch', expected '$OMP_REMOTE_BRANCH'." >&2
  exit 1
fi
if [[ -n "$(git status --short)" ]]; then
  echo "Remote checkout has local changes; refusing to pull over them." >&2
  git status --short >&2
  exit 1
fi

git pull --ff-only origin "$OMP_REMOTE_BRANCH"
OMP_CONFIG_PRUNE=1 bash _omp/install.sh
REMOTE_INSTALL
  then
    echo "  $host OMP config is current from Git."
  else
    exit_code=$?
    failures+=("$host")
    echo "  Warning: could not pull/install OMP config on $host (exit $exit_code); it may be offline, dirty, or misconfigured." >&2
  fi
done

if (( ${#failures[@]} > 0 )); then
  printf 'OMP config was not deployed to: %s\n' "${failures[*]}" >&2
  if [[ "$STRICT" == 1 ]]; then
    exit 1
  fi
fi
