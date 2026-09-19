#!/usr/bin/env python3
"""Merge the managed Paseo daemon config into a live ~/.paseo/config.json.

Merge semantics:
  - objects merge recursively; keys absent from the managed config are preserved
  - daemon.agentProfiles merges by profile name: managed profiles update in
    place, locally added profiles are kept after the managed ones
  - every other list is replaced by the managed value
  - scalars are overwritten by the managed value

The managed config is authoritative for the keys it names; everything else in
the live file (auth state, per-host tweaks, future daemon keys) is left alone.
"""
import json
import os
import shutil
import sys

PROFILES_PATH = ("daemon", "agentProfiles")


def merge_profiles(managed, existing):
    """Merge agentProfiles by name: managed first, then local-only profiles."""
    if not isinstance(managed, list):
        return managed
    if not isinstance(existing, list):
        existing = []
    by_name = {}
    for profile in existing:
        if isinstance(profile, dict) and isinstance(profile.get("name"), str):
            by_name[profile["name"]] = profile
    merged = []
    seen = set()
    for profile in managed:
        if isinstance(profile, dict) and isinstance(profile.get("name"), str):
            name = profile["name"]
            local = by_name.get(name)
            if isinstance(local, dict):
                merged.append(merge_values(local, profile))
            else:
                merged.append(profile)
            seen.add(name)
        else:
            merged.append(profile)
    for profile in existing:
        if isinstance(profile, dict) and isinstance(profile.get("name"), str):
            if profile["name"] not in seen:
                merged.append(profile)
        elif profile not in managed:
            merged.append(profile)
    return merged


def merge_values(existing, managed, path=()):
    if isinstance(managed, dict) and isinstance(existing, dict):
        out = dict(existing)
        for key, value in managed.items():
            out[key] = merge_values(existing.get(key), value, path + (key,))
        return out
    if isinstance(managed, list) and path == PROFILES_PATH:
        return merge_profiles(managed, existing)
    return managed


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <managed-config> <target-config>", file=sys.stderr)
        return 2
    managed_path, target_path = sys.argv[1], sys.argv[2]

    with open(managed_path, "r", encoding="utf-8") as fh:
        managed = json.load(fh)

    existing = {}
    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as fh:
            existing = json.load(fh)
        if not isinstance(existing, dict):
            print(f"error: {target_path} does not contain a JSON object", file=sys.stderr)
            return 1

    merged = merge_values(existing, managed)
    rendered = json.dumps(merged, indent=2) + "\n"

    current = None
    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as fh:
            current = fh.read()
    if current == rendered:
        print(f"Paseo config already current at {target_path}")
        return 0

    if current is not None:
        backup = target_path + ".before-ai-configs"
        if not os.path.exists(backup):
            shutil.copy2(target_path, backup)
            os.chmod(backup, 0o600)
            print(f"Preserved previous Paseo config at {backup}")

    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
    tmp_path = target_path + ".ai-configs-tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(rendered)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, target_path)
    print(f"Installed managed Paseo config at {target_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
