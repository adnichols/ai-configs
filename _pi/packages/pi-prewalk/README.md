# pi-prewalk (ai-configs vendored)

Vendored fork of [pi-prewalk](https://github.com/lukeramsden/pi-prewalk) for this repository.

A strong model plans, then at the first `edit`/`write` (todo-gated) the session switches to a configured execution model and reasoning level.

## Why vendored

Upstream is an npm package. ai-configs owns execution defaults and multi-profile switching here under `_pi/packages/pi-prewalk` so changes are reviewable in-repo and not lost on `pi update`.

## Profiles

Built-in profiles live in `profiles.json`:

| Profile | Model | Thinking |
|---------|--------|----------|
| `flash` (default) | `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731` | `low` |
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
pi --prewalk                      # arm default profile (flash unless overridden)
pi --prewalk-into terra           # arm named profile
pi --prewalk-into sol:high        # profile with thinking override
pi --prewalk-into openai-codex/gpt-5.6-terra:high   # ad-hoc model
```

In-session:

```
/prewalk                    # arm default profile
/prewalk profiles           # list profiles
/prewalk terra              # arm named profile
/prewalk flash:medium       # profile + thinking override
/prewalk default sol        # session default profile
/prewalk openai-codex/gpt-5.6-terra:high
/prewalk status
/prewalk off
```

Thinking levels: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`.

## Install

Managed by ai-configs `install.sh --pi` / `--all`. Source: `_pi/packages/pi-prewalk` → `~/.pi/agent/local-packages/ai-configs/pi-prewalk`.

Do not `pi install npm:pi-prewalk`; the installer removes that registration.

## Upstream

Based on lukeramsden/pi-prewalk MIT. Local changes: named profiles, user config merge, baked DeepSeek Flash default, session default switching.
