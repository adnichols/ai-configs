from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import shlex
import time
from typing import Optional

logger = logging.getLogger(__name__)

_PATCHED = False
_ORIGINAL_HANDLE_MESSAGE = None


class PiBridge:
    def __init__(self, session_key: str, process_id: str, source, mode: str, target: str, command: str):
        self.session_key = session_key
        self.process_id = process_id
        self.source = source
        self.mode = mode
        self.target = target
        self.command = command
        self.relay_task: Optional[asyncio.Task] = None


_BRIDGES: dict[str, PiBridge] = {}


def _session_slug(repo_path: Path) -> str:
    resolved = repo_path.expanduser().resolve()
    return f"--{str(resolved).replace('/', '-')}--"


def _resolve_session_file(raw_target: str) -> tuple[Optional[Path], Optional[Path], Optional[str]]:
    target = Path(raw_target).expanduser()

    if target.is_file():
        if target.suffix != ".jsonl":
            return None, None, f"Pi session files must end in .jsonl: {target}"
        return target.resolve(), target.parent.resolve(), None

    if target.is_dir():
        direct_candidates = sorted(
            (p for p in target.rglob("*.jsonl") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if direct_candidates:
            return direct_candidates[0].resolve(), target.resolve(), None

        session_root = (
            Path(os.getenv("PI_CODING_AGENT_DIR") or str(Path.home() / ".pi" / "agent"))
            / "sessions"
            / _session_slug(target)
        )
        if not session_root.exists():
            return None, None, f"No Pi sessions found for repo: {target}"
        repo_candidates = sorted(
            (p for p in session_root.rglob("*.jsonl") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not repo_candidates:
            return None, None, f"No Pi sessions found for repo: {target}"
        return repo_candidates[0].resolve(), target.resolve(), None

    return None, None, f"No such Pi session target: {target}"


def _sanitize_output(text: str) -> str:
    from tools.ansi_strip import strip_ansi

    cleaned = strip_ansi(text or "")
    return cleaned.replace("\r\n", "\n").replace("\r", "\n")


async def _send_output(runner, bridge: PiBridge, content: str) -> None:
    if not content:
        return
    adapter = runner.adapters.get(bridge.source.platform)
    if not adapter:
        return
    metadata = {"thread_id": bridge.source.thread_id} if bridge.source.thread_id else None
    await adapter._send_with_retry(
        chat_id=bridge.source.chat_id,
        content=content,
        metadata=metadata,
    )


async def _relay_loop(runner, session_key: str) -> None:
    from tools.process_registry import process_registry

    bridge = _BRIDGES.get(session_key)
    if not bridge:
        return

    sent_chars = 0
    pending = ""
    last_flush = 0.0
    exit_code = None
    try:
        while True:
            session = process_registry.get(bridge.process_id)
            if session is None:
                break

            with session._lock:
                snapshot = _sanitize_output(session.output_buffer)
                exited = bool(session.exited)
                exit_code = session.exit_code

            if len(snapshot) < sent_chars:
                sent_chars = 0
            if len(snapshot) > sent_chars:
                pending += snapshot[sent_chars:]
                sent_chars = len(snapshot)

            now = time.monotonic()
            should_flush = bool(pending) and (
                exited or len(pending) >= 1200 or (now - last_flush) >= 0.35
            )
            if should_flush:
                await _send_output(runner, bridge, pending)
                pending = ""
                last_flush = now

            if exited:
                break

            await asyncio.sleep(0.15)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning("Pi relay loop failed for %s: %s", session_key[:30], e, exc_info=True)
        try:
            await _send_output(runner, bridge, f"⚠ Pi relay error: {e}")
        except Exception:
            pass
    finally:
        current = _BRIDGES.get(session_key)
        if current and current.process_id == bridge.process_id:
            _BRIDGES.pop(session_key, None)
            try:
                await _send_output(
                    runner,
                    bridge,
                    f"🧵 Pi bridge closed (exit code: {exit_code if exit_code is not None else 'unknown'}).",
                )
            except Exception:
                pass


async def _start_bridge(runner, event, *, mode: str, target: str, command: str) -> str:
    from tools.process_registry import process_registry

    source = event.source
    session_key = runner._session_key_for_source(source)
    existing = _BRIDGES.get(session_key)
    if existing:
        return (
            "Pi bridge already active in this thread. "
            "Send `exit` to Pi to end it, or use `/STOP` to send ESC."
        )

    process_session = process_registry.spawn(
        command=command,
        task_id=session_key,
        session_key=session_key,
        use_pty=True,
    )
    bridge = PiBridge(
        session_key=session_key,
        process_id=process_session.id,
        source=source,
        mode=mode,
        target=target,
        command=command,
    )
    _BRIDGES[session_key] = bridge
    bridge.relay_task = asyncio.create_task(_relay_loop(runner, session_key))
    bg_tasks = getattr(runner, "_background_tasks", None)
    if bg_tasks is not None:
        bg_tasks.add(bridge.relay_task)
        bridge.relay_task.add_done_callback(bg_tasks.discard)
    return (
        f"🧵 Pi bridge active ({mode}: `{target}`).\n"
        "All new thread messages now go straight to Pi.\n"
        "Use `/STOP` to send ESC, or send `exit` to Pi to close the bridge."
    )


async def _handle_passthrough(runner, event, session_key: str) -> Optional[str]:
    from tools.process_registry import process_registry

    bridge = _BRIDGES.get(session_key)
    if not bridge:
        return None

    session = process_registry.get(bridge.process_id)
    if session is None or session.exited:
        _BRIDGES.pop(session_key, None)
        return None

    raw_text = event.text or ""
    if raw_text.strip() == "/STOP":
        result = process_registry.write_stdin(bridge.process_id, "\x1b")
        if result.get("status") == "ok":
            return "⎋ Sent ESC to Pi."
        return f"Failed to send ESC to Pi: {result.get('error', 'unknown error')}"

    result = process_registry.submit_stdin(bridge.process_id, raw_text)
    if result.get("status") not in {"ok", "already_exited"}:
        return f"Failed to send input to Pi: {result.get('error', 'unknown error')}"
    return ""


async def _handle_pi_command(runner, event) -> str:
    from tools.process_registry import process_registry

    args = event.get_command_args().strip()
    session_key = runner._session_key_for_source(event.source)

    if not args or args.lower() in {"help", "-h", "--help"}:
        return (
            "Usage:\n"
            "`/pi new <repo-path>` — start a fresh interactive Pi session in that repo\n"
            "`/pi attach <session-file-or-repo-path>` — attach to an existing Pi session\n"
            "`/pi status` — show Pi bridge status for this thread"
        )

    subcommand, _, remainder = args.partition(" ")
    subcommand = subcommand.lower().strip()
    target = remainder.strip()

    if subcommand == "status":
        bridge = _BRIDGES.get(session_key)
        if not bridge:
            return "No active Pi bridge in this thread."
        status = process_registry.poll(bridge.process_id)
        lines = [
            f"**Pi bridge:** {status.get('status', 'unknown')}",
            f"**Mode:** {bridge.mode}",
            f"**Target:** `{bridge.target}`",
            f"**Process:** `{bridge.process_id}`",
        ]
        preview = (status.get("output_preview") or "").strip()
        if preview:
            lines.extend(["", "**Recent output:**", f"```\n{preview[-700:]}\n```"])
        return "\n".join(lines)

    if subcommand == "new":
        if not target:
            return "Usage: `/pi new <repo-path>`"
        repo_path = Path(target).expanduser()
        if not repo_path.is_dir():
            return f"Repo path not found: `{repo_path}`"
        command = f"cd {shlex.quote(str(repo_path.resolve()))} && exec pi"
        return await _start_bridge(
            runner,
            event,
            mode="new",
            target=str(repo_path.resolve()),
            command=command,
        )

    if subcommand == "attach":
        if not target:
            return "Usage: `/pi attach <session-file-or-repo-path>`"
        session_path, cwd_path, error = _resolve_session_file(target)
        if error:
            return error
        assert session_path is not None
        cwd = cwd_path or Path.home()
        command = f"cd {shlex.quote(str(cwd))} && exec pi --session {shlex.quote(str(session_path))}"
        return await _start_bridge(
            runner,
            event,
            mode="attach",
            target=str(session_path),
            command=command,
        )

    return "Unknown `/pi` subcommand. Use `/pi help`."


async def _patched_handle_message(self, event):
    text = event.text or ""
    session_key = self._session_key_for_source(event.source)

    passthrough = await _handle_passthrough(self, event, session_key)
    if passthrough is not None:
        return passthrough

    stripped = text.strip()
    if stripped == "/pi" or stripped.startswith("/pi "):
        return await _handle_pi_command(self, event)

    return await _ORIGINAL_HANDLE_MESSAGE(self, event)


def _apply_patch() -> None:
    global _PATCHED, _ORIGINAL_HANDLE_MESSAGE
    if _PATCHED:
        return

    import gateway.run as gateway_run

    _ORIGINAL_HANDLE_MESSAGE = gateway_run.GatewayRunner._handle_message
    gateway_run.GatewayRunner._handle_message = _patched_handle_message
    gateway_run.GatewayRunner._pi_thread_bridge_hook = True
    _PATCHED = True
    logger.info("pi-thread-bridge hook installed")


async def handle(event_type, context):
    if event_type == "gateway:startup":
        _apply_patch()
