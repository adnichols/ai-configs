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
    def test_retired_skill_is_backed_up_and_modified_skill_is_preserved(self):
        for modified in (False, True):
            with self.subTest(modified=modified), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                codex = home / '.codex'
                old = codex / 'skills/luvus/SKILL.md'
                old.parent.mkdir(parents=True)
                old.write_text('original')
                state = {'skills': ['luvus'], 'files': {
                    'skills/luvus/SKILL.md': hashlib.sha256(old.read_bytes()).hexdigest()}}
                (codex / 'ai-configs-skills.json').write_text(json.dumps(state))
                if modified:
                    old.write_text('user edit')
                result = installer.install(home, codex)
                if modified:
                    self.assertEqual(old.read_text(), 'user edit')
                    self.assertEqual(result['preserved_retired_skills'], ['luvus'])
                else:
                    self.assertFalse(old.exists())
                    self.assertEqual((Path(result['retired_backup']) / 'luvus/SKILL.md').read_text(), 'original')
    def test_catalog_exclusions_preserve_shared_and_system_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / '.codex'
            names = ['.codex/skills/.system/skill-creator', '.agents/skills/skill-creator',
                     '.agents/skills/template', '.agents/skills/vercel-react-best-practices',
                     '.codex/skills/vercel-react-best-practices', '.codex/skills/custom-system-only']
            for name in names:
                path = home / name
                path.mkdir(parents=True)
                (path / 'SKILL.md').write_text(name)
            installer.install(home, codex)
            rows = tomllib.loads((codex / 'config.toml').read_text())['skills']['config']
            disabled = {r['path'] for r in rows if not r['enabled']}
            self.assertIn(str(home / '.agents/skills/skill-creator/SKILL.md'), disabled)
            self.assertIn(str(home / '.agents/skills/template/SKILL.md'), disabled)
            self.assertIn(str(codex / 'skills/vercel-react-best-practices/SKILL.md'), disabled)
            self.assertNotIn(str(codex / 'skills/.system/skill-creator/SKILL.md'), disabled)
            for name in names:
                self.assertEqual((home / name / 'SKILL.md').read_text(), name)

    def test_isolated_install_preserves_shared_files_and_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / '.codex'
            codex.mkdir()
            original = 'model = "user-choice"\n[mcp_servers.example]\ncommand = "unchanged"\n\n[[skills.config]]\npath = "/custom/SKILL.md"\nenabled = false\n'
            (codex / 'config.toml').write_text(original)
            stale = codex / 'skills/verfied-build'
            stale.mkdir(parents=True)
            (stale / 'SKILL.md').write_text('misspelled old copy')
            (codex / 'ai-configs-skills.json').write_text('{"skills":["verfied-build"],"files":{}}')
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
            self.assertTrue((codex / 'skills/verified-build/SKILL.md').exists())
            self.assertEqual((codex / 'skills/verfied-build/SKILL.md').read_text(), 'misspelled old copy')
            self.assertEqual(result['preserved_retired_skills'], ['verfied-build'])
            self.assertFalse((home / '.agents/skills/verified-build').exists())
            self.assertGreater(result['installed'], 0)
            self.assertEqual(len(list(codex.glob('config.toml.before-skills-*'))), 1)
            state = json.loads((codex / 'ai-configs-skills.json').read_text())
            for path, digest in state['files'].items():
                self.assertEqual(hashlib.sha256((codex / path).read_bytes()).hexdigest(), digest)
            installer.install(home, codex)
            self.assertEqual(first, (codex / 'config.toml').read_bytes())
            with_hooks = first.decode().replace(
                installer.END,
                '[hooks.state]\nkept = "yes"\n' + installer.END,
            )
            (codex / 'config.toml').write_text(with_hooks)
            installer.install(home, codex)
            preserved = (codex / 'config.toml').read_text()
            self.assertEqual(tomllib.loads(preserved)['hooks']['state']['kept'], 'yes')
            self.assertLess(preserved.index('[hooks.state]'), preserved.index(installer.BEGIN))

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
