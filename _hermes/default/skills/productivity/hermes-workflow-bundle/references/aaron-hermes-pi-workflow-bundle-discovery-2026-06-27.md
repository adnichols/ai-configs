# Aaron Hermes/Pi workflow bundle discovery — 2026-06-27

## Canonical location found

Shared Hermes/Pi workflow bundle:

```text
/Users/anichols/Obsidian/adn_vault/_pi/extensions/hermes-pi-workflow-bundle
```

Git root:

```text
/Users/anichols/Obsidian/adn_vault
```

The bundle contains a `bundle/` export plus `build/` tooling. Its portable tool verifies/imports/exports the workflow bundle:

```bash
python3 _pi/extensions/hermes-pi-workflow-bundle/bundle/tools/hermes_pi_workflow_bundle.py verify --bundle-root _pi/extensions/hermes-pi-workflow-bundle
```

The correct `--bundle-root` is the directory containing `bundle/`, not the `bundle/` directory itself.

## Related snapshot

A broader Dever workflow snapshot also exists:

```text
/Users/anichols/Obsidian/adn_vault/_pi/dever-dev-workflow
```

It includes Pi agents/prompts/extensions/packages plus a redacted Hermes config from Dever. Treat it as a shared reference/install bundle, not a blind overwrite source.

## Adding a Hermes skill to the shared bundle

1. Add the skill to `DEFAULT_SELECTED_SKILLS` in:

```text
_pi/extensions/hermes-pi-workflow-bundle/build/hermes_pi_workflow_bundle.py
```

2. Update `build_spec()` so the SPEC names the skill and its reason for inclusion.
3. Copy/export the skill under:

```text
bundle/skills/<category>/<skill-name>/
```

4. Keep the distributable tool in sync:

```text
bundle/tools/hermes_pi_workflow_bundle.py
```

5. Regenerate/update `bundle/manifest.json` and verify.

## Pitfall discovered

The export tool rewrites `bundle/` from scratch before copying selected skills. If a selected legacy skill exists in the checked-in bundle but not in the current local `~/.hermes/skills`, a naive export can delete much of the bundle before failing.

Durable fix pattern: before deleting `bundle/`, copy the existing export to a temp backup and fall back to the backup copy for selected skills that are absent from the current Hermes home. This preserves legacy/exported skills such as `ltui` while allowing new local skills like `aaron-good-morning` to be added.

## 2026-06-27 change made

`productivity/aaron-good-morning` was added to the bundle, including its references. Verification passed with `ok: true` after excluding `manifest.json` from self-hashing in the manifest file list.
