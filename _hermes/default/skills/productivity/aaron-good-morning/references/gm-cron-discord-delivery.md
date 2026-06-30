# Good Morning cron delivery to Discord home channel

Session-derived note for Aaron's Good Morning automation.

## Current supported pattern

For the recurring `/gm` cron job, use Hermes cron delivery to the configured Discord home channel rather than trying to create a new Discord thread dynamically:

- `deliver: "discord"` delivers to `DISCORD_HOME_CHANNEL`.
- `deliver: "discord:<channel_id>"` delivers to a specific channel.
- `deliver: "discord:<channel_id>:<thread_id>"` delivers to an existing thread.
- `DISCORD_HOME_CHANNEL_THREAD_ID` can point home-channel deliveries at an existing thread.

Aaron's configured Discord home channel for this workflow is `<#1492535022811480126>` / `1492535022811480126`.

## Important limitation

Hermes has Discord thread support in the gateway and a Discord tool action for creating public threads, but cron final delivery currently resolves only static targets. It does not natively support: "create a fresh Discord thread per cron run, then deliver the final cron output there."

Do not tell Aaron this is merely a Discord permission issue. The practical gap is Hermes cron-delivery orchestration: dynamic thread creation before final delivery.

## Safe workaround

Use the Discord home channel as the default cron delivery target and publish the full GM report as a plan-review URL. If Aaron wants isolated discussion later, use an existing thread target or implement proper cron delivery support for per-run Discord thread creation.

## Testing pattern

When changing the daily GM cron delivery, create a one-off test cron with the same prompt/skills/toolsets/workdir and `deliver: "discord"`, scheduled a couple minutes in the future with `repeat: 1`. This mimics the scheduled run without waiting until morning.

If updating an existing cron job via the `cronjob` tool, include its current schedule/prompt/skills/toolsets/workdir when updating nontrivial fields; an update call with an empty schedule can fail validation.