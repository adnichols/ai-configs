#!/usr/bin/env python3
"""Launch OMP the way verified-build pins: Paseo profile named omp in a worktree.

create_workspace (worktree) then paseo run with the omp row materialized.
Asserts provider, profile model, profile mode, and Paseo worktree cwd.
Cleans up the workspace unless --keep is set.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, text=True, capture_output=True, cwd=cwd)


def must_ok(proc: subprocess.CompletedProcess[str], what: str) -> str:
    if proc.returncode != 0:
        sys.stderr.write(f"{what} failed ({proc.returncode})\n{proc.stderr}\n")
        raise SystemExit(1)
    return proc.stdout


def normalize_model(value: str) -> str:
    return (value or "").split(":", 1)[0]


def named_omp_profile() -> dict:
    path = Path.home() / ".paseo" / "config.json"
    if not path.is_file():
        raise SystemExit("fail-closed: ~/.paseo/config.json missing")
    data = json.loads(path.read_text())
    profiles = ((data.get("daemon") or {}).get("agentProfiles")) or []
    for profile in profiles:
        if isinstance(profile, dict) and profile.get("name") == "omp":
            if profile.get("provider") != "omp" or not profile.get("model") or not profile.get("modeId"):
                raise SystemExit(f"fail-closed: omp profile incomplete: {profile}")
            return profile
    raise SystemExit("fail-closed: Paseo profile named omp missing")


def make_repo() -> tuple[Path, str]:
    tmp = Path(tempfile.mkdtemp(prefix="vb-omp-eval-"))
    must_ok(run(["git", "init", "-q"], cwd=tmp), "git init")
    must_ok(run(["git", "config", "user.email", "eval@example.com"], cwd=tmp), "git email")
    must_ok(run(["git", "config", "user.name", "eval"], cwd=tmp), "git name")
    (tmp / "README").write_text("eval\n")
    must_ok(run(["git", "add", "README"], cwd=tmp), "git add")
    must_ok(run(["git", "commit", "-q", "-m", "init"], cwd=tmp), "git commit")
    sha = must_ok(run(["git", "rev-parse", "HEAD"], cwd=tmp), "git rev-parse").strip()
    return tmp, sha


def workspace_id_from_create(payload: dict) -> str:
    for key in ("workspaceId", "id", "Id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    nested = payload.get("workspace")
    if isinstance(nested, dict):
        for key in ("workspaceId", "id", "Id"):
            value = nested.get(key)
            if isinstance(value, str) and value:
                return value
    raise SystemExit(f"workspace create missing id: {payload}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    profile = named_omp_profile()
    expected_model = str(profile["model"])
    expected_mode = str(profile["modeId"])
    thinking = profile.get("thinkingOptionId")
    repo, sha = make_repo()
    branch = "vb-omp-eval"
    prompt = "Reply with only the word PONG and stop. Do not edit files."
    workspace_id = None
    agent_id = None
    try:
        created = json.loads(
            must_ok(
                run(
                    [
                        "paseo",
                        "workspace",
                        "create",
                        "--json",
                        "--isolation",
                        "worktree",
                        "--mode",
                        "branch-off",
                        "--base",
                        sha,
                        "--new-branch",
                        branch,
                        "--path",
                        str(repo),
                        "--title",
                        "vb-omp-eval",
                    ]
                ),
                "paseo workspace create",
            )
        )
        workspace_id = workspace_id_from_create(created)
        launch = [
            "paseo",
            "run",
            "-d",
            "--json",
            "--workspace",
            workspace_id,
            "--title",
            "vb-omp-eval",
            "--provider",
            f"omp/{expected_model}",
            "--mode",
            expected_mode,
        ]
        if isinstance(thinking, str) and thinking:
            launch.extend(["--thinking", thinking])
        launch.append(prompt)
        launched = json.loads(must_ok(run(launch), "paseo run"))
        agent_id = launched.get("agentId")
        if not agent_id:
            raise SystemExit(f"paseo run missing agentId: {launched}")
        inspect = json.loads(
            must_ok(run(["paseo", "inspect", "--json", str(agent_id)]), "paseo inspect")
        )
        provider = inspect.get("Provider")
        model = inspect.get("Model")
        mode = inspect.get("Mode")
        inspect_cwd = inspect.get("Cwd") or launched.get("cwd")
        worktree_root = str(Path.home() / ".paseo" / "worktrees")
        listing = json.loads(must_ok(run(["paseo", "workspace", "ls", "--json"]), "workspace ls"))
        ws = next((item for item in listing if item.get("workspaceId") == workspace_id), None)
        failures: list[str] = []
        if provider != "omp":
            failures.append(f"provider {provider!r} != 'omp'")
        if normalize_model(str(model or "")) != normalize_model(expected_model):
            failures.append(f"model {model!r} != omp profile {expected_model!r}")
        if mode != expected_mode:
            failures.append(f"mode {mode!r} != omp profile {expected_mode!r}")
        if not str(inspect_cwd or "").startswith(worktree_root):
            failures.append(f"cwd {inspect_cwd!r} is not a Paseo worktree")
        if ws is not None and ws.get("isolation") != "worktree":
            failures.append(f"workspace isolation {ws.get('isolation')!r} != 'worktree'")
        report = {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "provider": provider,
            "model": model,
            "mode": mode,
            "cwd": inspect_cwd,
            "ompProfile": {
                "model": expected_model,
                "modeId": expected_mode,
                "thinkingOptionId": thinking,
            },
            "workspace": ws,
        }
        print(json.dumps(report, indent=2))
        if failures:
            for item in failures:
                sys.stderr.write(f"FAIL: {item}\n")
            return 1
        print("PASS")
        return 0
    finally:
        if not args.keep:
            if workspace_id:
                run(["paseo", "workspace", "archive", workspace_id])
            elif agent_id:
                run(["paseo", "archive", str(agent_id)])
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
