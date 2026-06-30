# Release cleanup + version baseline restoration

Use when a release was published with the wrong semantic version and the user asks to remove it so the next release can use the intended version.

## Key lesson
Deleting a GitHub release and its tag only removes GitHub release metadata and the tag ref. If the release workflow also committed version metadata to the default branch (`package.json`, lockfiles, app manifests, Xcode project files, etc.), the next release command will still calculate from that committed version. Restore the version baseline in git if the next release should continue from the prior version.

Example: if `0.1.7` was accidentally released as `0.2.0` and the next intended release is `0.1.8`, remove `v0.2.0` **and** revert version files from `0.2.0` back to `0.1.7` in a PR.

## Checklist

1. Inspect the release before deletion:
   ```bash
   gh release view vX.Y.Z --json tagName,name,url,targetCommitish,assets,publishedAt
   git ls-remote --tags origin refs/tags/vX.Y.Z
   git tag --list vX.Y.Z
   ```

2. Identify whether a release commit touched version metadata:
   ```bash
   git log --oneline -10 origin/main
   git show --stat --name-status <release-commit-sha>
   git show origin/main:package.json | node -e "let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>console.log(JSON.parse(s).version))"
   ```

3. Delete the GitHub release and remote tag:
   ```bash
   gh release delete vX.Y.Z --cleanup-tag --yes
   git tag -d vX.Y.Z 2>/dev/null || true
   ```

4. Verify deletion:
   ```bash
   gh release view vX.Y.Z   # should fail: release not found
   git ls-remote --tags origin refs/tags/vX.Y.Z  # should print nothing
   git tag --list vX.Y.Z  # should print nothing
   ```

5. Restore the version baseline if needed:
   - Prefer a normal PR over rewriting protected/default branch history.
   - Revert only version metadata from the accidental release commit when possible:
     ```bash
     git revert --no-commit <release-commit-sha>
     git diff --cached --stat
     git diff --cached --check
     git commit -m "fix: restore version baseline after erroneous release"
     git push
     ```
   - Confirm project-specific scripts/config changes from the active branch were not accidentally removed.

6. Update the PR body/report with:
   - deleted GitHub release tag
   - deleted remote/local tags
   - restored baseline version
   - expected next version after the intended bump

## Pitfalls
- A release tag may point at one commit while the release commit that bumped files is a different commit; inspect both release metadata and `origin/main` history.
- `gh release delete --cleanup-tag` removes the remote tag, but local tags remain until deleted.
- If the release uploaded assets, the release deletion removes their GitHub-hosted download URLs; local artifacts may still exist and should not be deleted unless requested.
