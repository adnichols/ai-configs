---
description: Debug issues by investigating logs, database state, and git history
---

# Debug

You are tasked with helping debug issues during manual testing or implementation. This command allows you to investigate problems by examining logs, database state, and git history without editing files. Think of this as a way to bootstrap a debugging session without using the primary window's context.

## Initial Response

When invoked WITH a plan/ticket file:
```
I'll help debug issues with [file name]. Let me understand the current state.

What specific problem are you encountering?
- What were you trying to test/implement?
- What went wrong?
- Any error messages?

I'll investigate the logs, database, and git state to help figure out what's happening.
```

When invoked WITHOUT parameters:
```
I'll help debug your current issue.

Please describe what's going wrong:
- What are you working on?
- What specific problem occurred?
- When did it last work?

I can investigate logs, database state, and recent changes to help identify the issue.
```

## Environment Information

You have access to these key locations and tools:

**Logs** (automatically created by `make dev` and `make dev`):
- MCP logs: `~/.local/logs/mcp-claude-approvals-*.log`
- Combined WUI/Daemon logs: `~/.local/logs/wui-${BRANCH_NAME}/codelayer.log`
- First line shows: `[timestamp] starting [service] in [directory]`

**Database**:
- Location: `~/.local/data/app-{BRANCH_NAME}.db`
- SQLite database with sessions, events, approvals, etc.
- Can query directly with `sqlite3`

**Git State**:
- Check current branch, recent commits, uncommitted changes
- Similar to how `commit` and `describe_pr` commands work

**Service Status**:
- Check if daemon is running: `ps aux | grep hld`
- Check if WUI is running: `ps aux | grep wui`
- Socket exists: `~/.local/data/app.sock`

## Process Steps

### Step 1: Understand the Problem

After the user describes the issue:

1. **Read any provided context** (plan or ticket file):
   - Understand what they're implementing/testing
   - Note which phase or step they're on
   - Identify expected vs actual behavior

2. **Quick state check**:
   - Current git branch and recent commits
   - Any uncommitted changes
   - When the issue started occurring

### Step 2: Investigate the Issue

Investigate directly in the driving session. Run independent read-only checks in parallel when useful, but do not invoke Claude subagents.

1. **Recent logs**
   - Find the latest daemon log: `ls -t ~/.local/logs/daemon-*.log | head -1`
   - Find the latest WUI log: `ls -t ~/.local/logs/wui-*.log | head -1`
   - Search for errors, warnings, stack traces, and repeated failures around the problem timeframe.
   - Record timestamps and the working directory from each relevant log.

2. **Database state**
   - Inspect the relevant SQLite schema and recent rows directly.
   - Start with sessions and recent conversation events, then narrow queries based on the reported issue.
   - Look for stuck states, missing transitions, and anomalous values.

3. **Git and file state**
   - Check the current branch, `git status`, recent commits, and the current diff.
   - Verify expected files and permissions.
   - Correlate repository changes with the first observed failure.

### Step 3: Present Findings

Based on the investigation, present a focused debug report:

```markdown
## Debug Report

### What's Wrong
[Clear statement of the issue based on evidence]

### Evidence Found

**From Logs** (`~/.local/logs/`):
- [Error/warning with timestamp]
- [Pattern or repeated issue]

**From Database**:
```sql
-- Relevant query and result
[Finding from database]
```

**From Git/Files**:
- [Recent changes that might be related]
- [File state issues]

### Root Cause
[Most likely explanation based on evidence]

### Next Steps

1. **Try This First**:
   ```bash
   [Specific command or action]
   ```

2. **If That Doesn't Work**:
   - Restart services: `make dev` and `make dev`
   - Check browser console for WUI errors
   - Run with debug: `HUMANLAYER_DEBUG=true make dev`

### Can't Access?
Some issues might be outside my reach:
- Browser console errors (F12 in browser)
- MCP server internal state
- System-level issues

Would you like me to investigate something specific further?
```

## Important Notes

- **Focus on manual testing scenarios** - This is for debugging during implementation
- **Always require problem description** - Can't debug without knowing what's wrong
- **Read files completely** - No limit/offset when reading context
- **Think like `commit` or `describe_pr`** - Understand git state and changes
- **Guide back to user** - Some issues (browser console, MCP internals) are outside reach
- **No file editing** - Pure investigation only

## Quick Reference

**Find Latest Logs**:
```bash
ls -t ~/.local/logs/daemon-*.log | head -1
ls -t ~/.local/logs/wui-*.log | head -1
```

**Database Queries**:
```bash
sqlite3 ~/.local/data/app.db ".tables"
sqlite3 ~/.local/data/app.db ".schema sessions"
sqlite3 ~/.local/data/app.db "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;"
```

**Service Check**:
```bash
ps aux | grep hld     # Is daemon running?
ps aux | grep wui     # Is WUI running?
```

**Git State**:
```bash
git status
git log --oneline -10
git diff
```

Remember: This command helps you investigate without burning the primary window's context. Perfect for when you hit an issue during manual testing and need to dig into logs, database, or git state.
