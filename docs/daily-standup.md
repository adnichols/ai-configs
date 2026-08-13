# Daily stand-up collector

`scripts/daily_standup.py` creates a read-only evidence packet and a first-pass Nodaste `Y / T / B` draft. It does not post to Slack or mutate Herdr/Doct.

## Sources

- Herdr workspaces, agents, and prior-day Git activity on this host, `dever`, and `mbp`
- Doct plan boards in Shared and Personal
- Recent messages in Nodaste `#stand-up`, used as format context
- Nodaste-Lab Heddle PRs merged on the requested date
- Granola meetings whose metadata looks Nodaste-related

Granola excludes titles/metadata matching Jack, coaching, Workday/WD, personal, therapy, or doctor. Its positive filter includes Nodaste, Heddle, CCore, Doct, Herdr, Weft, Navi, Monsoon, Mycelios, Tinker, and Find Studio. Update `WORK_RE` and `EXCLUDE_RE` as the customer/program list changes.

## Run

```bash
python3 scripts/daily_standup.py \
  --date 2026-07-21 \
  --output /tmp/standup-context-2026-07-21.json
```

Omit `--date` to summarize yesterday. The Markdown draft is printed to stdout; the optional JSON packet preserves source evidence and collector warnings for a human/LLM refinement pass.

## Requirements

The existing CLIs must be authenticated and on `PATH`: `herdr`, `doct-agent`, `agent-slack`, `granola`, `gh`, `git`, and `ssh`. Remote hosts need Herdr at `~/.local/bin/herdr` and the configured SSH aliases.

A source failure is reported as a warning and does not stop the other collectors. In particular, the current Granola CLI may report authenticated status while meeting-list calls still reject authentication; the stand-up draft will omit calls and state that caveat until the CLI credentials are repaired.
