from __future__ import annotations

import json
import logging
from typing import Any

from .client import (
    DEFAULT_TOOLS,
    SessionError,
    current_context_key,
    get_manager,
    is_pi_available,
)

logger = logging.getLogger(__name__)

PI_RPC_SESSION_SCHEMA = {
    "name": "pi_rpc_session",
    "description": (
        "Relay to or inspect an existing pi RPC session. For Aaron's observable coding workflow, "
        "direct headless starts are disabled — launch pi in tmux first, then use this tool only for bridge/maintenance actions if explicitly needed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "send", "status", "abort", "stop", "list", "bind", "unbind"],
                "description": "What to do with the pi RPC session."
            },
            "repo": {
                "type": "string",
                "description": "Repo name under ~/code or an explicit path. Required for action='start'."
            },
            "session_id": {
                "type": "string",
                "description": "Optional pi session id. If omitted, the tool uses the current thread's bound session when available."
            },
            "message": {
                "type": "string",
                "description": "Message to relay to pi. Required for action='send'."
            },
            "mode": {
                "type": "string",
                "enum": ["prompt", "steer", "follow_up"],
                "description": "How to deliver the message to pi. Use 'prompt' for normal messages, 'steer' to interrupt current work, 'follow_up' to queue after completion. Default: prompt."
            },
            "display_name": {
                "type": "string",
                "description": "Optional human-readable pi session name to set inside pi."
            },
            "provider": {
                "type": "string",
                "description": "Optional pi provider override, e.g. anthropic or openai."
            },
            "model": {
                "type": "string",
                "description": "Optional pi model override."
            },
            "thinking": {
                "type": "string",
                "enum": ["off", "minimal", "low", "medium", "high", "xhigh"],
                "description": "Optional pi thinking level."
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional explicit pi tool list. Defaults to read,bash,edit,write,grep,find,ls."
            },
            "bind_to_current_thread": {
                "type": "boolean",
                "description": "When starting or binding, attach the pi session to the current Hermes chat/thread context. Default: true."
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "How long to wait for pi to finish processing a relayed message. Default: 1800."
            },
            "remove_binding": {
                "type": "boolean",
                "description": "When stopping, remove any thread bindings for the session. Default: true."
            }
        },
        "required": ["action"]
    }
}


def _success(**data: Any) -> str:
    payload = {"ok": True}
    payload.update(data)
    return json.dumps(payload)



def _error(message: str, **data: Any) -> str:
    payload = {"ok": False, "error": message}
    payload.update(data)
    return json.dumps(payload)



def _tool_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    manager = get_manager()
    action = (args.get("action") or "").strip().lower()
    current_context = current_context_key()
    session_id = (args.get("session_id") or "").strip() or None
    bind_to_current_thread = args.get("bind_to_current_thread")
    if bind_to_current_thread is None:
        bind_to_current_thread = True
    try:
        if action == "start":
            return _error(
                "Direct pi RPC starts are disabled for Aaron's workflow. Launch pi in tmux first (for example with ~/.hermes/scripts/launch_pi_tmux.sh or the tmux-based pi workflow skills), then use bridge/status actions only if explicitly needed."
            )

        if action == "send":
            message = args.get("message") or ""
            if not str(message).strip():
                return _error("message is required for action='send'")
            result = manager.send(
                message=str(message),
                mode=(args.get("mode") or "prompt").strip() or "prompt",
                session_id=session_id,
                current_context=current_context,
                timeout=float(args.get("timeout_seconds") or 1800),
            )
            return _success(action=action, **result)

        if action == "status":
            result = manager.status(session_id=session_id, current_context=current_context)
            return _success(action=action, **result)

        if action == "abort":
            result = manager.abort(session_id=session_id, current_context=current_context)
            return _success(action=action, **result)

        if action == "stop":
            result = manager.stop(
                session_id=session_id,
                current_context=current_context,
                remove_binding=bool(args.get("remove_binding", True)),
            )
            return _success(action=action, **result)

        if action == "list":
            result = manager.list_sessions(current_context=current_context)
            return _success(action=action, **result)

        if action == "bind":
            if not session_id:
                return _error("session_id is required for action='bind'")
            result = manager.bind(session_id=session_id, context_key=current_context)
            return _success(action=action, **result)

        if action == "unbind":
            result = manager.unbind(context_key=current_context)
            return _success(action=action, **result)

        return _error(f"Unknown action: {action}")
    except SessionError as exc:
        return _error(str(exc), action=action, session_id=session_id, current_context=current_context)
    except Exception as exc:
        logger.exception("pi_rpc_session failed")
        return _error(f"Unexpected error: {type(exc).__name__}: {exc}", action=action)



def _pre_llm_call_hook(**kwargs: Any):
    manager = get_manager()
    manager.cleanup_dead_sessions()
    context_key = current_context_key()
    binding = manager.list_sessions(current_context=context_key).get("current_binding")
    if not binding:
        return None
    user_message = (kwargs.get("user_message") or "").strip()
    if not user_message:
        return None
    lowered = user_message.lower()
    if lowered.startswith("/help") or lowered.startswith("/model") or lowered.startswith("/status"):
        return None
    try:
        session = manager.get_session(session_id=binding)
    except Exception:
        return None
    return {
        "context": (
            f"[pi-rpc bridge] This Hermes chat is currently bound to pi session {session.session_id} "
            f"({session.display_name}) for repo {session.repo_path}. "
            "For Aaron's workflow, pi should be launched in tmux first so it is visible live. "
            "Use this bridge only for relay/maintenance actions on an already-established session. "
            "If the user is continuing work in that pi session, relay the message with pi_rpc_session action='send'. "
            "Use mode='steer' when the user wants to interrupt or redirect the current run; otherwise use mode='prompt'. "
            "If the user is asking to inspect the bridge itself, manage bindings, or stop pi, use the corresponding pi_rpc_session management action instead."
        )
    }



def register(ctx) -> None:
    ctx.register_tool(
        name="pi_rpc_session",
        toolset="pi_rpc",
        schema=PI_RPC_SESSION_SCHEMA,
        handler=_tool_handler,
        check_fn=is_pi_available,
        description=PI_RPC_SESSION_SCHEMA["description"],
        emoji="🧠",
    )
    ctx.register_hook("pre_llm_call", _pre_llm_call_hook)
