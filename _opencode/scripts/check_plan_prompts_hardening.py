#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from check_dev_plan_hardening import main as check_dev_plan_hardening_main
from check_planning_workflow_doctrine import (
    main as check_planning_workflow_doctrine_main,
)


PROMPT_PATHS = [
    Path("agents/plan-gpt.md"),
    Path("agents/plan-k2.5.md"),
    Path("agents/_plan.md"),
    Path("agents/aplan.md"),
]

REQUIRED_PHRASES = [
    "You are a planning partner in discovery mode. You inspect the codebase, validate assumptions, and prepare the inputs needed for a later plan-writing step. You are read-only in this mode.",
    "Your job is to help the user shape a plan that is well thought through, appropriately scoped, broken into phases, testable, and executable. You may inspect code and gather context, but you are not responsible for writing the final plan file in this mode. Use a later plan-materialization step such as `dev:plan` to write the actual plan.",
    "Use targeted `Read`, `Grep`, and `Glob` passes first; delegate broader discovery only when those read-only passes are not enough.",
    "Treat unresolved contracts, migrations, rollout semantics, compatibility behavior, safety constraints, or cross-surface behavior as `low-confidence` decisions.",
    "Resolve low-confidence decisions from repo evidence first and capture the evidence needed for a later `dev:plan` handoff.",
    "If repo evidence is insufficient and the choice changes intended behavior, ask the user before recommending handoff to `dev:plan`.",
    "If the answer is researchable without new user intent, recommend delegated research or a research-first branch before `dev:plan` materializes anything.",
    "When delegating research, use only `Task` with `subagent_type=Explore` or another read-only explore helper that exists in the current runtime; never delegate implementation or other state-changing work from plan mode.",
    "Make it explicit that open foundational questions require research-first or a non-ready `research-ready` planning output; they must not be carried into a misleadingly `execution-ready` plan.",
    "Never bury low-confidence decisions inside future execution phases just to keep planning moving.",
    "Keep this workflow read-only and domain-agnostic.",
]

BANNED_TERMS = ["rust", "mcp", "react", "next.js", "tokio"]

FORBIDDEN_BODY_PHRASES = [
    "You can write plans to thoughts/plans/ directory",
    "You are responsible for authoring and writing out a plan file",
    "Never modify non-plan files",
]

REQUIRED_FRONTMATTER_VALUES = {
    ("permission", "question"): "allow",
    ("permission", "edit", "*"): "deny",
    ("permission", "write", "*"): "deny",
    ("permission", "pty_spawn"): "deny",
    ("permission", "pty_read"): "deny",
    ("permission", "pty_write"): "deny",
    ("permission", "pty_list"): "deny",
    ("permission", "pty_kill"): "deny",
    ("tools", "edit"): "false",
    ("tools", "write"): "false",
    ("tools", "bash"): "false",
    ("tools", "webfetch"): "true",
    ("tools", "read"): "true",
    ("tools", "glob"): "true",
    ("tools", "grep"): "true",
    ("tools", "exa_web_search_exa"): "true",
    ("tools", "exa_get_code_context_exa"): "true",
    ("tools", "exa-code_get_code_context_exa"): "true",
    ("tools", "exa_company_research_exa"): "true",
    ("tools", "task"): "true",
    ("tools", "list"): "true",
    ("tools", "todowrite"): "false",
    ("tools", "todoread"): "true",
}

FORBIDDEN_FRONTMATTER_TERMS = ["thoughts/plans/"]
FORBIDDEN_FRONTMATTER_PREFIXES = [("permissions",)]

EXPECTED_BODY = """# Plan Mode - System Reminder

You are a planning partner in discovery mode. You inspect the codebase, validate assumptions, and prepare the inputs needed for a later plan-writing step. You are read-only in this mode.

Your job is to help the user shape a plan that is well thought through, appropriately scoped, broken into phases, testable, and executable. You may inspect code and gather context, but you are not responsible for writing the final plan file in this mode. Use a later plan-materialization step such as `dev:plan` to write the actual plan.

Non-negotiable boundaries
- Never modify files: do not create/edit/delete/rename/format files.
- Avoid side effects: do not run commands that can change the working tree or environment (no installs, codegen, formatters, migrations, git commits, rebases, resets).

## Responsibility

Your current responsibility is to think, read, search, and delegate explore agents to construct the evidence and decisions that a later plan-writing step will need. Be comprehensive enough to support execution, but keep the output focused on validated facts, open decisions, and recommended phase structure.

Use targeted `Read`, `Grep`, and `Glob` passes first; delegate broader discovery only when those read-only passes are not enough.

Ask the user clarifying questions or ask for their opinion when weighing tradeoffs.

**NOTE:** At any point in time through this workflow you should feel free to ask the user questions or clarifications. Don't make large assumptions about user intent. The goal is to prepare a well researched planning package and tie up loose ends before `dev:plan` writes the execution plan.

## Low-confidence decision handling

- Treat unresolved contracts, migrations, rollout semantics, compatibility behavior, safety constraints, or cross-surface behavior as `low-confidence` decisions.
- Resolve low-confidence decisions from repo evidence first and capture the evidence needed for a later `dev:plan` handoff.
- If repo evidence is insufficient and the choice changes intended behavior, ask the user before recommending handoff to `dev:plan`.
- If the answer is researchable without new user intent, recommend delegated research or a research-first branch before `dev:plan` materializes anything.
- When delegating research, use only `Task` with `subagent_type=Explore` or another read-only explore helper that exists in the current runtime; never delegate implementation or other state-changing work from plan mode.
- Make it explicit that open foundational questions require research-first or a non-ready `research-ready` planning output; they must not be carried into a misleadingly `execution-ready` plan.
- Never bury low-confidence decisions inside future execution phases just to keep planning moving.
- Keep this workflow read-only and domain-agnostic.

</system-reminder>"""


def require_phrases(label: str, content: str, phrases: list[str]) -> None:
    missing = [phrase for phrase in phrases if phrase not in content]
    if missing:
        raise AssertionError(f"{label} missing phrases: {missing}")


def require_terms(label: str, content: str, terms: list[str]) -> None:
    haystack = content.lower()
    missing = [term for term in terms if term.lower() not in haystack]
    if missing:
        raise AssertionError(f"{label} missing terms: {missing}")


def require_exact_body(label: str, content: str, expected: str) -> None:
    if content != expected:
        raise AssertionError(
            f"{label} body drifted from canonical prompt contract; update the prompt and checker together"
        )


def forbid_terms(label: str, content: str, terms: list[str]) -> None:
    haystack = content.lower()
    present = [term for term in terms if term.lower() in haystack]
    if present:
        raise AssertionError(f"{label} contains forbidden terms: {present}")


def prompt_body(text: str) -> str:
    marker = "<system-reminder>\n"
    start = text.find(marker)
    if start == -1:
        raise AssertionError("missing <system-reminder> block")
    return text[start + len(marker) :].strip()


def prompt_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise AssertionError("missing frontmatter start")

    end = text.find("\n---\n", 4)
    if end == -1:
        raise AssertionError("missing frontmatter end")

    return text[4:end]


def parse_frontmatter_paths(content: str) -> dict[tuple[str, ...], str]:
    paths: dict[tuple[str, ...], str] = {}
    stack: list[tuple[int, str]] = []

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        if not raw_line.strip():
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise AssertionError(f"frontmatter line {line_number} has non-even indent")

        line = raw_line.strip()
        if ":" not in line:
            raise AssertionError(
                f"frontmatter line {line_number} is not a key/value entry"
            )

        key, value = line.split(":", 1)
        key = key.strip().strip('"').strip("'")
        value = value.strip()

        while stack and stack[-1][0] >= indent:
            stack.pop()

        path = tuple(part for _, part in stack) + (key,)
        if path in paths:
            rendered = ".".join(path)
            raise AssertionError(f"duplicate frontmatter key path: {rendered}")

        if value:
            paths[path] = value
        else:
            stack.append((indent, key))

    return paths


def require_frontmatter_values(
    label: str, paths: dict[tuple[str, ...], str], expected: dict[tuple[str, ...], str]
) -> None:
    missing = []
    wrong = []
    for path, expected_value in expected.items():
        actual_value = paths.get(path)
        rendered = ".".join(path)
        if actual_value is None:
            missing.append(rendered)
            continue
        if actual_value != expected_value:
            wrong.append(f"{rendered}={actual_value!r} (expected {expected_value!r})")

    if missing or wrong:
        details = []
        if missing:
            details.append(f"missing {missing}")
        if wrong:
            details.append(f"wrong values {wrong}")
        raise AssertionError(f"{label} frontmatter invalid: {'; '.join(details)}")


def forbid_unexpected_permission_or_tool_paths(
    label: str, paths: dict[tuple[str, ...], str], expected: dict[tuple[str, ...], str]
) -> None:
    allowed_paths = set(expected)
    unexpected = [
        ".".join(path)
        for path in paths
        if path[:1] in {("permission",), ("tools",)} and path not in allowed_paths
    ]
    if unexpected:
        raise AssertionError(
            f"{label} contains unexpected permission/tool paths: {unexpected}"
        )


def forbid_frontmatter_terms(label: str, content: str, terms: list[str]) -> None:
    present = [term for term in terms if term in content]
    if present:
        raise AssertionError(f"{label} contains forbidden frontmatter terms: {present}")


def forbid_frontmatter_prefixes(
    label: str, paths: dict[tuple[str, ...], str], prefixes: list[tuple[str, ...]]
) -> None:
    present = []
    for path in paths:
        for prefix in prefixes:
            if path[: len(prefix)] == prefix:
                present.append(".".join(path))
                break

    if present:
        raise AssertionError(
            f"{label} contains forbidden frontmatter key paths: {present}"
        )


def forbid_non_question_allows(label: str, paths: dict[tuple[str, ...], str]) -> None:
    unexpected = []
    for path, value in paths.items():
        if path[:1] != ("permission",) or value != "allow":
            continue
        if path != ("permission", "question"):
            unexpected.append(".".join(path))

    if unexpected:
        raise AssertionError(
            f"{label} contains unexpected writable permission grants: {unexpected}"
        )


def require_frontmatter_parity(parsed: dict[Path, dict[tuple[str, ...], str]]) -> None:
    reference_path = PROMPT_PATHS[0]
    reference = {
        path: value
        for path, value in parsed[reference_path].items()
        if path[:1] in {("permission",), ("tools",)}
    }

    drifted = []
    for prompt_path, values in parsed.items():
        if prompt_path == reference_path:
            continue
        current = {
            path: value
            for path, value in values.items()
            if path[:1] in {("permission",), ("tools",)}
        }
        if current != reference:
            drifted.append(str(prompt_path))

    if drifted:
        raise AssertionError(
            "plan-mode prompt frontmatter drifted from each other: "
            + ", ".join(drifted)
        )


def main() -> None:
    bodies: dict[Path, str] = {}
    frontmatters: dict[Path, dict[tuple[str, ...], str]] = {}

    check_planning_workflow_doctrine_main()
    check_dev_plan_hardening_main()

    for path in PROMPT_PATHS:
        text = path.read_text()
        frontmatter_text = prompt_frontmatter(text)
        frontmatter = parse_frontmatter_paths(frontmatter_text)
        body = prompt_body(text)
        bodies[path] = body
        frontmatters[path] = frontmatter

        require_frontmatter_values(str(path), frontmatter, REQUIRED_FRONTMATTER_VALUES)
        forbid_unexpected_permission_or_tool_paths(
            str(path), frontmatter, REQUIRED_FRONTMATTER_VALUES
        )
        forbid_frontmatter_terms(
            str(path), frontmatter_text, FORBIDDEN_FRONTMATTER_TERMS
        )
        forbid_frontmatter_prefixes(
            str(path), frontmatter, FORBIDDEN_FRONTMATTER_PREFIXES
        )
        forbid_non_question_allows(str(path), frontmatter)
        require_exact_body(str(path), body, EXPECTED_BODY)
        require_phrases(str(path), body, REQUIRED_PHRASES)
        require_terms(
            str(path),
            body,
            [
                "low-confidence",
                "repo evidence",
                "ask the user",
                "research",
                "read",
                "grep",
                "glob",
                "task",
                "subagent_type=explore",
                "read-only explore helper",
                "research-ready",
                "execution-ready",
                "read-only",
                "domain-agnostic",
            ],
        )
        forbid_terms(str(path), body, FORBIDDEN_BODY_PHRASES)
        forbid_terms(str(path), body, BANNED_TERMS)

    require_frontmatter_parity(frontmatters)

    reference_path = PROMPT_PATHS[0]
    reference_body = bodies[reference_path]
    drifted = [
        str(path)
        for path, body in bodies.items()
        if path != reference_path and body != reference_body
    ]
    if drifted:
        raise AssertionError(
            "plan-mode prompt bodies drifted from each other: " + ", ".join(drifted)
        )

    print("planning-agent prompts contain required hardening concepts")


if __name__ == "__main__":
    main()
