# pi-thread-bridge

User hook that patches Hermes gateway at startup to add an upgrade-safe Pi passthrough mode without modifying Hermes core files.

## Behavior
- `/pi new <repo-path>` starts an interactive Pi session in that repo
- `/pi attach <session-file-or-repo-path>` attaches to an existing Pi session
- `/pi status` shows bridge state
- while active, every thread message is forwarded directly to Pi
- `/STOP` is intercepted and sends ESC to Pi
- Pi output is relayed back into the thread

## Location
This hook lives under `~/.hermes/hooks/pi-thread-bridge/`, so normal Hermes upgrades should not wipe it.

## Activation
Loaded by the gateway on startup via the standard `~/.hermes/hooks` mechanism.
Restart Hermes gateway after editing this hook.
