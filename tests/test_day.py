"""Tests for the day pages and for add: the page path, shared vaults, entries and their line numbers, and the example
vaults as acceptance tests (on temporary copies, since the examples are not to be changed).
Run: python3 -m unittest discover -s tests
"""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import REPO, pkm_env, run_pkm

EXAMPLES = REPO / "docs/examples"


class DayCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        self.config = self.tmp / "config"
        self.config.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def copy_example(self, name):
        target = self.tmp / name
        shutil.copytree(EXAMPLES / name, target)
        return target

    def empty_vault(self):
        vault = self.tmp / "empty"
        (vault / ".pkm").mkdir(parents=True)
        return vault

    def set_writer(self, writer):
        (self.config / "pkm").mkdir(exist_ok=True)
        (self.config / "pkm/config").write_text(f"writer={writer}\n")

    def run_pkm(self, vault, args, now, stdin=None, env=None):
        environment = pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=str(self.config), **(env or {}))
        if stdin is None:
            return run_pkm(list(args), cwd=vault, env=environment, vault=vault)
        feed = self.tmp / "stdin.txt"
        feed.write_text(stdin)
        with open(feed) as handle:
            return run_pkm(list(args), cwd=vault, env=environment, vault=vault, stdin=handle)


class AddAcceptance(DayCase):
    def test_marta_is_posted_to_the_work_day_and_the_line_matches_the_method(self):
        vault = self.copy_example("work")
        result = self.run_pkm(vault, ["add", "[[marta-kovac|Marta Kovac]] is [[acme|Acme]]'s project lead"], "20261116090500")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md:8")
        lines = (vault / "daybook/2026/11/2026-11-16.md").read_text().split("\n")
        self.assertEqual(lines[7], "- 09:05 [[marta-kovac|Marta Kovac]] is [[acme|Acme]]'s project lead")

    def test_a_shared_vault_writes_the_writers_page_from_the_template(self):
        vault = self.copy_example("family")
        self.set_writer("alex")
        result = self.run_pkm(vault, ["add", "Paid the rent"], "20261115200000")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-15-alex.md:7")
        text = (vault / "daybook/2026/11/2026-11-15-alex.md").read_text()
        self.assertTrue(text.startswith("# 2026-11-15 Alex\n\n## Tasks\n\n## Log\n\n- 20:00 Paid the rent\n"), text)

    def test_an_empty_vault_gets_its_first_page(self):
        vault = self.empty_vault()
        result = self.run_pkm(vault, ["add", "Started a daybook"], "20261116083000")
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md:7")
        self.assertEqual((vault / "daybook/2026/11/2026-11-16.md").read_text().split("\n")[6],
                         "- 08:30 Started a daybook")


class PagesAndEntries(DayCase):
    def test_a_shared_vault_without_a_writer_exits_2_with_one_line(self):
        vault = self.copy_example("family")
        result = self.run_pkm(vault, ["day"], "20261115200000")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("writer=", result.stderr)

    def test_a_shared_day_page_title_has_the_writers_name_capitalised(self):
        vault = self.copy_example("family")
        self.set_writer("sam")
        result = self.run_pkm(vault, ["day", "2026-11-13"], "20261115200000")
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-13-sam.md")
        self.assertEqual((vault / result.stdout.strip()).read_text().split("\n")[0], "# 2026-11-13 Sam")

    def test_day_returns_a_page_an_editor_made_flat_and_creates_no_second_one(self):
        vault = self.empty_vault()
        (vault / "daybook").mkdir()
        (vault / "daybook/2026-11-17.md").write_text("# 2026-11-17\n\n## Log\n\n- 10:00 Flat page\n")
        result = self.run_pkm(vault, ["day", "2026-11-17"], "20261116083000")
        self.assertEqual(result.stdout.strip(), "daybook/2026-11-17.md")
        self.assertFalse((vault / "daybook/2026/11/2026-11-17.md").exists())

    def test_day_creates_the_month_folder_and_is_idempotent(self):
        vault = self.empty_vault()
        first = self.run_pkm(vault, ["day"], "20261116083000").stdout
        second = self.run_pkm(vault, ["day"], "20261116083000").stdout
        self.assertEqual(first, "daybook/2026/11/2026-11-16.md\n")
        self.assertEqual(first, second)

    def test_day_edit_opens_the_page_in_the_editor(self):
        vault = self.empty_vault()
        result = self.run_pkm(vault, ["day", "--edit"], "20261116083000", env={"EDITOR": "true"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md")

    def test_a_missing_log_section_is_added_at_the_end(self):
        vault = self.empty_vault()
        (vault / "daybook/2026/11").mkdir(parents=True)
        (vault / "daybook/2026/11/2026-11-16.md").write_text("# 2026-11-16\n\n## Tasks\n")
        result = self.run_pkm(vault, ["add", "Late entry"], "20261116083000")
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md:7")
        self.assertEqual((vault / "daybook/2026/11/2026-11-16.md").read_text(),
                         "# 2026-11-16\n\n## Tasks\n\n## Log\n\n- 08:30 Late entry\n")

    def test_an_entry_goes_after_the_last_entry_of_the_log_not_after_the_next_section(self):
        vault = self.copy_example("work")
        self.run_pkm(vault, ["add", "After the first entry"], "20261116083000")
        text = (vault / "daybook/2026/11/2026-11-16.md").read_text()
        self.assertTrue(text.index("After the first entry") > text.index("john-roe"))

    def test_several_lines_go_under_a_heading_verbatim_from_stdin(self):
        vault = self.empty_vault()
        result = self.run_pkm(vault, ["add", "-"], "20261116083000", stdin="Call notes\n  - indented\n\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (vault / "daybook/2026/11/2026-11-16.md").read_text()
        self.assertIn("\n### 08:30\n\nCall notes\n  - indented\n", text)
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md:7")

    def test_empty_input_exits_2(self):
        vault = self.empty_vault()
        self.assertEqual(self.run_pkm(vault, ["add", ""], "20261116083000").returncode, 2)
        self.assertEqual(self.run_pkm(vault, ["add", "-"], "20261116083000", stdin="\n\n").returncode, 2)

    def test_day_backfills_an_earlier_page(self):
        vault = self.empty_vault()
        result = self.run_pkm(vault, ["add", "--day", "2026-11-10", "Forgot to write this"], "20261116083000")
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-10.md:7")
        self.assertFalse((vault / "daybook/2026/11/2026-11-16.md").exists())


if __name__ == "__main__":
    unittest.main()
