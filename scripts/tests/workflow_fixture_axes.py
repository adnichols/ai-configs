"""Explicit environment axes shared by workflow integration fixtures."""

import os
from pathlib import Path

AXIS_KEYS = {
    "hub_state": "AI_CONFIGS_TEST_HUB_STATE",
    "profile_root": "AI_CONFIGS_TEST_PROFILE_ROOT",
    "transport_result": "AI_CONFIGS_TEST_TRANSPORT_RESULT",
}
INHERITED_KEYS = {
    *AXIS_KEYS.values(),
    "HERDR_HUB_STATE",
    "HERDR_PROFILE",
    "PI_CODING_AGENT_DIR",
    "TARGET_CHECKOUT",
}


def workflow_fixture_env(*, home, hub_state=None, profile_root=None, transport_result=None, base=None):
    axes = {
        "hub_state": hub_state,
        "profile_root": str(Path(profile_root)) if profile_root is not None else None,
        "transport_result": transport_result,
    }
    missing = [name for name, value in axes.items() if value is None or value == ""]
    if missing:
        raise ValueError("workflow fixture missing explicit axis: %s" % ", ".join(missing))
    if hub_state not in {"available", "unavailable", "degraded"}:
        raise ValueError("workflow fixture has invalid Hub state: %s" % hub_state)
    if transport_result not in {"pass", "fail", "mixed"}:
        raise ValueError("workflow fixture has invalid transport result: %s" % transport_result)
    env = dict(os.environ if base is None else base)
    for key in INHERITED_KEYS:
        env.pop(key, None)
    env["HOME"] = str(Path(home))
    for name, key in AXIS_KEYS.items():
        env[key] = axes[name]
    return env
