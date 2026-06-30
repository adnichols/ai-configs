# C-Core to Doct linked-copy workflow

Use this reference when copying C-Core documents/signals/project_contexts into Doct for human review while preserving provenance.

## Proven workflow

1. Verify Doct auth and discover target workspace/folder:
   ```bash
   doct-agent auth status --json
   doct-agent workspaces list --json
   doct-agent documents list --workspace-id <shared-workspace-id> --json
   ```
2. Verify C-Core local state and read source docs:
   ```bash
   ccore health
   ccore status
   ccore space sync-status nodaste --json
   ccore doc list nodaste
   ccore doc show <source-id> --space nodaste --include-content
   ```
3. For signals, parse `current_version_content | fromjson` to get `body`, `requester_actor_id`, `assignee_actor_id`, `status`, and related fields.
4. For non-signal managed objects, `current_version_content` may itself be a JSON-encoded string containing fields such as `project_registry_id`, `search_text`, and `status`.
5. Create Doct documents under the shared folder with a stable path such as:
   ```text
   ccore/source-copies/<slug>-<source-id-prefix>.md
   ```
6. Include a visible `## Source Metadata` section instead of leading YAML frontmatter:
   ```markdown
   ## Source Metadata

   - **Source system:** C-Core
   - **Source space:** `nodaste`
   - **Source kind:** `project_context`
   - **Source document ID:** `<uuid>`
   - **Source updated at:** `<timestamp or unknown>`
   - **Linked copy created at:** `<timestamp>`
   ```
7. Prefer an index Doct doc listing every source ID, Doct ID, and modeling pattern.
8. After creation, verify with:
   ```bash
   doct-agent documents get --id <index-doc-id> --text
   doct-agent documents list --workspace-id <workspace-id> --json
   ```

## Important quirks learned

- `doct-agent documents create --content <markdown>` can fail if the markdown starts with `---`; pass generated content as `--content=<markdown>` instead.
- Doct can render YAML-style frontmatter as visible markdown (`## source: ...`) rather than hiding it. Use explicit human-readable source metadata for linked copies.
- `doct-agent documents list --json` may return a bare array, not `{ "documents": [...] }`; parsing code should handle both.
- `ccore doc show --include-content` may return content but missing/null top-level `title` or `id` for some IDs. Use `ccore doc list <space>` plus the originating signal text for authoritative titles when exporting.
- If a first draft export creates bad copies, clean up only the documents you just created and verified by ID; do not delete/recreate existing collaborative Doct docs for routine revisions.

## Python argv-safe create pattern

```python
subprocess.run([
    "doct-agent", "documents", "create",
    "--workspace-id", workspace_id,
    "--title", title,
    "--path", path,
    "--kind", "text",
    "--parent-id", parent_id,
    f"--content={content}",
    "--json",
], check=True, text=True, capture_output=True)
```
