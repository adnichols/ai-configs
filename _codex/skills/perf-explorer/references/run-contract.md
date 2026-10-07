# Run contract

## Delegation packet shared by every agent

Supply concrete values, not an instruction to rediscover the run:

- Role, run ID, owned output directory, orchestrator/return channel, and task.
- Checkout/SHA, deployed Worker versions and receipt path, lab origin, lab name,
  non-secret claim ID and generation. No claim or fixture file contents.
- Assigned fixture person/role, Organization/Space IDs, private credential
  accessor path, target corpus profile and sizes, record prefix and ownership.
- Feature map and verification paths; installed computer-use/CUA skill paths.
- Inventory URL for context only; agents return findings to its sole writer.
- Allowed lab mutations, prohibited global mutations, and current concurrency.
- Output shape below, no-fix boundary, stopping condition and blocker channel.
- The skill's recoverable-obstacle policy, permitted recovery actions, shared
  setup owner and requirement to continue independent work after reporting.

Agents may read relevant source/specs and collect runtime evidence. Allowed
writes are their own evidence and assigned disposable lab records. No product,
spec, dependency, configuration, deployment, or shared inventory edits. No
production testing. No other agents' credential-store changes. Do not launch
additional explorers or investigators without the orchestrator assigning them.

Read the installed skills rather than relying on command examples in a prompt.
Keep credentials out of screenshots and transcripts. Sign in before capturing
evidence; avoid capture of enrollment/token screens. Do not use the real
inventory Organization as the test target.

## Explorer assignments

### Walkthrough

Read every linked feature map entry, including sub-features, manual recipes,
prerequisites and gotchas. Build operation-level rows, then drive actual Web
actions through CUA. Verification scripts inform preconditions, expected results
and durable readback; executing a scripted browser scenario does not replace
the CUA action. CLI/API setup and readback are allowed and labeled separately.

Cover the applicable roles, shared/personal Spaces, empty/populated states,
desktop/mobile layouts, success/error/cancel paths, and reload persistence.
Inventory visible controls or routes missing from the map. Unsupported UI
surfaces are explicitly unavailable; never invent a UI for a CLI-only action.
Inspect screenshots in context as well as semantic state.

After every feature, save `coverage.md` and send new findings to the orchestrator.
Try bounded recovery within your lab assignment before marking a path blocked.
Preserve the original failure and workaround separately. Send shared setup
recovery to the orchestrator and continue independent features while it works.
Stop when every reachable operation and its applicable variants has a result,
and return the
unresolved coverage rows. Continue if the orchestrator supplies missing rows.

### Fuzzy

Use the map to learn scope and avoid destructive global controls, then pursue
uncovered behavior instead of repeating its recipes. Keep a sequence log with
starting state, exact actions and parameters so exploration is reproducible.
Use a logged seed if choosing actions programmatically; otherwise preserve the
actual sequence rather than claiming deterministic randomness.

Explore realistic combinations: rapid navigation then Back/Forward, repeated
Space/document switching, large trees and long documents, unusual search text,
empty results and clearing filters, opening/closing panels mid-load, cancelling
forms then reopening, repeated submit, two-window collaboration on assigned
records, permission transitions and recovery. Bias toward underexplored surfaces
and long or erroring operations. Avoid meaningless destructive input volume.

Keep `frontier.md` of combinations tried and next candidates. After the first
pass, make two deliberate passes across remaining plausible combinations.
Exhaustion means neither adds a new actionable behavior or unvisited reachable
surface. This is bounded exploratory saturation, not proof over every possible
input. Send findings promptly and preserve the original failure sequence.

## Lab and browser concurrency

Use one persistent CUA MCP/SDK connection per agent, its own session label on
every call, and a separate driver-owned browser process/profile. One-shot CLI
transports do not preserve browser refs, recordings or session ownership.
Discover the native window, bind exactly, snapshot, act using fresh refs or
grounded coordinates, and verify from a fresh snapshot after every action.
Never silently change browser input trust class or foreground the user's apps.

On the Linux authoring host, the shell omitted `DISPLAY` although an X11
session existed. Inspect the running Xorg socket owner with `ss -xlpn`, then
pass the proven display to `cua-driver doctor` and the owned driver process.
Do not hardcode the observed `:1` for future runs. A persistent
`cua-driver mcp --socket <observed-service-socket>` connection, isolated Chrome
profile launched through CUA, and native accessibility `click` plus
`get_window_state` worked without granting personal-profile browser access.
Typed browser binding may need explicit preparation. Native CUA remains a
valid fallback. Chrome `verify_state` returned `unknown/untrusted_source` on
this host; fresh tree and screenshot inspection supplied the actual proof.

Separate profiles do not isolate the server or shared desktop input. Give
explorers disjoint record prefixes and fixture people. Use the imported large
Spaces for realistic read paths and owned test records for mutations; do not
duplicate the corpus into an empty Space and call its timings equivalent.
Coordinate permissions, deletion, Organization settings, shared clipboard,
downloads and other globally shared state through the orchestrator. A test
that can invalidate the other explorer's session needs an exclusive interval.

Never run verification scenarios concurrently against the same harness state
or share fixture-pool leases. Only the orchestrator owns lab lifecycle and
verification setup. Investigators use distinct identities/private state and
the same lab, never a newly seeded substitute. Serialize destructive checks
and quiet timing reproductions while allowing other read-only investigation.
Log concurrent activity and compare isolated repeats before blaming application
architecture for contention introduced by the testers.

## Measuring the one-second threshold

The primary measure is elapsed time from dispatched user input until its
declared useful UI completion. Choose the completion predicate before acting:
document content usable, results stable, save acknowledged, modal operation
finished, or downloaded artifact ready. For asynchronous work, report both
acknowledgment latency and full task completion; a quick toast cannot conceal
a slow job. Validate persisted effects separately by reload or CLI/API readback.

Measure on the host/browser clock with bounded observation and no model turn
inside the timed interval. Use a supported CUA action plus continuous CUA
observation in one persistent client, preserving timestamps, polling intervals,
action dispatch uncertainty and completion evidence. An authorized scoped
recording with visible dispatch/completion frames can establish intervals;
screen recording is optional and follows CUA's consent/capture rules. Do not
record the entire desktop merely to time a tab.

Tool wall time, timestamp gaps between model messages, HTTP latency, and a pair
of screenshots taken after thinking are not exact user-perceived latency.
With polling, preserve lower/upper bounds from the last observed incomplete
and first complete state, including dispatch uncertainty. Classify as confirmed
`>1000 ms` only when the lower bound exceeds 1000 ms. An upper bound below or
equal to 1000 ms establishes a fast sample. A crossing interval is inconclusive;
repeat with finer supported observation or leave a suspected slow finding.
Do not subtract a guessed tool-overhead constant. Network traces and server
timings are diagnostic evidence and never silently replace the UI measurement.

A conservative native CUA implementation uses `time.monotonic_ns()` around
each call on one persistent transport. Record action-call start/end and each
snapshot-call start/end. For a state that changes once from pending to complete,
the lower bound is the last explicitly pending snapshot's **start** minus the
action-call **end**, clamped to zero. The upper bound is the first complete
snapshot's **end** minus the action-call **start**. Preserve the raw brackets.
Require a known pending indicator and a unique completion predicate visible
in fresh snapshots; missing text in a truncated tree is not proof of pending.
Do not issue other actions inside the interval. Transient/reverting states,
ambiguous predicates or missing observations yield inconclusive timing.
Use three states: explicitly pending, explicitly complete, and unknown.
Unknown never advances the lower bound. Preserve refused actions and transport
errors as tool failures rather than pretending input was delivered. Enforce
an elapsed deadline, retain timeout observations, and stop when it expires.
Tree and screenshot captures are not atomic. Inspect the first-complete image
and last-pending evidence; record disagreements and widen or invalidate bounds
when the evidence undermines the chosen visible-completion predicate.

Preserve the first slow/error occurrence immediately. Repeat safely five times
where feasible, keeping all individual values, failures, min/max and median.
Separate cold/warm state, first-load effects, cache behavior, concurrency and
dataset size. Any valid over-threshold sample remains a finding even if its
median is fast. One-shot or destructive operations can remain single-sample;
state why they were not repeated. A timeout records its actual observation
bound and unresolved outcome, not a fabricated completion time.

If the current CUA backend cannot establish adequate timing bounds, functional
exploration can continue. Record `measurement-blocked` and suspected slow
operations; do not certify one-second coverage. Test the chosen timing method
on a known-delay scratch control before trusting threshold classifications.

## Investigation assignment

For each `PERF-NNN`, launch a fresh Paseo agent with the shared packet, original
steps/evidence, expected behavior and exact timing boundary. It must:

1. Reproduce on the same lab/generation/build and equivalent data/role. Request
   an exclusive interval for clean timing or global state changes.
2. Preserve pass/fail and timing evidence, including unsuccessful repetitions.
3. Inspect the relevant runtime traces, requests and source. Identify measured
   blocking work and its owner. Distinguish demonstrated causes from hypotheses
   and tool/infrastructure failures. Source reading alone is not causal proof.
4. Explain what the customer cannot do or must wait for. Propose a coherent fix
   with affected components, behavior/contracts preserved, risks, expected
   benefit and how another agent would verify it. Do not invent speedup numbers.
5. Apply zero-tech-debt and ADN principles to the proposal. Look for duplicated
   work, broad reads, repeated subscriptions, serialized requests, redundant
   materialization and unclear responsibility only where evidence supports them.
   Name related findings and supporting evidence, without merging them itself.
6. Attempt permitted recovery from reproduction obstacles; escalate shared lab
   setup to the orchestrator and continue independent source/evidence analysis.
   Include attempted remedies and their results for any remaining blocker.
7. Return `reproduced`, `intermittent`, `not-reproduced`, or `blocked`, confidence,
   findings file and evidence paths. Stop without implementing anything.

## Inventory and coverage shape

The document begins with run identity, status, current progress and blockers,
then a priority table, architectural groups, detailed individual findings,
coverage and retained reproduction resources. Keep it usable throughout the run.
Include: "This live inventory body is maintained exclusively by the run's
orchestrator. Please add contributions as comments while the run is active."
This ownership protocol is required because current text body replacement
does not offer compare-and-swap; it is not a claim of server-enforced locking.

For each issue capture:

- Stable ID, title, discovery timestamp/agent, priority and investigation status.
- Customer impact and expected versus actual behavior.
- Feature/route/control, exact lab/build/generation, role/identity, Organization,
  Space/document identifiers and dataset shape. Use returned canonical URLs.
- Setup, exact numbered actions and inputs, completion predicate, durable
  readback, frequency, cold/warm state, and concurrency.
- Timing method, raw samples or bounds in ms, count/range/median when valid,
  failure/error codes and whether delay is confirmed, suspected or blocked.
- Sanitized screenshots/traces/logs and evidence locations another agent can
  access. Attach useful sanitized artifacts through Ava when appropriate;
  local paths alone are not remotely available evidence.
- Paseo investigator ID, reproduction result, causal evidence, proposed change,
  affected owners, confidence, risks and suggested future verification.
- Related issue/group IDs, duplicate occurrences, and remaining questions.

Each architecture group additionally lists linked symptoms, the common cause
and evidence chain, disproving evidence or uncertainty, intended end state,
why it outranks comparable isolated fixes, and coverage gained by addressing it.
Do not delete child findings or count the group as an extra failed operation.

Each coverage row names a feature, operation, role/state, corpus, evidence and
result: `passed`, `failed`, `slow`, `suspected-slow`, `blocked`, `unavailable`,
or `not-run`. Keep functionality and latency outcomes separate where needed.
Slow success is still a performance finding. Unsupported provider prerequisites
and timing limitations never count as passes. Distinguish observations, distinct
issues and architectural groups when reporting totals.

## Exhaustion and interruption

Finish when all reachable mapped operations and manual variants are accounted
for, new UI controls discovered by either explorer have owners/results, the
fuzzy frontier meets its saturation condition, every distinct finding has an
investigation disposition, and the final inventory is read back successfully.
Give explicit exceptions for provider credentials, role restrictions, exhausted
one-shot fixtures, unsupported surfaces and unmeasurable timing. Say coverage
is partial when these prevent the claimed full run. Reporting a blocker alone
is not exhaustion: attempt or rule out plausible permitted remedies with
evidence and finish independent work before ending for that blocker.

Keep the orchestrator active through delegated work. Use notifications and
bounded waits; no new cron, heartbeat or scheduler is required. If interrupted,
checkpoint agent IDs, pending investigations, last Ava revision, private resource
owners and the exact next action. Do not release the lab on timeout, compaction,
or investigation completion. Preserve the observed dataset for later fixes.
