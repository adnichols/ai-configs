#!/usr/bin/env python3
"""Guardrail against direct Claude Code CLI launch transports in review surfaces."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_ROOTS = ["_pi", "skills", "_opencode", "_claude", "_omp", "_codex", "scripts"]
REVIEW_HINT_RE = re.compile(r"claude-code-review|review|reviewed-html-plan|run-plan|codex-full-build|linear_build|linear-build|review:change-claude-code|review:plan-adversarial|_pi/README\.md", re.I)
FORBIDDEN_MARKER = "[FORBIDDEN-EXAMPLE]"
FORBIDDEN_FENCE = "forbidden-claude-launch"
CANONICAL_LAUNCHER_SUFFIX = "claude-code-review/scripts/claude_interactive_review.py"
GUARDRAIL_SUFFIX = "claude-code-review/scripts/check_no_direct_claude_review_launches.py"
TEST_SUFFIX_FRAGMENT = "claude-code-review/tests/"
ALLOWED_LAUNCHER_FORMS = (
    "zsh -ilc 'command -v claude'",
    "claude auth status",
    "zsh -ilc 'claude --model claude-sonnet-4-6'",
    "zsh -ilc 'claude --model {CLAUDE_REVIEW_MODEL}'",
)
IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
SCAN_EXTENSIONS = {".md", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml", ".txt", ".html"}

DIRECT_PATTERNS = [
    re.compile(r"\bclaude\s+-(?:p|\-print)\b"),
    re.compile(r"\bclaude\s+--permission-mode\b"),
    re.compile(r"\bclaude\s+--file\b"),
    re.compile(r"\bclaude\s+--future-[\w-]+\b"),
    re.compile(r"\|\s*claude\b"),
    re.compile(r"\bclaude\s*<"),
    re.compile(r"\bos\.execvp\([^\n]*claude"),
    re.compile(r"\bsubprocess\.[A-Za-z_]+\([^\n]*claude"),
    re.compile(r"\binteractive_shell\([^\n]*claude"),
    re.compile(r"\bprocess\([^\n]*claude"),
    re.compile(r"\bbash\([^\n]*claude"),
    re.compile(r"\btmux\s+(?:new-window|new-session|split-window|send-keys)[^\n]*\bclaude\b"),
    re.compile(r"\bzsh\s+-il?c\s+['\"][^'\"]*\bclaude\b"),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*['\"]?(?:exec\s+)?claude(?:\s|['\"]|$)"),
]
RAW_CLAUDE_CMD_RE = re.compile(r"(^|[;&|`$({\[]|\s)(?:exec\s+)?claude(?:\s|$)")
MULTILINE_DIRECT_PATTERNS = [
    re.compile(r"\bsubprocess\.[A-Za-z_]+\s*\([^\n)]*\[[^\]]*['\"]claude['\"]", re.S),
    re.compile(r"\bos\.execv?p?\s*\([^\n)]*\[[^\]]*['\"]claude['\"]", re.S),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*\[\s*['\"]claude['\"]", re.S),
]


def rel_suffix(path: Path) -> str:
    return str(path).replace(os.sep, "/")


def is_exempt_path(path: Path) -> bool:
    rel = rel_suffix(path)
    return rel.endswith(GUARDRAIL_SUFFIX) or TEST_SUFFIX_FRAGMENT in rel


def is_launcher_path(path: Path) -> bool:
    return rel_suffix(path).endswith(CANONICAL_LAUNCHER_SUFFIX)


def is_scan_path(path: Path) -> bool:
    rel = rel_suffix(path)
    if path.suffix and path.suffix not in SCAN_EXTENSIONS:
        return False
    return REVIEW_HINT_RE.search(rel) is not None


def iter_files(root: Path):
    if root.is_file():
        if is_scan_path(root):
            yield root
        return
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if is_scan_path(path):
                yield path


def in_forbidden_fence(lines: list[str], index: int) -> bool:
    in_fence = False
    for line in lines[: index + 1]:
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = stripped[3:].strip() == FORBIDDEN_FENCE
            else:
                in_fence = False
    return in_fence


def is_marked_forbidden_example(lines: list[str], index: int) -> bool:
    line = lines[index]
    return FORBIDDEN_MARKER in line or in_forbidden_fence(lines, index)


def is_benign_non_candidate(line: str) -> bool:
    stripped = line.strip()
    benign_bits = [
        "claude-code-review",
        "claude_interactive_review.py",
        "claude-plan-",
        "CLAUDE_REVIEW_",
        "interactive Claude review",
        "Claude Code review",
        "claude-opus",
        "opencode-zen/claude",
        "canonical private-tmux interactive launcher",
        "missing `tmux` or `claude`",
    ]
    if any(bit in stripped for bit in benign_bits) and not any(p.search(stripped) for p in DIRECT_PATTERNS):
        return True
    return False


def line_has_invocation_candidate(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or is_benign_non_candidate(stripped):
        return False
    if any(p.search(stripped) for p in DIRECT_PATTERNS):
        return True
    if RAW_CLAUDE_CMD_RE.search(stripped):
        # Do not flag prose sentences like "Claude Code ..."; require command-like context.
        commandish_prefixes = ("claude ", "claude", "exec claude", "command -v claude", "cd ", "RUN_", "CLAUDE_", "python", "node", "tmux", "zsh", "bash")
        return stripped.startswith(commandish_prefixes) or any(token in stripped for token in ("| claude", "&& claude", "; claude", "'claude", '"claude'))
    return False


def allowed_launcher_line(path: Path, line: str) -> bool:
    if not is_launcher_path(path):
        return False
    return any(form in line for form in ALLOWED_LAUNCHER_FORMS)


def scan_file(path: Path) -> list[tuple[int, str]]:
    if is_exempt_path(path):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="replace")
    lines = text.splitlines()
    findings: list[tuple[int, str]] = []
    seen_lines: set[int] = set()
    for idx, line in enumerate(lines):
        if not line_has_invocation_candidate(line):
            continue
        if is_marked_forbidden_example(lines, idx):
            continue
        if allowed_launcher_line(path, line):
            continue
        findings.append((idx + 1, line.strip()))
        seen_lines.add(idx + 1)
    for pattern in MULTILINE_DIRECT_PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            if line_no in seen_lines:
                continue
            if is_marked_forbidden_example(lines, line_no - 1):
                continue
            snippet = " ".join(match.group(0).split())
            findings.append((line_no, snippet))
            seen_lines.add(line_no)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail if review surfaces contain direct Claude Code CLI launches")
    parser.add_argument("--root", action="append", dest="roots")
    args = parser.parse_args(argv)
    roots = [Path(p).expanduser() for p in (args.roots or DEFAULT_ROOTS)]
    all_findings: list[str] = []
    for root in roots:
        for path in iter_files(root):
            for line_no, line in scan_file(path):
                all_findings.append(f"{path}:{line_no}: direct Claude review launch candidate: {line}")
    if all_findings:
        print("CLAUDE_DIRECT_REVIEW_LAUNCHES_FOUND")
        print("\n".join(all_findings))
        return 1
    print("NO_DIRECT_CLAUDE_REVIEW_LAUNCHES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
