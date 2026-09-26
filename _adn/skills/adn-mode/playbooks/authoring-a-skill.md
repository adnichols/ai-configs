ADN_RUNTIME_MARKER:playbook-authoring-a-skill:ecc249f1e306fc64ddf83c7bed16cacf7c2239db

### Authoring or modifying a skill

**You own the skill's voice.**

<!-- source-step:authoring-a-skill:1 -->
1. Use the **create-skill** skill (Cursor's built-in for authoring SKILL.md files).
<!-- source-step:authoring-a-skill:2 -->
2. Validate the skill: frontmatter has `name` and `description`, referenced files exist, cross-skill links resolve.
<!-- source-step:authoring-a-skill:3 -->
3. Test cases if structural. Skip if subjective.
<!-- source-step:authoring-a-skill:4 -->
4. Run **Opening a PR** (`playbooks/opening-a-pr.md`).

When in doubt, delete. Keep only prose that changes a decision. Tell it to do the thing and skip the reason. Explain only when the rule is confusing without one. Match tone to scope. Point at structural sources (types, READMEs, config) per the **encode-lessons-in-structure** principle skill. Delegate to other skills by path. Don't restate. A workflow you keep hitting but isn't captured → propose a new skill.

**Reply:** summary of the skill, key design decisions, validation notes.
