# GitHub PR review-thread GraphQL recipes

Use when PR feedback includes inline review threads and you need to inspect, reply, and resolve them. REST pull comments show inline comments but not thread resolution state, so use GraphQL for the thread lifecycle.

## Query review threads

When using a query file with `gh api graphql`, pass it with `-F query=@file` (uppercase `-F`). Using `-f query=@file` can send the literal `@file` string and produce a GraphQL parse error like `Expected one of SCHEMA... actual: DIR_SIGN ("@")`.

`/tmp/pr-reviewthreads.graphql`:

```graphql
query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$number){
      reviewThreads(first:100){
        nodes{
          id
          isResolved
          path
          line
          comments(first:20){
            nodes{ databaseId body author{login} createdAt url }
          }
        }
      }
    }
  }
}
```

Run:

```bash
gh api graphql \
  -F owner=OWNER -F repo=REPO -F number=PR_NUMBER \
  -F query=@/tmp/pr-reviewthreads.graphql
```

Hermes/macOS reliability tip: when piping `HOME=/Users/anichols zsh -lc 'gh api graphql ...' | python3 - ...`, stdin may arrive empty if shell quoting or HOME wrapping goes sideways. Prefer redirecting the GraphQL JSON to a temp file and parsing that file when the next step depends on the result:

```bash
HOME=/Users/anichols zsh -lc 'gh api graphql -F owner=OWNER -F repo=REPO -F number=PR_NUMBER -F query=@/tmp/pr-reviewthreads.graphql > /tmp/pr-reviewthreads.json'
python3 - <<'PY'
import json
with open('/tmp/pr-reviewthreads.json') as f:
    data = json.load(f)
print(data)
PY
```

## Reply to an inline review thread

`/tmp/add-pr-thread-reply.graphql`:

```graphql
mutation($thread:ID!,$body:String!){
  addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$thread,body:$body}){
    comment{ id databaseId url }
  }
}
```

Run:

```bash
gh api graphql \
  -F thread=PRRT_... \
  -F body="$(cat /tmp/reply.md)" \
  -F query=@/tmp/add-pr-thread-reply.graphql
```

## Resolve a review thread

`/tmp/resolve-review-thread.graphql`:

```graphql
mutation($thread:ID!){
  resolveReviewThread(input:{threadId:$thread}){
    thread{ id isResolved }
  }
}
```

Run:

```bash
gh api graphql \
  -F thread=PRRT_... \
  -F query=@/tmp/resolve-review-thread.graphql
```

## Verification

After replying/resolving, re-run the thread query and confirm:

- `isResolved: true` on each addressed thread
- do not confuse `isOutdated: true` with resolution; a pushed fix may make a thread outdated while it remains `isResolved: false`
- your reply comment is present with the commit SHA and validation evidence
- PR metadata/checks still show the expected branch head
- if `gh pr checks` exits nonzero with `no checks reported`, record/report that as an informational no-checks state rather than a CI failure
