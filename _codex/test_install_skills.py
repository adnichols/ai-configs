import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).with_name('install-skills.py'))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class SkillInstallation(unittest.TestCase):
    def test_isolated_install_preserves_shared_files_and_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / '.codex'
            codex.mkdir()
            original = 'model = "user-choice"\n[mcp_servers.example]\ncommand = "unchanged"\n\n[[skills.config]]\npath = "/custom/SKILL.md"\nenabled = false\n'
            (codex / 'config.toml').write_text(original)
            shared = home / '.agents/skills/adn-mode'
            target = home / '.agents/adn/skills/adn-mode'
            target.mkdir(parents=True)
            (target / 'SKILL.md').write_text('shared original')
            shared.parent.mkdir(parents=True)
            shared.symlink_to(target, target_is_directory=True)
            result = installer.install(home, codex)
            first = (codex / 'config.toml').read_bytes()
            config = tomllib.loads(first.decode())
            entries = {row['path']: row['enabled'] for row in config['skills']['config']}
            self.assertEqual(config['model'], 'user-choice')
            self.assertEqual(config['mcp_servers']['example']['command'], 'unchanged')
            self.assertFalse(entries['/custom/SKILL.md'])
            self.assertFalse(entries[str(shared / 'SKILL.md')])
            self.assertFalse(entries[str((target / 'SKILL.md').resolve())])
            self.assertTrue(entries[str(codex / 'skills/adn-mode/SKILL.md')])
            self.assertEqual((target / 'SKILL.md').read_text(), 'shared original')
            self.assertTrue(shared.is_symlink())
            self.assertFalse((codex / 'skills/build-run-debug').exists())
            self.assertGreater(result['installed'], 0)
            self.assertEqual(len(list(codex.glob('config.toml.before-skills-*'))), 1)
            state = json.loads((codex / 'ai-configs-skills.json').read_text())
            for path, digest in state['files'].items():
                self.assertEqual(hashlib.sha256((codex / path).read_bytes()).hexdigest(), digest)
            installer.install(home, codex)
            self.assertEqual(first, (codex / 'config.toml').read_bytes())

    def test_unmanaged_collision_does_not_modify_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / '.codex'
            owned = codex / 'skills/adn-mode'
            owned.mkdir(parents=True)
            (owned / 'SKILL.md').write_text('user owned')
            (codex / 'config.toml').write_text('model = "original"\n')
            with self.assertRaisesRegex(ValueError, 'Unmanaged'):
                installer.install(home, codex)
            self.assertEqual((owned / 'SKILL.md').read_text(), 'user owned')
            self.assertEqual((codex / 'config.toml').read_text(), 'model = "original"\n')

    def test_optional_copy_requires_existing_shared_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / '.agents/skills/build-run-debug').mkdir(parents=True)
            installer.install(home, home / '.codex')
            self.assertTrue((home / '.codex/skills/build-run-debug/SKILL.md').exists())
            (home / '.agents/skills/build-run-debug').rmdir()
            installer.install(home, home / '.codex')
            self.assertFalse((home / '.codex/skills/build-run-debug').exists())


if __name__ == '__main__':
    unittest.main()
