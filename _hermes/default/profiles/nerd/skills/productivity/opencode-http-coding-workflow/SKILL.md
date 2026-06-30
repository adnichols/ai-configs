---
name: opencode-http-coding-workflow
description: "Compatibility wrapper for Aaron's former Hermes-orchestrated OpenCode HTTP workflow. For new Linear-backed OpenCode builds, load `hermes-opencode-linear-build`: OpenCode runs `/cmd:linear-build-workspace` and owns orchestration; Hermes only launches, monitors, nudges, and verifies terminal status."
version: 0.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [opencode, coding-workflow, http-api, linear, compatibility]
    related_skills: [hermes-opencode-linear-build, opencode, opencode-gated-pr-bundle-sync, github-pr-workflow]
---

# OpenCode HTTP Coding Workflow (Retired Wrapper)

## Current Status

This skill used to describe a Hermes-side gated workflow where Hermes created OpenCode workspaces, ran/recorded deterministic gates, called Codex and Claude reviewers, prompted PM review stages, and drove Linear transitions. That controller and its scripts have been removed from this skill.

That operating model is retired for new Linear-backed OpenCode work.

For new work, use:

```text
/skill hermes-opencode-linear-build
```

The OpenCode command is now the orchestrator:

```text
/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>
```

Active OpenCode command/helper files live at:

```text
~/.config/opencode/commands/cmd:linear-build-workspace.md
~/.config/opencode/scripts/create_linear_workspace.py
~/.config/opencode/scripts/linear_build_orchestrator.py
```

The version-controlled source normally lives at:

```text
~/code/ai-configs/_opencode/commands/cmd:linear-build-workspace.md
~/code/ai-configs/_opencode/scripts/create_linear_workspace.py
~/code/ai-configs/_opencode/scripts/linear_build_orchestrator.py
```

## New Operating Model

OpenCode owns the workflow end to end:

- create or reuse the OpenCode workspace
- capture the Linear issue
- initialize/update the durable run ledger
- plan
- run plan gates
- implement
- validate
- gather evidence
- run code/PM review
- commit, push, open/link PR
- move Linear state
- record blockers and final verdicts

Hermes owns only liveness supervision:

- find repo / issue key / base ref
- launch or resume the OpenCode slash command
- read OpenCode messages
- read the workspace JSON and run ledger
- inspect read-only git/PR/Linear state after OpenCode claims progress
- nudge OpenCode to continue if it stalls
- report terminal completion or an explicit blocker

Hermes must not recreate the old orchestration by running individual gates itself.

## HTTP Helper Still Available

The only helper retained in this skill is `scripts/opencode_http.py`, for launching/observing OpenCode sessions over HTTP. It is **not** the controller for new Linear builds.

Locate the installed skill directory:

```bash
export OPENCODE_WORKFLOW_SKILL_DIR="${OPENCODE_WORKFLOW_SKILL_DIR:-$HOME/.hermes/profiles/nerd/skills/productivity/opencode-http-coding-workflow}"
test -d "$OPENCODE_WORKFLOW_SKILL_DIR" || export OPENCODE_WORKFLOW_SKILL_DIR="$HOME/.hermes/skills/productivity/opencode-http-coding-workflow"
```

Health check:

```bash
python3 "$OPENCODE_WORKFLOW_SKILL_DIR/scripts/opencode_http.py" health
```

Create an OpenCode session in the primary repo checkout and send the OpenCode-owned command:

```bash
SESSION_JSON="$(python3 "$OPENCODE_WORKFLOW_SKILL_DIR/scripts/opencode_http.py" create \
  --repo /Users/anichols/code/<repo> \
  --title "<ISSUE_KEY> linear build" \
  --agent build)"

SESSION_ID="$(python3 -c 'import json,sys; data=json.loads(sys.stdin.read()); print(data.get("id") or data.get("session", {}).get("id", ""))' <<< "$SESSION_JSON")"

python3 "$OPENCODE_WORKFLOW_SKILL_DIR/scripts/opencode_http.py" prompt \
  --repo /Users/anichols/code/<repo> \
  --session "$SESSION_ID" \
  --agent build \
  --text "/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>"
```

For monitoring only:

```bash
python3 "$OPENCODE_WORKFLOW_SKILL_DIR/scripts/opencode_http.py" messages \
  --repo /Users/anichols/code/<repo> \
  --session "$SESSION_ID" \
  --limit 30
```

## Forbidden Legacy Pattern for New Builds

Do not use these old Hermes-controller stages for new Linear builds unless Aaron explicitly asks for legacy recovery:

- old Hermes-controller init/status/record/advance/gate-check commands
- Hermes-run Codex plan review gates
- Hermes-run Claude Code plan review gates
- Hermes-run PM review gates
- Hermes-managed Linear state transitions
- Hermes-managed validation artifacts
- Hermes-created OpenCode worktree/workspace sequence

The OpenCode command and `linear_build_orchestrator.py` own those stages now.

## What to Do Instead

1. Load `hermes-opencode-linear-build`.
2. Verify the OpenCode command/helper files exist.
3. Launch `/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>` in OpenCode.
4. Monitor OpenCode messages, `.opencode/tmp/<ISSUE_KEY>-workspace.json`, and the run ledger in `thoughts/runs/<issue-slug>.md`.
5. If OpenCode stalls, resume the same process from the ledger rather than taking over.
6. Report only terminal completion or an explicit OpenCode-recorded blocker.

## User-Facing Report

When reporting status, keep it concise:

- issue key
- OpenCode session id
- workspace id/directory if known
- ledger path
- current stage/final verdict
- PR URL if created
- blocker/next decision if blocked

## Common Pitfalls

1. **Thinking this skill still authorizes Hermes orchestration.** It does not. It is a compatibility wrapper.
2. **Calling old controller scripts for new work.** Use the OpenCode command and ledger instead.
3. **Running tests or review gates from Hermes.** OpenCode owns validation/review; Hermes can read results.
4. **Reporting timeout as completion.** Inspect messages and the run ledger before reporting.
5. **Forgetting to load the replacement skill.** `hermes-opencode-linear-build` is the canonical skill for new Linear builds.

## Verification Checklist

- [ ] `hermes-opencode-linear-build` was loaded for new Linear work.
- [ ] Hermes launched/resumed `/cmd:linear-build-workspace` rather than running old gates.
- [ ] Status/final report was grounded in OpenCode messages, run ledger, PR/Linear read-only checks, or a recorded blocker.
