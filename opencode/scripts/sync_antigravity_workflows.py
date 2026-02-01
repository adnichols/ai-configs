#!/usr/bin/env python3
"""Generate Antigravity global workflows from opencode command markdown.

This creates Antigravity-compatible workflow files (YAML frontmatter + numbered
steps) in the global workflows directory so they can be invoked as `/...`
commands.

Defaults:
  - Source: ~/code/ai-configs/opencode/commands/*.md
  - Dest:   ~/.gemini/antigravity/global_workflows/
  - Names:  oc-<sanitized-stem>.md (':' -> '-', lowercased, safe chars only)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
from pathlib import Path


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def sanitize_workflow_stem(stem: str, prefix: str) -> str:
    # Prefer portable workflow names (no ':'), and avoid collisions.
    s = stem.lower().replace(":", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s:
        s = "workflow"
    return f"{prefix}{s}"


def extract_description(markdown: str, fallback: str) -> str:
    # Antigravity workflow metadata is YAML frontmatter with `description`.
    if markdown.startswith("---"):
        lines = markdown.splitlines()
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx is not None:
            for line in lines[1:end_idx]:
                if line.lstrip().startswith("description:"):
                    value = line.split(":", 1)[1].strip().strip("\"'")
                    if value:
                        return value

    for line in markdown.splitlines():
        s = line.strip()
        if s:
            return s[:200]

    return fallback


def build_wrapper_workflow(*, description: str, src_path: Path, stem: str) -> str:
    oc_tag = f"[OpenCode {stem}]"
    full_desc = f"{oc_tag} {description}".strip()

    # Keep the workflow body short; it delegates to the source command file.
    return "\n".join(
        [
            "---",
            f"description: {full_desc}",
            "---",
            "",
            "1. Ask for any missing inputs implied by this command (OpenCode may refer to `$ARGUMENTS`).",
            f"2. Read the source command file at `{src_path}`.",
            "3. Follow the source instructions, adapting OpenCode-specific terms using `Compatibility` below.",
            "4. If you cannot read the source file (workspace/permissions limits), open `~/code/ai-configs` in Antigravity and retry.",
            "",
            "## Compatibility",
            "- OpenCode `Task` / subagents: use Antigravity Agent Manager (parallel chats) or split the work into multiple conversations.",
            "- OpenCode `todowrite`: use a numbered plan / Task Plan artifact and update it as you work.",
            "- OpenCode `Bash` tool: run terminal commands in Antigravity (respect terminal policy; don't auto-run destructive commands unless allowed).",
            "",
            "## Source",
            f"- `{src_path}`",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Antigravity global workflows from opencode command markdown.",
    )
    parser.add_argument(
        "--src",
        default="~/code/ai-configs/opencode/commands",
        help="Directory containing opencode command .md files",
    )
    parser.add_argument(
        "--dst",
        default="~/.gemini/antigravity/global_workflows",
        help="Destination directory for Antigravity global workflows",
    )
    parser.add_argument(
        "--prefix",
        default="oc-",
        help="Prefix for generated workflow filenames",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without writing files",
    )
    args = parser.parse_args()

    src_dir = _expand(args.src)
    dst_dir = _expand(args.dst)
    prefix = args.prefix

    if not src_dir.is_dir():
        raise SystemExit(f"Missing source directory: {src_dir}")

    dst_dir.mkdir(parents=True, exist_ok=True)

    src_files = sorted(glob.glob(str(src_dir / "*.md")))
    if not src_files:
        print(f"No source files found at: {src_dir}/*.md")
        return 0

    written = 0
    for src_file in src_files:
        src_path = Path(src_file).resolve()
        if src_path.name == "README.md":
            continue

        raw = src_path.read_text(encoding="utf-8", errors="replace")
        desc = extract_description(
            raw, fallback=f"OpenCode command wrapper for {src_path.name}"
        )
        stem = src_path.stem
        out_stem = sanitize_workflow_stem(stem, prefix)
        out_path = dst_dir / f"{out_stem}.md"

        content = build_wrapper_workflow(description=desc, src_path=src_path, stem=stem)

        if args.dry_run:
            print(out_path)
            continue

        out_path.write_text(content, encoding="utf-8")
        written += 1

    if not args.dry_run:
        print(f"Wrote {written} workflow(s) to: {dst_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
