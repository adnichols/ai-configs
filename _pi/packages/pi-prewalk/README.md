# pi-prewalk (ai-configs vendored)

Vendored fork of [pi-prewalk](https://github.com/lukeramsden/pi-prewalk) for this repository.

The current model plans as-is, then at the first `edit`/`write` (todo-gated) the session switches to a configured execution model and that profile's reasoning level (default Flash implementation uses **max** thinking).

## Why vendored

Upstream is an npm package. ai-configs owns execution defaults and multi-profile switching here under `_pi/packages/pi-prewalk` so changes are reviewable in-repo and not lost on `pi update`.

## Profiles

Built-in profiles live in `profiles.json`:

| Profile | Model | Thinking |
|---------|--------|----------|
| `flash` (default) | `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731` | `max` |
| `terra` | `openai-codex/gpt-5.6-terra` | `high` |
| `glm` | `deepinfra/zai-org/GLM-5.2` | `high` |
| `luna` | `openai-codex/gpt-5.6-luna` | `xhigh` |

User overrides (optional): `~/.pi/agent/prewalk-profiles.json`

```json
{
  "defaultProfile": "terra",
  "profiles": {
    "cheap": {
      "label": "My cheap executor",
      "provider": "deepinfra",
      "id": "deepseek-ai/DeepSeek-V4-Flash-0731",
      "thinkingLevel": "minimal"
    },
    "terra": {
      "thinkingLevel": "xhigh"
    }
  }
}
```

User entries merge over package defaults by profile name. Set `defaultProfile` to choose the unqualified `/prewalk` and `--prewalk` target.

## Usage

```bash
pi --prewalk                      # arm generic default profile (flash unless overridden)
pi --prewalk-into terra           # arm named profile
pi --prewalk-into sol:high        # profile with thinking override
pi --prewalk-into openai-codex/gpt-5.6-terra:high   # ad-hoc model
pi --delivery-hydrate --prewalk-into terra   # delivery dual-plan hydrate framing
```

Generic prewalk keeps its independent Flash default. Delivery-owned `--delivery-hydrate` is pinned by the delivery ledger to Luna xhigh and uses an adapted hydrate nudge (materialize from the agentic plan; do not reopen product decisions), injects the executor checklist even when hydrate and executor resolve to the same model, and writes `.delivery/hydrate-transition.json` at the first successful `edit`/`write`.

Operator `/prewalk` and delivery are mutually exclusive in the same worktree.
If `.delivery/ledger.json` exists, `/prewalk` refuses (delivery-owned
`--delivery-hydrate` at session start still works). While prewalk is armed it
writes `~/.pi/prewalk-armed/<sha256(cwd)>` so `delivery arm` can refuse.
`/prewalk off` or the first successful `edit`/`write` switch clears the marker.
After prewalk has switched and disarmed, a late `delivery arm --from existing-implementation`
is allowed.

In-session:

```
/prewalk                    # arm default profile
/prewalk profiles           # list profiles
/prewalk terra              # arm named profile
/prewalk flash:medium       # profile + thinking override
/prewalk default sol        # session default profile
/prewalk delivery-hydrate terra   # delivery hydrate mode into terra
/prewalk openai-codex/gpt-5.6-terra:high
/prewalk status
/prewalk off
```

Thinking levels: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Arming does **not** change the current planning model or thinking level. The profile `thinkingLevel` applies only when the implementation switch fires.

## Install

Managed by ai-configs `install.sh --pi` / `--all`. Source: `_pi/packages/pi-prewalk` → `~/.pi/agent/local-packages/ai-configs/pi-prewalk`.

Do not `pi install npm:pi-prewalk`; the installer removes that registration.

## Upstream

Based on lukeramsden/pi-prewalk MIT. Local changes: named profiles, user config merge, baked DeepSeek Flash default, session default switching, delivery-hydrate mode + transition receipts.
