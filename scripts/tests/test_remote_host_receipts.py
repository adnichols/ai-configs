import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tests.workflow_fixture_axes import workflow_fixture_env

ROOT = Path(__file__).resolve().parents[2]


class RemoteHostReceiptTest(unittest.TestCase):
    def fixture(self, root: Path):
        for relative in (
            "scripts/install-kitty-remote-hosts.sh", "scripts/pi_review_stack_contract.py",
            "scripts/pi-review-stack-managed-surfaces.json", "scripts/probe_pi_review_transport.py",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copytree(ROOT / "_pi/agents", root / "_pi/agents")
        manifest = json.loads((root / "scripts/pi-review-stack-managed-surfaces.json").read_text())
        for item in manifest["surfaces"]:
            source = item.get("source")
            if not source:
                continue
            target = root / source
            if target.exists():
                continue
            if item["kind"] in {"exact-directory", "overlay-children"}:
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("{}\n" if item["kind"] == "json-merge" else "fixture\n")
        for name in ("herdr", "kitty"):
            script = root / name / "install.sh"
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text("""#!/usr/bin/env bash
set -euo pipefail
root=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"
package=\"$HOME/.pi/agent/npm/node_modules/@tintinweb/pi-subagents\"
mkdir -p \"$package/src\" \"$package/dist\" \"$HOME/.pi/agent/agents\"
printf '%s\\n' 'isolation: agentConfig?.isolation ?? params.isolation,' >\"$package/src/invocation-config.ts\"
printf '%s\\n' 'isolation: agentConfig?.isolation ?? params.isolation,' >\"$package/dist/invocation-config.js\"
cp \"$root/_pi/agents/planner.md\" \"$root/_pi/agents/reviewer.md\" \"$HOME/.pi/agent/agents/\"
""")
            script.chmod(0o755)
        for name in ("clipssh", "kitty-paste-image-to-ssh"):
            script = root / "scripts" / name
            script.write_text("#!/usr/bin/env bash\nexit 0\n")
        fake = root / "fake-bin" / "ssh"
        fake.parent.mkdir(parents=True)
        fake.write_text("""#!/usr/bin/env bash
set -euo pipefail
host=\"${@: -2:1}\"; command=\"${!#}\"
[[ \"$host\" != offline ]] || exit 44
bash -c \"$command\"
""")
        fake.chmod(0o755)
        return fake.parent

    def run_case(self, strict: bool):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"; root.mkdir()
            fake_bin = self.fixture(root)
            home = Path(temp) / "home"; home.mkdir()
            package = home / ".pi/agent/npm/node_modules/@tintinweb/pi-subagents"
            for relative in ("src/invocation-config.ts", "dist/invocation-config.js"):
                target=package/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text("isolation: agentConfig?.isolation ?? params.isolation,\n")
            agents=home/".pi/agent/agents";agents.mkdir(parents=True)
            for name in ("planner.md","reviewer.md"): shutil.copy2(root/"_pi/agents"/name,agents/name)
            receipt = Path(temp) / "receipt.json"
            env = workflow_fixture_env(home=home, hub_state="unavailable", profile_root=home / ".config", transport_result="mixed")
            env.update({"PATH": str(fake_bin) + os.pathsep + env["PATH"], "KITTY_REMOTE_HOSTS": "online online offline"})
            command = ["bash", str(root / "scripts/install-kitty-remote-hosts.sh")]
            if strict: command.append("--strict")
            command += ["--summary-json", str(receipt)]
            result = subprocess.run(command, env=env, text=True, capture_output=True)
            payload = json.loads(receipt.read_text())
            self.assertEqual(1 if strict else 0, result.returncode, result.stderr)
            self.assertEqual("failed" if strict else "partial", payload["status"])
            self.assertEqual("remote-kitty", payload["mode"])
            self.assertEqual("fail", payload["transportProbe"]["status"])
            self.assertEqual(["online", "offline"], [item["host"] for item in payload["hosts"]])
            self.assertEqual(["success", "failed"], [item["status"] for item in payload["hosts"]])
            self.assertTrue(payload["hosts"][0]["cwd"].startswith("/"))
            self.assertEqual(0o600, stat.S_IMODE(receipt.stat().st_mode))

    def test_strict_and_best_effort_receipts(self):
        self.run_case(True)
        self.run_case(False)

    def test_fixture_axes_reject_omission_and_override_hostile_environment(self):
        hostile = {"AI_CONFIGS_TEST_HUB_STATE": "available", "AI_CONFIGS_TEST_PROFILE_ROOT": "/wrong", "AI_CONFIGS_TEST_TRANSPORT_RESULT": "pass", "HERDR_PROFILE": "wrong"}
        with self.assertRaisesRegex(ValueError, "transport_result"):
            workflow_fixture_env(home="/tmp/home", hub_state="unavailable", profile_root="/tmp/profile", base=hostile)
        env = workflow_fixture_env(home="/tmp/home", hub_state="degraded", profile_root="/tmp/profile", transport_result="fail", base=hostile)
        self.assertEqual("degraded", env["AI_CONFIGS_TEST_HUB_STATE"])
        self.assertEqual("/tmp/profile", env["AI_CONFIGS_TEST_PROFILE_ROOT"])
        self.assertEqual("fail", env["AI_CONFIGS_TEST_TRANSPORT_RESULT"])
        self.assertNotIn("HERDR_PROFILE", env)


if __name__ == "__main__":
    unittest.main()
