# OMP runtime contract

Read this contract when using ADN or any of its routed skills in OMP. It takes precedence over retained Cursor examples in leaf skills, reference packets, and playbooks. Preserve their requested outcomes and evidence; use the installed OMP capabilities below.

## Execution and authority

The driving session owns implementation, tests, fixes, Git, and external actions. Repository and user instructions govern scope and authorization. Mode activation does not authorize publishing a PR, merging, messaging others, deploying, changing branches, or editing another repository. A broken skill does not authorize a separate PR. Delivery stays explicit opt-in under the OMP guidance.

Use `read`, `grep`, `glob`, and `bash` for inspection, `edit` and `write` for changes, and the native todo tool for task tracking. OMP `eval` (Python and JS) is available for computation and scratch work; it never writes tracked files. Read the actual tool schemas before calling tools; Cursor `Task`, `Agent`, `AskQuestion`, Plan Mode, cloud workers, `computerUse`, and `hub` are not OMP requirements.

## Independent agents

Use OMP `task` with the installed agent name. Give exact allowed paths, the question or review lens, verification evidence, output format, read-only authority, and a stopping condition. Collect the completed report. Do not pass Cursor `subagent_type`, `readonly`, or cloud/worktree fields. Follow the native task tool's completion and cancellation contract.

| Requested work | OMP agent |
| --- | --- |
| Architecture alternatives and convergence | `arch-one`, `arch-two`, `arch-three` |
| Required review (exactly one per cycle) | `reviewer` for routine work; `reviewer-two` or `reviewer-three` for complex or high-risk work |
| Comment Sicko | `comment-sicko` |
| Planning | `planner` |
| Consequential decision support | `oracle` |

Named agents use their frontmatter and configured model roles. Do not override their models. For investigation or synthesis, use the installed general `task` agent with a bounded read-only packet if delegation is useful. Do not assume a `scout` persona is installed. Multi-agent playbooks use these native agents within available capacity; cloud ownership and Graphite are not prerequisites. Git and GitHub CLI operations remain subject to task authorization.

## Required reviews

A required review is exactly one read-only reviewer agent per review cycle. It is never the driving session. Adversarial fix review, `autoreview`, and any "final" or "independent" verdict are the same review and are satisfied by one agent. Do not run a second reviewer, a confirmation pass, or a separate verdict pass over the same unchanged candidate. Another pass is warranted only by a material change to the candidate or by the review-budget rules in `autoreview` and `run-plan`. A completed review over the same unchanged diff that answered the required questions satisfies every gate that asks for one.

Choose the role by the complexity and risk of the work. Routine changes use `reviewer`. Data loss, auth or security, concurrency, migrations, cross-boundary contracts, and other hard-to-verify work use `reviewer-two` or `reviewer-three`. Prefer a role whose configured model family differs from the driving session's; read `omp config get modelRoles --json` for that purpose only. If no configured role differs, run the best-fit role anyway and record the same-family limitation in the review record. Same-family is a note, not a blocker.

Roles define coverage, not models. Never compare a role's resolved model to a name in a brief, reject a review because a role resolves to an unexpected model, or invalidate a review because a role's model was reconfigured. If a role fails to launch, report its exact error; the coordinator may pick another reviewer role and records the substitution as a note.

For a claimed fix or necessity claim, add the original reported behavior, the candidate diff, reproduction evidence, and a request to disprove the claimed cause and fix to that one reviewer's packet. The reviewer says whether the bug exists without the change, whether the change is necessary, and whether the fix works. Require PASS / BLOCK / INCOMPLETE with concrete evidence. The retired standalone skill is not required.

## Model roles

OMP owns every model choice through `modelRoles`. ADN agents name a role in frontmatter (`model: "@<role>"`), and the OMP `task` tool takes no per-call model. Ignore the Cursor model slugs in leaf skills, playbooks, and `pstack-models.mdc`; pick the agent whose role fits the work instead.

| Leaf-skill model line | OMP agent (role) |
| --- | --- |
| `feature`, `refactoring`, `bug-fix`, `perf-issue`, `hillclimb`, `swarm workers`, `reflect tooling` | `task` (`@task`) |
| `how explorer`, `why investigators`, `judgment and prose`, `how explainer`, `why synthesizer`, `reflect judgment, divergent, synthesizer` | `task` (`@task`), or the driving session (`@default`) when no delegation is needed |
| `hardest tasks` | `oracle` (`@Oracle`) for a bounded decision packet |
| `architect runners` | `arch-one`, `arch-two`, `arch-three` |
| `arena runners`, `arena cross-judge pool`, `interrogate reviewers` | One read-only agent per distinct model family, chosen from `arch-one`, `arch-two`, `arch-three`, `reviewer`, `reviewer-two`, `reviewer-three`, and `oracle` |

A panel's value is family diversity. Read `omp config get modelRoles --json`, group the candidate agents' roles by model family, and run one agent per family. If fewer families are configured than the panel asks for, run the families you have and say so.

That rule is for panels (`interrogate`, `arena`, architect councils). It does not apply to required reviews above.

## Skills and verification

- `deslop` is the managed ADN skill at `skill://deslop`. No plugin installation is required.
- `no-comments` is the managed skill at `skill://no-comments`. It invokes the installed `comment-sicko` agent. An ordinary implementation review does not replace this review.
- For retained `create-skill` references, use the Authoring or modifying a skill playbook. Write name and description frontmatter, explicit scope, native tool instructions, and resolvable references; verify discovery and a representative invocation. Cursor's built-in skill is not required.
- For retained `control-cli` references, exercise the actual CLI through `bash` and use an available terminal control tool for interactive states. For `control-ui`, use an installed browser or computer-use tool or skill and inspect the actual output. Do not claim that an OMP plugin supplies either skill. If the necessary control tool is unavailable, report the specific interaction left unverified.
- For history and session pickup, use OMP's exposed session tools or the caller's handoff and Git evidence. Never invent Cursor transcript paths or claim unavailable history was inspected.

Missing required tools, authentication, sources, or review coverage produce an explicit incomplete result. Never waive a named gate silently or claim an unrun check passed.
