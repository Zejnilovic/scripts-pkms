"""No command replaces a file that is already on disk, even one .pkmignore hides from pkm: new, rename, mv, the routines
note, a day page and a close page. Run: python3 -m unittest discover -s tests. Names are made up. NOW is 2026-10-25.
"""

from helpers import VaultCase


class NoOverwrite(VaultCase):
    def hide(self, *lines):
        self.write(".pkmignore", "".join(line + "\n" for line in lines))

    def test_new_refuses_a_hidden_file_at_the_target(self):
        self.hide("exports/")
        self.write(".pkm/config", "format=1\nfolder_diary=exports\n")
        self.ok("new", "diary", "one")
        self.write("exports/one.md", "MY WORDS\n")
        result = self.pkm("new", "diary", "one")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("exports/one.md", result.stdout)
        self.assertIn("already exists", result.stderr)
        self.assertIn(".pkmignore hides it", result.stderr)
        self.assertEqual(self.read("exports/one.md"), "MY WORDS\n")

    def test_new_refuses_a_visible_file_at_the_target_too(self):
        self.write("notes/plain.md", "MY WORDS\n")
        result = self.pkm("new", "person", "Plain", "--name", "plain")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.read("notes/plain.md"), "MY WORDS\n")

    def test_rename_refuses_a_hidden_file_at_the_new_path(self):
        self.hide("notes/hidden-target.md")
        self.write("notes/srcnote.md", "# Src\n")
        self.write("notes/hidden-target.md", "MY WORDS\n")
        result = self.pkm("rename", "srcnote", "hidden-target")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("notes/hidden-target.md", result.stdout)
        self.assertIn(".pkmignore hides it", result.stderr)
        self.assertEqual(self.read("notes/hidden-target.md"), "MY WORDS\n")
        self.assertTrue(self.exists("notes/srcnote.md"))

    def test_mv_refuses_a_hidden_file_at_the_new_path(self):
        self.hide("archive/")
        self.write("notes/apollo.md", "# Apollo\n")
        self.write("archive/apollo.md", "MY WORDS\n")
        result = self.pkm("mv", "apollo", "archive")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.read("archive/apollo.md"), "MY WORDS\n")
        self.assertTrue(self.exists("notes/apollo.md"))

    def test_the_routines_note_is_not_replaced_when_a_hidden_file_holds_its_path(self):
        self.hide("notes/routines.md")
        self.write("notes/routines.md", "MY WORDS\n")
        result = self.pkm("todo", "Water", "--every", "1w")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.read("notes/routines.md"), "MY WORDS\n")

    def test_a_day_page_is_not_replaced_when_a_hidden_file_holds_it(self):
        self.hide("daybook/")
        self.write("daybook/2026/10/2026-10-25.md", "MY WORDS\n")
        self.pkm("day")
        self.assertEqual(self.read("daybook/2026/10/2026-10-25.md"), "MY WORDS\n")

    def test_a_close_page_is_not_replaced_when_a_hidden_file_holds_it(self):
        self.hide("closes/")
        self.write("closes/2026/2026-10-19-week.md", "MY WORDS\n")
        result = self.pkm("new", "close")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.read("closes/2026/2026-10-19-week.md"), "MY WORDS\n")


if __name__ == "__main__":
    import unittest

    unittest.main()
