#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
OBSIDIAN_ROOT = HOME / 'Documents' / 'Obsidian'
VAULTS = [
    OBSIDIAN_ROOT / 'adn_vault',
    OBSIDIAN_ROOT / 'studio',
]
STATE_PATH = HOME / '.hermes' / 'state' / 'obsidian_signal_watch_state.json'
SIGNAL_LOG = HOME / '.hermes' / 'state' / 'obsidian_signal_watch_log.md'

EXCLUDE_PARTS = {
    '.git', '.obsidian', '.trash', '.tmp', 'node_modules', '__pycache__',
    'attachments', 'Assets', 'assets', 'Browsers', '.ruff_cache'
}

PRIORITY_TERMS = [
    'c-core', 'ccore', 'context core', 'hud', 'doct', 'doc t', 'dock t', 'heddle',
    'design partner', 'decision log', 'action tracking', 'nodaste agents'
]

PATH_BOOSTS = {
    'projects': 4,
    'Action Tracking': 4,
    'Nodaste Agents': 3,
    'Meeting Transcripts': 2,
    'reference': 2,
    'writing': 1,
}

MAX_CANDIDATES = 12
MAX_SUMMARY = 5
SKEW_SECONDS = 5


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state):
    ensure_parent(STATE_PATH)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def should_skip(path: Path):
    return any(part in EXCLUDE_PARTS for part in path.parts)


def collect_candidates(since_ts: float):
    candidates = []
    for vault in VAULTS:
        if not vault.exists():
            continue
        for path in vault.rglob('*.md'):
            if should_skip(path):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_mtime <= since_ts:
                continue
            candidates.append((path, stat.st_mtime))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:MAX_CANDIDATES]


def first_content_line(text: str):
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('---'):
            continue
        if ':' in line and len(line) < 80 and line.split(':', 1)[0].isidentifier():
            continue
        return line[:220]
    return ''


def score_candidate(path: Path, text: str):
    path_str = str(path)
    text_l = text.lower()
    score = 0
    reasons = []

    for key, boost in PATH_BOOSTS.items():
        if key.lower() in path_str.lower():
            score += boost
            reasons.append(f'path:{key}')

    for term in PRIORITY_TERMS:
        hits = text_l.count(term) + path_str.lower().count(term)
        if hits:
            add = min(6, hits * 2)
            score += add
            reasons.append(f'term:{term}')

    if '# ' in text[:200]:
        score += 1

    if 'decision' in text_l or 'design partner' in text_l or 'release' in text_l:
        score += 2

    return score, reasons


def analyze_candidates(candidates):
    enriched = []
    for path, mtime in candidates:
        try:
            text = path.read_text(errors='ignore')
        except Exception:
            continue
        score, reasons = score_candidate(path, text)
        excerpt = first_content_line(text)
        rel = path.relative_to(OBSIDIAN_ROOT)
        enriched.append({
            'path': str(rel),
            'mtime': mtime,
            'iso_time': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'score': score,
            'reasons': reasons[:6],
            'excerpt': excerpt,
        })
    enriched.sort(key=lambda x: (x['score'], x['mtime']), reverse=True)
    return enriched


def is_signal(items):
    if not items:
        return False
    top = items[0]
    if top['score'] >= 6:
        return True
    if len(items) >= 3 and sum(1 for i in items[:5] if i['score'] >= 3) >= 3:
        return True
    return False


def append_log(report: str):
    ensure_parent(SIGNAL_LOG)
    with SIGNAL_LOG.open('a') as f:
        f.write(report + '\n\n')


def build_report(items):
    top = items[:MAX_SUMMARY]
    headline_paths = ', '.join(item['path'] for item in top[:3])
    lines = [f'SIGNAL: Obsidian signal detected - {headline_paths}']
    for item in top:
        reason_str = ', '.join(item['reasons']) if item['reasons'] else 'recently modified'
        excerpt = f" — {item['excerpt']}" if item['excerpt'] else ''
        lines.append(f"- {item['path']} [{item['iso_time']}] ({reason_str}){excerpt}")
    return '\n'.join(lines)


def main():
    now = time.time()
    state = load_state()

    if 'last_scan' not in state:
        state['last_scan'] = now
        save_state(state)
        return

    since_ts = max(0, float(state.get('last_scan', now)) - SKEW_SECONDS)
    candidates = collect_candidates(since_ts)
    items = analyze_candidates(candidates)

    state['last_scan'] = now
    save_state(state)

    if not is_signal(items):
        return

    report = build_report(items)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    append_log(f'## {timestamp}\n\n{report}')
    print(report)


if __name__ == '__main__':
    main()
