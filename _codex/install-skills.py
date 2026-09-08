#!/usr/bin/env python3
"""Install the parallel Codex skills and disable their shared counterparts in Codex only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent
BEGIN, END = '# BEGIN ai-configs Codex skill overrides', '# END ai-configs Codex skill overrides'


def install(home, codex):
    manifest = json.loads((ROOT / 'skill-overrides.json').read_text())['skills']
    state_path = codex / 'ai-configs-skills.json'
    previous = json.loads(state_path.read_text()) if state_path.exists() else {'skills': []}
    selected = {n: v for n, v in manifest.items() if v['profile'] == 'default' or (home / '.agents/skills' / n).exists()}
    config = codex / 'config.toml'
    original = config.read_text() if config.exists() else ''
    tomllib.loads(original)
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('Malformed managed config block; refusing to rewrite it')
    retained = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', '', original, flags=re.S).rstrip()
    for name in selected:
        dest = codex / 'skills' / name
        if not (ROOT / 'skills' / name / 'SKILL.md').is_file():
            raise ValueError(f'Missing Codex skill source: {name}')
        if (dest.exists() or dest.is_symlink()) and name not in previous['skills']:
            raise ValueError(f'Unmanaged Codex skill collision: {dest}')
    paths = set()
    for name in selected:
        shared = home / '.agents/skills' / name / 'SKILL.md'
        paths.update([str(shared), str(shared.resolve())])
    entries = ['\n[[skills.config]]\npath = ' + json.dumps(p) + '\nenabled = false\n' for p in sorted(paths)]
    for name in selected:
        entries.append('\n[[skills.config]]\npath = ' + json.dumps(str(codex / 'skills' / name / 'SKILL.md')) + '\nenabled = true\n')
    updated = retained + '\n\n' + BEGIN + '\n' + ''.join(entries) + END + '\n'
    parsed = tomllib.loads(updated)
    before = tomllib.loads(original)
    assert {k: v for k, v in parsed.items() if k != 'skills'} == {k: v for k, v in before.items() if k != 'skills'}
    codex.mkdir(parents=True, exist_ok=True)
    if original != updated and config.exists():
        backup = codex / ('config.toml.before-skills-' + hashlib.sha256(original.encode()).hexdigest()[:12])
        if not backup.exists():
            shutil.copy2(config, backup)
            backup.chmod(0o600)
    files = {}
    for name in selected:
        dest = codex / 'skills' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.ai-configs-', dir=dest.parent) as staging:
            payload = Path(staging) / name
            shutil.copytree(ROOT / 'skills' / name, payload)
            if dest.is_symlink():
                dest.unlink()
            elif dest.exists():
                shutil.rmtree(dest)
            payload.rename(dest)
        for path in dest.rglob('*'):
            if path.is_file():
                files[str(path.relative_to(codex))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in set(previous['skills']) - selected.keys():
        stale = codex / 'skills' / name
        if stale.is_symlink():
            stale.unlink()
        elif stale.exists():
            shutil.rmtree(stale)
    for path, body in [(config, updated), (state_path, json.dumps({'skills': sorted(selected), 'files': files}, indent=2) + '\n')]:
        if not path.exists() or path.read_text() != body:
            temp = path.with_suffix(path.suffix + '.tmp')
            temp.write_text(body)
            temp.chmod(0o600)
            temp.replace(path)
    return {'installed': len(selected), 'codex_home': str(codex), 'shared_paths_disabled': len(paths)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--codex-home', type=Path)
    args = parser.parse_args()
    target = args.codex_home or Path(os.environ.get('CODEX_HOME', str(args.home / '.codex')))
    print(json.dumps(install(args.home.resolve(), target.resolve())))
