# Pre-PR review: README note for Devin global instructions

- Date: 2026-09-22
- Branch: `docs/devin-pr-lifecycle-20260922`
- Base/range: `origin/main...HEAD` (base `ff17a9c`)
- Reviewed HEAD: `0faf81a` (cycle 1), `0137502` (cycle 2 rereview of the
  `DEVIN_CONFIG_TARGET` wording delta; artifact file amended into the same
  commit afterward, reviewed content unchanged)
- Scope: standalone request, no plan file
- fast-path: true; small, reversible, docs-only change, one reviewer pass per stakes-scaled policy

## Task and intended behavior

Add a short, clearly placed note to README.md explaining where Devin's global
instructions are maintained (`_devin/AGENTS.md`) and installed
(`~/.config/devin/AGENTS.md`), with a link to the source file. Documentation
only; no installer, config, or code changes.

## Pre-review scope baseline

- Supported paths: the `### \`_devin/\`` section under "Key directories" in
  README.md.
- Non-goals: no changes to `_devin/install.sh`, `install.sh`, agent profiles,
  or any behavior; no restructuring of other README sections.
- Changed files: `README.md` only (committed diff); this artifact added
  uncommitted after the review pass.

## Review cycles

Cycle 1: active-harness `reviewer` subagent profile (pins own model, sonnet).

- Provenance: REVIEW_ROOT = TARGET_CHECKOUT (this worktree), HEAD `0faf81a`,
  STATUS_SHORT EMPTY, REVIEW_SOURCE target-live-worktree.
- Coverage: README diff matched packet; `_devin/AGENTS.md` link target exists;
  source→destination claim verified against `_devin/install.sh` lines 6-7 and
  67; model pins (`reviewer`/`planner` sonnet, `oracle`/`completeness` opus)
  verified against `_devin/agents/*.md` frontmatter; consistency with the
  "What the installer does" bullet confirmed; markdown link syntax clean.
- Findings: none.
- `Not examined:` executable checks (read-only mandate); relied on
  caller-supplied results and independent static verification.
- VERDICT: PASS

Cycle 2: targeted rereview by the same `reviewer` profile after the operator
asked to document the `DEVIN_CONFIG_TARGET` override.

- Scope: the added sentence "`DEVIN_CONFIG_TARGET` overrides the install
  root." and the "by default" qualifier on the `~/.config/devin/AGENTS.md`
  destination, plus paragraph consistency.
- Verified: `_devin/install.sh` derives `TARGET_ROOT` from
  `DEVIN_CONFIG_TARGET` (default `~/.config/devin`) once, and uses it for the
  AGENTS.md install, the `agents/` profile installs, and skill-link pruning,
  so "install root" is accurate, not narrower than reality. The later
  "Isolated installer tests set `DEVIN_CONFIG_TARGET`." sentence is
  corroborated by `test_devin_config_install.sh` lines 18 and 46.
- Findings: none.
- `Not examined:` full README beyond the `_devin/` paragraph and the line-85
  bullet; no executable checks (read-only mandate).
- VERDICT: PASS

## Triage

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---|---|---|---|
| none | - | - | - | - | - |

## Verification

- `bash test_devin_config_install.sh` → "Devin config installer tests passed."
  (asserts `_devin/AGENTS.md` installs to `$DEVIN_CONFIG_TARGET/AGENTS.md`,
  default `~/.config/devin`)
- `git diff --check` → clean
- Paths read directly from `_devin/install.sh` (`TARGET_ROOT` default
  `$HOME/.config/devin`, `SOURCE_GUIDANCE` `$SOURCE_DIR/AGENTS.md`, install to
  `$TARGET_ROOT/AGENTS.md`) and `install.sh` `install_devin_config()` which
  delegates to `_devin/install.sh` for `--devin` and `--all`.

## Follow-ups

None.

## Gate result

PASS. No unresolved in-scope P1/P2 findings. Not invoked from `run-plan`; no
external thumbs-up required beyond this clean local reviewer artifact.
