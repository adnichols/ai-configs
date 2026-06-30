---
name: todoist
description: Manage Todoist tasks via the `td` CLI, with Aaron's workflow treating Todoist as the primary task system and Apple Reminders as a secondary intake source.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [todoist, tasks, productivity, td, aaron]
    related_skills: [aaron-good-morning, apple-reminders]
prerequisites:
  commands: [td]
---

# Todoist

Use the `td` CLI to read and manage Todoist tasks from the terminal.

For Aaron's workflow:
- **Todoist is the primary task system**.
- **Apple Reminders may also receive tasks**, but should be treated as a secondary intake source rather than the canonical project/task list.
- If both sources are involved, prefer Todoist as the authoritative source for current task state unless Aaron explicitly says otherwise.

## When to Use

Use this skill when:
- Aaron asks about tasks, todo lists, inbox items, or upcoming work
- a workflow needs the canonical task list
- `/gm` or another routine needs Todoist-backed task review
- tasks may need to be created, updated, completed, or triaged in Todoist

## Command Notes

Live CLI behavior verified on Aaron's machine:
- `td --version` should be `1.74.0` or newer. Older `@doist/todoist-cli@1.18.0` broke against the current Todoist API shape with `Cannot read properties of undefined (reading 'map')` after successful `GET /api/v1/tasks/filter` / `GET /api/v1/projects` calls. If that error appears, run `td update --check` then `td update`, or reinstall with `npm install -g @doist/todoist-cli@latest`.
- `td today --json` shows due-today and overdue tasks
- `td upcoming 3 --json` shows upcoming tasks for the next 3 days
- both commands return an object with a top-level `results` array, not a bare array
- for AI/LLM agents, the CLI recommends `td task add` instead of `td add` for structured creation
- use `--json` or `--ndjson` for parseable output whenever possible

## Quick Reference

### Review tasks

```bash
td today --json
td upcoming 3 --json
td inbox --json
td task list --json
```

Useful filters when needed:

```bash
td today --json --limit 50
td upcoming 7 --json --workspace Personal
td task list --json --project "Project Name"
```

### Create tasks

Prefer structured creation:

```bash
td task add "Buy milk"
td task add "Prep HUD rollout notes" --due tomorrow --priority p1
td task add "Follow up with Ana" --project Work --labels waiting,followup
```

### Update tasks

```bash
td task update id:123456789 --content "Updated task title"
td task update id:123456789 --due "2026-04-18"
td task update id:123456789 --priority p2
```

### Complete or reopen

```bash
td task complete id:123456789
td task uncomplete id:123456789
```

### Delete tasks

```bash
td task delete id:123456789
```

### Reminders

```bash
td reminder list id:123456789
td reminder add id:123456789 --type at --at "2026-04-18T09:00:00"
```

## Aaron-specific operating rule

When Aaron asks to "track" a task, default to this interpretation:
1. the task should exist in Todoist unless he asks for another system
2. Apple Reminders may still be relevant for capture or follow-up prompts
3. if a task appears in Reminders first, it can be migrated or mirrored into Todoist when appropriate

If a request is ambiguous between:
- an agent reminder/alert
- an Apple Reminder
- a Todoist task

then clarify only when the destination materially changes the outcome. Otherwise, for Aaron's general task tracking, default to Todoist.

## Parsing Guidance

When reading JSON from `td today --json` or `td upcoming 3 --json`:
- parse `results`
- dedupe by task `id` if combining multiple calls
- use due dates, deadlines, priority, project, labels, and URL when preparing summaries

## Mutation output quirk

- `td task add` may not support `--json` on Aaron's machine even though read commands do.
- For creation flows, check `td task add --help` first if you need machine-readable output.
- If `--json` is unavailable, capture the plain-text success output (`Created: ...`, `Due: ...`, `ID: ...`) and parse the task id from that.

## Guardrails

- Do not treat Apple Reminders as the canonical task source when Todoist is available.
- Avoid older guessed commands like `td next 3` or `td overdue` unless you have confirmed they work in the current CLI.
- Prefer structured `td task ...` subcommands over looser shortcuts when mutating tasks.
- Use JSON output for agent workflows whenever possible.
