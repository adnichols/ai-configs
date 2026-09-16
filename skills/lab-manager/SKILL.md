---
name: lab-manager
description: Register, provision, claim, inspect, deploy to, and explicitly release CCore development labs through Lab Manager. Use when choosing a free lab or cleaning up an agent worktree's lab accounting, not for production deployment.
---

# CCore lab manager

Run from the intended CCore checkout. Read its `AGENTS.md` and
`apps/lab-manager/AGENTS.md`; use the repository's CLI rather than recreating
the HTTP client or provisioning resources manually. The default manager is
`https://labs.keramos.tech`. This skill has no other skill dependencies.

Use the existing human Cloudflare Access session or already-configured fleet
Access environment. The CLI handles authentication and idempotency. Wrangler
authentication remains separate and is used for product deployment. Never
print credentials or create replacement credentials to work around an error.

## Choose and claim

```sh
pnpm --filter @ccore/lab-manager run lab -- list --all
pnpm --filter @ccore/lab-manager run lab -- inspect <lab>
```

Choose an unclaimed provisioned lab within the user's authorized scope. If a
new lab is needed, register its `labNNN` name and let the manager provision it:

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

Release only this work's claim when the user accepts the work or asks for
worktree cleanup, before deleting the worktree. Multiple PRs do not end a claim:

```sh
pnpm --filter @ccore/lab-manager run lab -- release --host <recorded-host> --worktree <recorded-worktree>
```

If the manager is unreachable during requested worktree cleanup, report the
unreleased accounting and continue safe worktree cleanup. Do not claim release
succeeded. Deprovision only when the user authorized removing that lab's
infrastructure, using `lab deprovision <lab> --wait`. Imported labs require
explicit force; never use it to bypass uncertain ownership. Preserve shared
credentials and other agents' data.
