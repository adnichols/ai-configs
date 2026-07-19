# Rolling ecosystem intelligence for Good Morning — planning notes (2026-07-18)

## Design that fits the deterministic GM runner

Use a **deterministic, evidence-first** pipeline rather than a free-form daily research-agent prompt:

1. A human-reviewed ecosystem manifest declares project/tool IDs, aliases, upstream repositories/feeds, lifecycle (`active`, `watch`, `inactive-broad`), relevance notes, source preferences, and local evidence patterns.
2. A nightly host inventory observes installed CLIs, Hermes config/cron/skill/plugin references, declared source roots, and repository metadata. A clone alone is not active-use evidence.
3. A narrow SSH JSON probe may contribute remote-host inventory; it must not read secrets, publish GM/Doct artifacts, or create tasks.
4. Collect only bounded, declared external sources: GitHub official API, project RSS/Atom/release feeds, official version metadata, and one configured licensed search provider. X and Reddit are optional official-API adapters—not browser/cookie scraping fallbacks.
5. Normalize/fingerprint events (`source + canonical identifier/URL + project + release/version/commit`), retain first/last seen state, classify rolling windows, score relevance, and only then allow a model to expand selected adoption candidates.
6. Render a stable `ecosystem-intelligence` section with: New since yesterday, This week, Uptake required/recommended, Discovery/patterns, Usage/manifest drift, and Collector health.

## Recommendation threshold

An `action_required` / mandatory uptake item needs:

- primary official source evidence, and
- a direct local relevance link (observed or declared active configuration/use).

Social/community/search-only signals can be `watch` items but not mandatory uptake. Routine commits should be compact or suppressed; materially changed events can reappear, ordinary duplicates cannot.

## Lifecycle rule

A tool no longer observed should move only by a reviewable suggestion to `inactive-broad`, not disappear from future discovery. Manual manifest state always overrides inference.

## Credentials / ToS posture

- GitHub `gh`/API is an appropriate initial primary collector when authenticated.
- For broader web discovery, configure exactly one licensed search provider deliberately; do not rely on accidental provider fallback.
- X official client setup needs all required app/user credentials, not only an API key.
- Reddit collection should use an official Data API client with declared scopes, user agent, rate budget, and bounded subreddits/queries.
- Do not use cookie/session scraping, protected-page automation, CAPTCHA bypass, or browser automation as a social-source fallback.

## Scheduling

Prefer a quiet nightly pre-collector that writes checkpoints/state before the morning publisher consumes them. The morning job should use fresh pre-collected evidence or a bounded fallback collection; avoid adding an unbounded LLM research step to the 06:00 deterministic GM run.

## Audit finding to verify before adopting a remote host

Treat remote GM jobs as independent only after checking their workdir/script paths and delivery entitlement on that host. A valid SSH connection or a copied cron definition is not evidence that the remote publisher works. The canonical host should remain the sole publisher unless the remote workflow is deliberately repaired and verified.
