ADN_RUNTIME_MARKER:playbook-trace-forensics:46756f89270d7e7dcb8c28c90fd0f957ade4ce2c

### Trace forensics

**You own the diagnosis from the artifact. Load it, shape it, narrow to the cause, attribute to source.** For a dropped `.cpuprofile`, `Trace-*.json.gz`, `Spindump.txt`, or `.heapsnapshot` paired with "why is this slow / unresponsive / leaking / crashing".

Distinct from **Runtime forensics**, which instruments the live process. Here the capture already exists; the artifact is a fixed dataset, read it, don't re-run it. Keep tooling generic so the playbook stays portable: a DevTools or trace parser for cpuprofile and `.json.gz`, a text editor for a spindump, your heap tooling for a heapsnapshot.

<!-- source-step:trace-forensics:1 -->
1. Identify the format and load it with the right tool. Parse large artifacts in a subagent (the **principle-guard-the-context-window** skill) and keep the reduced finding in the main thread.
<!-- source-step:trace-forensics:2 -->
2. Transform the raw artifact into a form you can query. Dump the trace or heap snapshot into sqlite, one row per sample, frame, or node. Reach the queryable shape before you read.
<!-- source-step:trace-forensics:3 -->
3. Narrow to the cause. Query for the frames that hold the most time and walk the call tree to the hot path. For a leak, follow the retainer chain from the leaked object to a GC root. For a spindump, find the thread stuck on-CPU or blocked and its wait reason.
<!-- source-step:trace-forensics:4 -->
4. Attribute to source. Map the hot frame to file, symbol, and line via the artifact's own symbols. A frame with no source mapping is not yet a diagnosis; resolve the symbols, or say plainly the artifact does not carry them.
<!-- source-step:trace-forensics:5 -->
5. Confirm against a paired capture when you have one. Diff a before and after artifact so the attribution is the real regression, not background noise. Without one, mark the finding as the strongest hypothesis the artifact supports, not a confirmed cause.
<!-- source-step:trace-forensics:6 -->
6. Hand back a cited diagnosis, no fix unless asked. Route to Bug fix or Perf issue once the cause is known. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

<!-- source-step:trace-forensics:7 -->
7. No PR. End cleanly.

**Reply:** the artifact and format, the reduced finding, the source location, the artifact paths, and whether a paired capture confirmed it.
