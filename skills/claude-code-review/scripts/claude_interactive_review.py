#!/usr/bin/env python3
"""Canonical interactive tmux launcher for required Claude Code reviews."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

READY_RE = re.compile(r"❯")
ANSWER_MARKER_PREFIX = "CLAUDE_REVIEW_ANSWER_START_"
CLAUDE_REVIEW_MODEL = "claude-opus-4-7"
CLAUDE_REVIEW_EFFORT = "xhigh"
DEFAULT_TIMEOUT_SECONDS = 3600
READY_TIMEOUT_SECONDS = 120
BOUNDARY_TIMEOUT_SECONDS = 45
PASTE_SETTLE_SECONDS = 5
TEARDOWN_TIMEOUT_SECONDS = 8
TMUX_HISTORY_LIMIT = 50000
CAPTURE_DEPTH = 50000
MIN_SENTINEL_LENGTH = 16
COMMON_SENTINELS = {"DONE", "END", "SUCCESS", "STOP", "EOF", "FINISHED", "COMPLETE"}
SHELL_AMBIGUOUS = set("`$\\;|&<>(){}[]*!?\"'")

ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class LauncherError(RuntimeError):
    def __init__(self, code: str, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def run(cmd: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise LauncherError("CLAUDE_REVIEW_COMMAND_FAILED", f"command failed: {' '.join(cmd)}\n{proc.stderr or proc.stdout}")
    return proc


def normalize(text: str) -> str:
    text = ANSI_RE.sub("", text.replace("\r", ""))
    text = CONTROL_RE.sub("", text)
    return "\n".join(line.rstrip() for line in text.splitlines())


def slugify(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe or "claude-review"


def make_nonce() -> str:
    return secrets.token_hex(6)


def generated_sentinel(review_name: str, nonce: str) -> str:
    return f"CLAUDE_REVIEW_DONE_{slugify(review_name).replace('-', '_')}_{os.getpid()}_{nonce}"


def validate_sentinel(sentinel: str) -> None:
    if not sentinel:
        raise LauncherError("CLAUDE_REVIEW_INVALID_SENTINEL", "sentinel must not be empty")
    if len(sentinel) < MIN_SENTINEL_LENGTH:
        raise LauncherError("CLAUDE_REVIEW_INVALID_SENTINEL", f"sentinel must be at least {MIN_SENTINEL_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in sentinel):
        raise LauncherError("CLAUDE_REVIEW_INVALID_SENTINEL", "sentinel must not contain control characters or newlines")
    if sentinel.upper() in COMMON_SENTINELS:
        raise LauncherError("CLAUDE_REVIEW_INVALID_SENTINEL", "sentinel must not be a common completion token")
    if any(ch in SHELL_AMBIGUOUS for ch in sentinel):
        raise LauncherError("CLAUDE_REVIEW_INVALID_SENTINEL", "sentinel must avoid shell-ambiguous punctuation")


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise LauncherError("CLAUDE_REVIEW_MISSING_PREREQUISITE", f"missing required tool: {name}")


def require_claude_login_shell() -> None:
    proc = run(["zsh", "-ilc", "command -v claude"], check=False, timeout=30)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise LauncherError("CLAUDE_REVIEW_MISSING_PREREQUISITE", "missing required tool in login shell: claude")


def tmux(socket: str, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["tmux", "-L", socket, *args], check=check)


def capture(socket: str, session: str, window: str) -> str:
    proc = tmux(socket, ["capture-pane", "-t", f"{session}:{window}", "-p", "-J", "-S", f"-{CAPTURE_DEPTH}"], check=False)
    return proc.stdout or ""


def count_token(text: str, token: str) -> int:
    return text.count(token)


def write_failure(output: Path, code: str, message: str, *, socket: str | None = None, session: str | None = None, transcript: str | None = None) -> None:
    lines = [code, message]
    if output:
        if transcript:
            transcript_path = output.with_suffix(output.suffix + ".transcript.txt")
            transcript_path.write_text(transcript, encoding="utf-8")
            lines.append(f"transcript={transcript_path}")
        if socket and session:
            lines.append(f"inspect=tmux -L {socket} attach -t {session}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_tui_unavailable(text: str, *, after_submit: bool = False) -> None:
    if re.search(r"not logged in|please run /login", text, re.I):
        suffix = " after submit" if after_submit else ""
        raise LauncherError("CLAUDE_AUTH_UNAVAILABLE_IN_TUI", f"Claude TUI reported not logged in{suffix}; run /login in Claude Code or unlock the keychain", 21)
    if re.search(r"session limit|rate limit|limit reached|resets\s+\d", text, re.I):
        suffix = " after submit" if after_submit else ""
        raise LauncherError("CLAUDE_SESSION_LIMIT_IN_TUI", f"Claude TUI reported a session/rate limit{suffix}; wait for reset or choose a non-required review path only if the workflow allows it", 25)


def wait_for_prompt(socket: str, session: str, window: str, output: Path, timeout_seconds: int) -> str:
    deadline = time.time() + timeout_seconds
    last = ""
    while time.time() < deadline:
        raw = capture(socket, session, window)
        text = normalize(raw)
        last = raw
        check_tui_unavailable(text)
        if READY_RE.search(text):
            return raw
        time.sleep(1)
    raise LauncherError("CLAUDE_TUI_NOT_READY", "Claude TUI did not reach a usable prompt before readiness timeout", 22)


def start_private_tmux(socket: str, session: str) -> None:
    tmux(socket, ["new-session", "-d", "-s", session, "-n", "control", "sleep 3600"])
    tmux(socket, ["set-option", "-g", "history-limit", str(TMUX_HISTORY_LIMIT)], check=False)


def auth_status_logged_in(text: str) -> bool:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("loggedIn") is True:
            return True
    return False


def auth_preflight(socket: str, session: str, cwd: Path, output: Path) -> None:
    auth_path = output.with_suffix(output.suffix + ".auth.json")
    command = f"cd {sh_quote(str(cwd))} && zsh -ilc 'claude auth status; printf EXIT=%s\\n $?' > {sh_quote(str(auth_path))} 2>&1"
    tmux(socket, ["new-window", "-t", session, "-n", "auth", command])
    deadline = time.time() + 60
    while time.time() < deadline:
        if auth_path.exists() and "EXIT=" in auth_path.read_text(errors="replace"):
            break
        time.sleep(0.5)
    text = auth_path.read_text(errors="replace") if auth_path.exists() else ""
    if not auth_status_logged_in(text):
        raise LauncherError("CLAUDE_AUTH_UNAVAILABLE_IN_TMUX_PREFLIGHT", "claude auth status inside private tmux did not report loggedIn true; run /login or unlock the keychain", 20)


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def launch_tui(socket: str, session: str, window: str, cwd: Path) -> None:
    command = f"cd {sh_quote(str(cwd))} && zsh -ilc 'claude --model {CLAUDE_REVIEW_MODEL} --effort {CLAUDE_REVIEW_EFFORT}'"
    tmux(socket, ["new-window", "-t", session, "-n", window, command])
    tmux(socket, ["resize-window", "-t", f"{session}:{window}", "-x", "220", "-y", "60"], check=False)


def teardown_success(socket: str, session: str, window: str) -> None:
    tmux(socket, ["send-keys", "-t", f"{session}:{window}", "/exit", "Enter"], check=False)
    deadline = time.time() + TEARDOWN_TIMEOUT_SECONDS
    while time.time() < deadline:
        if tmux(socket, ["has-session", "-t", session], check=False).returncode != 0:
            return
        time.sleep(0.5)
    tmux(socket, ["kill-server"], check=False)


def compose_prompt(prompt_file: Path, marker: str, sentinel: str) -> str:
    body = prompt_file.read_text(encoding="utf-8")
    return f"""{body.rstrip()}

---
Claude review launcher emission protocol:
Return the review text only. Do not edit files. Emit the following answer-start marker on its own line, then the review, then the final sentinel on its own line. Do not repeat the final sentinel anywhere except the final line.
{marker}
<review text here>
{sentinel}
CLAUDE_REVIEW_FINAL_SENTINEL:{sentinel}"""


def extract_answer(new_text: str, marker: str, sentinel: str) -> str:
    marker_index = new_text.rfind(marker)
    if marker_index < 0:
        raise LauncherError("CLAUDE_REVIEW_MARKER_MISSING", "answer marker not found after prompt boundary")
    answer_start = marker_index + len(marker)
    sentinel_index = -1
    offset = 0
    for line in new_text[answer_start:].splitlines(keepends=True):
        if line.strip() == sentinel:
            sentinel_index = answer_start + offset
            break
        offset += len(line)
    if sentinel_index < 0:
        sentinel_index = new_text.find(sentinel, answer_start)
    if sentinel_index < answer_start:
        raise LauncherError("CLAUDE_REVIEW_SENTINEL_MISSING", "sentinel not found after answer marker")
    answer = new_text[answer_start:sentinel_index].strip("\n ")
    if not answer:
        raise LauncherError("CLAUDE_REVIEW_EMPTY_ANSWER", "answer region between marker and sentinel was empty")
    return answer


def suffix_after_baseline(baseline: str, later: str, marker: str, sentinel: str) -> str | None:
    if later.startswith(baseline):
        return later[len(baseline):]
    base_marker_count = count_token(baseline, marker)
    base_sentinel_count = count_token(baseline, sentinel)
    marker_positions = [m.start() for m in re.finditer(re.escape(marker), later)]
    sentinel_positions = [m.start() for m in re.finditer(re.escape(sentinel), later)]
    if len(marker_positions) > base_marker_count and len(sentinel_positions) > base_sentinel_count:
        start = min(marker_positions[base_marker_count], sentinel_positions[base_sentinel_count])
        return later[start:]
    return None


def extract_prompt_cleared_answer(text: str, marker: str, sentinel: str) -> str | None:
    if sentinel not in text:
        return None
    if marker in text:
        if f"CLAUDE_REVIEW_FINAL_SENTINEL:{sentinel}" in text:
            return extract_sentinel_only_answer(text, sentinel)
        try:
            answer = extract_answer(text, marker, sentinel)
        except LauncherError:
            return None
        if answer_is_prompt_template(answer):
            return None
        return answer
    return extract_sentinel_only_answer(text, sentinel)


def answer_is_prompt_template(answer: str) -> bool:
    return "Claude review launcher emission protocol" in answer or "<review text here>" in answer


def extract_sentinel_only_answer(text: str, sentinel: str) -> str | None:
    lines = text.splitlines()
    sentinel_line_index = next((index for index, line in enumerate(lines) if line.strip() == sentinel), None)
    if sentinel_line_index is None:
        return None
    answer = "\n".join(lines[:sentinel_line_index]).strip()
    if not answer or "VERDICT:" not in answer or answer_is_prompt_template(answer):
        return None
    return answer


def prompt_visible_or_collapsed(candidate: str, marker_count: int, sentinel_count: int, prompt_marker_count: int, prompt_sentinel_count: int) -> bool:
    if marker_count == prompt_marker_count and sentinel_count == prompt_sentinel_count:
        return True
    return "[Pasted text #" in candidate and marker_count == 0 and sentinel_count == 0


def run_smoke(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    nonce = make_nonce()
    socket = f"claude-review-{slugify(args.review_name)}-{os.getpid()}-{nonce}"
    session = "review"
    window = "claude-smoke"
    cwd = Path(args.cwd or os.getcwd()).resolve()
    try:
        require_tool("tmux")
        require_claude_login_shell()
        start_private_tmux(socket, session)
        auth_preflight(socket, session, cwd, output)
        launch_tui(socket, session, window, cwd)
        wait_for_prompt(socket, session, window, output, min(args.timeout_seconds, READY_TIMEOUT_SECONDS))
        text = f"CLAUDE_REVIEW_SMOKE_READY\nsocket={socket}\nsession={session}\nwindow={window}\nmodel={CLAUDE_REVIEW_MODEL}\neffort={CLAUDE_REVIEW_EFFORT}\nreadiness_regex={READY_RE.pattern}\nhistory_limit={TMUX_HISTORY_LIMIT}\ncapture_depth={CAPTURE_DEPTH}\n"
        output.write_text(text, encoding="utf-8")
        print(text, end="")
        teardown_success(socket, session, window)
        return 0
    except LauncherError as exc:
        raw = capture(socket, session, window) if shutil.which("tmux") else ""
        write_failure(output, exc.code, str(exc), socket=socket, session=session, transcript=raw)
        print(output.read_text(errors="replace"), file=sys.stderr, end="")
        return exc.exit_code


def run_review(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cwd = Path(args.cwd).resolve()
    prompt_file = Path(args.prompt_file).resolve()
    nonce = make_nonce()
    sentinel = args.sentinel or generated_sentinel(args.review_name, nonce)
    try:
        validate_sentinel(sentinel)
        require_tool("tmux")
        require_claude_login_shell()
        marker = f"{ANSWER_MARKER_PREFIX}{nonce}"
        socket = f"claude-review-{slugify(args.review_name)}-{os.getpid()}-{nonce}"
        session = "review"
        window = "claude-review"
        start_private_tmux(socket, session)
        auth_preflight(socket, session, cwd, output)
        launch_tui(socket, session, window, cwd)
        wait_for_prompt(socket, session, window, output, min(args.timeout_seconds, READY_TIMEOUT_SECONDS))
        final_prompt = compose_prompt(prompt_file, marker, sentinel)
        prompt_tmp = output.with_suffix(output.suffix + ".submitted-prompt.md")
        prompt_tmp.write_text(final_prompt, encoding="utf-8")
        tmux(socket, ["load-buffer", "-b", "review-prompt", str(prompt_tmp)])
        tmux(socket, ["paste-buffer", "-d", "-b", "review-prompt", "-t", f"{session}:{window}"])
        prompt_marker_count = count_token(final_prompt, marker)
        prompt_sentinel_count = count_token(final_prompt, sentinel)
        paste_deadline = time.time() + PASTE_SETTLE_SECONDS
        while time.time() < paste_deadline:
            candidate = normalize(capture(socket, session, window))
            check_tui_unavailable(candidate)
            marker_count = count_token(candidate, marker)
            sentinel_count = count_token(candidate, sentinel)
            if prompt_visible_or_collapsed(candidate, marker_count, sentinel_count, prompt_marker_count, prompt_sentinel_count):
                break
            if marker_count > prompt_marker_count or sentinel_count > prompt_sentinel_count:
                raise LauncherError("CLAUDE_TUI_BOUNDARY_UNCERTAIN", "answer marker appeared before prompt submission", 23)
            time.sleep(0.1)
        tmux(socket, ["send-keys", "-t", f"{session}:{window}", "Enter"])
        boundary_deadline = time.time() + BOUNDARY_TIMEOUT_SECONDS
        baseline = ""
        while time.time() < boundary_deadline:
            raw = capture(socket, session, window)
            candidate = normalize(raw)
            check_tui_unavailable(candidate, after_submit=True)
            prompt_cleared_answer = extract_prompt_cleared_answer(candidate, marker, sentinel)
            if prompt_cleared_answer:
                transcript_path = output.with_suffix(output.suffix + ".transcript.txt")
                transcript_path.write_text(raw, encoding="utf-8")
                metadata = f"\n\n---\nCLAUDE_REVIEW_LAUNCHER_METADATA\nsocket={socket}\nsession={session}\nwindow={window}\nmodel={CLAUDE_REVIEW_MODEL}\neffort={CLAUDE_REVIEW_EFFORT}\ntranscript={transcript_path}\nreadiness_regex={READY_RE.pattern}\nclear_boundary=prompt-cleared marker/sentinel extraction before baseline\nhistory_limit={TMUX_HISTORY_LIMIT}\ncapture_depth={CAPTURE_DEPTH}\n"
                output.write_text(prompt_cleared_answer.strip() + metadata, encoding="utf-8")
                teardown_success(socket, session, window)
                return 0
            marker_count = count_token(candidate, marker)
            sentinel_count = count_token(candidate, sentinel)
            if prompt_visible_or_collapsed(candidate, marker_count, sentinel_count, prompt_marker_count, prompt_sentinel_count):
                baseline = candidate
                break
            if marker_count > prompt_marker_count or sentinel_count > prompt_sentinel_count:
                raise LauncherError("CLAUDE_TUI_BOUNDARY_UNCERTAIN", "answer marker appeared before a post-submit baseline could be established", 23)
            time.sleep(0.1)
        if not baseline:
            raise LauncherError("CLAUDE_TUI_BOUNDARY_UNCERTAIN", "could not establish post-submit baseline before answer extraction", 23)
        deadline = time.time() + args.timeout_seconds
        last_raw = ""
        while time.time() < deadline:
            last_raw = capture(socket, session, window)
            text = normalize(last_raw)
            check_tui_unavailable(text, after_submit=True)
            suffix = suffix_after_baseline(baseline, text, marker, sentinel)
            answer = None
            boundary = "baseline-relative marker/sentinel occurrence diff after submit"
            if suffix and count_token(suffix, marker) >= 1 and count_token(suffix, sentinel) >= 1:
                try:
                    candidate_answer = extract_answer(suffix, marker, sentinel)
                except LauncherError:
                    candidate_answer = None
                if candidate_answer and not answer_is_prompt_template(candidate_answer):
                    answer = candidate_answer
            else:
                answer = extract_prompt_cleared_answer(text, marker, sentinel)
                boundary = "prompt-cleared marker/sentinel extraction after submit"
            if answer:
                transcript_path = output.with_suffix(output.suffix + ".transcript.txt")
                transcript_path.write_text(last_raw, encoding="utf-8")
                metadata = f"\n\n---\nCLAUDE_REVIEW_LAUNCHER_METADATA\nsocket={socket}\nsession={session}\nwindow={window}\nmodel={CLAUDE_REVIEW_MODEL}\neffort={CLAUDE_REVIEW_EFFORT}\ntranscript={transcript_path}\nreadiness_regex={READY_RE.pattern}\nclear_boundary={boundary}\nhistory_limit={TMUX_HISTORY_LIMIT}\ncapture_depth={CAPTURE_DEPTH}\n"
                output.write_text(answer.strip() + metadata, encoding="utf-8")
                teardown_success(socket, session, window)
                return 0
            time.sleep(1)
        raise LauncherError("CLAUDE_REVIEW_TIMEOUT", f"timed out waiting for {marker} and sentinel after prompt boundary", 24)
    except LauncherError as exc:
        socket_val = locals().get("socket")
        session_val = locals().get("session")
        window_val = locals().get("window")
        raw = capture(socket_val, session_val, window_val) if socket_val and session_val and window_val and shutil.which("tmux") else ""
        write_failure(output, exc.code, str(exc), socket=socket_val, session=session_val, transcript=raw)
        print(output.read_text(errors="replace"), file=sys.stderr, end="")
        return exc.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Claude Code reviews through an interactive private tmux TUI")
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--prompt-file")
    parser.add_argument("--output", required=True)
    parser.add_argument("--review-name", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--sentinel")
    parser.add_argument("--smoke", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.smoke:
        if args.prompt_file:
            raise SystemExit("--smoke does not accept --prompt-file")
        return run_smoke(args)
    if not args.prompt_file:
        raise SystemExit("--prompt-file is required unless --smoke is set")
    return run_review(args)


if __name__ == "__main__":
    raise SystemExit(main())
