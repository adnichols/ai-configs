#!/usr/bin/env python3
"""Reject maintained Pi required-review instructions that bypass codex_review."""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
FILES = [
    ROOT / "skills/pre-pr-implementation-review/SKILL.md",
    ROOT / "skills/run-plan/SKILL.md",
    ROOT / "skills/reviewed-html-plan/SKILL.md",
    *sorted((ROOT / "_pi/prompts").glob("*.md")),
]
REVIEW_MODES = r"(?:implementation-review|adversarial-implementation-review|plan-review)"


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_text(text: str, *, prompt_file: bool) -> list[tuple[int, str]]:
    """Find positive launch signatures across continuation lines and shell variables."""
    findings: list[tuple[int, str]] = []
    # Explicit exemptions are line-local and intentionally narrow; they are for
    # policy documentation/fixtures, never an exemption for an executable block.
    exempt_lines = {index for index, line in enumerate(text.splitlines(), 1) if "codex-review-policy-exempt" in line}
    normalized = re.sub(r"\\\s*\n\s*", " ", text)
    patterns = []
    if prompt_file:
        patterns.extend([
            rf"run-review\.sh\b(?:(?!\n\s*\n)[\s\S]){{0,500}}?--mode\s+{REVIEW_MODES}\b",
            r"\bcodex\s+exec\s+review\b",
        ])
        assignments = re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^\n]*run-review\.sh[^\n]*$", normalized)
        for variable in assignments:
            reference = rf"(?:\$\{{{re.escape(variable)}\}}|\${re.escape(variable)})"
            patterns.append(rf"(?:bash\s+)?[\"']?{reference}[\"']?(?:(?!\n\s*\n)[\s\S]){{0,500}}?--mode\s+{REVIEW_MODES}\b")
    else:
        patterns.append(r"In Pi(?:(?!\n\s*\n)[\s\S]){0,500}?(?:subprocess|run Codex as)")
    for pattern in patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            line = _line_number(normalized, match.start())
            if line in exempt_lines:
                continue
            snippet = " ".join(match.group(0).split())[:240]
            findings.append((line, snippet))
    return sorted(set(findings))


def main() -> int:
    bad = []
    for file in FILES:
        for number, snippet in scan_text(file.read_text(), prompt_file=True):
            bad.append(f"{file.relative_to(ROOT)}:{number}: {snippet}")
    if bad:
        print("Maintained Pi required reviews must use codex_review:", file=sys.stderr)
        print("\n".join(bad), file=sys.stderr)
        return 1
    print("PASS: maintained Pi required Codex reviews use codex_review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
