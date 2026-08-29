ADN_RUNTIME_MARKER:playbook-runtime-forensics:46756f89270d7e7dcb8c28c90fd0f957ade4ce2c

### Runtime forensics

**You own the diagnosis. Instrument the live process, don't theorize from source.** For "why is X leaking / spinning / slow at runtime", heap snapshots, idle-but-busy processes, intermittent glitches. The deliverable is a cited diagnosis, not a fix.

<!-- source-step:runtime-forensics:1 -->
1. Capture the live signal on the matching surface via the control skill: a CPU profile for a spinning process, a heap snapshot for a leak, a CDP trace for a visual glitch. A real artifact, not a guess.
<!-- source-step:runtime-forensics:2 -->
2. Reduce the artifact to the smoking gun: the function on the hot path, the retainer chain from the leaked object to a GC root, the loop firing without input. Parse large artifacts in a subagent (the **guard-the-context-window** principle skill), keep the reduced finding in the main thread.
<!-- source-step:runtime-forensics:3 -->
3. Prove the mechanism before believing it. Inject instrumentation via CDP eval on the running process, or hotfix the live code without reloading, to confirm the hypothesis cheaply. A plausible-but-unconfirmed cause can be wrong while the real one sits one layer over.
<!-- source-step:runtime-forensics:4 -->
4. Map the finding back to source: file, symbol, the line that allocates or schedules.
<!-- source-step:runtime-forensics:5 -->
5. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

<!-- source-step:runtime-forensics:6 -->
6. No PR. End cleanly.

**Reply:** the signal captured, the reduced finding, how you proved the mechanism, the source location, artifact paths. No fix unless asked; hand back to Bug fix or Perf once the cause is known.
