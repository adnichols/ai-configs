# Prompt and skill cleanup — 2026-09-14

## Scope and outcome

Reviewed working-tree baseline: `43c25145de31dc22ac649c491fdd00385fe9678a`, including existing unrelated edits. No commit, push, remote install, or edits to Hermes/ADN source were made for this cleanup.

- Retired Codex delivery slash prompts, cmd:debug, dev:debug, and dev:run. cmd:execute-plan defaults to local execution/verification; explicit run-plan selects publication scope. Pi commands remain available to Pi.
- Removed the Tailwind-specific design skill and Luvus from source, the shared matrix, and managed local installations.
- Preserved every surviving shared SKILL.md byte-for-byte against the pre-change snapshot, including descriptions. Preserved Codex PSTack principle bodies/descriptions. Shorter descriptions are Codex-only.
- Codex disables the shared skill-creator when its bundled author exists, the empty template, and the older local React duplicate when the shared React skill exists. Files remain available to their other consumers.
- Reduced root AGENTS.md from 4,714 to 367 words. Repository-specific procedures moved into three local conditional skills.
- Converted Codex Doct, planning-workflow, and reviewed-html-plan entry points from 4,867/4,100/4,203 words to 221/222/212 words. Detailed procedures remain in references; this measures entry-point size, not total instructions removed or actual token savings.
- Reconciled installed shared cmd-create-pr and run-plan with their unchanged repository sources, with backups. Installed 68 selected Codex skills and 47 prompts; repeated prompt installation made no replacements.

## Evaluation

Runnable checks:

```bash
python3 -m unittest discover -s _codex -p 'test_install*.py'
bash test_install_shared_skills.sh
cd _adn
bun test
bun tests/routing-eval.ts
```

Six Python installer tests pass, covering repeated installation, ownership, edited/custom files, retirement backups, collision exclusions, and optional profiles. ADN tests pass: 38 tests, 1,900 expectations; routing checks pass: 28 fixtures covering 23 playbooks and six formal workflows. Shell syntax and scoped diff-whitespace checks pass. Live manifest hashes, retirement absence, collision paths, and source/install parity were checked.

Two independent instruction-interpretation trials used the same 24 request cases in prompt-routing-cases.json against baseline and candidate snapshots. They were not end-to-end application runs. The candidate removed a mandatory mode-selection question for a local execution request and made local-versus-published plan routing explicit. Trials exposed a lost Doct planning-only completion rule and conflicting review-budget wording; both were corrected. A missing cua-driver dependency in the isolated fixture limits the GUI-routing comparison. Do not interpret these trials as demonstrated latency, cost, or completion-rate improvements.

Independent bounded static implementation review found an unsafe retired-skill deletion path; the fix preserves modified/unverifiable entries and backs up pristine retirements. Targeted rereview found no material blockers. Final test-isolation rereview also found no material blockers.

The shared installer suite is not claimed fully green. The earlier run had seven failures; the obsolete Codex/Pi parity assertion was corrected. Remaining failures concern Firstmate fixture files (two tests), an existing Pi-local skill tree, Hermes product-owner text, Hermes cron review guidance, and Herdr handoff expectations. These surfaces were not changed here; no exhaustive clean-baseline comparison was completed.

During validation, shared tests inherited live CODEX_HOME despite overriding HOME. The run was stopped, both test wrappers now set fixture-local CODEX_HOME, and live managed Codex configuration was refreshed. The separate installed verified-build skill was restored byte-for-byte from its independently installed commit `43ddbca`; it is not adopted into this older checkout's manifest. The final isolated suite reports 27 passes and the six failures listed above. Live config and both managed manifests had identical checksums before and after that isolated run.

## Recovery and follow-up

### Fresh-session validation

Two fresh `codex exec` sessions used the live installed configuration, Codex CLI 0.154.0, and its default GPT-5.6 Sol at high effort. Both ran read-only in this repository, without inherited conversation history.

- Discovery passed: the supplied catalog contained only the system skill-creator, Codex computer-use, and shared React skill for those names. Exact template, design, and luvus entries were absent. All three repository-local skills were visible. The session correctly treated installation guidance as conditional rather than necessary for a general repository-purpose question.
- A practical explanation and local verification-planning task passed: the session naturally selected ai-configs-installation and how, correctly explained edited-file preservation versus pristine-file backup/removal, cited the implementation, and proposed isolated repeated-install checks. Its recorded commands were read-only. It did not publish to Doct, launch Pi, change files, or ask for an unnecessary workflow choice.
- The practical task did not load Doct publication/listener procedures. This is evidence of appropriate selection on this request, not coverage of every router or execution command.
- Both sessions still reported that skill descriptions were shortened to fit the overall context budget. Catalog collisions are resolved in these fresh CLI sessions, but the overall discovery budget remains exceeded. No baseline timing comparison or Astra-specific behavioral test was performed.

Session IDs: `01a0a256-9fdf-7e22-b525-522ddc2cc849` for discovery. Raw outputs and command traces for both sessions are in `/tmp/codex-fresh-validation.YFsr44/`, including `discovery.txt`, `work.txt`, and their JSONL event logs. These temporary artifacts are not durable repository fixtures.

Removed local prompts are recoverable from `/Users/anichols/.codex/prompts-backup-w6rpclhs`. Removed shared skills are under `/Users/anichols/.agents/skill-backups/ai-configs/20260914-172236/deprecated/shared/`; pre-refresh cmd-create-pr and run-plan copies are under the same backup root at `20260914-172422/`. Repository deletions remain uncommitted and recoverable from Git.

Start a fresh Codex session to load the changed catalog. For outcome evaluation, repeat the 24 cases in fresh sessions with the full installed dependencies, compare baseline/candidate at the same model settings, and record correct skill selection, unintended publication/implementation, unnecessary questions, task completion, and loaded context. Require no authority regressions and no completion-quality loss; retain individual reductions only when they preserve those outcomes. Real-task latency/cost improvements remain unproven.
