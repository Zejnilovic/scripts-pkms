"""Tests for names and links: every link form resolves, notices and problems in check, backlinks through aliases,
and the acceptance check of the two example vaults. Run: python3 -m unittest discover -s tests
Names and data are made up.
"""

import os
import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm


class LinkForms(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("people/jane-doe.md", "---\ntype: person\naliases: [JD, Jane D.]\n---\n\n# Jane Doe\n\n## Budget\n")
        self.write("attachments/plan.png", "png")
        self.write("notes/apollo.md", "# Apollo\n")

    def test_every_form_of_a_link_to_a_note_resolves(self):
        self.write("notes/forms.md", "[[jane-doe]] [[jane-doe|Jane]] [[jane-doe#Budget]] [[jane-doe^b]] ![[plan.png]]\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("broken link", result.stdout)
        self.assertIn("notes/forms.md:1: ", self.ok("backlinks", "jane-doe"))

    def test_a_link_by_words_resolves_and_is_a_notice_that_gives_the_full_form(self):
        self.write("notes/words.md", "Met [[Jane Doe]] today\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("notes/words.md:1: [[Jane Doe]] works only in pkm, through the slug of jane-doe: write [[jane-doe|Jane Doe]]",
                      result.stdout)
        self.assertIn("notes/words.md:1:", self.ok("backlinks", "jane-doe"))

    def test_an_alias_resolves_and_is_a_notice(self):
        self.write("notes/alias.md", "Sent to [[JD]]\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("works only in pkm, through the alias of jane-doe", result.stdout)
        self.assertIn("notes/alias.md:1:", self.ok("backlinks", "jane-doe"))
        self.assertIn("people/jane-doe.md", self.ok("path", "Jane D."))

    def test_a_struck_link_still_counts(self):
        self.write("notes/struck.md", "- ~~[[nobody]]~~ was true\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/struck.md:1: broken link [[nobody]]", result.stdout)

    def test_a_link_to_a_name_with_no_note_is_dead_but_its_lines_are_listed(self):
        self.write("notes/pending.md", "Waiting on [[nobody]]\n")
        result = self.pkm("backlinks", "nobody")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notes/pending.md:1: Waiting on [[nobody]]", result.stdout)

    def test_a_file_the_pkmignore_leaves_out_is_said_to_be_ignored(self):
        self.write(".pkmignore", "private/\n")
        self.write("private/diary.md", "# Diary\n")
        self.write("notes/peek.md", "See [[diary]]\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/peek.md:1: broken link [[diary]]: the file is in .pkmignore", result.stdout)

    def test_day_pages_resolve_in_their_month_folders_and_in_a_shared_vault(self):
        self.write("daybook/2026/11/2026-11-10.md", "# 2026-11-10\n")
        self.write("daybook/2026/11/2026-11-10-sam.md", "# 2026-11-10 Sam\n\n- Plan [[2026-11-10]] and [[2026-11-10-sam]]\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)
        self.assertIn("daybook/2026/11/2026-11-10-sam.md:3:", self.ok("backlinks", "2026-11-10"))


class ProblemsAndNotices(VaultCase):
    def test_an_alias_on_two_notes_is_a_problem(self):
        self.write("people/one.md", "---\naliases: [Apollo]\n---\n# One\n")
        self.write("notes/two.md", "---\naliases: [Apollo]\n---\n# Two\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("alias Apollo is on more than one note", result.stdout)

    def test_a_file_name_that_is_not_a_slug_is_a_notice(self):
        self.write("people/Jane Doe.md", "# Jane\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("people/Jane Doe.md: the file name isn't a slug: name it jane-doe.md", result.stdout)

    def test_the_path_of_a_name_or_alias_is_found(self):
        self.write("people/jane-doe.md", "---\naliases: [JD]\n---\n# Jane\n")
        self.assertEqual(self.ok("path", "jane doe").strip(), "people/jane-doe.md")
        self.assertEqual(self.ok("path", "[[JD|Jane]]").strip(), "people/jane-doe.md")
        self.assertEqual(self.pkm("path", "nobody").returncode, 1)


class ExampleVaults(unittest.TestCase):
    """The method's example vaults are the acceptance test: their links and names must check clean."""

    def run_check(self, vault):
        # On a copy: pkm writes its cache into .pkm, and the examples are not to be changed.
        with tempfile.TemporaryDirectory() as copies:
            copy = pathlib.Path(copies) / vault
            shutil.copytree(REPO / "docs/examples" / vault, copy)
            with tempfile.TemporaryDirectory() as config:
                environment = pkm_env(XDG_CONFIG_HOME=config)
                return run_pkm(["check"], cwd=copy, env=environment, vault=copy)

    def test_work_vault_has_no_dead_links_and_no_duplicate_names(self):
        result = self.run_check("work")
        self.assertNotIn("broken link", result.stdout)
        self.assertNotIn("duplicate name", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_family_vault_has_no_dead_links_and_no_duplicate_names(self):
        result = self.run_check("family")
        self.assertNotIn("broken link", result.stdout)
        self.assertNotIn("duplicate name", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_the_example_settings_are_valid(self):
        for vault in ["work", "family"]:
            with tempfile.TemporaryDirectory() as copies, tempfile.TemporaryDirectory() as config:
                copy = pathlib.Path(copies) / vault
                shutil.copytree(REPO / "docs/examples" / vault, copy)
                result = run_pkm(["doctor"], cwd=copy, env=pkm_env(XDG_CONFIG_HOME=config), vault=copy)
                self.assertNotIn("problem", result.stdout, result.stdout)


if __name__ == "__main__":
    unittest.main()
