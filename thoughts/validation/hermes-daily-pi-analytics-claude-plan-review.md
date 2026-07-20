# Bounded readiness review — Hermes Daily Pi Analytics Morning Review

## Completed checks

- Read the full plan HTML (`thoughts/plans/hermes-daily-pi-analytics-morning-review.html`, 87 lines) and `AGENTS.md`.
- Confirmed `scripts/pi_session_analytics.py` and the v1 schema doc do **not** exist yet — matches the plan's own "Current implementation reality" claim and correctly gates all downstream work on P1.
- Confirmed real Pi JSONL sessions (`~/.pi/agent/sessions/*.jsonl`, this host) contain the structured fields the analyzer needs: `message.provider`, `message.model`, `message.stopReason`, `message.api` — corroborates P1's premise without inspecting prompt/transcript content.
- Confirmed cron job `039f96dcecfc` ("Daily Good Morning Doct Plan + Todoist Review", `_hermes/default/cron/jobs.json:43-51`) is real and matches `_hermes/default/scripts/gm_deterministic_cron.py:22` (`GM_JOB_ID`). P2's verify assertion about this job is grounded.
- Confirmed `gm_deterministic_cron.py` parses `manifest.get("phase_statuses", [])` with `name`/`status`/`error` — corroborates P3's "phase" insertion architecture is plausible, though I could not read the actual orchestrator source (this dever checkout's `~/Documents/Obsidian/adn_vault/_agents/scripts/gm/` contains only `__pycache__`, no `.py` files — mbp-only, consistent with the plan's host-ownership claim but unverifiable from here).
- Independently exercised `scripts/hermes_config_sync.py` logic (`install`/`verify`/`install_all`) and the `ccore` and `doct-agent` skill docs via two Explore subagents plus direct reads.
- Found and read a **pre-existing Codex readiness review** already on disk: `thoughts/validation/hermes-daily-pi-analytics-codex-plan-review.md` (verdict `PLAN_NEEDS_REVISION`, 3 `READINESS_BLOCKER` + 1 `PRODUCT_QUESTION` + 1 `OPTIONAL_CLARITY`). My independent investigation (below) reproduces/confirms three of its blockers from first principles and adds two more.

## Findings

**F1 — READINESS_BLOCKER (item 3, singleton/rollout).** The P2 install command is invalid as written, and the tool has no way to achieve "collector-only on dever" at all.
`hermes_config_sync.py:602-622` calls `verify(bundle)` before every install, and `verify()` (`:575-580`) does `if not manifest_path.exists(): raise SystemExit("Missing manifest.json")`. Only `_hermes/default/manifest.json` exists — nothing under `_hermes/default/profiles/pi-analytics/`. The plan's literal command (plan `:62-64`) exits immediately. Deeper problem: `install_all()` (`:525,548-551`) only knows how to install profiles as a nested loop over `bundle/profiles/*` while installing the *whole* default bundle into one `hermes_home`; there's no flag to install a single profile in isolation. Pointing `--bundle` at `_hermes/default` (which has a manifest) to fix the crash would also install the main default files/scripts/cron onto dever — exactly what AC-9 forbids. Corroborated independently by `thoughts/validation/hermes-daily-pi-analytics-codex-plan-review.md:3`.

**F2 — READINESS_BLOCKER (item 3, rollout).** No supervised process is defined to execute a profile's cron. `_hermes/default/skills/software-development/hermes-s6-container-supervision/SKILL.md:47-53,84` and `_hermes/default/skills/autonomous-ai-agents/hermes-agent/SKILL.md:503-517` describe each profile as requiring its own supervised gateway process (`hermes -p <name> gateway run`, an s6 service slot). The plan (P2 Work/Verify) never mentions starting or supervising a second Hermes process for `~/.hermes/profiles/pi-analytics` — only the file-sync tool is invoked. Without that, the 05:00 job has nothing to fire it. Same evidence file as F1, line 3.

**F3 — READINESS_BLOCKER (item 2, retention).** No supported C-Core delete path exists for the report shape described. D5 (`:30`), AC-8 (`:41`), and P2 Work (`:60`) all rely on "the normal supported C-Core delete command" against a "document." `ccore-cli-operations/SKILL.md:261-267` (also present at `_hermes/default/profiles/nerd/skills/software-development/ccore-cli-operations/SKILL.md:261`) states `ccore doc` exposes only `list/new/show` — no delete/update for plain documents; delete only exists for typed managed objects (`ccore object delete <OBJECT_ID>`). The plan never specifies publishing as a typed object, so AC-8's cleanup requirement has no implementable path as scoped. Corroborated by Codex review, line 5.

**F4 — READINESS_BLOCKER (item 4, authenticated actions).** P4's authorization boundary is unspecified where it matters most. All three existing comment listeners (`_hermes/default/scripts/gm_plan_comment_listener.py`, `doct_document_comment_listener.py`, `hermes_pr_codex_plan_comment_listener.py`) dispatch a general-purpose, broadly-capable Hermes worker (`terminal,file,skills,delegation`) and filter only on `queueState == "pending"` — none validate comment author or card identity today. No script or skill doc in the repo defines an "immutable Doct user ID" field for comment authors (`doct-agent-commands.md` documents claim payloads as carrying generic "reviewer context" with no named field). AC-6/AC-7 require author-restricted, card-scoped, negative-authority behavior, but the plan doesn't specify the dispatcher change or the concrete author-identity field that would make this true — it only specifies what the new worker must not be able to do. Corroborated by Codex review, line 7.

**F5 — PRODUCT_QUESTION (item 2/4, cross-cutting).** "Materially changed signal" and card/snapshot identity are undefined. D4 (`:29`) says `dismiss` hides "that exact evidence snapshot" while "a materially changed signal may produce a new card later," but no section defines the identity key (host+category+date? host+category+count-bucket?) that distinguishes "same snapshot" from "changed." This key is load-bearing for the SQLite idempotency key (P4) and for correctly carrying `accept`/`investigate` visibility across days when counts naturally shift. Same open question independently raised in Codex review, line 9.

**F6 — Minor/spec-clarity.** The plan repeatedly names a ccore "Private" space (D1 `:26`, reality `:35`, P2 `:60`) that does not exist under that name — the real ccore concept is a "Personal" space (`ccore-skill-guide.md` `--display-name` doc; SKILL.md's worked example space is literally named `Personal`). Left uncorrected, an implementer could search for/attempt to create a nonexistent "Private" space instead of reusing the existing personal space both hosts already have.

**F7 — Minor/verification-coherence.** "Private-space sync is healthy" (Verification strategy `:76`, P2 `:60`) isn't an executable pass/fail check. `ccore space sync-status <space> --json` returns `lag`/`pending_local_changes`/`last_error` fields requiring interpretation, not a boolean "healthy" — the ccore skill doc itself warns against reading this output as self-explanatory. (The 05:00 run + 30-minute timeout = 05:30 deadline in P2/`recommendation-rules` *is* internally consistent — no issue there.)

## Remaining checks

None required to reach a verdict. I did not have direct read access to mbp's live Good Morning orchestrator source (dever's local checkout has only compiled `__pycache__`, no `.py`), so P3's exact phase-insertion point and dry-run fixture flag are corroborated only indirectly via the cron wrapper's `phase_statuses` parsing, not read directly — this is a host-access limitation of this review, not a claim I can falsify, and does not change the verdict given F1–F5 are already sufficient blockers.

## Assessment

Items 1 and 5 from the requested risk areas are in reasonably good shape: the privacy/classification boundary is well-scoped against real session-file structure, and the phase/AC/BDD/verification-command scaffolding is largely internally consistent (job ID, timing math, expected files). But items 2, 3, and 4 each contain at least one concrete, reproducible blocker — a crashing install command with no working substitute, an unaddressed process-supervision requirement, a retention contract with no supported delete path, and an authorization gap in the comment-action pipeline — plus one genuine unresolved product question about snapshot identity. Three of these are independently confirmed by a second reviewer (Codex) already on disk in this repo, not just by this pass.

VERDICT: PLAN_NEEDS_REVISION

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-35e6058cc7e7-984173-bcf39a0529e2
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/hermes-daily-pi-analytics-claude-plan-review.md.transcript.txt
claude_session_id=c30af06d-cbf3-453b-99ce-2976c05e41fc
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/c30af06d-cbf3-453b-99ce-2976c05e41fc.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
