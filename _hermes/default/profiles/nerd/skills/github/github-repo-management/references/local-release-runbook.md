# Local repository release runbook notes

Use these notes when a repo has its own local release script rather than a generic GitHub Actions release.

## Trigger pattern from Heddle

A reliable local-release flow observed in `~/code/heddle-release`:

1. Use a dedicated clean checkout for releases, separate from active development work.
2. Copy required local prereq config such as `.env` from the main working checkout, but never commit it.
3. Verify GitHub auth from the same environment that will run the release. In Aaron's Hermes gateway sessions, run auth-bearing GitHub commands through the real macOS home and login shell:
   ```bash
   HOME=/Users/anichols zsh -lc 'gh auth status && gh api user --jq .login'
   ```
4. Inspect `package.json` and `scripts/release/*` to find the repo-native release command instead of assuming plain `gh release create`.
5. For Heddle specifically, follow the repo's current persisted-version release flow rather than generic `gh release create` or old bumping commands:
   ```bash
   HOME=/Users/anichols zsh -lc 'cd /Users/anichols/code/heddle-release && npm ci'
   HOME=/Users/anichols zsh -lc 'cd /Users/anichols/code/heddle-release && npm run release:local -- --publish'
   ```
   The `develop -> main` PR must already contain the intended release version and native build number. The post-merge local release command builds, tags, and publishes that already-merged version; it must not run `release:local:minor`, `release:local:patch`, pass a new version argument, or create a follow-up version-bump commit on `main`.
   If the version is wrong, stop and fix the release PR/version files before merge instead of overriding the watcher command. If `v<package.version>` already exists for a different commit after a non-release main merge, the watcher should treat that SHA as already covered/no-op rather than bumping to a new version; if the tag points at the merged commit, it may still run the release path to repair a missing GitHub asset.
6. Monitor the running process and release log until completion. Check for lock files/state if a watcher launched the process.
7. Verify the result with both git and GitHub:
   ```bash
   HOME=/Users/anichols zsh -lc 'cd /path/to/repo && git log -3 --oneline --decorate && git describe --tags --abbrev=0'
   HOME=/Users/anichols zsh -lc 'cd /path/to/repo && git rev-list -n 1 <tag> && git rev-parse origin/main'
   HOME=/Users/anichols zsh -lc 'gh release view <tag> --repo <owner/repo> --json tagName,name,isDraft,isPrerelease,url,createdAt,publishedAt,assets --jq .'
   ```
   For annotated tags, `git ls-remote --tags origin refs/tags/<tag>` returns the tag object SHA, not the tagged release commit; use `git rev-list -n 1 <tag>` when confirming that the tag resolves to `origin/main`.

## What to report

Keep the final status concise and evidence-backed:

- release tag and URL
- trigger commit and released main commit/tag target
- uploaded asset name, size or digest when available
- local artifact path
- full log path
- verification gates that passed
- non-blocking warnings that appeared in the release log

## Pitfalls

- Do not create a generic GitHub release before checking the repo's local release script; local scripts may build native packages, sign/ad-hoc-sign assets, push tags, and upload assets in one controlled path. For current Heddle, version bumping belongs in the main-release PR before merge, not in the local release command.
- Do not trust `gh auth status` from a sandboxed Hermes `HOME`; a false unauthenticated result can block a valid release path.
- Do not stop after starting a long-running release. Monitor until the process exits and verify the GitHub release asset exists.
- Treat release logs as potentially sensitive if they include environment-derived build configuration; summarize rather than dumping them.
