# Pi VCC continuation rollback and rollout evidence

Recorded 2026-07-10 for the `pi-vcc-continuation-guarantee` implementation.

## Source checkpoints and archives

- Pre-change commit: `3d6ab5b` (`chore: retire legacy agent configs`).
- Pre-change archive: `/tmp/pi-vcc-rollback/pre-change-3d6ab5b.tar.gz`.
- Pre-change archive SHA-256: `988f52de1628b11e0e2ae9e547413b6119c4368f33a8e0456a99999d0043839a`.
- Original candidate checkpoint: `a860ec7` (`fix(pi-vcc): guarantee continuation after compaction`).
- Original candidate archive: `/tmp/pi-vcc-rollback/candidate-a860ec7.tar.gz`.
- Original candidate archive SHA-256: `c0afabd58761391c50d2f27dd1fb16bc34407d73c873561ed4c4ff18a77e2c9c`.
- The `a860ec7` candidate archive is superseded by final review-fix checkpoint `62c9b40` (`fix(pi-vcc): close continuation review gaps`).
- Final candidate archive: `/tmp/pi-vcc-rollback/candidate-62c9b40.tar.gz`.
- Final candidate archive SHA-256: `25e2cc258638b96bc04faa67add8c8728c228077df07938e81c6b4cec422562d`.

## Rollback switch and procedure

- Runtime authority switch: `PI_VCC_CONTINUATION_AUTHORITY=legacy` disables coordinator sends while preserving persisted protocol evidence. Default is `coordinator`.
- Installed rollback procedure: run `./install.sh --pi` from the recorded pre-change archive/worktree, then run `bash scripts/verify-pi-vcc-install.sh` and the installed soak. Never patch installed Pi `dist`, the stable package mirror, or the live extension directly.
- Candidate install command after a committed checkpoint: `./install.sh --pi`.
- No rollback execution is claimed in this artifact. Archives were created and hashed; an actual rollback was not performed.

## Hash evidence

At the initial committed candidate before these review fixes, source/stable/live matched:

- Package source and stable mirror tree hash: `058ed95cc742175c4b9d58c335b31ef6b1ec8778ebbb0bd05c14a8067d700263`.
- Standalone source and live extension SHA-256: `4a2101a55bd92be8e53a95842a442b474150085ffd0114bbc02d1732a694af4a`.

After committed review fixes at `62c9b40`, source intentionally drifts from installed runtime until the prescribed install:

- Current package source tree hash: `1f3c72c63fbf16510acd7ef5b77973baca877c7f9bf3a970711aee3ddc96d0e7`.
- Current standalone source extension SHA-256: `4ab45dee4cd10ec44b4158398453d93bd6b4bcd6538cc2a183f78823b4430df6`.
- After final installation, stable/live were updated to the committed review-fix source hashes: package `1f3c72c63fbf16510acd7ef5b77973baca877c7f9bf3a970711aee3ddc96d0e7`; extension `4ab45dee4cd10ec44b4158398453d93bd6b4bcd6538cc2a183f78823b4430df6`.

## Verification evidence

Before review fixes, strict installed verification and installed soak both passed against the committed installed candidate:

- `bash scripts/verify-pi-vcc-install.sh` → exit `0`, Pi `0.80.6`, matching package/extension hashes, registered package, enabled extension path.
- `bash scripts/run-pi-vcc-continuation-soak.sh --candidate installed --compactions 10 --fault-matrix all` → PASS.

After review fixes, source soak evidence:

- `bash scripts/run-pi-vcc-continuation-soak.sh --candidate source --compactions 10 --fault-matrix all` → PASS with the actual selected `createContinuationCoordinator`, host-faithful handlers/timers/EventBus/session mock, selected standalone extension publisher, and mixed-log audit.
- `bash scripts/verify-pi-vcc-install.sh --source-only` → PASS.
- Strict `bash scripts/verify-pi-vcc-install.sh` after final installation → exit `0`, Pi `0.80.6`, matching package/extension hashes, registered package, enabled extension path.
- `bash scripts/run-pi-vcc-continuation-soak.sh --candidate installed --compactions 10 --fault-matrix all` after final installation → PASS with 10 terminal coordinator transactions, selected installed standalone publisher, and strict audit.
- `python3 scripts/audit-pi-vcc-continuations.py --require-terminal --sessions ~/.pi/agent/sessions --log ~/.pi/logs/pi-vcc.jsonl` → PASS after mixed-log recognition was restricted to strict transaction records tied to audited durable requests.

The final candidate checkpoint/archive and post-install rollout evidence are recorded. No rollback execution is claimed.
