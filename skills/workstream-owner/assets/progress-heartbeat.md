Progress check for the WKS workstream "{{NAME}}". Paseo sends this on cron `{{CRON}}` while you are idle, never during a turn.

Continue skill://workstream-owner's Owner contract from where you are.
- If your next step can be done now, do it, and keep going until the workstream is done or blocked.
- If you are waiting on something outside your control (the driver's reply or your brief, CI, a review, the merge, another workstream, a deploy, an operator action), check it once and act on any change. If nothing changed, end the turn with one line naming what you wait on.
- If the wait will last more than a day, such as a ring promotion, slow this heartbeat with `paseo heartbeat update <id> --cron "0 */4 * * *"`, and set it back with `--cron "{{CRON}}"` when the wait ends.
- When the contract's Finish is complete, delete it with `paseo heartbeat delete <id>`.

`<id>` is the `id=` value in this message's `fired (id=...)` line.
