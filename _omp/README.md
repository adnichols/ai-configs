# OMP surfaces

This tree contains the repo-managed OMP runtime surfaces installed by `install.sh --omp`:

- `commands/` → prompt-backed OMP commands installed to `~/.omp/agent/commands/`
- `agents/` → OMP agent definitions installed to `~/.omp/agent/agents/`
- `extensions/` → repo-managed OMP extensions installed to `~/.omp/agent/extensions/`
- `models.yml` → GPT-5.6 catalog merged into `~/.omp/agent/models.yml` while preserving unrelated local providers/models; the installer migrates the prior ai-configs GPT-5.5 `slow`, `plan`, and `vision` role values to Sol high/medium but preserves custom role choices and the intentionally selected default role

## Planning entrypoint

Use `/aplan` for the repo-managed OMP planning workflow in this repository.

- `/aplan` is provided by `_omp/extensions/aplan/index.ts`
- interactive `/aplan` enters built-in `/plan` mode and queues the repo-managed planning workflow guidance for the next planning turn
- built-in `/plan` remains untouched; `/aplan` is the repo-managed entrypoint layered on top of it
- while `/aplan` is active, plan updates in `thoughts/plans/` surface `/review:plan` as a non-blocking next step; if standard review leaves inline `[REVIEW:...]` comments, `/review:change-integrate` is auto-run before any manual handoff, and `/review:plan-adversarial` remains an optional follow-up review pass
- `/dev:pm-review <plan> [plan|implementation]` is available as a corrective PM pass that reshapes the plan against intended outcomes, product principles, and early-stage scope fit rather than only listing issues
- after review, `/aplan` leaves execution handoff manual via `/cmd:execute-plan <plan> --target ...` so execution starts outside `/aplan` mode without popping a menu

## Compaction entrypoint

Use the vendored `_omp/extensions/pi-vcc/` extension when you want the same VCC compaction behavior this repo ships for Pi.

- `./install.sh --omp` installs it to `~/.omp/agent/extensions/pi-vcc/`
- it registers the `session_before_compact` hook for algorithmic compaction
- it adds `/pi-vcc` for manual compaction
- it adds `vcc_recall` for searching full session history after compaction
- optional debug config lives at `~/.omp/agent/pi-vcc-config.json`

## Legacy note about `_omp/agents/aplan-legacy.md`

The legacy shim was renamed off the `/aplan` name so the runtime extension owns `/aplan` unambiguously. Keep `_omp/agents/aplan-legacy.md` only for historical guidance that points users back to the runtime `/aplan`; it is not a command entrypoint.
