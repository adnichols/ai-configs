#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from check_dev_plan_hardening import main as check_dev_plan_hardening_main
from check_planning_workflow_doctrine import (
    main as check_planning_workflow_doctrine_main,
)
from check_ralph_run_feedback_loop import main as check_ralph_run_feedback_loop_main


SKILL_PATH = Path("skills/repo-agents-bootstrap/SKILL.md")
ROOT_TEMPLATE_PATH = Path(
    "skills/repo-agents-bootstrap/references/root_agents_template.md"
)
PLAN_TEMPLATE_PATH = Path(
    "skills/repo-agents-bootstrap/references/plan_agents_template.md"
)
README_PATH = Path("commands/README.md")


def get_section(text: str, heading: str, level: int = 2) -> str:
    marker = f"{'#' * level} {heading}\n"
    start = text.find(marker)
    if start == -1:
        raise AssertionError(f"missing section: {heading}")
    start += len(marker)
    next_marker = f"\n{'#' * level} "
    end = text.find(next_marker, start)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def require_terms(label: str, content: str, terms: list[str]) -> None:
    haystack = content.lower()
    missing = [term for term in terms if term.lower() not in haystack]
    if missing:
        raise AssertionError(f"{label} missing terms: {missing}")


def require_phrases(label: str, content: str, phrases: list[str]) -> None:
    missing = [phrase for phrase in phrases if phrase not in content]
    if missing:
        raise AssertionError(f"{label} missing phrases: {missing}")


def forbid_phrases(label: str, content: str, phrases: list[str]) -> None:
    present = [phrase for phrase in phrases if phrase in content]
    if present:
        raise AssertionError(f"{label} contains forbidden phrases: {present}")


def main() -> None:
    check_planning_workflow_doctrine_main()
    check_dev_plan_hardening_main()
    check_ralph_run_feedback_loop_main()

    skill_text = SKILL_PATH.read_text()
    root_template_text = ROOT_TEMPLATE_PATH.read_text()
    plan_template_text = PLAN_TEMPLATE_PATH.read_text()
    readme_text = README_PATH.read_text()

    operating_model = get_section(skill_text, "Operating Model To Codify")
    require_phrases(
        "bootstrap skill operating model",
        operating_model,
        [
            "- `dev:plan` must fail closed on `low-confidence` foundational decisions: it only hands off an `execution-ready` plan when those decisions are resolved, and otherwise asks the user or writes exactly one non-ready `research-ready` plan artifact with the exact next research action.",
            "- Phase advancement only when the latest review returns `VERDICT: PASS_NO_ISSUES`, or `VERDICT: PASS_LOW_RISK_ONLY` after each remaining item is proven out-of-scope, low-risk, not required for truthful verification, and logged in the repo's discovery ledger (for example `thoughts/discoveries/<plan-or-feature>.md`) plus the plan's `## Decisions / Deviations Log`.",
            "- Review loops are hard gates: reviewer narrative alone never clears a phase; only the verdict-based phase-advance rule above can do that.",
            "- Keep planning depth `complexity-aware`: simple tasks stay lightweight, while non-trivial ready plans need complete contracts plus a `test coverage matrix` strong enough to catch partial implementations.",
            "- Execution feedback loops must reassess the `original test scope` and original plan when substantive misses appear; repeated or cross-surface misses widen coverage or plan scope instead of staying local.",
            "- Repo-local planning overrides stay additive: they can tighten the shared defaults, but they must not replace or relax the central doctrine.",
        ],
    )
    forbid_phrases(
        "bootstrap skill operating model",
        operating_model,
        [
            "until zero critical issues",
            "unresolved critical issues",
            "zero critical issues",
        ],
    )

    write_agents = get_section(skill_text, "3) Write/update root AGENTS.md", level=3)
    require_phrases(
        "bootstrap skill root AGENTS guidance",
        write_agents,
        [
            "- The shared fail-closed ready bar: only `execution-ready` plans hand off to implementation, while unresolved `low-confidence` decisions stay in discovery or move into a single `research-ready` artifact.",
            "- The shared expectation that non-trivial ready plans include a `test coverage matrix`.",
            "- The shared execution feedback loop: substantive review misses reassess the `original test scope` and original plan, and repeated or cross-surface misses widen coverage before phase advance.",
            "- The repo's discovery-ledger destination for documented out-of-scope low-risk items (for example `thoughts/discoveries/<plan-or-feature>.md`).",
        ],
    )

    add_overrides = get_section(
        skill_text, "4) Add repo-local planning overrides only when needed", level=3
    )
    require_phrases(
        "bootstrap skill override guidance",
        add_overrides,
        [
            "- Keep repo-local overrides additive to the shared `execution-ready` / `research-ready` readiness model, `low-confidence` decision closure, `test coverage matrix` default, and execution feedback loop.",
        ],
    )

    audit_plan_corpus = get_section(
        skill_text,
        "2b) Audit current plan corpus against standards (required for `audit_only` and `migrate_existing`)",
        level=3,
    )
    require_phrases(
        "bootstrap skill plan corpus audit guidance",
        audit_plan_corpus,
        [
            "- `Open Questions` only in non-ready plans (`draft`, `discovery`, or `research-ready`), never in `execution-ready` plans",
        ],
    )
    forbid_phrases(
        "bootstrap skill plan corpus audit guidance",
        audit_plan_corpus,
        ["- `Open Questions` present in execution-ready plans"],
    )

    require_phrases(
        "bootstrap skill legacy migration rule",
        add_overrides,
        [
            "- Only allow `Open Questions` when plan status is explicitly `draft`, `discovery`, or `research-ready`; `execution-ready` plans must resolve them.",
        ],
    )

    root_plan_mode = get_section(root_template_text, "5) Plan execution mode", level=2)
    require_phrases(
        "root AGENTS template plan execution mode",
        root_plan_mode,
        [
            "Add the shared fail-closed ready bar:",
            "- only `execution-ready` plans can hand off to execution",
            "- unresolved `low-confidence` foundational decisions stay in read-only discovery or move into a single non-ready `research-ready` plan artifact with the exact next research action",
            "- only `execution-ready` plans should continue into review/execution commands; `research-ready` artifacts should send the agent to the recorded next research action and then back through `dev:plan`",
            "Require non-trivial ready plans to include a `test coverage matrix` that maps acceptance criteria and scenarios to intended tests and verify commands.",
            "Codify the execution feedback loop: substantive review misses must reassess the `original test scope` and original plan, and repeated or cross-surface misses must widen coverage or plan scope before the phase can advance.",
            "- re-review until the latest verdict is `VERDICT: PASS_NO_ISSUES` or `VERDICT: PASS_LOW_RISK_ONLY` with every remaining item proven out-of-scope, low-risk, not required for truthful verification, and logged in the repo's discovery ledger (for example `thoughts/discoveries/<plan-or-feature>.md`) plus the plan's `## Decisions / Deviations Log`",
            "Require the repo guidance to name the canonical discovery-ledger destination explicitly so documented out-of-scope low-risk findings always have a durable home.",
        ],
    )

    plan_objective = get_section(plan_template_text, "Objective")
    require_phrases(
        "plan overrides template objective",
        plan_objective,
        [
            "- Keep repo-local overrides additive to the shared `planning-workflow` doctrine for `execution-ready` versus `research-ready` readiness, `low-confidence` decision handling, the default `test coverage matrix`, and the execution review-to-`original test scope` feedback loop.",
        ],
    )

    plan_tdd_bdd = get_section(
        plan_template_text, "Repo-specific TDD / BDD expectations"
    )
    require_phrases(
        "plan overrides template TDD/BDD",
        plan_tdd_bdd,
        [
            "- Only document repo-local additions here; shared execution-path reassessment of the `original test scope` and shared `test coverage matrix` expectations already come from the global doctrine.",
        ],
    )

    plan_ready_bar = get_section(plan_template_text, "Local ready bar additions")
    require_phrases(
        "plan overrides template ready bar",
        plan_ready_bar,
        [
            "- Only add repo-specific conditions beyond the shared `execution-ready` / `research-ready` ready bar; do not relax low-confidence decision closure or convert a shared `research-ready` case into local execution.",
        ],
    )

    planning_workflow = get_section(
        readme_text, "Workflow 0: Plan-First Execution (Shared Default)", level=3
    )
    require_phrases(
        "README plan-first workflow",
        planning_workflow,
        [
            "`[plan mode discovery] → /dev:plan → [execution-ready → optional /dev:pm-review <plan> plan → /review:plan <plan> → /review:change-integrate <plan> → /cmd:execute-plan <plan> → choose /run-plan <plan> or /dev:run <plan>] | [research-ready / blocking question → next research or answer → /dev:plan]`",
            "- Read-only plan mode gathers evidence, resolves `low-confidence` decisions, and prepares inputs for plan materialization.",
            "- `/dev:plan` fails closed: it only writes an `execution-ready` plan when foundational decisions are resolved; otherwise it asks the user or writes exactly one non-ready `research-ready` artifact with the next research action.",
            "- Only `execution-ready` reviewed plans move into `/cmd:execute-plan`; the handoff preserves the reviewed plan argument and asks whether to continue with `/run-plan` or `/dev:run`.",
            "- Keep simple tasks lightweight, but require complete contracts plus a `test coverage matrix` before a non-trivial plan is treated as `execution-ready`.",
            "- `/run-plan` is the full lifecycle reviewed-plan continuation through PR creation and monitoring; `/dev:run` remains the direct execution path with one `quality-reviewer` pass after each phase.",
        ],
    )

    planning_defaults = get_section(
        readme_text, "Execution-Ready Planning Defaults", level=3
    )
    require_phrases(
        "README planning defaults",
        planning_defaults,
        [
            "- A plan is only `execution-ready` when important questions and `low-confidence` foundational decisions are resolved with evidence.",
            "- If research is still the next handoff, `/dev:plan` writes one non-ready `research-ready` artifact instead of pretending execution can safely start.",
            "- `/review:plan` is the standard plan review pass, and `/review:change-integrate` should clean those inline comments before `/cmd:execute-plan`.",
            "- Non-trivial ready plans should include a `test coverage matrix` that maps acceptance criteria and BDD scenarios to suites/files and `### Verify` commands.",
            "- `/run-plan` can resume from a reviewed plan, keep the plan truthfully aligned with execution, run pre-PR review gates, create the PR, and monitor post-PR feedback.",
            "- `/dev:run` applies one `quality-reviewer` pass after each phase. A phase only advances after review receives `VERDICT: PASS_NO_ISSUES`, or `VERDICT: PASS_LOW_RISK_ONLY` with each remaining item proven out-of-scope, low-risk, not required for truthful verification, and logged in `thoughts/discoveries/<plan-or-feature>.md` (or the repo's documented equivalent) plus the plan's `## Decisions / Deviations Log`.",
        ],
    )

    coherence_terms = {
        str(SKILL_PATH): [
            "execution-ready",
            "research-ready",
            "low-confidence",
            "test coverage matrix",
            "original test scope",
            "execution feedback loop",
        ],
        str(ROOT_TEMPLATE_PATH): [
            "execution-ready",
            "research-ready",
            "low-confidence",
            "test coverage matrix",
            "original test scope",
            "execution feedback loop",
            "planning-workflow",
        ],
        str(PLAN_TEMPLATE_PATH): [
            "execution-ready",
            "research-ready",
            "low-confidence",
            "test coverage matrix",
            "original test scope",
            "execution",
            "planning-workflow",
        ],
        str(README_PATH): [
            "dev:plan",
            "execution-ready",
            "research-ready",
            "low-confidence",
            "test coverage matrix",
            "original test scope",
            "run-plan",
            "TDD",
        ],
    }

    for label, terms in coherence_terms.items():
        content = {
            str(SKILL_PATH): skill_text,
            str(ROOT_TEMPLATE_PATH): root_template_text,
            str(PLAN_TEMPLATE_PATH): plan_template_text,
            str(README_PATH): readme_text,
        }[label]
        require_terms(label, content, terms)

    print("bootstrap guidance and command docs contain required hardening concepts")


if __name__ == "__main__":
    main()
