import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / "install.sh"
EXTENSION = ROOT / "_pi/extensions/percentage-compaction.ts"


def make_package(path: Path, marker: str) -> Path:
    (path / "src/core").mkdir(parents=True)
    (path / "package.json").write_text(json.dumps({"name": "@test/pi-vcc"}) + "\n")
    (path / "index.ts").write_text("export default function extension() {}\n")
    (path / "src/core/coordinator.ts").write_text(f"export const marker = {marker!r};\n")
    (path / "src/core/custom-message-classifier.ts").write_text("export const classifier = true;\n")
    return path


def tree_manifest(root: Path):
    if not root.exists():
        return None
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        metadata = path.lstat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        mode = stat.S_IMODE(metadata.st_mode)
        if path.is_symlink():
            value = ("link", os.readlink(path))
        elif path.is_dir():
            value = ("directory", "")
        else:
            value = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        result[relative] = (mode, value)
    return result


def test_environment(root: Path):
    root = root.resolve()
    home = root / "home"
    agent = home / ".pi/agent"
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    pi = bin_dir / "pi"
    pi.write_text("#!/bin/sh\n[ \"$1\" = --version ] && echo 'pi test' && exit 0\nexit 0\n")
    pi.chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(home),
        "PI_CODING_AGENT_DIR": str(agent),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
    }
    return env, agent


def prepare_install(root: Path):
    env, agent = test_environment(root)
    old = make_package(root / "old-package", "old")
    candidate = make_package(root / "candidate-package", "candidate")
    stable = agent / "local-packages/ai-configs/pi-vcc"
    shutil.copytree(old, stable, copy_function=shutil.copy2)
    live_extension = agent / "extensions/percentage-compaction.ts"
    live_extension.parent.mkdir(parents=True)
    shutil.copy2(EXTENSION, live_extension)
    settings = agent / "settings.json"
    settings.write_text(json.dumps({
        "theme": "caller-owned",
        "packages": ["npm:unrelated", "npm:company-pi-vcc-tools", str(stable)],
        "extensions": [],
    }, indent=2) + "\n")
    settings.chmod(0o640)
    return env, agent, old, candidate, stable, settings


class InstallPiVccTest(unittest.TestCase):
    def run_install(self, env, source=None, failpoint=None):
        command = ["bash", str(INSTALL), "--pi-vcc"]
        if source is not None:
            command.append(str(source))
        run_env = dict(env)
        if failpoint:
            run_env["PI_VCC_INSTALL_FAILPOINT"] = failpoint
        return subprocess.run(
            command, cwd=ROOT, env=run_env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=600,
        )

    def assert_no_transaction_debris(self, stable: Path):
        parent = stable.parent
        debris = list(parent.glob(".pi-vcc-stage.*")) + list(parent.glob(".pi-vcc-backup.*")) + list(parent.glob(".pi-vcc-settings.*"))
        self.assertEqual(debris, [])

    def test_candidate_install_and_explicit_source_rollback_are_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env, agent, old, candidate, stable, settings = prepare_install(root)
            unrelated = agent / "unrelated.txt"
            unrelated.write_text("keep\n")
            result = self.run_install(env, candidate)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tree_manifest(stable), tree_manifest(candidate))
            installed_settings = json.loads(settings.read_text())
            self.assertEqual(installed_settings["theme"], "caller-owned")
            self.assertEqual(installed_settings["packages"], ["npm:unrelated", "npm:company-pi-vcc-tools", str(stable)])
            self.assertEqual(unrelated.read_text(), "keep\n")
            rollback = self.run_install(env, old)
            self.assertEqual(rollback.returncode, 0, rollback.stderr)
            self.assertEqual(tree_manifest(stable), tree_manifest(old))
            self.assertEqual(unrelated.read_text(), "keep\n")
            self.assert_no_transaction_debris(stable)

    def test_relative_and_official_repo_registrations_are_replaced_without_touching_foreign_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env, _agent, _old, candidate, stable, settings = prepare_install(root)
            settings.write_text(json.dumps({
                "packages": [
                    "local-packages/ai-configs/pi-vcc",
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
                    # Non-Git / foreign sources must remain untouched.
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
                    "npm:company-pi-vcc-tools",
                ],
                "extensions": [],
            }) + "\n")
            result = self.run_install(env, candidate)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(settings.read_text())["packages"],
                [
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
                    "npm:company-pi-vcc-tools",
                    str(stable),
                ],
            )

    def test_missing_pi_parser_fails_closed_before_settings_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env, _agent, _old, candidate, stable, settings = prepare_install(root)
            settings_data = json.loads(settings.read_text())
            settings_data["packages"] = [str(stable), "git:adnichols/pi-vcc", "npm:company-pi-vcc-tools"]
            settings.write_text(json.dumps(settings_data, indent=2) + "\n")
            before_settings = settings.read_bytes()
            before_tree = tree_manifest(stable)
            env = dict(env)
            env["PI_CODING_AGENT_PACKAGE_ROOT"] = str(root / "not-pi")
            (root / "not-pi").mkdir()
            result = self.run_install(env, candidate)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                "registration classification unavailable" in result.stderr
                or "PI_CODING_AGENT_PACKAGE_ROOT" in result.stderr
                or "parseGitUrl" in result.stderr
                or "pi-coding-agent" in result.stderr,
                result.stderr,
            )
            self.assertEqual(before_settings, settings.read_bytes())
            self.assertEqual(before_tree, tree_manifest(stable))

    def test_default_source_installs_repo_package_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env, agent, _old, _candidate, stable, _settings = prepare_install(root)
            result = self.run_install(env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tree_manifest(stable), tree_manifest(ROOT / "_pi/packages/pi-vcc"))
            self.assertFalse((agent / "prompts").exists())

    def test_missing_malformed_node_modules_and_symlinked_sources_fail_before_mutation(self):
        variants = ("missing", "malformed", "node_modules", "root-symlink")
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env, _agent, _old, candidate, stable, settings = prepare_install(root)
                if variant == "missing":
                    source = root / "does-not-exist"
                elif variant == "malformed":
                    source = root / "malformed"
                    source.mkdir()
                elif variant == "node_modules":
                    (candidate / "node_modules").mkdir()
                    source = candidate
                else:
                    source = root / "candidate-link"
                    source.symlink_to(candidate, target_is_directory=True)
                before_tree = tree_manifest(stable)
                before_settings = settings.read_bytes()
                result = self.run_install(env, source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before_tree, tree_manifest(stable))
                self.assertEqual(before_settings, settings.read_bytes())
                self.assert_no_transaction_debris(stable)

    def test_overlapping_sources_fail_before_mirror_or_settings_mutation(self):
        for variant in ("equal", "nested", "ancestor", "symlink-alias"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env, _agent, _old, _candidate, stable, settings = prepare_install(root)
                if variant == "equal":
                    source = stable
                elif variant == "nested":
                    source = make_package(stable / "nested-source", "nested")
                elif variant == "ancestor":
                    source = stable.parent
                    (source / "package.json").write_text("{}\n")
                    (source / "src/core").mkdir(parents=True)
                    (source / "src/core/coordinator.ts").write_text("export const marker = 'ancestor';\n")
                else:
                    source = root / "stable-alias"
                    source.symlink_to(stable, target_is_directory=True)
                before_tree = tree_manifest(stable)
                before_settings = settings.read_bytes()
                result = self.run_install(env, source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("overlaps the stable mirror", result.stderr)
                self.assertEqual(before_tree, tree_manifest(stable))
                self.assertEqual(before_settings, settings.read_bytes())
                self.assert_no_transaction_debris(stable)

    def test_symlinked_managed_ancestors_fail_before_external_mutation(self):
        for ancestor in ("local-packages", "ai-configs"):
            with self.subTest(ancestor=ancestor), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env, agent, _old, candidate, stable, settings = prepare_install(root)
                external = root / "external"
                external.mkdir()
                stable_manifest = tree_manifest(stable)
                settings_bytes = settings.read_bytes()
                if ancestor == "local-packages":
                    shutil.rmtree(agent / "local-packages")
                    (agent / "local-packages").symlink_to(external, target_is_directory=True)
                else:
                    shutil.rmtree(agent / "local-packages/ai-configs")
                    (agent / "local-packages/ai-configs").symlink_to(external, target_is_directory=True)
                result = self.run_install(env, candidate)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("symlink ancestor", result.stderr)
                self.assertEqual(list(external.iterdir()), [])
                self.assertEqual(settings_bytes, settings.read_bytes())
                self.assertIsNotNone(stable_manifest)

    def test_symlinked_dot_pi_ancestor_fails_before_external_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env, agent, _old, candidate, stable, settings = prepare_install(root)
            before_tree = tree_manifest(stable)
            before_settings = settings.read_bytes()
            pi_dir = agent.parent
            external = root / "external-pi"
            pi_dir.rename(external)
            pi_dir.symlink_to(external, target_is_directory=True)
            result = self.run_install(env, candidate)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink ancestor", result.stderr)
            self.assertEqual(before_tree, tree_manifest(stable))
            self.assertEqual(before_settings, settings.read_bytes())

    def test_custom_agent_root_symlink_ancestor_fails_before_external_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            env, agent, _old, candidate, stable, settings = prepare_install(root)
            actual_parent = root / "actual-custom-root"
            actual_agent = actual_parent / "agent"
            actual_parent.mkdir()
            shutil.move(agent, actual_agent)
            linked_parent = root / "linked-custom-root"
            linked_parent.symlink_to(actual_parent, target_is_directory=True)
            env["PI_CODING_AGENT_DIR"] = str(linked_parent / "agent")
            moved_stable = actual_agent / stable.relative_to(agent)
            moved_settings = actual_agent / settings.relative_to(agent)
            before_tree = tree_manifest(moved_stable)
            before_settings = moved_settings.read_bytes()

            result = self.run_install(env, candidate)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink ancestor", result.stderr)
            self.assertEqual(before_tree, tree_manifest(moved_stable))
            self.assertEqual(before_settings, moved_settings.read_bytes())

    def test_symlinks_and_special_entries_inside_source_fail_before_mutation(self):
        for variant in ("file-symlink", "directory-symlink", "fifo"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env, _agent, _old, candidate, stable, settings = prepare_install(root)
                if variant == "file-symlink":
                    (candidate / "linked-file").symlink_to(candidate / "package.json")
                elif variant == "directory-symlink":
                    (candidate / "linked-directory").symlink_to(candidate / "src", target_is_directory=True)
                else:
                    os.mkfifo(candidate / "special-entry")
                before_tree = tree_manifest(stable)
                before_settings = settings.read_bytes()
                result = self.run_install(env, candidate)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before_tree, tree_manifest(stable))
                self.assertEqual(before_settings, settings.read_bytes())
                self.assert_no_transaction_debris(stable)

    def test_every_transaction_failpoint_restores_prior_bytes_and_registration(self):
        for failpoint in ("copy", "staged-hash", "backup-move", "swap", "registration", "post-swap-verification"):
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env, _agent, _old, candidate, stable, settings = prepare_install(root)
                before_tree = tree_manifest(stable)
                before_settings = settings.read_bytes()
                before_mode = stat.S_IMODE(settings.stat().st_mode)
                result = self.run_install(env, candidate, failpoint)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before_tree, tree_manifest(stable))
                self.assertEqual(before_settings, settings.read_bytes())
                self.assertEqual(before_mode, stat.S_IMODE(settings.stat().st_mode))
                registrations = json.loads(settings.read_text())["packages"]
                self.assertEqual(registrations.count(str(stable)), 1)
                self.assert_no_transaction_debris(stable)

    def test_restore_failures_retain_recovery_evidence(self):
        for failpoint in ("remove-candidate", "restore-mirror", "restore-settings"):
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env, agent, _old, candidate, stable, settings = prepare_install(root)
                prior_tree = tree_manifest(stable)
                if failpoint == "restore-settings":
                    settings_data = json.loads(settings.read_text())
                    settings_data["packages"].insert(0, "git:adnichols/pi-vcc")
                    settings.write_text(json.dumps(settings_data, indent=2) + "\n")
                    settings.chmod(0o640)
                prior_settings = settings.read_bytes()
                prior_settings_mode = stat.S_IMODE(settings.stat().st_mode)
                result = self.run_install(env, candidate, failpoint)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("recovery evidence retained", result.stderr)
                parent = stable.parent
                evidence = list(parent.glob(".pi-vcc-backup.*")) + list(parent.glob(".pi-vcc-settings.*"))
                self.assertTrue(evidence)
                for path in evidence:
                    self.assertIn(str(path), result.stderr)
                if failpoint == "remove-candidate":
                    backups = list(parent.glob(".pi-vcc-backup.*"))
                    self.assertEqual(len(backups), 1)
                    self.assertIn(f"backup={backups[0]}", result.stderr)
                    self.assertNotIn("backup=none", result.stderr)
                    self.assertEqual(prior_tree, tree_manifest(backups[0]))
                if failpoint == "restore-mirror":
                    backups = list(parent.glob(".pi-vcc-backup.*"))
                    self.assertEqual(len(backups), 1)
                    self.assertIn(f"backup={backups[0]}", result.stderr)
                    self.assertNotIn("backup=none", result.stderr)
                    self.assertEqual(prior_tree, tree_manifest(backups[0]))
                    self.assertFalse(stable.exists())
                if failpoint == "restore-settings":
                    live_settings = json.loads(settings.read_text())
                    self.assertNotEqual(settings.read_bytes(), prior_settings)
                    self.assertNotIn("git:adnichols/pi-vcc", live_settings["packages"])
                    self.assertEqual(stat.S_IMODE(settings.stat().st_mode), prior_settings_mode)
                    self.assertEqual(list(agent.glob(".pi-vcc-settings-restore.*")), [])
                    snapshots = list(parent.glob(".pi-vcc-settings.*"))
                    self.assertEqual(len(snapshots), 1)
                    self.assertEqual(snapshots[0].read_bytes(), prior_settings)


if __name__ == "__main__":
    unittest.main()
