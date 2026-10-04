ADN_RUNTIME_MARKER:playbook-perf-issue:e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a

### Perf issue

**You own the measurement story. Plan, review, verify the numbers.** Tie every fix to a measurement, don't read source instead of measuring.

<!-- source-step:perf-issue:1 -->
1. Capture a baseline trace via the matching control skill. Vet the baseline, and each later number, with the **benchmark-checklist** skill.
<!-- source-step:perf-issue:2 -->
2. `how` to ground hypotheses. Don't claim a perf ceiling without running it first.
   Try the performance mantras in order, cheapest first. A mantra earns an attempt only when the trace shows the cost it removes.
   1. Don't do it. Stop work whose result nothing uses rather than cheapening it.
   2. Do it, but don't do it again.
   3. Do it less.
   4. Do it later.
   5. Do it when they're not looking.
   6. Do it concurrently.
   7. Do it cheaper.

   When an earlier mantra meets the target, stop.
<!-- source-step:perf-issue:3 -->
3. Plan the fix from the trace. If it crosses a function boundary, `architect` first. Delegate implementation to a subagent using your configured perf-issue model (default `gpt-5.6-sol-max`). Review the diff. Capture a post-fix trace.
   Apply the **sequence-verifiable-units** principle skill, verifying each attempt before trying the next.
<!-- source-step:perf-issue:4 -->
4. Parse and compare the artifacts (JSON to sqlite, diff). "Inconclusive" or wrong-surface is not a pass. Flag it.
<!-- source-step:perf-issue:5 -->
5. Cite the measurement in the PR.
<!-- source-step:perf-issue:6 -->
6. Run **Opening a PR** (`playbooks/opening-a-pr.md`).

For sustained improvement against a metric rather than a one-off fix, use the Hillclimb playbook (`playbooks/hillclimb.md`).

**Reply:** baseline number, post-fix number, delta, artifact path.
