# OMP runtime contract

Read this contract when using ADN or any of its routed skills in OMP. It takes precedence over retained Cursor examples in leaf skills, reference packets, and playbooks. Preserve their requested outcomes and evidence; use the installed OMP capabilities below.

## Execution and authority

The driving session owns implementation, tests, fixes, Git, and external actions. Repository and user instructions govern scope and authorization. Mode activation does not authorize publishing a PR, merging, messaging others, deploying, changing branches, or editing another repository. A broken skill does not authorize a separate PR. Delivery stays explicit opt-in under the OMP guidance.

Use `read`, `grep`, `glob`, and `bash` for inspection, `edit` and `write` for changes, and the native todo tool for task tracking. OMP `eval` is disabled. Read the actual tool schemas before calling tools; Cursor `Task`, `Agent`, `AskQuestion`, Plan Mode, cloud workers, `computerUse`, and `hub` are not OMP requirements.

## Independent agents

Use OMP `task` with the installed agent name. Give exact allowed paths, the question or review lens, verification evidence, output format, read-only authority, and a stopping condition. Collect the completed report. Do not pass Cursor `subagent_type`, `readonly`, or cloud/worktree fields. Follow the native task tool's completion and cancellation contract.

| Requested work | OMP agent |
| --- | --- |
| Architecture alternatives and convergence | `architect-grok`, `architect-kimi` |
| Material implementation review | `reviewer` |
| Independent adversarial fix review | `reviewer-kimi` or `reviewer`, selecting a different configured model family from the driver |
| Comment Sicko | `comment-sicko` |
| Planning | `planner` |
| Consequential decision support | `oracle` |
| Requested completeness walk | `completeness` |

Named agents use their frontmatter and configured model roles. Do not override their models. For investigation or synthesis, use the installed general `task` agent with a bounded read-only packet if delegation is useful. Do not assume a `scout` persona is installed. Multi-agent playbooks use these native agents within available capacity; cloud ownership and Graphite are not prerequisites. Git and GitHub CLI operations remain subject to task authorization.

For the retained `adversarial-fix-review` trigger, give the independent reviewer the original reported behavior, the candidate diff, reproduction evidence, and a request to disprove the claimed cause and fix. Require PASS / BLOCK / INCOMPLETE with concrete evidence. Verify the configured family differs from the driver. If no different family is available, report that exact limitation instead of counting same-family review as cross-family proof. The retired standalone skill is not required.

## Skills and verification

- `deslop` is the managed ADN skill at `skill://deslop`. No plugin installation is required.
- `no-comments` is the managed skill at `skill://no-comments`. It invokes the installed `comment-sicko` agent. An ordinary implementation review does not replace this review.
- For retained `create-skill` references, use the Authoring or modifying a skill playbook. Write name and description frontmatter, explicit scope, native tool instructions, and resolvable references; verify discovery and a representative invocation. Cursor's built-in skill is not required.
- For retained `control-cli` references, exercise the actual CLI through `bash` and use an available terminal control tool for interactive states. For `control-ui`, use an installed browser or computer-use tool or skill and inspect the actual output. Do not claim that an OMP plugin supplies either skill. If the necessary control tool is unavailable, report the specific interaction left unverified.
- For history and session pickup, use OMP's exposed session tools or the caller's handoff and Git evidence. Never invent Cursor transcript paths or claim unavailable history was inspected.

Missing required tools, authentication, sources, or review coverage produce an explicit incomplete result. Never waive a named gate silently or claim an unrun check passed.
