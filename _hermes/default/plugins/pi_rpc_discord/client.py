from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from gateway.session_context import get_session_env

PLUGIN_NAME = "pi_rpc_discord"
PLUGIN_HOME = get_hermes_home() / "plugins" / PLUGIN_NAME
STATE_DIR = PLUGIN_HOME / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "bindings.json"
DEFAULT_TOOLS = ["read", "bash", "edit", "write", "grep", "find", "ls"]
MAX_EVENT_BUFFER = 250


class SessionError(RuntimeError):
    pass


@dataclass
class SessionMeta:
    session_id: str
    repo_path: str
    display_name: str
    created_at: float
    pid: int
    provider: str | None = None
    model: str | None = None
    thinking: str | None = None
    session_file: str | None = None
    bound_contexts: list[str] | None = None
    last_activity_at: float | None = None
    last_error: str | None = None


class PiRpcSession:
    def __init__(
        self,
        repo_path: str,
        display_name: str,
        provider: str | None = None,
        model: str | None = None,
        thinking: str | None = None,
        tools: list[str] | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.repo_path = str(Path(repo_path).expanduser().resolve())
        self.display_name = display_name
        self.provider = provider
        self.model = model
        self.thinking = thinking
        self.tools = list(tools or DEFAULT_TOOLS)
        self.extra_args = list(extra_args or [])
        self.session_id = f"pi-{uuid.uuid4().hex[:10]}"
        self.created_at = time.time()
        self.last_activity_at = self.created_at
        self.last_error = None
        self._proc: subprocess.Popen[bytes] | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._pending: dict[str, queue.Queue] = {}
        self._pending_lock = threading.Lock()
        self._event_seq = 0
        self._events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENT_BUFFER)
        self._stderr_lines: deque[str] = deque(maxlen=200)
        self._lock = threading.RLock()
        self._closed = False
        self._cached_state: dict[str, Any] = {}

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    def start(self) -> None:
        if self._proc is not None:
            return
        cmd = ["pi", "--mode", "rpc"]
        if self.provider:
            cmd += ["--provider", self.provider]
        if self.model:
            cmd += ["--model", self.model]
        if self.thinking:
            cmd += ["--thinking", self.thinking]
        if self.tools:
            cmd += ["--tools", ",".join(self.tools)]
        if self.extra_args:
            cmd += self.extra_args
        self._proc = subprocess.Popen(
            cmd,
            cwd=self.repo_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            bufsize=0,
        )
        self._stdout_thread = threading.Thread(target=self._read_stdout, name=f"{self.session_id}-stdout", daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, name=f"{self.session_id}-stderr", daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()
        try:
            state = self.send_command({"type": "get_state"}, timeout=20.0)
        except Exception as exc:
            self.close(force=True)
            raise SessionError(f"Failed to initialize pi RPC session: {exc}") from exc
        self._cached_state = state.get("data", {}) if isinstance(state, dict) else {}
        try:
            self.send_command({"type": "set_session_name", "name": self.display_name}, timeout=10.0)
        except Exception:
            pass

    def close(self, force: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin and not proc.stdin.closed and not force:
                try:
                    self._write_json({"type": "abort"})
                except Exception:
                    pass
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._fail_all_pending("pi RPC process exited")

    def is_alive(self) -> bool:
        return bool(self._proc and self._proc.poll() is None)

    def snapshot(self) -> SessionMeta:
        state = self._cached_state or {}
        return SessionMeta(
            session_id=self.session_id,
            repo_path=self.repo_path,
            display_name=self.display_name,
            created_at=self.created_at,
            pid=self.pid or -1,
            provider=self.provider,
            model=self.model,
            thinking=self.thinking,
            session_file=state.get("sessionFile"),
            bound_contexts=[],
            last_activity_at=self.last_activity_at,
            last_error=self.last_error,
        )

    def send_command(self, payload: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
        if not self.is_alive():
            raise SessionError("pi RPC process is not running")
        req_id = payload.get("id") or f"req-{uuid.uuid4().hex[:10]}"
        payload = dict(payload)
        payload["id"] = req_id
        resp_q: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[req_id] = resp_q
        try:
            self._write_json(payload)
            response = resp_q.get(timeout=timeout)
        except queue.Empty as exc:
            with self._pending_lock:
                self._pending.pop(req_id, None)
            raise SessionError(f"Timed out waiting for pi RPC response to {payload.get('type')}") from exc
        if not isinstance(response, dict):
            raise SessionError(f"Invalid pi RPC response: {response!r}")
        if response.get("success") is False:
            raise SessionError(response.get("error") or f"pi RPC command failed: {payload.get('type')}")
        return response

    def get_state(self) -> dict[str, Any]:
        resp = self.send_command({"type": "get_state"}, timeout=15.0)
        state = resp.get("data", {}) or {}
        if isinstance(state, dict):
            self._cached_state = state
        return state

    def prompt_and_wait(self, message: str, mode: str = "prompt", timeout: float = 1800.0) -> dict[str, Any]:
        if mode not in {"prompt", "steer", "follow_up"}:
            raise SessionError(f"Unsupported mode: {mode}")
        with self._lock:
            start_seq = self._event_seq
            self.last_activity_at = time.time()
            self.send_command({"type": mode, "message": message}, timeout=20.0)
            state = self._wait_until_idle(timeout=timeout)
            assistant_text = self._get_last_assistant_text()
            events = self._events_since(start_seq)
            summary = summarize_events(events)
            return {
                "assistant_text": assistant_text,
                "state": state,
                "event_summary": summary,
                "stderr_tail": list(self._stderr_lines)[-40:],
            }

    def abort(self) -> dict[str, Any]:
        with self._lock:
            self.last_activity_at = time.time()
            self.send_command({"type": "abort"}, timeout=10.0)
            return self.get_state()

    def _get_last_assistant_text(self) -> str:
        try:
            resp = self.send_command({"type": "get_last_assistant_text"}, timeout=15.0)
            data = resp.get("data", {}) or {}
            text = data.get("text")
            return text or ""
        except Exception:
            chunks = []
            for event in self._events:
                if event.get("type") != "message_update":
                    continue
                inner = event.get("assistantMessageEvent") or {}
                if inner.get("type") == "text_delta":
                    delta = inner.get("delta") or ""
                    if delta:
                        chunks.append(delta)
            return "".join(chunks).strip()

    def _wait_until_idle(self, timeout: float = 1800.0, poll_interval: float = 0.4) -> dict[str, Any]:
        deadline = time.time() + timeout
        last_state: dict[str, Any] = {}
        stable = 0
        while time.time() < deadline:
            if not self.is_alive():
                raise SessionError("pi RPC process exited while waiting for completion")
            state = self.get_state()
            last_state = state
            is_streaming = bool(state.get("isStreaming"))
            pending = int(state.get("pendingMessageCount") or 0)
            is_compacting = bool(state.get("isCompacting"))
            if not is_streaming and pending == 0 and not is_compacting:
                stable += 1
                if stable >= 2:
                    return state
            else:
                stable = 0
            time.sleep(poll_interval)
        raise SessionError(f"Timed out waiting for pi to become idle after {timeout:.0f}s")

    def _write_json(self, payload: dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise SessionError("pi RPC stdin is unavailable")
        line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n"
        self._proc.stdin.write(line.encode("utf-8"))
        self._proc.stdin.flush()

    def _read_stdout(self) -> None:
        proc = self._proc
        if not proc or not proc.stdout:
            return
        buf = b""
        try:
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    if raw.endswith(b"\r"):
                        raw = raw[:-1]
                    if not raw:
                        continue
                    self._handle_stdout_record(raw)
        finally:
            if buf.strip():
                self._handle_stdout_record(buf.strip())
            self._closed = True
            self._fail_all_pending("pi RPC stdout closed")

    def _handle_stdout_record(self, raw: bytes) -> None:
        try:
            msg = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:
            self.last_error = f"Invalid JSON from pi RPC: {exc}"
            self._stderr_lines.append(self.last_error)
            return
        if isinstance(msg, dict) and msg.get("type") == "response":
            req_id = msg.get("id")
            if req_id:
                with self._pending_lock:
                    resp_q = self._pending.pop(req_id, None)
                if resp_q:
                    resp_q.put(msg)
                    return
        self._event_seq += 1
        if isinstance(msg, dict):
            msg = dict(msg)
            msg["_seq"] = self._event_seq
            self._events.append(msg)
            self.last_activity_at = time.time()

    def _read_stderr(self) -> None:
        proc = self._proc
        if not proc or not proc.stderr:
            return
        try:
            for raw in iter(proc.stderr.readline, b""):
                if not raw:
                    break
                text = raw.decode("utf-8", "replace").rstrip("\n")
                if text:
                    self._stderr_lines.append(text)
                    self.last_error = text
        finally:
            pass

    def _events_since(self, start_seq: int) -> list[dict[str, Any]]:
        return [dict(event) for event in self._events if int(event.get("_seq", 0)) > start_seq]

    def _fail_all_pending(self, message: str) -> None:
        with self._pending_lock:
            items = list(self._pending.items())
            self._pending.clear()
        for _, resp_q in items:
            try:
                resp_q.put({"type": "response", "success": False, "error": message})
            except Exception:
                pass


class PiRpcManager:
    def __init__(self) -> None:
        self._sessions: dict[str, PiRpcSession] = {}
        self._bindings: dict[str, str] = {}
        self._lock = threading.RLock()
        self._load_bindings()

    def _load_bindings(self) -> None:
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self._bindings = dict(data.get("bindings") or {})
        except Exception:
            self._bindings = {}

    def _save_bindings(self) -> None:
        STATE_FILE.write_text(json.dumps({"bindings": self._bindings}, indent=2))

    def cleanup_dead_sessions(self) -> None:
        with self._lock:
            dead = [sid for sid, sess in self._sessions.items() if not sess.is_alive()]
            for sid in dead:
                self._sessions.pop(sid, None)
                for ctx, bound_sid in list(self._bindings.items()):
                    if bound_sid == sid:
                        self._bindings.pop(ctx, None)
            if dead:
                self._save_bindings()

    def start_session(
        self,
        repo: str,
        display_name: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        thinking: str | None = None,
        tools: list[str] | None = None,
        bind_context: str | None = None,
        extra_args: list[str] | None = None,
    ) -> SessionMeta:
        repo_path = resolve_repo_path(repo)
        if not Path(repo_path).exists():
            raise SessionError(f"Repository path does not exist: {repo_path}")
        if not Path(repo_path).is_dir():
            raise SessionError(f"Repository path is not a directory: {repo_path}")
        name = display_name or default_session_name(repo_path)
        session = PiRpcSession(repo_path, name, provider=provider, model=model, thinking=thinking, tools=tools, extra_args=extra_args)
        session.start()
        with self._lock:
            self._sessions[session.session_id] = session
            if bind_context:
                self._bindings[bind_context] = session.session_id
                self._save_bindings()
        meta = session.snapshot()
        meta.bound_contexts = [ctx for ctx, sid in self._bindings.items() if sid == session.session_id]
        return meta

    def list_sessions(self, current_context: str | None = None) -> dict[str, Any]:
        self.cleanup_dead_sessions()
        with self._lock:
            sessions = []
            for sid, session in sorted(self._sessions.items(), key=lambda item: item[1].created_at):
                meta = session.snapshot()
                meta.bound_contexts = [ctx for ctx, bound_sid in self._bindings.items() if bound_sid == sid]
                sessions.append(asdict(meta))
            return {
                "sessions": sessions,
                "current_context": current_context,
                "current_binding": self._bindings.get(current_context or "") if current_context else None,
            }

    def get_session(self, session_id: str | None = None, current_context: str | None = None) -> PiRpcSession:
        self.cleanup_dead_sessions()
        resolved = session_id
        if not resolved and current_context:
            resolved = self._bindings.get(current_context)
        if not resolved and len(self._sessions) == 1:
            resolved = next(iter(self._sessions.keys()))
        if not resolved:
            raise SessionError("No pi session selected. Start one first or specify session_id.")
        session = self._sessions.get(resolved)
        if not session:
            raise SessionError(f"Unknown pi session: {resolved}")
        if not session.is_alive():
            raise SessionError(f"pi session is no longer running: {resolved}")
        return session

    def bind(self, session_id: str, context_key: str) -> dict[str, Any]:
        session = self.get_session(session_id=session_id)
        with self._lock:
            self._bindings[context_key] = session.session_id
            self._save_bindings()
        return {"context_key": context_key, "session_id": session.session_id, "display_name": session.display_name}

    def unbind(self, context_key: str) -> dict[str, Any]:
        with self._lock:
            removed = self._bindings.pop(context_key, None)
            self._save_bindings()
        return {"context_key": context_key, "session_id": removed}

    def send(self, message: str, mode: str = "prompt", session_id: str | None = None, current_context: str | None = None, timeout: float = 1800.0) -> dict[str, Any]:
        session = self.get_session(session_id=session_id, current_context=current_context)
        result = session.prompt_and_wait(message=message, mode=mode, timeout=timeout)
        meta = session.snapshot()
        meta.bound_contexts = [ctx for ctx, sid in self._bindings.items() if sid == session.session_id]
        result["session"] = asdict(meta)
        return result

    def status(self, session_id: str | None = None, current_context: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id=session_id, current_context=current_context)
        state = session.get_state()
        meta = session.snapshot()
        meta.bound_contexts = [ctx for ctx, sid in self._bindings.items() if sid == session.session_id]
        return {
            "session": asdict(meta),
            "state": state,
            "recent_events": summarize_events(list(session._events)[-40:]),
            "stderr_tail": list(session._stderr_lines)[-25:],
        }

    def abort(self, session_id: str | None = None, current_context: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id=session_id, current_context=current_context)
        state = session.abort()
        return {"session_id": session.session_id, "state": state}

    def stop(self, session_id: str | None = None, current_context: str | None = None, remove_binding: bool = True) -> dict[str, Any]:
        session = self.get_session(session_id=session_id, current_context=current_context)
        sid = session.session_id
        session.close(force=False)
        with self._lock:
            self._sessions.pop(sid, None)
            removed_contexts = []
            if remove_binding:
                for ctx, bound_sid in list(self._bindings.items()):
                    if bound_sid == sid:
                        removed_contexts.append(ctx)
                        self._bindings.pop(ctx, None)
                self._save_bindings()
        return {"session_id": sid, "removed_bindings": removed_contexts}


_MANAGER: PiRpcManager | None = None


def get_manager() -> PiRpcManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = PiRpcManager()
    return _MANAGER


def resolve_repo_path(repo: str) -> str:
    repo = (repo or "").strip()
    if not repo:
        raise SessionError("repo is required")
    candidate = Path(repo).expanduser()
    if candidate.exists():
        return str(candidate.resolve())
    if repo.startswith("~") or repo.startswith("/") or repo.startswith("."):
        return str(candidate.resolve())
    code_dir = Path.home() / "code" / repo
    if code_dir.exists():
        return str(code_dir.resolve())
    return str(candidate.resolve())


def default_session_name(repo_path: str) -> str:
    folder = Path(repo_path).name or "repo"
    return f"{folder}-{time.strftime('%m%d-%H%M')}"


def current_context_key() -> str:
    session_key = get_session_env("HERMES_SESSION_KEY", "").strip()
    if session_key:
        return session_key
    platform = get_session_env("HERMES_SESSION_PLATFORM", "").strip() or "local"
    chat_id = get_session_env("HERMES_SESSION_CHAT_ID", "").strip()
    thread_id = get_session_env("HERMES_SESSION_THREAD_ID", "").strip()
    user_id = get_session_env("HERMES_SESSION_USER_ID", "").strip()
    parts = [platform, chat_id or "nochat", thread_id or "nothread", user_id or "nouser"]
    return ":".join(parts)


def is_pi_available() -> bool:
    return shutil.which("pi") is not None


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    etype = event.get("type")
    base = {"seq": event.get("_seq"), "type": etype}
    if etype == "message_update":
        inner = event.get("assistantMessageEvent") or {}
        inner_type = inner.get("type")
        base["assistant_event"] = inner_type
        if inner_type in {"text_delta", "thinking_delta"}:
            delta = inner.get("delta") or ""
            if delta:
                base["delta"] = str(delta)[:240]
    elif etype in {"tool_execution_start", "tool_execution_end", "tool_execution_update"}:
        if event.get("toolName"):
            base["tool"] = event.get("toolName")
        if etype == "tool_execution_end":
            base["is_error"] = bool(event.get("isError"))
    elif etype == "extension_ui_request":
        base["method"] = event.get("method")
        if event.get("method") == "notify" and event.get("message"):
            base["message"] = str(event.get("message"))[:240]
    elif etype == "queue_update":
        base["steering"] = len(event.get("steering") or [])
        base["follow_up"] = len(event.get("followUp") or [])
    return base


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    tool_names: list[str] = []
    notifications: list[str] = []
    text_deltas = 0
    thinking_deltas = 0
    for event in events:
        etype = event.get("type")
        if etype == "tool_execution_start":
            name = event.get("toolName")
            if name:
                tool_names.append(str(name))
        elif etype == "message_update":
            inner = event.get("assistantMessageEvent") or {}
            if inner.get("type") == "text_delta":
                text_deltas += 1
            elif inner.get("type") == "thinking_delta":
                thinking_deltas += 1
        elif etype == "extension_ui_request" and event.get("method") == "notify":
            msg = event.get("message")
            if msg:
                notifications.append(str(msg))
    deduped_tools = []
    for name in tool_names:
        if name not in deduped_tools:
            deduped_tools.append(name)
    return {
        "tool_calls": deduped_tools,
        "text_delta_events": text_deltas,
        "thinking_delta_events": thinking_deltas,
        "notifications": notifications[-10:],
        "event_count": len(events),
        "recent": [normalize_event(event) for event in events[-12:]],
    }
