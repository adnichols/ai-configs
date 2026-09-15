import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prompts', Path(__file__).with_name('install-prompts.py'))
prompts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompts)


class PromptInstallation(unittest.TestCase):
    def test_retirement_updates_and_custom_files_survive_reinstallation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'prompts'
            source.mkdir()
            destination = root / 'home/prompts'
            destination.mkdir(parents=True)
            (source / 'keep.md').write_text('new')
            (destination / 'keep.md').write_text('old')
            (destination / 'retired.md').write_text('retired')
            (destination / 'custom.md').write_text('custom')
            (destination / 'edited.md').write_text('user edit')
            (destination / 'legacy-dir').mkdir()
            (destination / 'legacy-dir/custom.md').write_text('nested')
            (destination / 'linked.md').symlink_to(destination / 'custom.md')
            legacy = {n: prompts.digest(destination / n) for n in ['keep.md', 'retired.md']}
            legacy['edited.md'] = 'previous-content-hash'
            legacy['linked.md'] = prompts.digest(destination / 'custom.md')
            (root / 'prompt-provenance.json').write_text(json.dumps(legacy))
            with patch.object(prompts, 'ROOT', root):
                result = prompts.install(destination)
                self.assertEqual(result['removed'], ['retired.md'])
                self.assertEqual(result['preserved'], ['edited.md', 'linked.md'])
                self.assertEqual((destination / 'keep.md').read_text(), 'new')
                self.assertFalse((destination / 'retired.md').exists())
                self.assertEqual((Path(result['backup']) / 'retired.md').read_text(), 'retired')
                self.assertEqual((Path(result['backup']) / 'keep.md').read_text(), 'old')
                self.assertEqual((destination / 'custom.md').read_text(), 'custom')
                self.assertEqual((destination / 'edited.md').read_text(), 'user edit')
                self.assertTrue((destination / 'linked.md').is_symlink())
                self.assertEqual((destination / 'legacy-dir/custom.md').read_text(), 'nested')
                self.assertIsNone(prompts.install(destination)['backup'])


if __name__ == '__main__':
    unittest.main()
