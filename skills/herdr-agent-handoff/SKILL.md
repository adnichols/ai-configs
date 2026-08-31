---
name: herdr-agent-handoff
description: >-
  Transfer live coding work to a new agent in a new Herdr session and a new Git
  worktree. Use whenever the operator asks to move, hand off, send, delegate,
  or continue current work in another Herdr agent and checkout. Default to a
  new same-host Herdr session plus worktree. Support a remote destination only
  when the operator specifies one. Preserve the source runtime and active model,
  give the receiver a callback path, verify acceptance, and leave the source
  agent available for context. This is a live agent transfer, not a handoff
  document workflow. Do not use for topology-only requests that explicitly ask
  not to start an agent.
---

# Hand off work to a Herdr agent

Move ownership, not only files. A completed handoff has a new Herdr session, a new Git worktree, and a live destination agent that accepted the task. The source agent stops implementing after acceptance but stays available for context questions.

Use the `herdr` skill as the authority for current CLI syntax and returned JSON fields.

## Keep the default shape

Unless the operator says otherwise:

- Create a new named Herdr session on the source host.
- Create a new Git worktree in that session.
- Start a new agent in the worktree's root pane.
- Use the same agent kind, active fully qualified model, and separate reasoning level as the source agent.
- Keep the source agent alive and addressable until the destination agent says that it no longer needs source context.

Do not reuse the source session or checkout. Do not create only a worktree and then continue the transferred work from the source agent.

If the operator specifies a remote host, create both the Herdr session and the worktree on that host. Without an explicit remote host, use the local host. Paths in remote commands refer to the destination host.

## Record the source before mutation

Before creating or opening destination resources, record:

- the source agent kind;
- the active fully qualified model ID;
- the separate reasoning or thinking level, when the runtime has one;
- the source host;
- the source Herdr session, if it is named;
- the source pane ID;
- the source agent name, if one exists;
- the repository, exact `HEAD`, staged changes, unstaged changes, untracked files, task, constraints, current state, and verification already run.

Use runtime identity from the current harness or the runtime's session metadata. Do not infer the active model from a configured default or from `herdr agent get`; Herdr identifies the agent kind but does not prove the active model. If native state cannot establish runtime or model identity, report an incomplete handoff instead of silently launching a different profile.

The source agent chooses the prompt and the amount of context. Do not create a handoff document unless the operator separately requests one. Do not dump the transcript when a short task packet is enough.

## Preserve the source checkout

If the operator already authorized a commit, commit before taking the snapshot and use the new exact `HEAD`. Otherwise, leave the index and worktree unchanged. Freeze task writes while taking the snapshot. Do not edit files, change the index, or update task refs until the destination state matches. The temporary bundle ref below is the only allowed source-repository mutation after the snapshot.

Record the exact source commit and a NUL-safe status snapshot:

```bash
git rev-parse HEAD
git status --porcelain=v1 -z --untracked-files=all
```

If the status snapshot is empty, create the destination branch from that exact commit. Do not use a branch name whose tip may move.

If the source is dirty, preserve all three Git states:

```bash
git diff --cached --binary --full-index > <state-dir>/staged.patch
git diff --binary --full-index > <state-dir>/unstaged.patch
git ls-files --others --exclude-standard -z > <state-dir>/untracked.paths
tar -C <source-root> --null -T <state-dir>/untracked.paths \
  -czf <state-dir>/untracked.tar.gz
```

Use absolute state-directory paths. Create the untracked archive only when `untracked.paths` contains entries.

Store the source `HEAD`, the exact NUL-safe status bytes, patch hashes, and an untracked-file manifest with path, mode, size, and content hash. Keep the state directory outside the repository. Exclude ignored files unless the operator explicitly names safe ignored files to transfer.

If a submodule has staged, unstaged, or untracked changes, apply this same snapshot and verification process inside that submodule. Otherwise, report `HANDOFF_INCOMPLETE`; the superproject diff does not contain the submodule's working files.

Use the patch and archive path whenever the frozen source remains dirty. Do not stash, reset, stage, or commit the operator's work merely to make transfer easier.

For a same-host transfer, the destination repository can use the source commit directly. For a remote transfer, first check whether the destination repository contains the source commit. If it does not, create a temporary source ref, put that ref in a `git bundle`, copy the bundle over SSH, fetch it into a temporary destination ref, and delete both temporary refs after destination verification. This moves Git history without pushing an operator branch or assuming that the destination remote is current.

```bash
git update-ref refs/herdr-handoff/<transfer-id> <source-head>
git bundle create <state-dir>/source.bundle \
  refs/herdr-handoff/<transfer-id>
git update-ref -d refs/herdr-handoff/<transfer-id>
scp <state-dir>/source.bundle <destination-ssh-target>:<remote-state-dir>/
ssh <destination-ssh-target> git -C <destination-repo-path> fetch \
  <remote-state-dir>/source.bundle \
  refs/herdr-handoff/<transfer-id>:refs/herdr-handoff/<transfer-id>
```

Copy the dirty-state directory to the remote host over SSH when the source is dirty. Keep credentials and ignored files out of the transfer.

## Select the destination

Build one reusable `<destination-herdr>` prefix and apply it unchanged to every Herdr command that targets the destination.

For the default same-host transfer, `<destination-herdr>` is:

```bash
herdr --session <new-session>
```

For an operator-specified remote transfer, `<destination-herdr>` is:

```bash
herdr --remote <destination-ssh-target> --session <new-session>
```

Always create a new destination session name. The `--remote` and `--session` selectors are global selectors before the command group. The `--session` selector creates or targets that named persistent Herdr session. Do not omit either selector from later destination discovery, creation, start, prompt, wait, get, read, or pane commands.

Begin destination discovery through the same prefix:

```bash
<destination-herdr> status
<destination-herdr> workspace list
<destination-herdr> worktree list --cwd <destination-repo-path>
```

For a remote destination, establish a source SSH target that the destination host can use for callbacks. Do not assume that the local hostname is reachable from the remote host.

## Create the worktree, restore state, and start the agent

Create the worktree through the destination prefix:

```bash
<destination-herdr> worktree create \
  --cwd <destination-repo-path> \
  --branch <new-branch> \
  --base <exact-source-head-or-fetched-transfer-ref> \
  --label <work-label> \
  --no-focus
```

Parse the worktree path, workspace ID, tab ID, and root pane ID from the JSON response. Never predict Herdr IDs. Confirm through `<destination-herdr> pane read` that the root pane is at an interactive shell prompt in the new worktree.

Every destination path is interpreted on the destination host. This includes `<destination-repo-path>`, the returned worktree path, state archives copied to that host, and paths passed to Git, verification, or bootstrap commands. Never run a local command against a remote-host path.

Before starting the agent, restore dirty source state in the destination worktree. Run destination shell operations through the same Herdr prefix and root pane:

```bash
<destination-herdr> pane run <root-pane-id> \
  "git apply --index --binary <destination-state-dir>/staged.patch"
<destination-herdr> pane run <root-pane-id> \
  "git apply --binary <destination-state-dir>/unstaged.patch"
<destination-herdr> pane run <root-pane-id> \
  "tar -xzf <destination-state-dir>/untracked.tar.gz -C <destination-worktree>"
```

For remote setup that must happen before the root pane exists, use non-interactive SSH to the destination host. Once the root pane exists, run restore, verification, and any delivery or repository bootstrap through `<destination-herdr> pane run`. Do not run local `git`, `tar`, or `delivery --cwd <remote-path>` commands for a remote destination.

Fail if an untracked destination path already exists. Do not overwrite a destination-generated file.

Recompute the destination state from the destination root pane and compare it with the source manifest. Require all of these facts before agent startup:

- destination `HEAD` equals the recorded source `HEAD`;
- the NUL-safe `git status --porcelain=v1 -z --untracked-files=all` bytes match;
- the staged and unstaged binary patch hashes match;
- every untracked path, mode, size, and content hash matches.

If any comparison fails, report `HANDOFF_INCOMPLETE`. Do not prompt the destination agent with a checkout that differs from the source.

Start the destination agent with a unique Herdr agent name. Pass runtime arguments after `--`:

```bash
<destination-herdr> agent start <destination-agent> \
  --kind <source-kind> \
  --pane <root-pane-id> \
  --timeout 30000 \
  -- <runtime-model-arguments>
```

Translate the recorded model identity into the source runtime's native flags. Preserve the exact model and reasoning level unless the operator requested an override. For OMP:

```bash
<destination-herdr> agent start <destination-agent> \
  --kind omp \
  --pane <root-pane-id> \
  --timeout 30000 \
  -- --model <source-active-model> --thinking <source-thinking-level>
```

If the runtime has no separate reasoning flag, pass only its model flag. Inspect the runtime's current help when its launch flags are unknown. Do not replace an unknown flag with a guessed one.

## Give the receiver a callback path

Include callback coordinates in the destination prompt. Use the callback form that reaches the source from the destination host.

Prove callback routing before the acceptance prompt. Use only non-interactive discovery so the destination does not prompt the source while the source is waiting for acceptance:

```bash
# Same host, source default session
herdr status
herdr agent get <source-pane-or-agent>

# Same host, source named session
herdr --session <source-session> status
herdr --session <source-session> agent get <source-pane-or-agent>

# From a remote destination host to the source
herdr --remote <source-ssh-target> --session <source-session> status
herdr --remote <source-ssh-target> --session <source-session> \
  agent get <source-pane-or-agent>
```

For a remote destination, run those commands through non-interactive SSH on the destination host. Omit `--session` when the source uses the default session. Require both `status` and `agent get` to succeed. This proves the route without occupying either agent.

The following `agent prompt` forms are for context questions only after the source has finished waiting for the acceptance receipt and has submitted the proceed prompt. Never use a synchronous source callback during acceptance.

Before each actual callback, run `agent get` through the proven route. If the source is `working`, wait for it to settle before sending the question.

Same host, source default session:

```bash
herdr agent prompt <source-pane-or-agent> "<question>" --wait --timeout 120000
```

Same host, source named session:

```bash
herdr --session <source-session> agent prompt <source-pane-or-agent> \
  "<question>" --wait --timeout 120000
```

Remote destination calling the source default session:

```bash
herdr --remote <source-ssh-target> agent prompt <source-pane-or-agent> \
  "<question>" --wait --timeout 120000
```

Remote destination calling a source named session:

```bash
herdr --remote <source-ssh-target> --session <source-session> \
  agent prompt <source-pane-or-agent> "<question>" \
  --wait --timeout 120000
```

Use this first prompt. Fill in only source-selected context. Do not require a file:

```text
You will own this task in a new Herdr session and Git worktree.

Source callback:
- Host or SSH target: <source-host-or-target>
- Herdr session: <source-session-or-default>
- Herdr pane: <source-pane-id>
- Herdr agent: <source-agent-name-or-unset>
- Callback command: <exact-command-prefix-and-target>

During acceptance, do not call the source agent. Put every missing-context question in the `HANDOFF_BLOCKED` receipt.
For this first response, do not edit files or start implementation.
Reply with exactly one line:
HANDOFF_ACCEPTED
or
HANDOFF_BLOCKED: <missing context or prerequisite>

Task and source-selected context:
<task packet>
```

Send the acceptance prompt and inspect the receiver through the same destination prefix:

```bash
<destination-herdr> agent prompt <destination-agent> \
  "<acceptance-prompt>" --wait --timeout 120000
<destination-herdr> agent get <destination-agent>
<destination-herdr> agent read <destination-agent> \
  --source recent-unwrapped --lines 120
```

Accept only the exact `HANDOFF_ACCEPTED` receipt. If the receiver returns `HANDOFF_BLOCKED`, the wait has ended. Answer the listed questions in a revised acceptance prompt, then wait for a new receipt through `<destination-herdr> agent prompt`. Do not implement the task from the source agent while resolving the block.

After acceptance, send a second prompt without `--wait`:

```text
Proceed with the transferred task. You own implementation and verification.
The source is no longer waiting for your acceptance receipt. You may now use
the source callback for missing source-session context.
When you no longer need source context, send this exact message to the source:
HANDOFF_CONTEXT_COMPLETE
```

```bash
<destination-herdr> agent prompt <destination-agent> "<proceed-prompt>"
```

Successful submission of that second prompt completes the ownership transfer. The source agent must stop editing or running implementation commands for the transferred task.

## Stay available without sharing ownership

After transfer, the source agent may answer context questions. It must not edit the destination worktree, run the destination's implementation, or take the task back unless the operator explicitly reassigns ownership.

Keep the source Herdr pane alive until one of these events occurs:

- the destination sends `HANDOFF_CONTEXT_COMPLETE`;
- the operator says that source context is no longer needed;
- a real lifecycle constraint requires shutdown.

Do not close the source session as cleanup immediately after transfer.

## Fail closed

A shell-only worktree is not a handoff. Report `HANDOFF_INCOMPLETE` and the failed step if any of these operations fail:

- destination session creation or selection;
- worktree creation;
- source Git-state capture;
- exact source commit availability on the destination host;
- patch, archive, or bundle transport;
- destination `HEAD`, staged, unstaged, and untracked state verification;
- agent startup;
- runtime or model fidelity;
- prompt delivery;
- the acceptance receipt;
- callback reachability for a remote destination.

Do not silently continue implementation from the source agent after an incomplete handoff. Leave created resources intact unless the operator asks for cleanup.
