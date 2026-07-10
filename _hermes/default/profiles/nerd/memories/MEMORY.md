On Aaron's machine: fastmail inbox mailbox is `Inbox` (case-sensitive). Auth CLIs under Hermes may need `HOME=/Users/anichols`; gh works with `zsh -lc`; Codex may need `HOME=/Users/anichols zsh -lic ...`; Claude Code requires PTY + `HOME=/Users/anichols zsh -lic ...` to see the Claude Max login.
§
Obsidian shared agent routines use `adn_vault/.agents` / `_agents` or `_pi`; old `~/Documents/Obsidian/.opencode` symlink is removed. Aaron has OpenCode server at http://localhost:63333 for Hermes HTTP session control; avoid dumping `/config` secrets.
§
In Discord adn_core #chief-dev coding thread, Aaron's references like 'ccore' or 'doct' should default to the repos in his code directory; this repo-centric interpretation is channel-specific and should not be generalized to other channels.
§
Tommy Lionelli follow-up should stay deferred until visible activity starts around going to design partners for C-Core/Heddle; once that motion is visible, resurface Tommy as a likely interested candidate.
§
Heddle release watcher: repo /Users/anichols/code/heddle-release, cron 725d93200439 (`heddle-main-release-watch`) calls repo `scripts/release/main-release-watch.py`; origin stays HTTPS; old profile script is a thin wrapper only.
§
In Discord, Aaron introduced two Hermes agents for Nodaste collaboration: <@1492518439783501834> runs on the MacBook Pro (mbp) and <@1492541112852938782> runs on the development system (dever). They can mention each other and coordinate in shared threads on projects for Aaron.
§
Discord agent identities: this agent is Chief; <@&1492542870631223499> / Dever agent is Dever; only Aaron can change identity assignments.
§
OpenCode Linear build is compatibility-only: before using `hermes-opencode-linear-build`, verify the independently maintained command and both helper scripts exist under ~/.config/opencode. If absent, use maintained Pi/Codex workflows. When provisioned, Hermes launches/monitors `/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>` and OpenCode owns orchestration. Bundle repo ~/code/hermes-configs.
§
On Aaron's macOS setup, background launchd jobs reading Obsidian vaults under ~/Documents can hit TCC permission issues; prefer Obsidian app-context triggers or a polling fallback over direct launchd-first designs.