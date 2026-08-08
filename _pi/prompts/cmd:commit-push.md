Commit all changes in the repo and push the changes to GitHub.

Load `safe-git-index` before staging or committing. Use its resolved `GIT_WL` wrapper for both operations; never fall back to raw index-mutating Git.

```bash
"$GIT_WL" add -A
"$GIT_WL" commit -m "$COMMIT_SUBJECT"
git push
```
