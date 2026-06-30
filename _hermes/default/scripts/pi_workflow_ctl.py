#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any



def _hermes_home() -> Path:
    env_home = os.environ.get('HERMES_HOME')
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / '.hermes'


STATE_DIR = _hermes_home() / 'tmp'
STATE_DIR.mkdir(parents=True, exist_ok=True)
LTUI = Path.home() / 'code' / 'ai-configs' / 'tools' / 'ltui' / 'bin' / 'ltui'

VALID_STAGES = {
    'plan',
    'review',
    'integrate',
    'commit-plan',
    'pm-plan',
    'execute',
    'validate',
    'pm-implementation',
    'create-pr',
    'post-pr-followup',
}

STAGE_TO_COMMAND = {
    'review': '/review:change {plan}',
    'integrate': '/review:change-integrate {plan}',
    'pm-plan': '/dev:pm-review stage=plan',
    'execute': '/dev:run',
    'validate': '/dev:validate {plan}',
    'pm-implementation': '/dev:pm-review stage=implementation',
    'post-pr-followup': (
        'The PR is open. Complete the post-PR follow-up loop now: wait for GitHub jobs/checks and PR feedback at least once, '
        'review what comes back, address the feedback/issues, and confirm the PR is mergeable. '
        'If the PR has conflicts or is behind develop, rebase onto develop, resolve conflicts, push again, then re-check jobs/feedback and mergeability. '
        'Do not stop at "PR opened".'
    ),
}

NEXT_STAGE = {
    'plan': {'review', 'commit-plan'},
    'review': {'integrate'},
    'integrate': {'commit-plan'},
    'commit-plan': {'pm-plan'},
    'pm-plan': {'execute', 'review'},
    'execute': {'validate', 'review'},
    'validate': {'pm-implementation', 'execute'},
    'pm-implementation': {'review', 'execute', 'validate', 'create-pr'},
    'create-pr': {'post-pr-followup'},
    'post-pr-followup': {'execute', 'validate', 'pm-implementation', 'create-pr'},
}


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def tmux_capture(target: str, lines: int = 120) -> str:
    result = run(['tmux', 'capture-pane', '-p', '-S', f'-{lines}', '-t', target])
    return result.stdout


def tmux_send(target: str, text: str) -> None:
    run(['tmux', 'load-buffer', '-b', 'pi-workflow-ctl', '-'], check=True)


def tmux_send_text(target: str, text: str) -> None:
    proc = subprocess.run(['tmux', 'load-buffer', '-b', 'pi-workflow-ctl', '-'], input=text, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or 'failed to load tmux buffer')
    run(['tmux', 'paste-buffer', '-b', 'pi-workflow-ctl', '-t', target])
    run(['tmux', 'send-keys', '-t', target, 'C-m'])
    subprocess.run(['tmux', 'delete-buffer', '-b', 'pi-workflow-ctl'], check=False, capture_output=True, text=True)


def git_status(repo: str) -> str:
    result = run(['zsh', '-l', '-c', f'cd {shlex.quote(repo)} && git status --short --branch'])
    return result.stdout.strip()


def git_commit_plan(repo: str, plan: str, issue: str | None) -> str:
    title = f'plan: approve execution plan for {issue}' if issue else 'plan: approve execution plan'
    body = f'''{title}\n\nWhy now:\n- The reviewed plan must be committed before implementation starts.\n\nDecision:\n- Commit {plan} as the approved execution plan for this branch.\n\nAlternatives considered:\n- Continue with an uncommitted plan, which weakens resumability and stage control.\n\nRisk / rollback:\n- Risk is limited to the planning artifact. Revert this commit if the plan changes materially.\n\nRefs:\n- {issue or plan}\n- {plan}\n'''
    cmd = f'cd {shlex.quote(repo)} && git add {shlex.quote(plan)} && git commit -F -'
    proc = subprocess.run(['zsh', '-l', '-c', cmd], input=body, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or 'git commit failed')
    return proc.stdout.strip()


def git_branch(repo: str) -> str:
    result = run(['zsh', '-l', '-c', f'cd {shlex.quote(repo)} && git branch --show-current'])
    return result.stdout.strip()


def git_has_upstream(repo: str) -> bool:
    proc = subprocess.run(
        ['zsh', '-l', '-c', f'cd {shlex.quote(repo)} && git rev-parse --abbrev-ref --symbolic-full-name @{{u}} >/dev/null 2>&1'],
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0


def ensure_clean_tree_for_pr(repo: str) -> None:
    status = git_status(repo)
    dirty = [line for line in status.splitlines() if line and not line.startswith('## ')]
    if dirty:
        raise SystemExit(f'refusing create-pr with dirty tree:\n{status}')


def gh_pr_view_for_branch(repo: str, branch: str) -> dict[str, Any] | None:
    proc = subprocess.run(
        ['zsh', '-l', '-c', f'cd {shlex.quote(repo)} && gh pr list --head {shlex.quote(branch)} --json number,title,state,url,isDraft,headRefName,baseRefName'],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or 'gh pr list failed')
    data = json.loads(proc.stdout or '[]')
    return data[0] if data else None


def gh_create_pr(repo: str, branch: str, base: str, title: str, body: str) -> dict[str, Any]:
    existing = gh_pr_view_for_branch(repo, branch)
    if existing:
        return {'created': False, 'pr': existing}
    proc = subprocess.run(
        ['zsh', '-l', '-c', f'cd {shlex.quote(repo)} && gh pr create --base {shlex.quote(base)} --head {shlex.quote(branch)} --title {shlex.quote(title)} --body-file -'],
        input=body,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or 'gh pr create failed')
    created = gh_pr_view_for_branch(repo, branch)
    return {'created': True, 'url': proc.stdout.strip(), 'pr': created}


def sync_issue_to_in_review(issue: str | None) -> dict[str, Any]:
    if not issue:
        return {'attempted': False, 'reason': 'no issue detected from plan path'}
    if not LTUI.exists():
        return {'attempted': False, 'issue': issue, 'reason': f'ltui not found at {LTUI}'}
    proc = subprocess.run(
        [str(LTUI), 'issues', 'update', issue, '--state', 'In Review'],
        text=True,
        capture_output=True,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        return {
            'attempted': True,
            'issue': issue,
            'ok': False,
            'error': stderr or stdout or 'ltui issues update failed',
        }
    state_name = None
    for line in stdout.splitlines():
        if line.startswith('STATE: '):
            state_name = line.split(': ', 1)[1].strip()
            break
    return {
        'attempted': True,
        'issue': issue,
        'ok': True,
        'state': state_name,
        'output': stdout,
    }


def state_path(target: str) -> Path:
    safe = re.sub(r'[^A-Za-z0-9_.-]+', '-', target)
    return STATE_DIR / f'pi-workflow-{safe}.json'


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2))


def detect_issue(plan: str) -> str | None:
    m = re.search(r'([A-Za-z]+-\d+)', plan)
    return m.group(1).upper() if m else None


def ensure_transition(current: str | None, nxt: str) -> None:
    if current is None:
        return
    allowed = NEXT_STAGE.get(current, set())
    if nxt not in allowed and nxt != current:
        raise SystemExit(f'invalid stage transition: {current} -> {nxt}; allowed: {sorted(allowed)}')


def cmd_for_stage(stage: str, plan: str) -> str:
    template = STAGE_TO_COMMAND.get(stage)
    if not template:
        raise SystemExit(f'no direct pi command for stage {stage}')
    return template.format(plan=plan)


def main() -> int:
    parser = argparse.ArgumentParser(description='Reliable pi workflow orchestrator for tmux panes.')
    parser.add_argument('--pane', required=True, help='tmux pane id for the pi worker, using pane-id syntax with a leading percent sign')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--stage', required=True, choices=sorted(VALID_STAGES))
    parser.add_argument('--message', help='custom message to send instead of the stage default')
    parser.add_argument('--base', default='develop', help='base branch for create-pr stage')
    parser.add_argument('--pr-title', help='PR title override for create-pr stage')
    parser.add_argument('--pr-body', help='PR body override for create-pr stage')
    parser.add_argument('--force', action='store_true', help='ignore stage transition guard')
    parser.add_argument('--print-only', action='store_true')
    args = parser.parse_args()

    pane = args.pane
    repo = str(Path(args.repo).expanduser().resolve())
    plan = args.plan
    issue = detect_issue(plan)
    spath = state_path(pane)
    state = load_state(spath)
    current_stage = state.get('stage')

    if not args.force:
        ensure_transition(current_stage, args.stage)

    if args.stage == 'commit-plan':
        status = git_status(repo)
        dirty = [line for line in status.splitlines() if line and not line.startswith('## ')]
        allowed = {f' M {plan}', f'M {plan}', f'?? {plan}'}
        if dirty and any(line not in allowed for line in dirty):
            raise SystemExit(f'refusing commit-plan with unexpected dirty tree:\n{status}')
        output = git_commit_plan(repo, plan, issue)
        state.update({'stage': 'commit-plan', 'last_action': 'git-commit', 'repo': repo, 'plan': plan, 'issue': issue, 'updated_at': time.time()})
        save_state(spath, state)
        print(output)
        return 0

    if args.stage == 'create-pr':
        ensure_clean_tree_for_pr(repo)
        branch = git_branch(repo)
        if not git_has_upstream(repo):
            raise SystemExit(f'refusing create-pr because {branch} has no upstream; push the branch first')
        title = args.pr_title or (f'fix: complete {issue}' if issue else f'Open PR for {Path(repo).name}')
        body = args.pr_body or (
            f"## Summary\n- execute the approved plan at `{plan}`\n- deliver the validated branch for review\n\n## Validation\n- Use repo validation evidence from the executed plan / progress log\n\nRefs: {issue or plan}\n"
        )
        if args.print_only:
            print(json.dumps({'title': title, 'body': body, 'base': args.base, 'branch': branch}, indent=2))
            return 0
        result = gh_create_pr(repo, branch, args.base, title, body)
        linear = sync_issue_to_in_review(issue)
        state.update({
            'stage': 'create-pr',
            'last_action': 'gh-pr-create',
            'repo': repo,
            'plan': plan,
            'issue': issue,
            'branch': branch,
            'base': args.base,
            'pr': result.get('pr'),
            'linear': linear,
            'next_stage': 'post-pr-followup',
            'updated_at': time.time(),
        })
        save_state(spath, state)
        print(json.dumps({**result, 'linear': linear, 'next_stage': 'post-pr-followup'}, indent=2))
        return 0

    text = args.message or cmd_for_stage(args.stage, plan)
    if '/dev:run-direct' in text:
        raise SystemExit('refusing to send removed command /dev:run-direct; use /dev:run')

    if args.print_only:
        print(text)
        return 0

    tmux_send_text(pane, text)
    header = tmux_capture(pane, lines=80)
    state.update({'stage': args.stage, 'last_action': text, 'repo': repo, 'plan': plan, 'issue': issue, 'updated_at': time.time()})
    save_state(spath, state)
    print(json.dumps({'ok': True, 'pane': pane, 'stage': args.stage, 'sent': text, 'state_path': str(spath), 'tail': '\n'.join(header.splitlines()[-20:])}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
