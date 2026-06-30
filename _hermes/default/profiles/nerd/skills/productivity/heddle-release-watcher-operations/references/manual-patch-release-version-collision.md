# Manual Heddle patch release when current main reuses an already-tagged version

Session example: `0.1.16` was already released at `81e6c0d`, then `origin/main` advanced to `f82a1ee` while `package.json` still said `0.1.16`. The release watcher correctly skipped because `v0.1.16` pointed elsewhere.

## Correct recovery pattern

1. Do not create a synthetic SHA/tag release without an installer asset (e.g. `v0.1.16-main-f82a1ee`). If one was created, delete the GitHub release and cleanup tag:
   ```bash
   HOME=/Users/anichols zsh -lc 'gh release delete v0.1.16-main-f82a1ee --repo Nodaste-Lab/heddle --cleanup-tag --yes'
   ```
2. Create a PR against `main` that bumps persisted release identity to a unique patch-release suffix, e.g. `0.1.16-2`:
   ```bash
   git switch -c release/v0.1.16-2 main
   bash scripts/release/set-version.sh 0.1.16-2
   npm run version:build -- --json
   npm run mac:web:build
   npm run mac:native:build
   git add package.json package-lock.json native/macos/SpriteHUD/SpriteHUD/Info.plist native/macos/SpriteHUD/SpriteHUD.xcodeproj/project.pbxproj
   git commit -m 'chore: bump release version to 0.1.16-2'
   HOME=/Users/anichols GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig XDG_CONFIG_HOME=/Users/anichols/.config zsh -lc 'git push -u origin release/v0.1.16-2'
   HOME=/Users/anichols zsh -lc 'gh pr create --repo Nodaste-Lab/heddle --base main --head release/v0.1.16-2 ...'
   ```
3. Merge the PR (squash is OK for this mechanical bump) rather than pushing direct to `main`.
4. Run the watcher manually with the auth/home environment forced:
   ```bash
   HOME=/Users/anichols HEDDLE_RELEASE_AUTH_HOME=/Users/anichols GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig XDG_CONFIG_HOME=/Users/anichols/.config zsh -lc 'python3 scripts/release/main-release-watch.py'
   ```
5. Verify the result by checking both tag target and asset:
   ```bash
   git rev-list -n 1 v0.1.16-2
   git rev-parse origin/main
   HOME=/Users/anichols zsh -lc 'gh release view v0.1.16-2 --repo Nodaste-Lab/heddle --json tagName,name,publishedAt,targetCommitish,url,assets'
   ```

## Compatibility notes

- `scripts/release/set-version.sh` and `scripts/release/build-identity.mjs` accept `0.1.16-2` via the repo's release-version regex: `^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$`.
- `npm run mac:web:build` and `npm run mac:native:build` validated that `CFBundleShortVersionString=0.1.16-2` builds in the current macOS project.
- The release script names the asset `Heddle-v0.1.16-2-installer.pkg` for tag `v0.1.16-2`.
- `gh release view` may show `targetCommitish` as a branch-ish default (e.g. `develop`) even when the git tag itself points at `origin/main`; verify with `git rev-list -n 1 <tag>`.

## Pitfall learned

The watcher is persisted-version based. If `origin/main` carries a version whose tag already exists at another commit, the right fix is to merge a unique version bump to main, then let the watcher/release script publish that real tag and installer asset.
