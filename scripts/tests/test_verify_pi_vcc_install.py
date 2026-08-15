import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts/verify-pi-vcc-install.sh"
EXTENSION = ROOT / "_pi/extensions/percentage-compaction.ts"


def make_package(path: Path, marker: str = "candidate") -> Path:
    (path / "src/core").mkdir(parents=True)
    (path / "package.json").write_text(json.dumps({"name": "@test/pi-vcc"}) + "\n")
    (path / "index.ts").write_text("export default function extension() {}\n")
    (path / "src/hooks").mkdir(parents=True, exist_ok=True)
    (path / "src/hooks/before-compact.ts").write_text(f"export const marker = {marker!r};\n")
    (path / "src/core/custom-message-classifier.ts").write_text("export const classifier = true;\n")
    return path


def fake_environment(root: Path) -> tuple[dict[str, str], Path]:
    root = root.resolve()
    home = root / "home"
    agent = home / ".pi/agent"
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    for name, body in {
        "pi": "#!/bin/sh\n[ \"$1\" = --version ] && echo 'pi test' && exit 0\nexit 0\n",
        "bun": "#!/bin/sh\nexit 0\n",
    }.items():
        executable = bin_dir / name
        executable.write_text(body)
        executable.chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(home),
        "PI_CODING_AGENT_DIR": str(agent),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
    }
    return env, agent


class VerifyPiVccInstallTest(unittest.TestCase):
    def run_verify(self, env, *args, check=False):
        return subprocess.run(
            ["bash", str(VERIFY), *map(str, args)], cwd=ROOT, env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check,
            timeout=600,
        )

    def install_fixture(self, root: Path, package: Path):
        env, agent = fake_environment(root)
        stable = agent / "local-packages/ai-configs/pi-vcc"
        shutil.copytree(package, stable, copy_function=shutil.copy2)
        live_extension = agent / "extensions/percentage-compaction.ts"
        live_extension.parent.mkdir(parents=True)
        shutil.copy2(EXTENSION, live_extension)
        (agent / "settings.json").write_text(json.dumps({"packages": [str(stable)], "extensions": []}) + "\n")
        return env, agent, stable

    def test_source_only_json_uses_expected_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "rollback", "rollback")
            env, _agent = fake_environment(root)
            result = self.run_verify(env, "--source-only", "--expected-package", package, "--json", check=True)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["sourcePackagePath"], str(package))
            self.assertRegex(payload["sourcePackageHash"], r"^[0-9a-f]{64}$")
            self.assertNotIn("stablePackageHash", payload)

    def test_installed_json_reports_equal_expected_and_stable_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "candidate")
            env, _agent, stable = self.install_fixture(root, package)
            result = self.run_verify(env, "--expected-package", package, "--json", check=True)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["sourcePackageHash"], payload["stablePackageHash"])
            self.assertEqual(payload["stablePackagePath"], str(stable))

    def test_content_and_permission_mode_change_tree_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "candidate")
            env, _agent = fake_environment(root)
            first = json.loads(self.run_verify(env, "--source-only", "--expected-package", package, "--json", check=True).stdout)
            hook = package / "src/hooks/before-compact.ts"
            hook.write_text("export const marker = 'changed';\n")
            second = json.loads(self.run_verify(env, "--source-only", "--expected-package", package, "--json", check=True).stdout)
            self.assertNotEqual(first["sourcePackageHash"], second["sourcePackageHash"])
            before_mode = second["sourcePackageHash"]
            hook.chmod(stat.S_IMODE(hook.stat().st_mode) ^ stat.S_IXUSR)
            third = json.loads(self.run_verify(env, "--source-only", "--expected-package", package, "--json", check=True).stdout)
            self.assertNotEqual(before_mode, third["sourcePackageHash"])

    def test_checkout_umask_bits_do_not_change_portable_tree_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_package = make_package(root / "first")
            second_package = root / "second"
            shutil.copytree(first_package, second_package)
            for path in [second_package, *second_package.rglob("*")]:
                mode = stat.S_IMODE(path.stat().st_mode)
                path.chmod(mode | stat.S_IWGRP)
            env, _agent = fake_environment(root)
            first_hash = json.loads(self.run_verify(
                env, "--source-only", "--expected-package", first_package, "--json", check=True,
            ).stdout)["sourcePackageHash"]
            second_hash = json.loads(self.run_verify(
                env, "--source-only", "--expected-package", second_package, "--json", check=True,
            ).stdout)["sourcePackageHash"]
            self.assertEqual(first_hash, second_hash)

    def test_symlink_special_entry_and_node_modules_are_rejected(self):
        for entry_type in ("file-symlink", "directory-symlink", "fifo", "node_modules"):
            with self.subTest(entry_type=entry_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package = make_package(root / "candidate")
                if entry_type == "file-symlink":
                    (package / "linked-file").symlink_to(package / "package.json")
                elif entry_type == "directory-symlink":
                    (package / "linked-directory").symlink_to(package / "src", target_is_directory=True)
                elif entry_type == "fifo":
                    os.mkfifo(package / "special-entry")
                else:
                    (package / "node_modules").mkdir()
                env, _agent = fake_environment(root)
                result = self.run_verify(env, "--source-only", "--expected-package", package, "--json")
                self.assertNotEqual(result.returncode, 0)

    def test_relative_stable_registration_is_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "candidate")
            env, agent, _stable = self.install_fixture(root, package)
            (agent / "settings.json").write_text(json.dumps({
                "packages": ["local-packages/ai-configs/pi-vcc", "npm:company-pi-vcc-tools"],
                "extensions": [],
            }) + "\n")
            result = self.run_verify(env, "--expected-package", package)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_official_git_forms_are_counted_while_foreign_hosts_are_not(self):
        # Only forms Pi itself parses as GitHub adnichols|sting8k/pi-vcc are official.
        official = (
            "git:adnichols/pi-vcc",
            "git:github.com/adnichols/pi-vcc@v1",
            "git:git@github.com:sting8k/pi-vcc@v1",
            "https://github.com/adnichols/pi-vcc.git@v1",
            "ssh://github.com/sting8k/pi-vcc",
            "ssh://git@github.com/adnichols/pi-vcc@v1",
            "git://github.com/sting8k/pi-vcc",
            "git:https://github.com/adnichols/pi-vcc",
            "git:https://github.com/adnichols/pi-vcc/",
            "git:https://github.com/adnichols/pi-vcc.git/",
            "git:https://github.com/adnichols/pi-vcc/.",
            "git:https://user:token@github.com/adnichols/pi-vcc",
            "git:https://github.com:443/adnichols/pi-vcc",
            "git:ssh://git@github.com/sting8k/pi-vcc",
            "git:ssh://git@github.com/sting8k/pi-vcc/",
            "git:ssh://git@github.com:22/sting8k/pi-vcc",
            "git:git://github.com/adnichols/pi-vcc",
            "git:git://github.com/adnichols/pi-vcc/",
            "git:github.com/adnichols/pi-vcc@release/v1",
            "git: https://github.com/adnichols/pi-vcc",
            "git:git+https://github.com/adnichols/pi-vcc",
            "git:git+ssh://git@github.com/adnichols/pi-vcc",
            " https://github.com/adnichols/pi-vcc/ ",
            "ssh://git@GITHUB.COM/adnichols/pi-vcc",
            "https://GITHUB.COM/sting8k/pi-vcc",
        )
        foreign = (
            "adnichols/pi-vcc",
            "sting8k/pi-vcc.git#main",
            "github:github.com/sting8k/pi-vcc",
            "git@github.com:adnichols/pi-vcc.git@v1",
            "GIT:https://github.com/adnichols/pi-vcc",
            "https://adnichols/pi-vcc",
            "ssh://sting8k/pi-vcc",
            "git://evil.example/adnichols/pi-vcc",
            "ssh://git@evil.example/sting8k/pi-vcc",
            "https://github.com.evil.example/adnichols/pi-vcc",
            r"https://evil.example\@github.com/adnichols/pi-vcc",
            "https://github.com:999999/adnichols/pi-vcc",
            "git:https://github.com/adnichols/pi-vcc@",
            "https://github.com/adnichols/pi-vcc%40evil",
            "https://github.com/adnichols%2Fpi-vcc",
            "https://github.com/adnichols/pi-vcc;param",
            "git:https://github.com/adnichols//pi-vcc",
            "git:https://github.com/adnichols/pi-vcc.git%2Egit",
            " npm:@adnichols/pi-vcc",
            "https://github.com/ADNICHOLS/pi-vcc",
            "https://github.com/adnichols/PI-VCC",
        )
        for source, should_count in [*((value, True) for value in official), *((value, False) for value in foreign)]:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package = make_package(root / "candidate")
                env, agent, stable = self.install_fixture(root, package)
                (agent / "settings.json").write_text(json.dumps({
                    "packages": [str(stable), source],
                    "extensions": [],
                }) + "\n")
                result = self.run_verify(env, "--expected-package", package)
                if should_count:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("exactly one total pi-vcc", result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_pi_parser_fails_closed_exact_one_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "candidate")
            env, agent, stable = self.install_fixture(root, package)
            (agent / "settings.json").write_text(json.dumps({
                "packages": [str(stable), "git:adnichols/pi-vcc"],
                "extensions": [],
            }) + "\n")
            # Point at a non-Pi layout so classification cannot load parseGitUrl.
            env = dict(env)
            env["PI_CODING_AGENT_PACKAGE_ROOT"] = str(root / "not-pi")
            (root / "not-pi").mkdir()
            result = self.run_verify(env, "--expected-package", package)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("registration classification unavailable", result.stderr)

    def test_symlinked_managed_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "candidate")
            env, agent, _stable = self.install_fixture(root, package)
            external = root / "external"
            shutil.rmtree(agent / "local-packages")
            external.mkdir()
            (agent / "local-packages").symlink_to(external, target_is_directory=True)
            result = self.run_verify(env, "--expected-package", package)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink ancestor", result.stderr)

    def test_symlinked_dot_pi_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = make_package(root / "candidate")
            env, agent, _stable = self.install_fixture(root, package)
            pi_dir = agent.parent
            external = root / "external-pi"
            pi_dir.rename(external)
            pi_dir.symlink_to(external, target_is_directory=True)
            result = self.run_verify(env, "--expected-package", package)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink ancestor", result.stderr)

    def test_custom_agent_root_symlink_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            package = make_package(root / "candidate")
            env, agent, _stable = self.install_fixture(root, package)
            actual_parent = root / "actual-custom-root"
            actual_agent = actual_parent / "agent"
            actual_parent.mkdir()
            shutil.move(agent, actual_agent)
            linked_parent = root / "linked-custom-root"
            linked_parent.symlink_to(actual_parent, target_is_directory=True)
            env["PI_CODING_AGENT_DIR"] = str(linked_parent / "agent")

            result = self.run_verify(env, "--expected-package", package)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink ancestor", result.stderr)

    def test_mismatch_and_duplicate_pi_vcc_registration_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = make_package(root / "expected", "expected")
            installed = make_package(root / "installed", "installed")
            env, agent, stable = self.install_fixture(root, installed)
            mismatch = self.run_verify(env, "--expected-package", expected)
            self.assertNotEqual(mismatch.returncode, 0)
            shutil.rmtree(stable)
            shutil.copytree(expected, stable, copy_function=shutil.copy2)
            legacy = make_package(root / "vcc-fork", "legacy")
            manifest = json.loads((legacy / "package.json").read_text())
            manifest["name"] = "@sting8k/pi-vcc"
            (legacy / "package.json").write_text(json.dumps(manifest) + "\n")
            (agent / "settings.json").write_text(json.dumps({
                "packages": [str(stable), str(legacy), "npm:company-pi-vcc-tools"], "extensions": []
            }) + "\n")
            duplicate = self.run_verify(env, "--expected-package", expected)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("exactly one total pi-vcc", duplicate.stderr)


if __name__ == "__main__":
    unittest.main()
