ADN_RUNTIME_MARKER:playbook-runtime-forensics:ecc249f1e306fc64ddf83c7bed16cacf7c2239db

### Runtime forensics

**You own the diagnosis. Instrument the live process, don't theorize from source.** The deliverable is a cited diagnosis, not a fix.

<!-- source-step:runtime-forensics:1 -->
1. Capture the live signal on the matching surface via the control skill: a CPU profile for a spinning process, a heap snapshot for a leak, a CDP trace for a visual glitch. A real artifact, not a guess.
<!-- source-step:runtime-forensics:2 -->
2. Reduce the artifact to the smoking gun: the function on the hot path, the retainer chain from the leaked object to a GC root, the loop firing without input. Parse large artifacts in a subagent (the **guard-the-context-window** principle skill), keep the reduced finding in the main thread.
<!-- source-step:runtime-forensics:3 -->
3. Prove the mechanism before believing it. Inject instrumentation via CDP eval on the running process, or hotfix the live code without reloading, to confirm the hypothesis cheaply.
<!-- source-step:runtime-forensics:4 -->
4. Map the finding back to source: file, symbol, the line that allocates or schedules.

<!-- source-step:runtime-forensics:5 -->
5. No PR. End cleanly.

**Reply:** the signal captured, the reduced finding, how you proved the mechanism, the source location, artifact paths. No fix unless asked. Hand back to Bug fix or Perf once the cause is known.
