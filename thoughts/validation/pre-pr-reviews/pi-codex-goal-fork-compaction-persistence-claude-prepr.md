1. Scope checked

  Read-only review of the working tree against origin/main plus the external fork-install evidence. I re-read the diff (install.sh, scripts/verify-pi-install.sh, test_install_shared_skills.sh, _pi/README.md,
  _codex/prompts/cmd:send-plan-to-doct.md), the plan HTML, the PM review, the Codex pre-PR result, and traced install/purge/verifier control flow end-to-end. I did not run any tools; I relied on the verification results
  provided.

  2. Coverage table

  ┌─────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬──────────────┬──────────┐
  │                     File / surface                      │                                                         Check performed                                                         │    Result    │  Status  │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ install.sh install_pi_codex_goal_package +              │ Purge keeps first desired-source entry, removes duplicates and any non-desired pi-codex-goal variant; loop is idempotent on     │ No blocking  │ Complete │
  │ purge_stale_pi_codex_goal_registrations                 │ re-run (has_desired path → pi update)                                                                                           │ issue        │          │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ install.sh ordering (install_pi_npm_packages →          │ Deprecated npm:pi-codex-goal removed first (matching Removing deprecated Pi package pi-codex-goal test assertion), then git     │ Correct      │ Complete │
  │ install_pi_codex_goal_package)                          │ source installed; python purge covers stale settings entries pi list misses                                                     │              │          │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ install.sh new deprecated-list entry pi-codex-goal      │ Correctly demotes upstream npm and prevents reinstall on re-run                                                                 │ Correct      │ Complete │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ scripts/verify-pi-install.sh                            │ Fork source moved to EXPECTED_GIT_PACKAGES; explicit npm:pi-codex-goal still-registered check added; failure emits both a       │ Correct      │ Complete │
  │                                                         │ missing-git entry and a stale-npm note                                                                                          │              │          │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │                                                         │ test_pi_codex_goal_fork_install_purges_stale_npm seeds npm:pi-codex-goal and asserts fork replaces it;                          │              │          │
  │ test_install_shared_skills.sh                           │ test_verify_pi_install_reports_stale_goal_package proves negative path; parity test still enforces Pi/Codex prompt agreement    │ Correct      │ Complete │
  │                                                         │ outside the codex-specific set                                                                                                  │              │          │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ _pi/README.md                                           │ Fork source documented under git-managed packages; stale npm removal explained                                                  │ Correct      │ Complete │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ _codex/prompts/cmd:send-plan-to-doct.md                 │ Listener wording now aligned with Pi/OMP listenerCommand guidance; test parity assertions updated in tandem                     │ Correct      │ Complete │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ Plan / PM review / Codex pre-PR                         │ Plan progress reflects P1–P3 complete + current-host P4 evidence; PM review PASS; Codex pre-PR CLEAN                            │ Consistent   │ Complete │
  ├─────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼──────────┤
  │ External fork                                           │ git ls-remote and installed checkout both at fe5f306579025c86b6d30b51203bf2451d349896; installed-runtime smoke shows            │ Consistent   │ Complete │
  │                                                         │ compact_context fired and goal remained active with PI_VCC_GOAL_OK marker                                                       │              │          │
  └─────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────┴──────────┘

  3. Findings

  None blocking.

  Non-blocking observation (informational; not a finding requiring resolution): the pi-list awk in install_pi_codex_goal_package (install.sh:2433) matches whole-line sources without stripping any @<ref> suffix, whereas
  scripts/verify-pi-install.sh:191 defensively strips @.* from git sources. If a future pi list variant renders the git-fork line with a commit suffix, the equality check against the unqualified desired_source would
  evaluate to false and cause a spurious pi remove / pi install cycle on each rerun. Current Dever evidence shows the unqualified form, so this is not observable today; leaving as follow-up rather than a gate. (Scope:
  OUT_OF_SCOPE_FOLLOW_UP; does not block PR.)

  5. Final verdict

  VERDICT: CLEAN_FOR_PR
