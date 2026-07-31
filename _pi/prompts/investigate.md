---
description: Run the deterministic evidence-closed investigation workflow
argument-hint: "<question>"
---
Run the saved evidence-closed investigation workflow now for this question:

$@

Do not investigate manually and do not substitute direct Agent calls. Invoke the `workflow` tool in the foreground with:

- `name`: `evidence-closed-investigation`
- `scriptPath`: `/Users/anichols/.pi/agent/workflows/evidence-closed-investigation.js`
- `args`: `{ "question": "$@" }`
- `foreground`: `true`

The workflow will perform a light landscape-discovery pass and a high-reasoning readiness review before deciding its investigation scope; do not assume the current Pi working directory is the entire scope. If it returns `operator-clarification-required`, ask every returned `operatorQuestions` item together and wait for one reply before continuing. Do not answer the original question until those answers are available. If no question was supplied, ask the user for one instead of launching the workflow.
