#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_PATH="${SKILL_DIR}/references/ccore-skill-guide.md"

ccore skill --output "${OUTPUT_PATH}"
printf 'Wrote %s\n' "${OUTPUT_PATH}"
