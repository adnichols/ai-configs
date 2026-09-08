---
name: principle-modes-not-exceptions
description: "Apply when writing a branch, flag, skip, or hostname check because the code is running in test, lab, CI, staging, local, or a named deploy. Differences across environments are a designed operating mode with a closed capability set, parsed at the process edge, not scattered ifs."
---

ADN_RUNTIME_MARKER:principle-modes-not-exceptions:46756f89270d7e7dcb8c28c90fd0f957ade4ce2c

# Modes Not Exceptions

Lab, test, CI, and production may differ. Those differences are a designed Operating Mode. They are not `if (hostname)`, `if (NODE_ENV)`, `if (isLab)`, or a skip because Playwright is running.

**Why:** Environment checks rot. They copy into the next file. They leak lab-only identity into the product. A mode parsed once at the process edge is the same kind of structure **principle-model-the-domain** demands, applied to runtime rather than to leases or sessions.

**The pattern:**

- Name the modes the product actually runs (`production`, `lab`, `testing`, or whatever the spec calls them).
- Give each mode a closed capability set. Interior code asks the capability, never the environment.
- Parse the mode at the Worker, CLI, or UI edge. Invalid combinations refuse to start. See **principle-boundary-discipline**.
- Tests and local e2e *select* a mode. They do not disable another mode's flags so startup does not throw.
- Clients learn mode-dependent UI from an advertisement the process already computed. They do not sniff `location.origin` or a Worker name.

**Allowed, and not this principle:**

- Deploy config (wrangler name, account id, origin URL) that pins *this checkout*.
- Operator destination guards that refuse to seed or verify against production.
- Harness config that sets the mode for vitest or Playwright.

**The tells you skipped it:**

- A second boolean that must stay in sync with "are we in labs".
- A hardcoded origin or `workers.dev` suffix in product source.
- A test-only route compiled into every deploy that 404s unless an env var is set.
- A UI control that appears only on one hostname.
- An e2e script that overrides lab flags so `wrangler dev` does not crash.

Do not paper this with more `AGENTS.md`. If a repo needs a reminder, name this skill. Encode the ban as a lint or structure check when the same literals keep coming back. See **principle-encode-lessons-in-structure**.
