#!/opt/homebrew/bin/python3
from __future__ import annotations

import fcntl
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

INBOX_RELATIVE = Path("Nodaste Agents/Signals/inbox/aaron")
SIG_RE = re.compile(r"^SIG-.*\.md$")
VALID_STATUSES = {"new", "acknowledged", "in_progress", "needs_info_from_requester", "blocked", "done", "cancelled"}

HOME = Path.home()
HERMES = Path("/Users/anichols/.hermes/hermes-agent/venv/bin/hermes")
STATE_DIR = HOME / ".hermes" / "watchers" / "aaron-realtime"
LOCK_PATH = STATE_DIR / "watcher.lock"
LOG_PATH = STATE_DIR / "watcher.log"
STUDIO_ROOT = HOME / "Documents" / "Obsidian" / "studio"
IDENTITY_FILE = HOME / "Documents" / "Obsidian" / "adn_vault" / "_pi" / "agents" / "aaron-agent.md"

PROMPT = """Process this exact Aaron inbound Nodaste signal file: {signal_path}

Follow these rules strictly:
- Only process this exact signal file.
- Treat the signal note itself as the source of truth.
- Keep edits concise and protocol-compliant.
- Update `## Response` with short timestamped progress/completion notes.
- Update `last_updated_at`.
- If the work is fully complete, set `status: done`.
- If missing requester context blocks completion, set `status: needs_info_from_requester` and add specific questions under `## Clarifying Questions`.
- Otherwise use `status: in_progress` only if work is genuinely still in flight.
- If `linked_signal_path` exists, sync the same status/response/frontmatter changes to the linked mirror.
- Do not send side-channel chat replies.
- Do not scan other inboxes.
- Return only a one-line watcher summary.

Relevant docs:
- {identity_file}
- {protocol_doc}
- {operating_model_doc}
- {onboarding_doc}
"""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"[{now()}] {message}\n")


def resolve_signal_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve()
    try:
        rel = p.relative_to(STUDIO_ROOT)
    except ValueError as exc:
        raise SystemExit(f"Signal path outside studio vault: {p}") from exc
    if rel.parent != INBOX_RELATIVE:
        raise SystemExit(f"Not Aaron inbox path: {rel}")
    if not SIG_RE.match(p.name):
        raise SystemExit(f"Not a SIG markdown note: {p.name}")
    return p


def parse_status(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    frontmatter = parts[1]
    for line in frontmatter.splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: process_aaron_signal_realtime.py /absolute/path/to/SIG-...md", file=sys.stderr)
        return 2

    if not HERMES.exists():
        log(f"Hermes binary missing: {HERMES}")
        return 1

    signal_path = resolve_signal_path(sys.argv[1])
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w") as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log(f"Skipped {signal_path.name}: watcher already running")
            return 0

        status = parse_status(signal_path)
        if status not in VALID_STATUSES:
            log(f"Skipped {signal_path.name}: invalid or missing status {status!r}")
            return 0
        if status != "new":
            log(f"Skipped {signal_path.name}: status is {status!r}, not 'new'")
            return 0

        prompt = PROMPT.format(
            signal_path=str(signal_path),
            identity_file=str(IDENTITY_FILE),
            protocol_doc=str(STUDIO_ROOT / "Nodaste Agents" / "Protocol - Team Signal Standard.md"),
            operating_model_doc=str(STUDIO_ROOT / "Nodaste Agents" / "Operating Model.md"),
            onboarding_doc=str(STUDIO_ROOT / "Nodaste Agents" / "Onboarding - Aaron and Katie Agents.md"),
        )
        env = os.environ.copy()
        env.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
        cmd = [str(HERMES), "chat", "-Q", "--source", "tool", "-q", prompt]
        log(f"Processing {signal_path.name}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
        summary = (result.stdout or result.stderr or "").strip().replace("\n", " ")
        if len(summary) > 500:
            summary = summary[:497] + "..."
        log(f"Hermes exit={result.returncode} for {signal_path.name}: {summary}")
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
