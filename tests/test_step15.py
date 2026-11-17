"""Review fixes for step 15: post into a note with no final newline, backlinks print each line once, doctor reads the
vault's config from a subfolder and checks the numeric settings, and new refuses a title that loses letters in its slug.
Run: python3 -m unittest discover -s tests. Names and data are made up. NOW is 2026-10-25.
"""

from helpers import VaultCase

SOURCE = "daybook/2026/10/2026-10-24.md"


class PostWithoutFinalNewline(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(SOURCE, "# 2026-10-24\n\n## Log\n\n- Decided: keep the plan\n")

    def test_an_entry_goes_on_its_own_line_after_a_last_line_with_no_newline(self):
        self.write("notes/apollo.md", "# Apollo\n\n## Decisions\n\n- Earlier decision")
        self.ok("post", f"{SOURCE}:5", "apollo#Decisions")
        lines = self.read("notes/apollo.md").splitlines()
        self.assertEqual(lines[-2:], ["- Earlier decision", "- Decided: keep the plan ([[2026-10-24]])"])
        self.assertTrue(self.read("notes/apollo.md").endswith("\n"))

    def test_an_entry_goes_on_its_own_line_after_a_heading_with_no_newline(self):
        self.write("people/jane-doe.md", "---\ntype: person\n---\n\n# Jane Doe")
        self.ok("post", f"{SOURCE}:5", "jane-doe")
        self.assertEqual(self.read("people/jane-doe.md").splitlines()[-3:],
                         ["# Jane Doe", "", "- Decided: keep the plan ([[2026-10-24]])"])

    def test_a_created_section_starts_on_its_own_line_after_a_last_line_with_no_newline(self):
        self.write("notes/apollo.md", "# Apollo\n\n- x")
        self.ok("post", f"{SOURCE}:5", "apollo#Plans")
        lines = self.read("notes/apollo.md").splitlines()
        self.assertIn("## Plans", lines)
        self.assertIn("- x", lines)
        self.assertEqual(lines[lines.index("## Plans") - 1], "")


class BacklinksOncePerLine(VaultCase):
    def test_a_line_with_the_same_link_twice_is_printed_once(self):
        self.write("notes/apollo.md", "# Apollo\n")
        self.write("notes/talk.md", "Met [[apollo]] and [[apollo]] and [[Apollo]] today\n")
        out = self.ok("backlinks", "apollo")
        self.assertEqual(out.splitlines(), ["notes/talk.md:1: Met [[apollo]] and [[apollo]] and [[Apollo]] today"])


class DoctorSettings(VaultCase):
    def test_doctor_reads_the_vault_config_from_a_subfolder(self):
        self.write(".pkm/config", "format=1\nlimit=0\n")
        self.write("notes/deep/x.md", "# X\n")
        from helpers import run_pkm, pkm_env
        result = run_pkm(["doctor"], cwd=self.root / "notes" / "deep", env=pkm_env(XDG_CONFIG_HOME=self.config_home),
                         vault=self.root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("limit", result.stdout)

    def test_a_numeric_setting_below_one_or_not_a_number_is_a_problem(self):
        self.write(".pkm/config", "format=1\nlimit=0\ndue_soon_days=x\nwaiting_days=2\n")
        result = self.pkm("doctor")
        self.assertEqual(result.returncode, 1)
        self.assertIn("limit", result.stdout)
        self.assertIn("due_soon_days", result.stdout)
        self.assertNotIn("waiting_days", result.stdout)


class TitleLosingLetters(VaultCase):
    def test_a_title_whose_slug_drops_letters_asks_for_a_name(self):
        result = self.pkm("new", "topic", "日本語 note")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--name", result.stderr)
        self.assertFalse(self.exists("notes/note.md"))

    def test_the_same_title_with_a_name_is_made(self):
        self.assertEqual(self.ok("new", "topic", "日本語 note", "--name", "nihongo-note").strip(), "notes/nihongo-note.md")


if __name__ == "__main__":
    import unittest

    unittest.main()
