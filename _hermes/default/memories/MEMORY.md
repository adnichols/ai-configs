Fastmail CLI mailbox names are case-sensitive: use `Inbox`; use `zsh -lc` for zsh-dependent CLIs like accli to avoid bash ~/.zshrc Oh My Zsh errors.
§
For Obsidian shared agent routines, use `adn_vault/.agents` / `adn_vault/_agents` or `_pi`; the old `~/Documents/Obsidian/.opencode` symlink has been removed.
§
In Discord adn_core #chief-dev coding thread, Aaron's references like 'ccore' or 'doct' should default to the repos in his code directory; this repo-centric interpretation is channel-specific and should not be generalized to other channels.
§
Aaron's C-Core code currently lives under ~/code/heddle/ccore; its git root is ~/code/heddle.
§
In Discord, Aaron introduced two Hermes agents for Nodaste collaboration: <@1492518439783501834> runs on the MacBook Pro (mbp) and <@1492541112852938782> runs on the development system (dever). They can mention each other and coordinate in shared threads on projects for Aaron.
§
Discord agent identities: this agent is Chief; <@&1492542870631223499> / Dever agent is Dever; only Aaron can change identity assignments.
§
Shared Hermes/Pi bundle: /Users/anichols/Obsidian/adn_vault/_pi/extensions/hermes-pi-workflow-bundle. Pi docs/prompts stay authoritative; scope shared workflow adoption to Hermes-side config/skills/plugins/scripts unless Aaron asks for Pi runtime config.
§
On Aaron's macOS setup, Obsidian must be running for vault sync; verify app/sync before blaming missing notes. Launchd vault readers can hit TCC; prefer Obsidian-context triggers or polling.
§
On Aaron's machine, `ccore health` can be OK while `ccore space list` fails because local runtime auth vault cannot unlock `account-session.enc` non-interactively; treat C-Core reads as unavailable until `CCORE_PASSPHRASE` is supplied or `ccore init` reseeds auth.
§
Aaron's /gm outputs: signal items need status/from/context/sent/responses; plan-review comment watchers must be quiet-by-default and durable until the plan is archived.
§
Hermes config source: ~/code/ai-configs/_hermes/default via scripts/hermes_config_sync.py export/verify/install; after Hermes config changes, export/verify then commit/push ai-configs; excludes secrets/runtime.