---
name: sync-remote-dev-workflow-to-obsidian
description: Inspect a remote development host over SSH, identify the real source-of-truth workflow/config files, and sync a redacted shared bundle into Aaron's Obsidian vault for access by multiple agent instances.
---

# Sync remote dev workflow to Obsidian

Use this when Aaron asks to review a development workflow on another host (for example `dever`) and sync it into a shared Obsidian location accessible by both Hermes instances.

## When to use
- The workflow lives on another machine reachable by SSH.
- Aaron wants a shared, vault-accessible copy rather than a giant full-home sync.
- The target shared location can be `~/Documents/Obsidian/adn_vault/_pi/...` or another vault path Aaron specifies.

## Core pattern
Do **not** assume the remote workflow is stored only in `~/.hermes` or only in runtime directories.

On Aaron's systems, the real source of truth may be:
- a repo such as `~/code/ai-configs/_pi`
- plus runtime config under `~/.pi/agent/`
- plus selected Hermes config from `~/.hermes/config.yaml`

Inspect first, then sync.

## Workflow

### 1. Verify host access and basic tool presence
Run a quick SSH probe first:
```bash
ssh -o BatchMode=yes <host> 'printf "HOST:%s\n" "$(hostname)"; printf "USER:%s\n" "$USER"; printf "HOME:%s\n" "$HOME"; command -v hermes || true; command -v pi || true; command -v codex || true; command -v claude || true'
```

Important finding: `hermes` may not be on PATH even when `~/.hermes/config.yaml` exists. Check files, not just commands.

### 2. Inspect candidate sources and sizes
Check these first:
```bash
ssh <host> 'for p in ~/.hermes ~/.pi ~/code/ai-configs ~/Documents/Obsidian/adn_vault; do if [ -e "$p" ]; then du -sh "$p"; else echo "MISSING $p"; fi; done'
```

Then list focused contents:
```bash
ssh <host> 'find ~/.hermes -maxdepth 2 -mindepth 1 | sort | sed -n "1,80p"'
ssh <host> 'find ~/.pi/agent -maxdepth 2 -mindepth 1 | sort | sed -n "1,120p"'
ssh <host> 'find ~/code/ai-configs/_pi -maxdepth 3 -type f | sort | sed -n "1,240p"'
```

### 3. Determine source of truth
Compare runtime directories to repo-managed config when both exist.

A useful check:
```bash
ssh <host> 'python3 - <<"PY"
from pathlib import Path
import hashlib
pairs=[
 (Path.home()/".pi/agent/agents", Path.home()/"code/ai-configs/_pi/agents"),
 (Path.home()/".pi/agent/prompts", Path.home()/"code/ai-configs/_pi/prompts"),
]
for a,b in pairs:
    print(f"## {a} vs {b}")
    ac={p.relative_to(a).as_posix(): p for p in a.rglob("*") if p.is_file()}
    bc={p.relative_to(b).as_posix(): p for p in b.rglob("*") if p.is_file()}
    same=0; diff=[]
    for k in sorted(set(ac)&set(bc)):
        if hashlib.sha256(ac[k].read_bytes()).hexdigest()==hashlib.sha256(bc[k].read_bytes()).hexdigest():
            same+=1
        else:
            diff.append(k)
    print("count", len(ac), len(bc), "same", same, "diff", len(diff))
    print("sample diff", diff[:20])
PY'
```

If `~/.pi/agent/agents` and `prompts` are byte-identical to `~/code/ai-configs/_pi`, prefer the repo as the source of truth and copy runtime-only files separately.

### 4. Sync into shared vault bundle
Recommended destination pattern:
```text
~/Documents/Obsidian/adn_vault/_pi/<host>-dev-workflow/
```

Copy:
- repo-managed workflow content from `~/code/ai-configs/_pi/`
- runtime config from `~/.pi/agent/`
- selected Hermes config from `~/.hermes/config.yaml`

Practical shell pattern:
```bash
BASE="$HOME/Documents/Obsidian/adn_vault/_pi/<host>-dev-workflow"
rm -r "$BASE" 2>/dev/null || true
mkdir -p "$BASE"

rsync -az <host>:~/code/ai-configs/_pi/agents/ "$BASE/agents"
rsync -az <host>:~/code/ai-configs/_pi/prompts/ "$BASE/prompts"
rsync -az <host>:~/code/ai-configs/_pi/extensions/ "$BASE/extensions"
rsync -az <host>:~/code/ai-configs/_pi/packages/ "$BASE/packages"
scp <host>:~/code/ai-configs/_pi/README.md "$BASE/README.remote.md"

scp <host>:~/.pi/agent/mcp.json "$BASE/runtime-mcp.json"
scp <host>:~/.pi/agent/models.json "$BASE/runtime-models.json"
scp <host>:~/.pi/agent/multi-pass.json "$BASE/runtime-multi-pass.json"
scp <host>:~/.pi/agent/keybindings.json "$BASE/runtime-keybindings.json"
scp <host>:~/.pi/agent/pi-sub-bar-settings.json "$BASE/runtime-pi-sub-bar-settings.json"
scp <host>:~/.pi/agent/pi-sub-core-settings.json "$BASE/runtime-pi-sub-core-settings.json"
scp <host>:~/.hermes/config.yaml "$BASE/hermes.config.<host>.raw.yaml"
```

### 5. Redact secrets before leaving the bundle behind
Redact at least:
- YAML `api_key:` values
- JSON `"apiKey": "..."` values

Example:
```python
from pathlib import Path
import re
base = Path.home()/"Documents/Obsidian/adn_vault/_pi/<host>-dev-workflow"
rt = base/"runtime-config"
rt.mkdir(exist_ok=True)

for src_name, dst_name in {
    "runtime-mcp.json":"mcp.json",
    "runtime-models.json":"models.json",
    "runtime-multi-pass.json":"multi-pass.json",
    "runtime-keybindings.json":"keybindings.json",
    "runtime-pi-sub-bar-settings.json":"pi-sub-bar-settings.json",
    "runtime-pi-sub-core-settings.json":"pi-sub-core-settings.json",
}.items():
    txt = (base/src_name).read_text()
    txt = re.sub(r'("apiKey"\s*:\s*").*?(")', r'\1<redacted>\2', txt)
    (rt/dst_name).write_text(txt)
    (base/src_name).unlink()

hermes = (base/"hermes.config.<host>.raw.yaml").read_text()
hermes = re.sub(r'(^\s*api_key:\s*).*$', r'\1<redacted>', hermes, flags=re.M)
(rt/f"hermes.config.<host>.redacted.yaml").write_text(hermes)
(base/f"hermes.config.<host>.raw.yaml").unlink()
```

### 6. Add documentation and verification
Create:
- `README.md` explaining source, contents, redactions, and install targets
- `manifest.json` with file sizes and sha256 hashes

Also verify size and counts:
```bash
du -sh "$BASE"
python3 - <<'PY'
from pathlib import Path
base=Path.home()/"Documents/Obsidian/adn_vault/_pi/<host>-dev-workflow"
for sub in ["agents","prompts","extensions","packages","runtime-config"]:
    p=base/sub
    print(sub, sum(1 for x in p.rglob('*') if x.is_file()))
PY
```

## Important findings to remember
- SSH inspection may succeed with `ssh`/`scp` from the terminal tool even if sandboxed Python subprocesses cannot authenticate to the same host. If Python-based copy fails with auth errors, fall back to direct terminal `rsync`/`scp`.
- On Aaron's setup, `~/code/ai-configs/_pi` was the durable workflow source and `~/.pi/agent/*` contained runtime material to bundle alongside it.
- Keep the shared copy compact; avoid syncing giant runtime directories like sessions, caches, checkpoints, or full `~/.hermes` trees.
- `packages/` is acceptable if still reasonably small, but confirm total bundle size stays well below Aaron's stated limit.

## Output pattern
Report:
- shared destination path
- what was identified as source of truth
- what was copied
- what was redacted
- total bundle size
- whether it is a snapshot or a live sync
