# ADN provenance

Upstream: https://github.com/cursor/plugins/tree/e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a/pstack
Pin: `e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a`
License: MIT (Lauren Tan). Full text: `LICENSE.pstack`
Review date: 2026-10-03

ADN translates pstack behavior into OMP. It does not copy Cursor runtime, Graphite, cloud workers, Plan Mode, Benny, or vendor model files.
Post-pin upstream changes require explicit `adopt-skill` adoption. Installed source is pinned; do not silently refresh it.

OMP adaptation policy: retain named outcomes; replace only declared runtime dependencies; fail closed on missing required sources or roles.

Local OMP adaptations include the runtime contract, managed deslop skill, and read-only Comment Sicko agent. These replace missing plugin and Cursor runtime dependencies without refreshing upstream.

## Adoption of ecc249f to e43c7ee (pstack 0.15.9, 2026-10-03)

Adopted:

- New `correct` skill. Locally, its mistake-class search also reads OMP session transcripts (`history://`, `~/.omp/agent/sessions/`), Paseo agent activity, and PR threads, because most corrections happen in chat. `principle-encode-lessons-in-structure` points to it for repeated classes.
- New `benchmark-checklist` skill and `principle-explain-the-number` principle, with their `adn-mode` trigger and index entry. Locally, the checklist picks tools by `uname -s` from a Linux and macOS table instead of naming Linux tools inline, and the report names the OS and hardware.
- `architect` agent-contributor screening line and the four new design red flags: split ownership, two ways to do one task, importable internals, hand-synced list.
- `perf-issue` performance mantras in place of the eight strategy families, and the `hillclimb` harness vetting and mantra ordering. Local deviation: a mantra still earns an attempt only when the trace shows the cost it removes, as the strategy families required.
- The full-autonomy default reports what the operator could say instead, never a shorthand token to type back.
- The Pi `adn-mode` gets the two new triggers and the new principle entry. It still lags this pin elsewhere.
- The schema-first `No as casts` example in `typescript-best-practices/references/patterns.md`, and the `swarm` aggregation wording "respawn that worker once".

Declined:

- The `autopilot-full` and `autopilot-stack` owner and tick rewrite: the hourly `/loop 1h` tick, `/goal` removal, push-after-every-unit for tick audits, a fresh owner per round, and the matching `check-plan.mjs` marker. They depend on Cursor `/loop` and `/goal`.
- The `autopilot-full` step 5 relaxation that skips a re-rebase when the head is green and `git merge-tree` against trunk is clean. The local step keeps the stricter patch-id re-verification.
- The `opening-a-pr` built-in PR tool section and the reworded PR-body headings. OMP has no built-in PR tool, and the local PR-body rules already apply.
- Fresh-subagent resume rules and the `poteto-agent` description. OMP `task` spawns fresh agents, and `adn-mode` already requires a fresh consolidated subagent.
- Removal of the `technical-writing` source citations.
- `disable-model-invocation` frontmatter on the new skills, per the earlier decision.
- Version, README, and guide count changes.

## Adoption of 46756f8 to ecc249f (2026-09-26)

Adopted by a three-way merge of each upstream change onto the local adaptation:

- New principles `principle-attack-the-premise` and `principle-test-behavior-not-implementation`.
- Principle citation rule: cite only principles whose leaf skill was read this session.
- Full-autonomy grant clause. Locally, a grant never expands PR, merge, or external-coordination authority.
- Evidence-label rule for replies.
- Forge-neutral PR, shipping, babysit, and autopilot playbooks using `gh` and git, with upstream's optional `origin` CLI branch. `orchestrate` still names `gt` for its single stacker, as upstream does.
- PR bodies as short briefings, swarm measurement briefs, show-me-your-work superseding rows, the multi-phase plan regression lane and `check-plan.mjs`, the TypeScript schema-first row, unslop rule changes, and upstream wording and punctuation cuts.
- Removal of the `how` Critique mode and the `how critics` role.

Declined:

- `make-bot-ui`. It builds webhook UIs for a Grok Bot service this setup does not run.
- `disable-model-invocation` frontmatter. ADN skills stay model-invocable and carry `ADN_RUNTIME_MARKER` instead.
- Upstream model defaults (`grok-4.7-xhigh-fast`, `claude-opus-5-5-max`) and three-entry panels. Local defaults and panel lists stay as the operator configured them.
- The `setup-pstack` reasoning-budget step and `# budget` rule line. They depend on Cursor slug grammar.
- The plugin logo, `plugin.json`, and README changes. ADN installs skills, not the Cursor plugin package.

Local deviations: "are we sure?" routes to `interrogate`, because the `how` skill no longer has a critique mode. In `autopilot-full`, merge authority comes from the operator's explicit request to run the queue to merged, not from a full-autonomy grant alone.

## Local deviations: one required review

Every required review is exactly one reviewer other than the driver. `adversarial-fix-review`, `autoreview`, and any "independent" or "final" verdict are the same review and share one pass, not stacked passes. The reviewer role is chosen by the complexity and risk of the work. Different model family is preferred, and same-family is a recorded note, not a blocker. The rule lives in `skills/adn-mode/references/omp-runtime.md` (Required reviews) and takes precedence over the retained upstream wording. Local edits also reword `adn-mode` (trigger line and role paragraph), `bug-fix` step 6, `opening-a-pr`, `show-me-your-work`, and the five council agent prompts. `interrogate`, `arena`, and architect councils stay multi-agent panels.
