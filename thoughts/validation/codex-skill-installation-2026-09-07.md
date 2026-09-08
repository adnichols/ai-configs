# Codex parallel skill installation

Implemented the requested parallel skill set under `_codex/skills`. The 70-entry `_codex/skill-overrides.json` records original sources and optional profiles. This includes ADN's complete supporting bundle and the affected shared runtime guides. The originals remain unchanged.

Installed 68 skills into `/Users/anichols/.codex/skills`. The two optional macOS copies were not installed because their shared counterparts were absent. The Codex config now contains a marked block disabling shared counterparts by both lexical and resolved paths and enabling each Codex copy. Other clients retain their shared originals. Account, model, MCP, and unrelated config values were compared before and after and are unchanged. A private config backup was created before the first update.

`python3 _codex/install-skills.py` repeats the scoped installation. The normal Codex installer also invokes it. The installer validates TOML, refuses unmanaged destination collisions, preserves unrelated config entries, handles optional-skill removal, and records installed file hashes. Live reinstall preserved identical config bytes.

Core ADN routing, delegation, history access, model setup, review, and all 23 playbooks now have native Codex contracts. Implementation stays in the driver. Independent review does not claim cross-family diversity. The external delivery ledger remains OMP/Pi-only and is not impersonated by Codex. Product-specific tool guides retain their operational commands for explicitly requested work on those products.

## Evidence

- Codex CLI `0.153.4`, native app-server `skills/list`, with forced reload: every one of the 68 expected names has exactly one enabled entry at its Codex-only path. Zero discovery errors and zero precedence failures.
- All installed files match the installer-recorded SHA-256 hashes.
- Skill Creator validation: all 70 entrypoints valid. Existing explicit invocation policy on necessity review was translated to `agents/openai.yaml`.
- Installer tests: three passed, including config preservation, shared symlink preservation, unmanaged collision refusal, repeated installation, optional selection and removal, and file hashes.
- `_adn` primary tests: 35 passed, zero failed. Routing evaluation passed for 23 playbooks and 28 fixtures.
- `bash -n install.sh` and `git diff --check`: passed.
- Independent read-only forward check: main-only CLI bug fix with no PR, narrow direct `how` with no agents, and planning-only HTML review. Initial planning contradictions were corrected. The targeted rereview passed. This was a scenario inspection, not execution of a live product bug or Doct workflow.
- Full `test_install_shared_skills.sh`: 29 passed, four failed. The failing checks concern files unchanged from HEAD: the obsolete assertion that `_pi/skills` is absent; a missing Hermes planning phrase; a Hermes cron review string; and three Herdr handoff expectations within one suite test. These failures were not relabeled as passing or repaired outside scope.

Restart Codex to reload its configuration and initial skill catalog. This task can retain the catalog it received before installation. No commit, push, remote installation, or application restart was performed.
