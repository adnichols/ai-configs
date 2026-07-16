import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import hermes_config_sync


def write_jobs(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class CronInstallTest(unittest.TestCase):
    def test_install_preserves_runtime_state_for_top_level_and_profile_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            hermes_home = root / "hermes"

            incoming_job = {
                "id": "matching",
                "prompt": "new prompt",
                "schedule": {"kind": "cron", "expr": "0 9 * * *"},
                "repeat": {"times": 9, "completed": 0},
                "enabled": False,
                "state": "incoming-state",
                "paused_at": None,
                "paused_reason": None,
                "next_run_at": "incoming-next",
                "last_run_at": None,
                "last_status": None,
                "last_error": None,
                "last_delivery_error": None,
                "fire_claim": None,
                "run_claim": None,
                "model": "incoming-model",
                "provider": "incoming-provider",
                "model_snapshot": "incoming-model-snapshot",
                "provider_snapshot": "incoming-provider-snapshot",
                "enabled_toolsets": ["terminal"],
                "workdir": "/incoming/workdir",
                "deliver": "incoming-delivery",
                "origin": {"platform": "incoming"},
            }
            new_job = {
                "id": "new",
                "prompt": "new job",
                "repeat": {"times": 2, "completed": 1},
                "enabled": False,
                "state": "paused",
            }
            write_jobs(
                bundle / "cron" / "jobs.json",
                {"jobs": [incoming_job, new_job], "updated_at": "incoming-updated"},
            )
            write_jobs(
                bundle / "profiles" / "nerd" / "cron" / "jobs.json",
                {
                    "jobs": [{"id": "profile-match", "prompt": "new profile prompt", "repeat": {"times": 4, "completed": 0}}],
                    "updated_at": "incoming-profile-updated",
                },
            )

            runtime_values = {
                "enabled": True,
                "state": "paused",
                "paused_at": "live-paused-at",
                "paused_reason": "live-paused-reason",
                "next_run_at": "live-next",
                "last_run_at": "live-last",
                "last_status": "error",
                "last_error": "live-error",
                "last_delivery_error": "live-delivery-error",
                "fire_claim": {"owner": "live-fire"},
                "run_claim": {"owner": "live-run"},
            }
            existing_job = {
                "id": "matching",
                "prompt": "old prompt",
                "schedule": {"kind": "cron", "expr": "0 1 * * *"},
                "repeat": {"times": 3, "completed": 27},
                "model": "old-model",
                "provider": "old-provider",
                "model_snapshot": "old-model-snapshot",
                "provider_snapshot": "old-provider-snapshot",
                "enabled_toolsets": ["old-toolset"],
                "workdir": "/old/workdir",
                "deliver": "old-delivery",
                "origin": {"platform": "old"},
                **runtime_values,
            }
            write_jobs(
                hermes_home / "cron" / "jobs.json",
                {
                    "jobs": [existing_job, {"id": "orphan", "prompt": "must be removed"}],
                    "updated_at": "live-updated",
                },
            )
            write_jobs(
                hermes_home / "profiles" / "nerd" / "cron" / "jobs.json",
                {
                    "jobs": [
                        {
                            "id": "profile-match",
                            "prompt": "old profile prompt",
                            "repeat": {"times": 1, "completed": 12},
                            "last_status": "live-profile-status",
                        }
                    ],
                    "updated_at": "live-profile-updated",
                },
            )

            original_home = hermes_config_sync.DEFAULT_HERMES_HOME
            hermes_config_sync.DEFAULT_HERMES_HOME = hermes_home
            try:
                with mock.patch.object(
                    hermes_config_sync,
                    "install_cron_jobs",
                    wraps=hermes_config_sync.install_cron_jobs,
                ) as install_cron_jobs:
                    hermes_config_sync.install_all(bundle, hermes_home, dry_run=False)
            finally:
                hermes_config_sync.DEFAULT_HERMES_HOME = original_home

            self.assertEqual(install_cron_jobs.call_count, 2)
            destinations = {call.args[1] for call in install_cron_jobs.call_args_list}
            self.assertEqual(
                destinations,
                {
                    hermes_home / "cron" / "jobs.json",
                    hermes_home / "profiles" / "nerd" / "cron" / "jobs.json",
                },
            )

            installed = json.loads((hermes_home / "cron" / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(installed["updated_at"], "live-updated")
            self.assertEqual([job["id"] for job in installed["jobs"]], ["matching", "new"])
            matching = installed["jobs"][0]
            self.assertEqual(matching["prompt"], "new prompt")
            self.assertEqual(matching["schedule"], incoming_job["schedule"])
            self.assertEqual(matching["repeat"], {"times": 9, "completed": 27})
            for field, value in runtime_values.items():
                self.assertEqual(matching[field], value)
            for field in (
                "model",
                "provider",
                "model_snapshot",
                "provider_snapshot",
                "enabled_toolsets",
                "workdir",
                "deliver",
                "origin",
            ):
                self.assertEqual(matching[field], incoming_job[field])
            self.assertEqual(installed["jobs"][1], new_job)
            self.assertTrue((hermes_home / "cron" / ".jobs.lock").exists())

            profile = json.loads(
                (hermes_home / "profiles" / "nerd" / "cron" / "jobs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(profile["updated_at"], "live-profile-updated")
            self.assertEqual(profile["jobs"][0]["prompt"], "new profile prompt")
            self.assertEqual(profile["jobs"][0]["repeat"], {"times": 4, "completed": 12})
            self.assertEqual(profile["jobs"][0]["last_status"], "live-profile-status")
            self.assertTrue((hermes_home / "profiles" / "nerd" / "cron" / ".jobs.lock").exists())


if __name__ == "__main__":
    unittest.main()
