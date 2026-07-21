**1. Scope checked**

- A. Installer/local ownership — `install.sh`, `scripts/tests/test_install_pi_transaction.py`, `scripts/verify-pi-install.sh`, `_pi/models.json` (working-tree diff vs `HEAD`==`origin/main`==`ef0f50d`).
- B. Review-infrastructure launcher fix — `skills/claude-code-review/scripts/claude_interactive_review.py`, `skills/claude-code-review/tests/test_claude_interactive_review.py`, `skills/claude-code-review/tests/fixtures/fake_claude.py`.
- Cross-checked against `thoughts/plans/consolidate-pi-agent-roster.html` (AC6/AC7/AC9, P1/P2/P4, and the 2026-07-21 deviation-log entry authorizing the launcher repair).

**2. Coverage table**

| Invariant | Verified how | Result |
|---|---|---|
| Exact repo-owned agent directory replacement (review-stack reuses `install_pi_agents_from_repo`, rm-rf+recreate) | Read `install.sh:1796-1805`, `2329-2333`; ran transaction suite | PASS |
| Exact-ID `gpt-5.4`/`gpt-5.4-mini` pruning + `enabledModels` alias pruning, caller/custom preservation | Read `install.sh:1958-2118`; ran `test_retired_pi_models_are_pruned_without_claiming_custom_entries` | PASS |
| Malformed models/settings + managed symlinks fail before bounded mutation (review-stack) | Read `install.sh:1859-1911, 2288-2300`; ran `test_malformed_settings_fail_before_any_bounded_install_mutation` | PASS |
| Verifier scope truthfulness (scoped vs full) | Read `verify-pi-install.sh` diff; confirmed retired-ID/regex parity with `install.sh`; ran the reintroduced-retired-route assertions in the transaction test | PASS |
| Informational usage banner must not abort | Read `HARD_LIMIT_RE` (`claude_interactive_review.py:21-29`); ran `test_weekly_usage_limit_banner_is_not_session_limit`, `test_usage_banner_after_submit_allows_review_to_complete` | PASS |
| Explicit exhaustion still fails closed, code 25 | Ran `test_explicit_hard_limit_language_is_session_limit`, `test_session_limit_after_submit_fails_closed` | PASS |
| E2E fake-TUI: banner-then-complete, and prompt-echoed examples don't block | Ran full suite (38 tests: 36 passed, 2 skipped — `RUN_REAL_CLAUDE_*`) | PASS |
| No alternate transport / extension-classifier changes | Diffed touched-file list for scope B | PASS (only the launcher, its tests, and its fixture changed) |
| Roster / installer / Codex-policy unit suites | Ran directly | roster 5/5, installer 13/13, codex source-policy 6/6 |
| Shell/JSON/diff hygiene | `bash -n`, `python3 -m json.tool`, `git diff --check` | PASS |
| Generated (non-prompt, non-banner) review text that itself must reference the exhaustion phrasing | Loaded the module directly and fed `post_submit_generated_output` a synthetic post-boundary candidate whose *generated* answer body cites the two example messages from this review's own "Launcher invariants" section, then ran the isolated text through `check_tui_unavailable` | **FAILS** — raises `CLAUDE_SESSION_LIMIT_IN_TUI` |

**3. Findings**

**[P1] [QUESTION]** `skills/claude-code-review/scripts/claude_interactive_review.py:147-153, 356-368`
Summary: `post_submit_generated_output` correctly isolates the echoed prompt from generated output (the fix for the "hard-limit examples echoed inside its own submitted prompt" bug works), and `HARD_LIMIT_RE` correctly narrows out informational banners. But everything downstream of that isolation still runs through the same phrase match with no allowance for *legitimate generated prose that discusses the trigger phrasing as evidence* — which is exactly what a correct review of this diff has to write, and exactly what this review is doing.
Evidence/reproduction: I built a synthetic post-submit candidate — prompt text ending in the real `CLAUDE_REVIEW_FINAL_SENTINEL:<sentinel>` boundary line (as `compose_prompt()` at `claude_interactive_review.py:206-216` always emits), followed by a generated answer whose body cites the two named example messages from this review request's "Launcher invariants" section as supporting evidence. `post_submit_generated_output` correctly stripped the prompt and returned only the generated text — that part of the fix works. Feeding that isolated text into `check_tui_unavailable(..., after_submit=True)` raised `LauncherError("CLAUDE_SESSION_LIMIT_IN_TUI", ..., 25)`, i.e. a valid, successfully-completing review would be aborted mid-stream purely because its own commentary names the trigger language.
Not caught by the new tests: `test_hard_limit_examples_in_submitted_prompt_do_not_block_valid_review` (`test_claude_interactive_review.py:92-114`) and `test_post_submit_generated_output_excludes_visible_or_collapsed_prompt` (`:250-296`) only put the phrases inside the *prompt* or inside *fake system banners* (`fake_claude.py:93-97`); no fixture drives the fake Claude's own answer body to contain the phrasing as generated commentary.
Failure scenario: any future required review of this launcher, its regex, or its tests — including this one — that must name the trigger messages as part of its findings can be terminated by the launcher before the answer is captured, even though the session is fine.
Classification note: not a regression introduced by this diff — the prior unfiltered `check_tui_unavailable(candidate, after_submit=True)` call would have matched this same generated text just as eagerly. This diff built the exact mechanism needed to close the gap (`post_submit_generated_output`) but didn't extend it to this case. Recommend either restricting `HARD_LIMIT_RE` to short banner-like lines (the TUI's own chrome, e.g. lines starting with `⎿`) rather than arbitrary generated prose, or an explicit decision that this residual risk is acceptable.

**[P3] [OUT_OF_SCOPE_FOLLOW_UP]** `install.sh:2178-2239` (`install_pi()`)
Summary: unlike the newly hardened `--pi-review-stack` path, the full `--pi` install still replaces prompts/agents/extensions before `install_pi_models_from_repo` (line 2237) validates `models.json`/`settings.json` shape, so a malformed models/settings file on a full install can leave those directories already mutated when the models step later fails.
Evidence: this call order is untouched by the diff (no hunk touches `install_pi()`'s body); `validate_pi_model_inputs` is pre-invoked explicitly only inside `install_pi_review_stack` (`install.sh:2298-2300`).
Why out of scope: the plan's P4 phase and its new tests deliberately target "the bounded `--pi-review-stack` agent copy" for the no-partial-mutation guarantee; the full-install path was never claimed atomic, and this diff doesn't touch its ordering, so this is a pre-existing characteristic rather than a regression from this diff.

**4. Final verdict**

VERDICT: FIX_IN_SCOPE_FINDINGS

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-44ce6dd72648-38260-ecdede8f4c56
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/Users/anichols/code/ai-configs/thoughts/validation/consolidate-pi-agent-roster-claude-review.md.transcript.txt
claude_session_id=142660de-44d1-4cb2-a134-72e7e6f1fff1
session_record=/Users/anichols/.claude/projects/-Users-anichols-code-ai-configs/142660de-44d1-4cb2-a134-72e7e6f1fff1.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
