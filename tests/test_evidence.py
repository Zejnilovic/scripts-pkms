"""Tests for evidence (what a source is, --verify, the Now section, close pages, stdin, the brief of the methodology)
and links --external. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import json
import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

SUMMARY = """---
type: project
---

# Summary

## Now

- Shipped the plan ([[2026-10-24]])
- Jane is on board ([[jane-doe]])
- Costs fell ([[paper]])
- Risk stays (notes/apollo.md:3)
- Late link [[nobody]]
- ~~Old claim~~
- Plain web source https://example.com/report
> - Quoted claim without source
> - Quoted list item with a day ([[2026-10-24]])
"""


class EvidenceRules(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("daybook/2026/10/2026-10-24.md", "# 2026-10-24\n")
        self.write("notes/paper.md", "---\ntype: source\n---\n\n# Paper\n")
        self.write("people/jane-doe.md", "---\ntype: person\n---\n\n# Jane Doe\n")
        self.write("notes/summary.md", SUMMARY)

    def test_only_lines_without_a_source_are_listed_with_their_place(self):
        result = self.pkm("evidence", "notes/summary.md")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "notes/summary.md:10: - Jane is on board ([[jane-doe]])",
            "notes/summary.md:13: - Late link [[nobody]]",
            "notes/summary.md:16: - Quoted claim without source",
        ])

    def test_verify_reports_missing_files_lines_and_broken_links(self):
        out = self.pkm("evidence", "--verify", "notes/summary.md").stdout.splitlines()
        self.assertIn("notes/summary.md:12: no such file: notes/apollo.md", out)
        self.assertIn("notes/summary.md:13: broken link [[nobody]]", out)
        self.assertIn("notes/summary.md:12: - Risk stays (notes/apollo.md:3)", out)
        self.assertFalse([line for line in out if line.startswith("notes/summary.md:9:")])

    def test_verify_passes_a_path_and_line_that_exist(self):
        self.write("notes/apollo.md", "# Apollo\n\n- one\n")
        self.write("notes/ok.md", "## Now\n\n- Risk ok (notes/apollo.md:3)\n")
        self.assertEqual(self.pkm("evidence", "--verify", "notes/ok.md").returncode, 0)

    def test_a_path_past_the_end_of_its_file_fails_on_that_line(self):
        self.write("notes/apollo.md", "# Apollo\n\n- one\n")
        self.write("notes/ok.md", "## Now\n\n- Risk moved (notes/apollo.md:99)\n")
        result = self.pkm("evidence", "--verify", "notes/ok.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/ok.md:3: no such line: notes/apollo.md:99 (it has 3 lines)", result.stdout)
        self.assertIn("notes/ok.md:3: - Risk moved", result.stdout)

    def test_a_note_checks_only_its_now_section(self):
        self.write("notes/x.md", "# X\n\n## Now\n\n- Claim without source\n\n## Log\n\n- Log item without source\n")
        result = self.pkm("evidence", "notes/x.md")
        self.assertEqual(result.stdout.splitlines(), ["notes/x.md:5: - Claim without source"])

    def test_a_note_without_a_now_section_exits_1(self):
        self.write("notes/y.md", "# Y\n\n- item\n")
        result = self.pkm("evidence", "notes/y.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Now", result.stdout + result.stderr)

    def test_a_close_page_is_checked_whole(self):
        self.write("closes/week-43.md", "# Week 43\n\n- Whole page item\n")
        self.assertEqual(self.pkm("evidence", "closes/week-43.md").stdout.splitlines(),
                         ["closes/week-43.md:3: - Whole page item"])

    def test_stdin_is_reported_with_a_dash(self):
        result = self.pkm("evidence", "-", stdin="- Claim without source\n> - Sourced ([[2026-10-24]])\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines(), ["-:1: - Claim without source"])

    def test_it_needs_a_note_or_a_dash(self):
        self.assertEqual(self.pkm("evidence").returncode, 2)
        self.assertEqual(self.pkm("evidence", "nothing-here").returncode, 1)

    def test_check_does_not_report_evidence(self):
        (self.root / "notes/summary.md").unlink()
        self.write("notes/x.md", "## Now\n\n- Claim without source\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Claim", result.stdout)


class LinksExternal(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/web.md", "# Web\n\n"
                   "- Board: https://dev.example.test/apollo/board\n"
                   "- See [the plan](https://example.test/plan).\n"
                   "- Twice https://example.test/a and https://example.test/b\n"
                   "`https://example.test/code` in code\n"
                   "```\nhttps://example.test/fenced\n```\n")

    def test_each_address_is_listed_with_its_place_outside_code(self):
        self.assertEqual(self.ok("links", "--external").splitlines(), [
            "notes/web.md:3: https://dev.example.test/apollo/board",
            "notes/web.md:4: https://example.test/plan",
            "notes/web.md:5: https://example.test/a",
            "notes/web.md:5: https://example.test/b",
        ])

    def test_json_gives_path_line_and_url(self):
        rows = [json.loads(line) for line in self.ok("links", "--external", "--json").splitlines()]
        self.assertEqual(rows[1], {"path": "notes/web.md", "line": 4, "url": "https://example.test/plan"})

    def test_a_note_limits_the_list_and_an_unknown_note_exits_1(self):
        self.assertEqual(len(self.ok("links", "--external", "notes/web.md").splitlines()), 4)
        self.assertEqual(self.pkm("links", "--external", "nothing-here").returncode, 1)

    def test_plain_links_is_a_usage_error_that_points_to_backlinks(self):
        result = self.pkm("links")
        self.assertEqual(result.returncode, 2)
        self.assertIn("pkm backlinks", result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1)


class Brief(unittest.TestCase):
    """The brief of docs/methodology.md in the agentic-pkms repo (lines 127-142), with its quote marks removed, checked
    against a copy of the work vault."""

    BRIEF = pathlib.Path(REPO).parent / "agentic-pkms/docs/methodology.md"

    def setUp(self):
        if not self.BRIEF.exists():
            self.skipTest("the agentic-pkms repo is not next to this one")
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self._tmp.name) / "work"
        shutil.copytree(REPO / "docs/examples/work", self.vault)
        self.lines = [line[2:] if line.startswith("> ") else line
                      for line in self.BRIEF.read_text().splitlines()[126:142]]

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def evidence(self, text):
        environment = pkm_env(PKM_NOW="20261116090500", XDG_CONFIG_HOME=self._config.name)
        return run_pkm(["evidence", "--verify", "-"], cwd=self.vault, env=environment, vault=self.vault, stdin=text)

    def test_the_brief_passes(self):
        result = self.evidence("\n".join(self.lines) + "\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_path_moved_past_the_end_of_its_file_fails_on_that_line(self):
        index = [i for i, line in enumerate(self.lines) if "2026-11-10.md:11" in line][0]
        self.lines[index] = self.lines[index].replace("2026-11-10.md:11", "2026-11-10.md:999")
        result = self.evidence("\n".join(self.lines) + "\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"-:{index + 1}: ", result.stdout)


if __name__ == "__main__":
    unittest.main()
