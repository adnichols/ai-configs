---
name: computer-use
description: >-
  Drive a native GUI app via the cua-driver CLI: snapshot its accessibility
  tree, act through snapshot-bound element tokens, native menu paths, exact
  window geometry, or pixel coordinates, and verify from fresh state. Use for
  desktop app interaction: list apps/windows, get app state, read visible UI,
  click controls, type, press keys, scroll, drag, set values, or perform
  accessibility actions. Also use for browser windows, webviews, or other
  desktop UI. Triggers include "computer use", "read Spotify", "read Slack",
  "control/click/read in a desktop app", and "get app state".
---

# Computer Use

This skill is a routing name. Immediately load and follow `skill://cua-driver`
with the same task, app, and arguments. Do not use Orca's computer-use CLI.

Default transport is the `cua-driver` CLI:

```text
cua-driver <tool-name> '<JSON-args>'
```

If the cua-driver skill pack is missing, run `cua-driver skills install` and
then follow `skill://cua-driver`. If the binary is missing, report that and
stop. Do not fall through to `orca`, `orca-dev`, or `orca-ide`.
