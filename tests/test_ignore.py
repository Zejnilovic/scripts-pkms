"""Tests for .pkmignore: every command that walks the vault leaves out what it lists, and .gitignore is not read.
Run: python3 -m unittest discover -s tests
"""

import unittest

from helpers import VaultCase

IGNORE = """# drafts and private notes stay out of pkm
drafts/
secret*.md
!secret-keep.md
"""


class PkmIgnoreTest(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(".pkmignore", IGNORE)
        self.write("drafts/idea.md", "# Idea\n\n- [ ] Draft task (due 2026-10-26)\n[[apollo]]\n")
        self.write("notes/apollo.md", "# Apollo\n\n- [ ] Real task (due 2026-10-26)\n")
        self.write("notes/secret-plan.md", "# Secret plan\n\n- [ ] Hidden task (due 2026-10-26)\n[[apollo]]\n")
        self.write("notes/secret-keep.md", "# Kept\n\n- [ ] Kept task (due 2026-10-26)\n[[apollo]]\n")
        self.write(".gitignore", "notes/\n")

    def test_find_skips_an_ignored_folder_and_file_but_finds_a_re_included_one(self):
        out = self.ok("find", "task")
        self.assertIn("notes/apollo.md", out)
        self.assertIn("notes/secret-keep.md", out)
        self.assertNotIn("drafts/", out)
        self.assertNotIn("secret-plan", out)

    def test_check_does_not_report_what_is_ignored(self):
        self.write("drafts/broken.md", "[[nobody-here]]\n")
        result = self.pkm("check")
        self.assertNotIn("drafts/", result.stdout)
        self.assertNotIn("secret-plan", result.stdout)

    def test_list_skips_ignored_notes(self):
        self.write("drafts/project.md", "---\ntype: project\n---\n# Draft\n")
        result = self.pkm("list", "type=project")
        self.assertNotIn("drafts/", result.stdout)
        self.assertEqual(result.returncode, 1, "no records is a 1 in the output contract")

    def test_tasks_and_upcoming_skip_ignored_notes(self):
        tasks = self.ok("tasks")
        self.assertIn("notes/apollo.md", tasks)
        self.assertIn("notes/secret-keep.md", tasks)
        self.assertNotIn("drafts/", tasks)
        self.assertNotIn("secret-plan", tasks)
        upcoming = self.ok("upcoming", "7")
        self.assertNotIn("drafts/", upcoming)
        self.assertNotIn("secret-plan", upcoming)

    def test_gitignore_is_not_read(self):
        self.assertIn("notes/apollo.md", self.ok("find", "Apollo"))

    def test_without_a_pkmignore_nothing_is_left_out_but_dot_folders(self):
        (self.root / ".pkmignore").unlink()
        out = self.ok("find", "task")
        self.assertIn("drafts/idea.md", out)
        self.assertIn("notes/secret-plan.md", out)


if __name__ == "__main__":
    unittest.main()
