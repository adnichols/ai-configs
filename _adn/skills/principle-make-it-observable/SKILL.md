---
name: principle-make-it-observable
description: "Apply when designing, changing or reviewing work nobody watches happen: a background job, a migration, a cleanup, an API whose effect is internal, a performance change. Build a read that shows it works, and make that read after it ships."
---

ADN_RUNTIME_MARKER:principle-make-it-observable:e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a

# Make It Observable, and Observe It

Work nobody else can read is unverified. Build a read that shows hidden work is on, moving and having its effect, and make that read after it ships.

**Why:** Background work fails quietly. A stalled job, a job that gave up and a finished job look the same from outside, so a person finds the damage days later. A small test passes and production fails, because nobody knew what one unit costs.

**Pattern:** There is no standard set of counters or tests. Answer these questions and build the least that answers them. A change with nothing hidden says so and why.

- **What would an agent who was not here read to know it works?** Name the conditions the read must tell apart, starting with a failure that looks like completion. Enabled is not running, and activity is not progress. Watch the outcome, not only the job. Missing or stale evidence must not read as healthy, and a log counts only if the reader can still retrieve it. The read must work where the change is verified, with the verifying agent's access. Internal detail stays internal unless you choose to show customers.
- **How does its cost grow with size?** Measure work per unit at a few small sizes, counting only the work under test. When a model of the work explains the numbers, extrapolate and say where it stops holding. Growing per-unit cost is the finding. Keep the measuring tool. Where useful, turn repeatable measurements into a budget test with a justified threshold.
- **What breaks it, and how would you know?** Pick the conditions the change assumes away, such as its largest input, a quota, concurrent writers or a restart. Say what fails and which reading shows it.
- **What should the next agent watch after deploy?** Write down what must be in place first, what the read should show by when, which reading means failure, and who makes the read. Observing a change never authorizes deploying it. A production result comes from that read, never from a test receipt. The work stays open until the read meets the stated expectation.

Review makes the read with the next agent's access. "Added logging" is not a read.

You skipped this when repeated reads cannot tell a stall from progress or a failure from completion, when the status read refuses the agent verifying it, or when the scale plan is "load a bigger lab and see".

Distinct from **principle-prove-it-works**, which checks an output at completion. This makes the system produce the evidence and carries the check past deploy. Distinct from **principle-explain-the-number**, which interprets a measurement. This decides which measurement must exist.
