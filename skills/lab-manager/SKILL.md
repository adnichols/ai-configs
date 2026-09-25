---
name: lab-manager
description: Register, provision, claim, inspect, deploy to, and explicitly release CCore development labs through Lab Manager. Use when choosing a free lab or cleaning up an agent worktree's lab accounting, not for production deployment.
---

# CCore lab manager

Run from the intended CCore checkout. Read its `AGENTS.md` and
`apps/lab-manager/AGENTS.md`; use the repository's CLI rather than recreating
the HTTP client or provisioning resources manually. The default manager is
`https://labs.keramos.tech`. This skill has no other skill dependencies.

The CLI defaults to browser-free fleet authentication using existing Wrangler
authorization for the Labs account. A disposable remote runtime attaches the
existing Access token from Cloudflare Secrets Store internally; secret values
are never returned to the host. No cloudflared or browser approval is needed.
Already-configured CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET remain
supported. Human Access authentication is opt-in with CCORE_LABS_AUTH=human.
Never print credentials, run wrangler login, or authorize Wrangler by browser
on the operator's behalf. Try a login shell and the checkout's installed
Wrangler first; report a genuine authentication blocker to the operator.

## Choose and claim

```sh
pnpm --filter @ccore/lab-manager run lab -- list --all
pnpm --filter @ccore/lab-manager run lab -- inspect <lab>
```

A request to use verified-build (Codex or OMP variant) authorizes choosing and
claiming an isolated lab without separate checkout permission. Choose an
unclaimed provisioned lab within the user's authorized scope. If a new lab is
needed, register its
`labNNN` name and let the manager provision it:

```sh
pnpm --filter @ccore/lab-manager run lab -- register <lab>
pnpm --filter @ccore/lab-manager run lab -- provision <lab> --wait
pnpm --filter @ccore/lab-manager run lab -- checkout --lab <lab> --agent <runtime> --session <actual-session-id> --project <project>
```

Claim from the actual worktree and host. The CLI derives their identity and
Git branch/SHA; pass overrides only for real metadata. Record the returned
claim ID. Attach actual Linear/PR/task metadata with `lab claim update` as
shown by the CLI help. Claims are advisory accounting, never access grants.
There is no heartbeat, expiry, claim secret, or automatic release on PR merge.

Do not replace another agent's claim merely because it is old. Inspect its
recorded host, worktree and runtime, check whether that agent still exists
when authorized, and use the explicit claim-ID replacement only after resolving
ownership. Do not steal in-use labs or delete another session's resources.

## Deploy and verify

Lab checkout alone does not authorize deployment or fixture mutations. Resolve
those actions from the requested task and existing session authorization; do
not ask again for actions already authorized.

```sh
pnpm run deploy -- --hub <lab>
pnpm --filter @ccore/lab-manager run lab -- fixtures seed <lab>
```

The manager provisions infrastructure and a placeholder, not the agent's
code. Product deployment must use the repository's deploy command. Lab
defaults enable `fixture-password-auth,labs-fixtures`; Google OAuth and
outbound Postmark email are disabled and require no provider secrets or
Google callback registration. Do not add those integrations to unblock an
ordinary lab deploy. Explicitly enabled integrations retain their own
requirements; production is unchanged. Verify the actual deployed artifact,
not only a dry-run or a successful infrastructure provision.

## Explicit cleanup

Keep the lab claimed through agent completion, validation, review handoff,
feedback waits, and idle or blocked work. Preserve the deployment and fixtures
needed for review. Prefer leaving a claim in place over releasing it early.
Include the lab URL, claim ID, owning host/worktree, related PRs, and pending
cleanup in the handoff.

Release only this work's claim during cleanup after all PRs using the lab have
merged and the operator has explicitly agreed the work is complete. Merge alone
or acceptance before merge is insufficient. For work without a PR, wait for
explicit completion and cleanup agreement. An explicit instruction to abandon
the work and release its lab also authorizes cleanup without merge. A generic
worktree cleanup request does not authorize releasing a lab still awaiting review;
preserve the claim and its recorded identity. Verify the release conditions
before running:

```sh
pnpm --filter @ccore/lab-manager run lab -- release --host <recorded-host> --worktree <recorded-worktree>
```

If the manager is unreachable during requested worktree cleanup, report the
unreleased accounting and continue safe worktree cleanup. Do not claim release
succeeded. Deprovision only when the user authorized removing that lab's
infrastructure, using `lab deprovision <lab> --wait`. Imported labs require
explicit force; never use it to bypass uncertain ownership. Preserve shared
credentials and other agents' data.
