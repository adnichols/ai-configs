VERDICT: PLAN_NEEDS_REVISION

**READINESS_BLOCKER: GLM scoped-model availability is not concretely implemented or verified.**  
Plan lines 248-258 and 308-331 require GLM-5.2 high to be available for scoped switching, but the existing installer only inserts `openai-codex/gpt-5.5` into `enabledModels`, and `scripts/verify-pi-install.sh` only asserts GPT is present there. `pi --list-models opencode/glm-5.2` proves provider resolvability, not that GLM is enabled in Pi scoped/model controls.  
Required plan change: explicitly add/update `install.sh` and `scripts/verify-pi-install.sh` so `enabledModels` contains both `openai-codex/gpt-5.5` and `opencode/glm-5.2`, while preserving GPT-5.5 as `defaultProvider/defaultModel`. Add a verification command that reads `~/.pi/agent/settings.json` and proves both entries plus the unchanged default.

**READINESS_BLOCKER: Agent discovery verification relies on the wrong surface.**  
P1 lines 237-240 uses `pi list`, but repo docs say `pi list` reports package-managed installs, not repo-managed subagents under `~/.pi/agent/agents/`. The plan says Pi must discover `orchestrator-glm` and `ui-design-glm`, but the phase verification only proves source text exists.  
Required plan change: replace or supplement `pi list` with an installed-agent check, such as verifying `~/.pi/agent/agents/orchestrator-glm.md` and `~/.pi/agent/agents/ui-design-glm.md` after `./install.sh --pi`, plus a manual `/agents` confirmation or an extension to `verify-pi-install.sh` that compares `_pi/agents` with installed Pi agents.
