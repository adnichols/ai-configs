# ADN provenance

Upstream: https://github.com/cursor/plugins/tree/ecc249f1e306fc64ddf83c7bed16cacf7c2239db/pstack
Pin: `ecc249f1e306fc64ddf83c7bed16cacf7c2239db`
License: MIT (Lauren Tan). Full text: `LICENSE.pstack`
Review date: 2026-09-26

ADN translates pstack behavior into OMP. It does not copy Cursor runtime, Graphite, cloud workers, Plan Mode, Benny, or vendor model files.
Post-pin upstream changes require explicit `adopt-skill` adoption. Installed source is pinned; do not silently refresh it.

OMP adaptation policy: retain named outcomes; replace only declared runtime dependencies; fail closed on missing required sources or roles.

Local OMP adaptations include the runtime contract, managed deslop skill, and read-only Comment Sicko agent. These replace missing plugin and Cursor runtime dependencies without refreshing upstream.

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
