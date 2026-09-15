#!/usr/bin/env python3
"""Sync managed Codex prompts, preserving custom files and backing up replacements."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(destination):
    destination.mkdir(parents=True, exist_ok=True)
    state = destination.parent / 'ai-configs-prompts.json'
    previous = json.loads(state.read_text()) if state.exists() else {}
    legacy = json.loads((ROOT / 'prompt-provenance.json').read_text())
    source = {p.name: p for p in (ROOT / 'prompts').glob('*.md')}
    managed, preserved, removed = {}, [], []
    backup = None
    for name in sorted(source.keys() | previous.keys() | legacy.keys()):
        if Path(name).name != name or not name.endswith('.md'):
            raise ValueError(f'Invalid managed prompt name: {name}')
        target = destination / name
        expected = previous.get(name, legacy.get(name))
        incoming = digest(source[name]) if name in source else None
        if target.is_symlink() or (target.exists() and not target.is_file()):
            preserved.append(name)
            continue
        current = digest(target) if target.exists() else None
        if current is not None and current not in (expected, incoming):
            preserved.append(name)
            continue
        if current != incoming:
            if current is not None:
                if backup is None:
                    backup = Path(tempfile.mkdtemp(prefix='prompts-backup-', dir=destination.parent))
                shutil.copy2(target, backup / name)
            if incoming is None:
                target.unlink()
                removed.append(name)
            else:
                shutil.copy2(source[name], target)
        if incoming is not None:
            managed[name] = incoming
    state.write_text(json.dumps(managed, indent=2) + '\n')
    return {'installed': len(managed), 'removed': removed, 'preserved': preserved,
            'backup': str(backup) if backup else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    print(json.dumps(install(parser.parse_args().destination)))
