# OpenCode Linear build migration notes (2026-05)

## Trigger
Aaron corrected the workflow source path: the `hermes-opencode-linear-build` skill was already present at `~/.agents/skills/hermes-opencode-linear-build/SKILL.md`. Future updates should treat user-provided source paths as authoritative, reconcile them into the active Hermes profile, and verify equality before rebuilding a portable bundle.

## Correct shape
- Canonical source for the Linear build workflow: `~/.agents/skills/hermes-opencode-linear-build/SKILL.md`.
- Installed profile copy for the nerd profile: `~/.hermes/profiles/nerd/skills/productivity/hermes-opencode-linear-build/SKILL.md`.
- Bundle repo: `~/code/hermes-configs/opencode-gated-pr-workflow`.
- OpenCode side files expected in `~/.config/opencode/commands` and `~/.config/opencode/scripts`:
  - `cmd:linear-build-workspace.md`
  - `create_linear_workspace.py`
  - `linear_build_orchestrator.py`

## Migration pattern
1. Load `hermes-agent`, `opencode-gated-pr-bundle-sync`, and `hermes-opencode-linear-build`.
2. Read/reconcile the canonical `~/.agents` skill into the active Hermes profile.
3. Verify source and installed copy match, e.g. `cmp -s ~/.agents/skills/hermes-opencode-linear-build/SKILL.md ~/.hermes/profiles/nerd/skills/productivity/hermes-opencode-linear-build/SKILL.md`.
4. Convert `opencode-http-coding-workflow` into a compatibility wrapper only; keep HTTP launch/observe helpers if needed, remove old Hermes controller scripts from the portable bundle.
5. Update bundle `SELECTED_SKILLS` to include `productivity/hermes-opencode-linear-build` before `productivity/opencode-http-coding-workflow`.
6. Rebuild the bundle from source skills and `build_bundle.py`; do not hand-edit generated `bundle/skills/...` except for inspection.
7. Verify Python scripts compile and smoke-test ledger classification if `workflow_gate_check.py` changed.
8. Search the regenerated bundle for stale old-controller strings before reporting done.

## Stale strings worth scanning for
- `controller_only`
- `controller-only`
- `opencode_workflow.py`
- `adverse_condition_policy`
- `plan-review-prompt`
- `PM_ACCEPTABLE_FOR_IMPLEMENTATION`

Some historical mentions can be acceptable in a retired-wrapper explanation, but generated policy/templates/scripts should not require Hermes-side plan/review/PM gates for new Linear builds.

## Desired final behavior
Hermes is a thin supervisor: it creates or resumes a repo-scoped OpenCode session, sends `/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>`, monitors OpenCode session/workspace/run-ledger state, and reports blocked or terminal states. OpenCode owns workspace creation, stages, validation, reviews, PR creation, PR feedback, and Linear linkage/state.
