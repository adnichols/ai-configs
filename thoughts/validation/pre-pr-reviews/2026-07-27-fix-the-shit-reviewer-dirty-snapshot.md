# PR #51 autoreview — reviewer dirty snapshot

## Candidate

- **PR:** https://github.com/adnichols/ai-configs/pull/51
- **Base/comparison:** `origin/main...HEAD` (merge-base `03631ae2a9bb31107f1c7797d8d286ab814bf5fa`)
- **Initial candidate tip:** `bb18edb`
- **Scope:** the live-worktree launch contract in `skills/autoreview/SKILL.md`, `skills/run-plan/SKILL.md`, `skills/reviewed-html-plan/SKILL.md`, `_pi/agents/reviewer.md`, changed Pi review/PRD prompts, and the dirty-snapshot validation records.

## Integration record

| Contract | Source of truth | Producers | Consumers | Cross-boundary proof |
|---|---|---|---|---|
| Required reviewers see the live dirty candidate | `skills/autoreview/SKILL.md` and `_pi/agents/reviewer.md` | Autoreview/run-plan/plan-review skills and review/PRD prompt launch sites | Configured `reviewer` subagent and its coordinator | Reviewer provenance plus a rejection/relaunch rule for isolated clean snapshots |
| Reviewer provenance and failure verdict | Same sources; run-plan generic template | Reviewer prompt templates | Coordinator gate acceptance | CWD/HEAD/STATUS_SHORT/INSPECTED_TREE and `REVIEW_INFRASTRUCTURE_FAILURE` must agree across all launch paths |
| Historical repro evidence is truthful | `thoughts/validation/dirty-snapshot-*` | Coordinator-recorded validation artifacts | PR reviewers/operators | Redacted records state that raw fixture/transcripts are not retained, rather than claiming independent auditability |

## Review cycle 1 — live source review

**Reviewer:** active-harness `reviewer`, GPT-5.6 Terra, medium reasoning.

Several direct review-launch attempts were discarded as `REVIEW_INFRASTRUCTURE_FAILURE`: their actual provenance was `<tmpdir>/pi-agent-*`, `STATUS_SHORT: EMPTY`, and `INSPECTED_TREE: isolated-clean`. They were not counted as review cycles because the candidate packet required live dirty-tree visibility.

A correctly launched live-worktree reviewer returned three in-scope findings:

| Finding | Severity / scope | Decision | Evidence |
|---|---|---|---|
| Run-plan generic reviewer template lacked provenance and the infrastructure-failure verdict | P2 / `IN_PLAN` | Fixed | `skills/run-plan/SKILL.md` reviewer template now requires CWD/HEAD/STATUS_SHORT/INSPECTED_TREE and lists `REVIEW_INFRASTRUCTURE_FAILURE` |
| Autoreview required `INSPECTED_TREE: live-worktree` even on the isolated failure path | P2 / `IN_PLAN` | Fixed | Template now permits `live-worktree | isolated-clean` and directs the latter for isolated failures |
| Validation records presented 3/3 and 5/5 historical counts as stronger evidence than retained files support | P2 / `IN_PLAN` | Fixed | JSON/Markdown records now say they are redacted coordinator observations; raw fixture and transcripts were not retained |

## Targeted rereview

**Reviewer:** active-harness `reviewer`, GPT-5.6 Terra, medium reasoning.

**Redacted provenance:**

```text
CWD: <repo-root>
HEAD: bb18edb (before the coordinator's uncommitted remediation)
STATUS_SHORT: non-empty; the focused skill and validation files were modified
INSPECTED_TREE: live-worktree
```

The reviewer checked only the three remediated areas and returned **APPROVE** with no material findings. It confirmed:

1. Run-plan now has the mandatory provenance block and accepts `REVIEW_INFRASTRUCTURE_FAILURE`.
2. Autoreview’s isolated failure provenance is internally consistent with `_pi/agents/reviewer.md`.
3. All five changed validation records qualify historical observations and the absence of independently auditable raw fixture/transcript material.

## Verification

- `python3 -m json.tool thoughts/validation/dirty-snapshot-fix-verify.json`
- `python3 -m json.tool thoughts/validation/dirty-snapshot-mechanical.json`
- `python3 -m json.tool thoughts/validation/dirty-snapshot-agent-path.json`
- `git diff --check`
- Targeted source checks for mandatory provenance, untracked `??` handling, `REVIEW_INFRASTRUCTURE_FAILURE`, path redaction, and artifact relocation.

All passed locally after the remediation.

## Gate result

**Reviewer verdict: PASS by substance** — the active reviewer approved the corrected focused areas with no unresolved in-scope P1/P2 findings. CodeRabbit’s follow-up review is unavailable because its account rate limit was reached; this is disclosed infrastructure availability, not a local reviewer failure.
