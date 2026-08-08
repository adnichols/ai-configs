---
name: cmd-graduate
description: Graduate completed work from thoughts/ directory to permanent spec/ documentation. Use when a feature is complete and ready for long-term documentation.
---

# Graduate Completed Work

Move completed features from the working `thoughts/` directory to permanent `spec/` documentation.

This skill is a **generic baseline**. It does not own Heddle develop-PR changelog
fragments, pre-PR disposition gates, or plan archive/CCore packages.

- **Heddle / repos with a local permanent-docs skill:** for pre-PR permanent-doc
  disposition and capture, prefer `.agents/skills/heddle-permanent-docs/SKILL.md`
  (or the local `*-permanent-docs` skill). On Heddle, use
  `changelog/unreleased/` fragments—do not append root `CHANGELOG.md` as the
  develop-PR contract. Do not delete plan sources or create CCore archive
  packages as a PR gate; follow the repo archive runbook post-merge.
- **Other repos:** continue with the generic process below when no local
  permanent-docs skill exists.

## Usage

```
/skill:cmd-graduate <plan-slug-or-path>
```

## Output Locations

Graduated features move to:
- `spec/architecture/[feature].md` - Feature architecture documents
- `spec/architecture/README.md` - Architecture index (updated)
- `spec/adr-log.md` - Architectural decision records (if applicable)
- `CHANGELOG.md` - Implementation summaries appended

## Process

### 1) Resolve Source

If argument is:
- A path: use it directly
- A slug: resolve using repo-local active plan guidance; do not infer a markdown path

### 2) Read and Summarize

Read the completed plan and extract:
- Feature name and purpose
- Key architectural decisions
- Implementation approach
- Important technical details worth preserving

### 3) Create Architecture Document

Write to `spec/architecture/[feature-slug].md`:

```markdown
---
date: [YYYY-MM-DD]
author: [author from plan]
original_plan: <plan_path>
status: graduated
---

# [Feature Name]

## Purpose
[What this feature does]

## Architecture
[Key components and design]

## Decisions
[Important technical decisions made]

## Implementation Notes
[Technical details for future reference]

## Related
- Original plan: `<plan_path>`
- [Other related docs]
```

### 4) Update Architecture Index

Update `spec/architecture/README.md` to include the new feature.

### 5) Update Changelog

Append to `CHANGELOG.md`:

```markdown
## [YYYY-MM-DD] - [Feature Name]

- Graduated from: `<plan_path>`
- Summary: [Brief description]
- Architecture: `spec/architecture/[feature-slug].md`
```

### 6) Report

- Architecture document location
- Index update status
- Changelog entry added
