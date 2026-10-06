import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "bugbash" / "scripts"))
import spec_diff

TABLE = """# Contract

## Routes

| Operation | Route | Purpose |
| --- | --- | --- |
| List | `GET /a` | Return a list. |
| Create | `POST /a` | Create one. |
| Remove | `DELETE /a/{id}` | Remove one. |

## Notes

See [the ADR](adr-1.md) and [the contract](../docs/contract.md#routes).
"""


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True)


class SpecDiffTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(shutil.which("pandoc"), "pandoc must be installed to run these tests")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "remote", "add", "origin", "git@github.com:acme/widgets.git")
        (self.root / "spec").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "docs" / "contract.md").write_text("# C\n")
        (self.root / "spec" / "contract.md").write_text(TABLE)
        (self.root / "spec" / "adr-1.md").write_text("# ADR 1\n\nDecision text.\n")
        (self.root / "spec" / "untouched.md").write_text("# Untouched\n\nNothing changes.\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")

    def render(self, head=None, **kw):
        src = spec_diff.resolve(self.root, "main", head)
        found = spec_diff.changes(src, ["spec"])
        opts = spec_diff.Options("Proposal", kw.get("summary", ""), "", kw.get("full_lines", spec_diff.FULL_LINES))
        return src, found, spec_diff.page(src, "https://github.com/acme/widgets", found, opts)

    def test_modified_table_row_reads_as_one_changed_row(self):
        text = TABLE.replace("| Create | `POST /a` | Create one. |", "| Create | `POST /a` | Create one and return it. |")
        (self.root / "spec" / "contract.md").write_text(text)
        _, found, page = self.render()
        self.assertEqual([c.path for c in found], ["spec/contract.md"])
        self.assertEqual(page.count('<tr class="row-rm">'), 1)
        self.assertEqual(page.count('<tr class="row-add">'), 1)
        self.assertEqual(page.count('<tr class="row-eq">'), 2)
        self.assertIn("<del>one.</del>", page)
        self.assertIn("<ins>one and return it.</ins>", page)

    def test_new_untracked_file_is_listed_and_fingerprinted(self):
        data = b"# ADR 2\n\nA new decision.\n"
        (self.root / "spec" / "adr-2.md").write_bytes(data)
        src, found, page = self.render()
        self.assertEqual([(c.path, c.status) for c in found], [("spec/adr-2.md", "added")])
        self.assertIn("The whole file is added.", page)
        self.assertNotIn('<table class="sbs">', page)
        self.assertEqual(spec_diff.manifest(src, found)["files"]["spec/adr-2.md"], spec_diff.sha256(data))

    def test_deleted_file_shows_every_line_as_removed(self):
        (self.root / "spec" / "adr-1.md").unlink()
        _, found, page = self.render()
        self.assertEqual([(c.path, c.status) for c in found], [("spec/adr-1.md", "deleted")])
        self.assertIn("The whole file is deleted.", page)
        self.assertIn("Decision text.", page)
        self.assertIn('<div class="rm">', page)
        self.assertNotIn('<div class="add">', page)
        self.assertIn("<li><code>spec/adr-1.md</code> removed</li>", page)

    def test_deleted_lines_inside_a_modified_file_keep_both_sides(self):
        (self.root / "spec" / "contract.md").write_text(TABLE.replace("| Remove | `DELETE /a/{id}` | Remove one. |\n", ""))
        _, _, page = self.render()
        self.assertIn('<td class="rm">| Remove | `DELETE /a/{id}` | Remove one. |</td>', page)
        self.assertIn('<td class="gap"></td>', page)

    def test_files_without_changes_are_skipped(self):
        (self.root / "spec" / "adr-1.md").write_text("# ADR 1\n\nDecision text, revised.\n")
        _, found, page = self.render()
        self.assertEqual([c.path for c in found], ["spec/adr-1.md"])
        self.assertNotIn("untouched.md", page)
        git(self.root, "checkout", "--", "spec")
        self.assertEqual(spec_diff.changes(spec_diff.resolve(self.root, "main", None), ["spec"]), [])

    def test_committed_head_is_read_from_git_not_the_working_tree(self):
        git(self.root, "checkout", "-qb", "proposal")
        (self.root / "spec" / "adr-1.md").write_text("# ADR 1\n\nCommitted wording.\n")
        git(self.root, "commit", "-qam", "propose")
        (self.root / "spec" / "adr-1.md").write_text("# ADR 1\n\nUncommitted wording.\n")
        src, found, page = self.render(head="proposal")
        self.assertIn("Committed wording.", page)
        self.assertNotIn("Uncommitted wording.", page)
        self.assertEqual(spec_diff.manifest(src, found)["files"]["spec/adr-1.md"], spec_diff.sha256(b"# ADR 1\n\nCommitted wording.\n"))

    def test_relative_links_become_github_urls_and_unresolvable_ones_become_text(self):
        (self.root / "spec" / "contract.md").write_text(TABLE + "\nAlso [gone](missing.md) and ![chart](chart.png).\n")
        src, _, page = self.render()
        base = src.base
        self.assertIn(f'href="https://github.com/acme/widgets/blob/{base}/spec/adr-1.md"', page)
        self.assertIn(f'href="https://github.com/acme/widgets/blob/{base}/docs/contract.md#routes"', page)
        self.assertNotIn('href="adr-1.md"', page)
        self.assertNotIn('href="missing.md"', page)
        self.assertIn("gone", page)
        self.assertIn("[image: chart]", page)

    def test_large_files_show_only_the_changed_section_with_omission_markers(self):
        sections = "\n".join(f"## Section {i}\n\nParagraph {i}.\n" for i in range(40))
        (self.root / "spec" / "big.md").write_text("# Big\n\n" + sections)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "big")
        (self.root / "spec" / "big.md").write_text(("# Big\n\n" + sections).replace("Paragraph 20.", "Paragraph twenty."))
        _, _, page = self.render(full_lines=50)
        self.assertIn("Paragraph twenty.", page)
        self.assertIn("Section 20", page)
        self.assertNotIn("Section 3<", page)
        self.assertNotIn("Paragraph 30.", page)
        self.assertEqual(page.count('class="skip"'), 2)
        self.assertIn("so only the sections around a change are shown", page)

    def test_check_flags_a_file_that_differs_from_the_approved_text(self):
        (self.root / "spec" / "adr-1.md").write_text("# ADR 1\n\nApproved wording.\n")
        src, found, _ = self.render()
        manifest = Path(self.tmp.name) / "manifest.json"
        manifest.write_text(json.dumps(spec_diff.manifest(src, found)))
        self.assertEqual(spec_diff.check(manifest, self.root, None), 0)
        (self.root / "spec" / "adr-1.md").write_text("# ADR 1\n\nApproved wording. \n")
        self.assertEqual(spec_diff.check(manifest, self.root, None), 1)

    def test_a_crlf_only_change_is_reported_not_skipped(self):
        (self.root / "spec" / "adr-1.md").write_bytes(b"# ADR 1\r\n\r\nDecision text.\r\n")
        _, found, page = self.render()
        self.assertEqual([c.path for c in found], ["spec/adr-1.md"])
        self.assertIn("Only line endings or the final newline differ", page)


if __name__ == "__main__":
    unittest.main()
