#!/opt/homebrew/bin/python3
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from urllib import error, request

HOME = Path.home()
STUDIO_ROOT = HOME / 'Documents' / 'Obsidian' / 'studio'
INBOX = STUDIO_ROOT / 'Nodaste Agents' / 'Signals' / 'inbox' / 'aaron'
STATE_DIR = HOME / '.hermes' / 'watchers' / 'aaron-realtime'
LOCK_PATH = STATE_DIR / 'watcher.lock'
LOG_PATH = STATE_DIR / 'watcher.log'
SEEN_PATH = STATE_DIR / 'dispatched_signals.json'
WEBHOOK_URL = 'http://127.0.0.1:8644/webhooks/aaron-signal'
WEBHOOK_SECRET = '0d09bc8dd4ab8212a582f0c5d637aac40b66c745f430e81c3dc3d6cb0064a52c'
DISCORD_CHANNEL_ID = '1492535022811480126'
DISCORD_API_BASE = 'https://discord.com/api/v10'
EVENT_TYPE = 'obsidian_signal'
SIG_PREFIX = 'SIG-'
PRIORITY_ORDER = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as fh:
        fh.write(f'[{now()}] {message}\n')


def parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding='utf-8')
    except Exception as exc:
        log(f'Failed to read {path.name}: {exc}')
        return {}
    if not text.startswith('---\n'):
        return {}
    parts = text.split('---\n', 2)
    if len(parts) < 3:
        return {}
    out: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        out[key.strip()] = value.strip()
    return out


def candidate_sort_key(item: tuple[Path, dict[str, str]]) -> tuple:
    path, fm = item
    priority = PRIORITY_ORDER.get(fm.get('priority', 'medium').lower(), 2)
    due_at = fm.get('due_at', 'null')
    created_at = fm.get('created_at', '')
    return (priority, due_at if due_at != 'null' else '9999', created_at, path.name)


def load_seen() -> dict[str, dict[str, str]]:
    if not SEEN_PATH.exists():
        return {}
    try:
        data = json.loads(SEEN_PATH.read_text(encoding='utf-8'))
    except Exception as exc:
        log(f'Failed to load seen state: {exc}')
        return {}
    return data if isinstance(data, dict) else {}


def save_seen(data: dict[str, dict[str, str]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')


def load_env_value(name: str) -> str:
    value = os.environ.get(name, '').strip()
    if value:
        return value
    env_path = HOME / '.hermes' / '.env'
    if not env_path.exists():
        return ''
    try:
        for line in env_path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue
            key, raw = stripped.split('=', 1)
            if key.strip() == name:
                return raw.strip().strip('"').strip("'")
    except Exception as exc:
        log(f'Failed to read {env_path}: {exc}')
    return ''


def discord_api_request(method: str, url: str, *, token: str, payload: dict | None = None) -> dict:
    headers = {
        'Authorization': f'Bot {token}',
        'Content-Type': 'application/json',
    }
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode('utf-8', errors='replace')
        return json.loads(raw) if raw else {}


def create_discord_thread(signal_path: Path, fm: dict[str, str]) -> tuple[bool, str, str]:
    token = load_env_value('DISCORD_BOT_TOKEN')
    if not token:
        return False, '', 'Missing DISCORD_BOT_TOKEN'

    signal_id = fm.get('signal_id', signal_path.stem)
    summary = fm.get('summary', '').strip()
    priority = fm.get('priority', '').strip() or 'unknown'
    seed_lines = [
        '🔔 New Aaron signal detected',
        f'signal_id: {signal_id}',
        f'from_agent: {fm.get("from_agent", "")}',
        f'priority: {priority}',
    ]
    if summary:
        seed_lines.append(f'summary: {summary}')
    seed_content = '\n'.join(seed_lines)

    try:
        seed = discord_api_request(
            'POST',
            f'{DISCORD_API_BASE}/channels/{DISCORD_CHANNEL_ID}/messages',
            token=token,
            payload={'content': seed_content},
        )
        seed_id = str(seed.get('id') or '')
        if not seed_id:
            return False, '', f'No message id in Discord seed response: {seed}'
        thread = discord_api_request(
            'POST',
            f'{DISCORD_API_BASE}/channels/{DISCORD_CHANNEL_ID}/messages/{seed_id}/threads',
            token=token,
            payload={
                'name': signal_id[:100],
                'auto_archive_duration': 1440,
            },
        )
        thread_id = str(thread.get('id') or '')
        if not thread_id:
            return False, '', f'No thread id in Discord thread response: {thread}'
        return True, thread_id, f'thread_id={thread_id} seed_message_id={seed_id}'
    except error.HTTPError as exc:
        body_text = exc.read().decode('utf-8', errors='replace')
        return False, '', f'Discord HTTP {exc.code}: {body_text}'
    except Exception as exc:
        return False, '', f'Discord {type(exc).__name__}: {exc}'


def build_payload(signal_path: Path, fm: dict[str, str], thread_id: str) -> dict[str, str]:
    return {
        'event_type': EVENT_TYPE,
        'signal_path': str(signal_path),
        'signal_id': fm.get('signal_id', signal_path.stem),
        'signal_type': fm.get('signal_type', ''),
        'priority': fm.get('priority', ''),
        'status': fm.get('status', ''),
        'summary': fm.get('summary', ''),
        'from_agent': fm.get('from_agent', ''),
        'to_agent': fm.get('to_agent', ''),
        'created_at': fm.get('created_at', ''),
        'thread_id': thread_id,
    }


def post_signal_webhook(signal_path: Path, fm: dict[str, str], thread_id: str) -> tuple[bool, str]:
    payload = build_payload(signal_path, fm, thread_id)
    body = json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode('utf-8'), body, hashlib.sha256
    ).hexdigest()
    delivery_id = f"{payload['signal_id']}:{int(signal_path.stat().st_mtime_ns)}"
    req = request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'X-GitHub-Event': EVENT_TYPE,
            'X-Hub-Signature-256': signature,
            'X-GitHub-Delivery': delivery_id,
        },
        method='POST',
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            status = getattr(resp, 'status', 200)
    except error.HTTPError as exc:
        body_text = exc.read().decode('utf-8', errors='replace')
        return False, f'HTTP {exc.code}: {body_text}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'

    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = {'raw': raw}

    if status not in (200, 202):
        return False, f'Unexpected status {status}: {parsed}'
    return True, f"status={status} response={parsed}"


def find_new_signals(seen: dict[str, dict[str, str]]) -> tuple[list[tuple[Path, dict[str, str]]], dict[str, dict[str, str]]]:
    candidates: list[tuple[Path, dict[str, str]]] = []
    if not INBOX.exists():
        return candidates, seen

    active_paths: set[str] = set()
    for path in INBOX.iterdir():
        if not path.is_file() or not path.name.startswith(SIG_PREFIX) or path.suffix.lower() != '.md':
            continue
        active_paths.add(str(path))
        fm = parse_frontmatter(path)
        status = fm.get('status')
        if status == 'new':
            if str(path) not in seen:
                candidates.append((path, fm))
        else:
            seen.pop(str(path), None)

    stale = [p for p in seen if p not in active_paths]
    for path_str in stale:
        seen.pop(path_str, None)

    candidates.sort(key=candidate_sort_key)
    return candidates, seen


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('w') as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log('Skipped run: watcher already active')
            return 0

        seen = load_seen()
        candidates, seen = find_new_signals(seen)
        if not candidates:
            save_seen(seen)
            return 0

        log(f'Found {len(candidates)} unnotified new signal(s) in {INBOX}')
        exit_code = 0
        for signal_path, fm in candidates:
            log(f'Creating Discord thread for {signal_path.name}')
            thread_ok, thread_id, thread_detail = create_discord_thread(signal_path, fm)
            if not thread_ok:
                exit_code = 1
                log(f'Discord thread creation failed for {signal_path.name}: {thread_detail}')
                continue

            log(f'Posting {signal_path.name} to webhook bridge for thread {thread_id}')
            ok, detail = post_signal_webhook(signal_path, fm, thread_id)
            if ok:
                seen[str(signal_path)] = {
                    'signal_id': fm.get('signal_id', signal_path.stem),
                    'thread_id': thread_id,
                    'notified_at': now(),
                }
                log(f'Webhook accepted {signal_path.name}: {detail}; {thread_detail}')
            else:
                exit_code = 1
                log(f'Webhook failed for {signal_path.name}: {detail}; thread={thread_id}')
        save_seen(seen)
        return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
