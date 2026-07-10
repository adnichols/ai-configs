#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
candidate="source"
compactions=10
fault_matrix="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --candidate) candidate="${2:?missing candidate}"; shift 2 ;;
    --compactions) compactions="${2:?missing count}"; shift 2 ;;
    --fault-matrix) fault_matrix="${2:?missing matrix}"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 --candidate source|installed --compactions N --fault-matrix all"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ "$candidate" == "source" || "$candidate" == "installed" ]] || { echo "candidate must be source or installed" >&2; exit 2; }
[[ "$compactions" =~ ^[0-9]+$ && "$compactions" -ge 10 ]] || { echo "compactions must be an integer >= 10" >&2; exit 2; }
[[ "$fault_matrix" == "all" ]] || { echo "only --fault-matrix all is supported" >&2; exit 2; }

root="$(mktemp -d "${TMPDIR:-/tmp}/pi-vcc-continuation-soak.XXXXXX")"
cleanup_on_success=0
finish() {
  status=$?
  if [[ $status -eq 0 && $cleanup_on_success -eq 1 ]]; then
    rm -rf "$root"
  else
    echo "pi-vcc soak artifacts preserved: $root" >&2
  fi
  exit $status
}
trap finish EXIT

export PI_CODING_AGENT_DIR="$root/agent"
export PI_CODING_AGENT_SESSION_DIR="$root/sessions"
export PI_VCC_LOG_PATH="$root/logs/pi-vcc.jsonl"
export PI_VCC_CONTINUATION_AUTHORITY=coordinator
export PI_OFFLINE=1
mkdir -p "$PI_CODING_AGENT_DIR" "$PI_CODING_AGENT_SESSION_DIR" "$root/logs"

if [[ "$candidate" == "source" ]]; then
  candidate_path="$repo_root/_pi/packages/pi-vcc"
  extension_path="$repo_root/_pi/extensions/percentage-compaction.ts"
else
  candidate_path="${PI_VCC_INSTALLED_PACKAGE:-$HOME/.pi/agent/local-packages/ai-configs/pi-vcc}"
  extension_path="${PI_VCC_INSTALLED_EXTENSION:-$HOME/.pi/agent/extensions/percentage-compaction.ts}"
fi

[[ -f "$candidate_path/src/core/coordinator.ts" ]] || { echo "candidate coordinator missing: $candidate_path" >&2; exit 1; }
[[ -f "$extension_path" ]] || { echo "candidate extension missing: $extension_path" >&2; exit 1; }

# Execute the selected candidate modules. The harness models Pi's public lifecycle contract
# without provider/network credentials; it does not silently substitute source for installed.
PI_VCC_CANDIDATE_PATH="$candidate_path" \
PI_VCC_EXTENSION_PATH="$extension_path" \
PI_VCC_SOAK_ROOT="$root" \
PI_VCC_SOAK_COMPACTIONS="$compactions" \
bun "$repo_root/scripts/pi-vcc-continuation-soak.ts"

python3 "$repo_root/scripts/audit-pi-vcc-continuations.py" \
  --log "$root/logs/pi-vcc.jsonl"

cat > "$root/validation-deviation.txt" <<EOF
Candidate: $candidate
Package: $candidate_path
Standalone extension inspected: $extension_path
Pi version: $(pi --version 2>/dev/null || echo unavailable)
Gate type: deterministic no-network host-faithful ExtensionAPI/EventBus/session harness.
Deviation: a real provider-backed Pi process was not driven because the rollout gate must not use external credentials/network. The selected source/installed createContinuationCoordinator was instantiated and driven through its real handlers/timers/reconcile/sendMessage paths, and the selected standalone percentage extension was loaded and executed through compact-now publisher ordering/wire parity. The mixed shared log audit passed. This artifact makes that boundary explicit rather than claiming a model-backed host run.
EOF

cleanup_on_success=1
echo "pi-vcc continuation soak: PASS candidate=$candidate compactions=$compactions fault-matrix=$fault_matrix"
