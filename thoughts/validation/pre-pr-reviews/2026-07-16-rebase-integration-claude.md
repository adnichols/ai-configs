## Scope checked

- `skills/autoreview/SKILL.md` — canonical policy, Pi/Codex routing, run-plan `OPEN_PR_READY` handoff, verdict profile references
- `skills/pre-pr-implementation-review/SKILL.md` — thin compatibility alias delegating to `/skill:autoreview`
- `_pi/extensions/codex-review/tests/source-policy.test.mjs` — workflow → `codex_review`/`verdictProfile` assertions, alias handoff assertion, wrapper-contradiction guard
- `skills/codex-review-partner/scripts/check_no_direct_codex_review_launches.py` — FILES set (includes alias), exempt-line handling, launch signature patterns
- `install.sh` — `--pi-review-stack` (2155–2212) mutation boundary and exact 5-skill copy at 2199, symlink guards at 2160–2168 and 2746–2747
- `scripts/install-pi-transactionally.sh` — `SKILLS`/`PATHS` (15, 35) both include the alias root; snapshot/rollback traps and parity/host-test sequence (80–96)
- `scripts/verify-pi-install.sh` — `pi-review-stack` scope (27–93), 5-skill parity loop at 88, `--check-only` non-mutating discipline
- `scripts/tests/test_install_pi_transaction.py` — bounded-install, scoped check-only, symlink-rejection, rollback-manifest, signal restore tests
- `_pi/README.md` — five-skill snapshot description at 153 and alias documentation at 266
- `thoughts/plans/codex-review-background-extension.html` — base-integration record at 105, 146, 200, 313–317, 383, 386, 437 acknowledging the four-to-five expansion driven by `autoreview` canonicalization

## Coverage cross-check

| Invariant | install.sh | transactional | verifier | tests | plan |
|---|---|---|---|---|---|
| 5-skill roots (autoreview + alias + partner + reviewed-html-plan + run-plan) | 2199 ✓ | 15, 35 ✓ | 88 ✓ | manifest-based ✓ | 146, 437 ✓ |
| Pi route → `codex_review` (not wrapper) | n/a | n/a | n/a | source-policy 4 ✓ | 105, 437 ✓ |
| Alias preserves handoff | n/a | n/a | 88 (parity) ✓ | source-policy 4 ✓ | 266 ✓ |
| Symlink refusal for managed `~/.pi` paths | 2160–2168, 2746 ✓ | 4–13 ✓ | n/a | test_install_pi_transaction 57–71 ✓ | AC15 ✓ |
| Rollback returns to exact prior manifest | n/a | 53–64 ✓ | n/a | test_transaction_rolls_back_every_structural_failpoint ✓ | 200 ✓ |

The alias skill contains only `/skill:autoreview <same arguments, unchanged>` and no `run-review.sh --mode …|codex exec review`, so `check_no_direct_codex_review_launches.py` scans it cleanly. `skills/autoreview/SKILL.md`'s only `run-review.sh --mode implementation-review` example (line 136) carries the `codex-review-policy-exempt` line-local marker; scan_text's exempt_lines skip is line-aligned with the physical file. The `In Pi …` lines (autoreview 124, 147) contain no `subprocess|wrapper|run Codex as`, so source-policy's contradiction guard passes for the canonical file. Both `SKILLS` and `PATHS` in the transactional installer independently enumerate the alias root, so its snapshot, rollback, and post-commit parity check all cover it, and `verify-pi-install.sh --scope pi-review-stack` diffs the alias tree at 88.

## Findings

No in-scope P1/P2 finding remains. Verified negative checks:

- Alias installation and verification: covered in the 5-skill loops at `install.sh:2199`, `install-pi-transactionally.sh:15/35`, `verify-pi-install.sh:88`, and `scripts/tests/test_install_pi_transaction.py` (via full `manifest(home)` before/after equality).
- Canonical Pi routing preservation: `source-policy.test.mjs:4` locks `codex_review` + workflow-specific `verdictProfile` for autoreview/run-plan/reviewed-html-plan and asserts the alias hands off to `/skill:autoreview` without wrapper contradictions.
- Non-Pi wrapper preservation: autoreview's exempt `run-review.sh` example is line-marked and the scanner's `exempt_lines` implementation is line-local, so the exemption cannot silently widen.
- Mutation boundary: `install_pi_review_stack` writes only to `~/.pi/agent/{prompts,agents,extensions,models.json,README.md,APPEND_SYSTEM.md}` and the five named `~/.agents/skills/<skill>` roots; symlinks at any managed path are rejected before any write; parent metadata is captured and restored on both success and rollback paths.
- Rollback completeness: `PATHS` at `install-pi-transactionally.sh:35` matches the mutation surface at `install.sh:2181/2199` (whole `.pi` plus the same five skill roots), so no added skill root is outside the snapshot.

VERDICT: PASS_SCOPED

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-7eb38a36be56-3821251-6432981fbf85
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/thoughts/validation/pre-pr-reviews/2026-07-16-rebase-integration-claude.md.transcript.txt
claude_session_id=dcdd09fe-af83-4c00-9c1e-faa24d667f95
session_record=/home/anichols/.claude/projects/-home-anichols--herdr-worktrees-ai-configs-codex-review-plugin/dcdd09fe-af83-4c00-9c1e-faa24d667f95.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
