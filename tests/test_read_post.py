"""Tests for get, post and strike: sections, the day suffix, placement, refusals, and the acceptance runs on copies of
the work and family examples (the Marta Kovac flow of the methodology and the bathroom's struck line). Run:
python3 -m unittest discover -s tests. Names and data are made up.
"""

import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

APOLLO = """---
type: project
aliases: [Portal]
---

# Apollo

## Now

- Demo moved ([[2026-11-09]])

## Goals

- Launch in December

### Milestones

- First release

## Risks

## Decisions

- Earlier decision

## Later

- Someday
"""

DAY = "# 2026-10-24\n\n## Tasks\n\n## Log\n\n- Decided: keep the plan\n- Second line\n"
SUFFIX = " ([[2026-10-24]])"


class GetSections(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", APOLLO)

    def test_a_section_runs_to_the_next_heading_of_the_same_or_a_higher_level(self):
        out = self.ok("get", "apollo#Goals")
        self.assertIn("### Milestones", out)
        self.assertIn("- First release", out)
        self.assertNotIn("## Risks", out)
        self.assertNotIn("Demo moved", out)

    def test_the_heading_matches_in_any_case_and_any_level(self):
        out = self.ok("get", "apollo#milestones")
        self.assertIn("### Milestones", out)
        self.assertNotIn("## Risks", out)

    def test_a_link_names_the_note_and_its_section_as_path_does(self):
        self.assertEqual(self.ok("get", "[[apollo#Goals]]").splitlines()[0], "<<<note notes/apollo.md lines 12-18")
        self.assertIn("- Earlier decision", self.ok("get", "[[apollo#Decisions|the decisions]]"))
        self.assertEqual(self.ok("get", "[[Portal|Apollo]]").splitlines()[0], "<<<note notes/apollo.md lines 1-28")

    def test_the_header_and_footer_name_the_note_and_its_lines(self):
        out = self.ok("get", "apollo#Goals").splitlines()
        self.assertEqual(out[0], "<<<note notes/apollo.md lines 12-18")
        self.assertEqual(out[-1], ">>>end")

    def test_no_section_prints_the_whole_note(self):
        out = self.ok("get", "apollo").splitlines()
        self.assertEqual(out[0], "<<<note notes/apollo.md lines 1-28")
        self.assertIn("- Someday", out)

    def test_lines_use_the_notes_own_line_numbers(self):
        out = self.ok("get", "apollo", "--lines", "10-10").splitlines()
        self.assertEqual(out, ["<<<note notes/apollo.md lines 10-10", "- Demo moved ([[2026-11-09]])", ">>>end"])
        out = self.ok("get", "apollo#Goals", "--lines", "14-14").splitlines()
        self.assertEqual(out[1], "- Launch in December")

    def test_lines_outside_the_section_are_refused(self):
        self.assertEqual(self.pkm("get", "apollo#Goals", "--lines", "1-2").returncode, 1)

    def test_an_alias_resolves_like_path(self):
        self.assertIn("- Earlier decision", self.ok("get", "Portal#Decisions"))

    def test_missing_section_or_note_exits_1_and_a_bad_range_exits_2(self):
        self.assertEqual(self.pkm("get", "apollo#Nowhere").returncode, 1)
        self.assertEqual(self.pkm("get", "nobody-here").returncode, 1)
        self.assertEqual(self.pkm("get", "apollo", "--lines", "5-3").returncode, 2)
        # An end past the last line is clamped to it (requirement change): the start is still checked.
        self.assertEqual(self.pkm("get", "apollo", "--lines", "1-999").returncode, 0)
        self.assertEqual(self.pkm("get", "apollo", "--lines", "999-1000").returncode, 2)


class PostPlacement(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", APOLLO)
        self.write("daybook/2026/10/2026-10-24.md", DAY)
        self.source = "daybook/2026/10/2026-10-24.md"

    def assert_refused(self, spec, target, code=1):
        result = self.pkm("post", spec, target)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stderr

    def test_the_entry_goes_after_the_last_line_of_the_section_with_the_day_suffix(self):
        self.assertEqual(self.ok("post", f"{self.source}:7", "apollo#Decisions").strip(), "notes/apollo.md:25")
        self.assertEqual(self.read("notes/apollo.md"),
                         APOLLO.replace("- Earlier decision\n", "- Earlier decision\n- Decided: keep the plan" + SUFFIX + "\n"))

    def test_a_range_posts_each_line_and_the_suffix_only_on_the_last(self):
        self.ok("post", f"{self.source}:7-8", "apollo#Decisions")
        self.assertEqual(self.read("notes/apollo.md"),
                         APOLLO.replace("- Earlier decision\n",
                                        "- Earlier decision\n- Decided: keep the plan\n- Second line" + SUFFIX + "\n"))

    def test_an_empty_section_gets_a_blank_line_and_then_the_entry(self):
        self.assertEqual(self.ok("post", f"{self.source}:7", "apollo#Risks").strip(), "notes/apollo.md:22")
        self.assertIn("## Risks\n\n- Decided: keep the plan" + SUFFIX + "\n\n## Decisions", self.read("notes/apollo.md"))

    def test_a_missing_section_is_created_at_the_end_as_given(self):
        self.assertEqual(self.ok("post", f"{self.source}:7", "apollo#Plans to test").strip(), "notes/apollo.md:32")
        self.assertEqual(self.read("notes/apollo.md"),
                         APOLLO + "\n## Plans to test\n\n- Decided: keep the plan" + SUFFIX + "\n")

    def test_a_note_that_ends_after_its_heading_gets_a_blank_line_then_the_entry(self):
        self.write("people/jane-doe.md", "---\ntype: person\n---\n\n# Jane Doe\n")
        self.assertEqual(self.ok("post", f"{self.source}:7", "jane-doe").strip(), "people/jane-doe.md:7")
        self.assertEqual(self.read("people/jane-doe.md"),
                         "---\ntype: person\n---\n\n# Jane Doe\n\n- Decided: keep the plan" + SUFFIX + "\n")


class PostRefusals(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", APOLLO)
        self.write("daybook/2026/10/2026-10-24.md", DAY)
        self.write("closes/week-43.md", "# Week 43\n")
        self.source = "daybook/2026/10/2026-10-24.md"

    def assert_refused(self, *args, code=1):
        before = {p: self.read(p) for p in ["notes/apollo.md"]}
        result = self.pkm("post", *args)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertEqual({p: self.read(p) for p in before}, before)
        return result.stderr

    def test_a_range_with_a_heading_is_refused(self):
        self.write("notes/src.md", "- one\n## Two\n- three\n")
        self.assertIn("heading", self.assert_refused("notes/src.md:1-2", "apollo#Decisions"))

    def test_an_open_task_is_refused(self):
        self.write("notes/todo.md", "- [ ] Send the invoice\n")
        self.assertIn("open task", self.assert_refused("notes/todo.md:1", "apollo#Decisions"))

    def test_a_day_or_close_target_is_refused(self):
        self.assertIn("day", self.assert_refused("daybook/2026/10/2026-10-24.md:7", "2026-10-24"))
        self.assertIn("close", self.assert_refused("daybook/2026/10/2026-10-24.md:7", "week-43"))

    def test_a_missing_target_exits_1(self):
        self.assert_refused("daybook/2026/10/2026-10-24.md:7", "nobody-here")

    def test_an_entry_already_in_the_note_is_not_written_twice(self):
        self.ok("post", f"{self.source}:7", "apollo#Decisions")
        before = self.read("notes/apollo.md")
        result = self.pkm("post", f"{self.source}:7", "apollo#Decisions")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "notes/apollo.md:25")
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("posted there already", result.stderr)
        self.assertEqual(self.read("notes/apollo.md"), before)

    def test_a_range_already_in_the_note_is_not_written_twice(self):
        self.ok("post", f"{self.source}:7-8", "apollo#Decisions")
        before = self.read("notes/apollo.md")
        result = self.pkm("post", f"{self.source}:7-8", "apollo#Decisions")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "notes/apollo.md:25")
        self.assertEqual(self.read("notes/apollo.md"), before)

    def test_the_wording_says_line_or_lines(self):
        self.assertIn("Line 99 is outside", self.assert_refused(f"{self.source}:99", "apollo", code=2))
        self.assertIn("Lines 7-99 are outside", self.assert_refused(f"{self.source}:7-99", "apollo", code=2))

    def test_a_malformed_source_or_a_line_out_of_range_exits_2(self):
        self.assert_refused("daybook/2026/10/2026-10-24.md", "apollo", code=2)
        self.assert_refused("../outside.md:1", "apollo", code=2)
        self.assert_refused("daybook/2026/10/2026-10-24.md:99", "apollo", code=2)
        self.assert_refused("daybook/2026/10/2026-10-24.md:7-6", "apollo", code=2)


class StrikeTests(VaultCase):
    """NOW is 2026-10-25, so the day's page is daybook/2026/10/2026-10-25.md."""

    def setUp(self):
        super().setUp()
        self.write("notes/plan.md", "# Plan\n\n  - Book the room\n")

    def test_a_list_item_keeps_its_indent_and_links_today(self):
        self.assertEqual(self.ok("strike", "notes/plan.md:3").strip(), "notes/plan.md:3")
        self.assertEqual(self.read("notes/plan.md").splitlines()[2], "  - ~~Book the room~~ ([[2026-10-25]])")
        self.assertTrue(self.exists("daybook/2026/10/2026-10-25.md"))

    def test_a_task_keeps_its_box(self):
        self.write("notes/plan.md", "- [ ] Book the room\n")
        self.ok("strike", "notes/plan.md:1")
        self.assertEqual(self.read("notes/plan.md"), "- [ ] ~~Book the room~~ ([[2026-10-25]])\n")

    def test_a_heading_blank_or_struck_line_is_refused_and_writes_nothing(self):
        self.write("notes/plan.md", "# Plan\n\n- ~~Old~~\n")
        for line in ["1", "2", "3"]:
            with self.subTest(line=line):
                self.assertEqual(self.pkm("strike", f"notes/plan.md:{line}").returncode, 1)
        self.assertEqual(self.read("notes/plan.md"), "# Plan\n\n- ~~Old~~\n")
        self.assertFalse(self.exists("daybook/2026/10/2026-10-25.md"))

    def test_the_link_it_adds_is_not_dead(self):
        self.ok("strike", "notes/plan.md:3")
        self.assertEqual(self.pkm("check").returncode, 0)

    def test_a_malformed_argument_exits_2(self):
        self.assertEqual(self.pkm("strike", "notes/plan.md").returncode, 2)
        self.assertEqual(self.pkm("strike", "notes/plan.md:99").returncode, 2)
        self.assertEqual(self.pkm("strike", "../plan.md:1").returncode, 2)


class ExampleVault(unittest.TestCase):
    """Runs on temporary copies of the example vaults; the examples are never changed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self._tmp.name)
        self.config_home = self._config.name

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def copy(self, name):
        vault = self.base / name
        shutil.copytree(REPO / "docs/examples" / name, vault)
        return vault

    def pkm(self, vault, *args, now="20261116090500", env=None):
        environment = pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=self.config_home, **(env or {}))
        return run_pkm(args, cwd=vault, env=environment, vault=vault)

    def ok(self, vault, *args, **kwargs):
        result = self.pkm(vault, *args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_the_marta_flow_of_the_methodology(self):
        vault = self.copy("work")
        self.assertEqual(self.ok(vault, "new", "person", "Marta Kovac").strip(), "notes/marta-kovac.md")
        self.assertEqual(self.ok(vault, "add", "[[marta-kovac|Marta Kovac]] is [[acme|Acme]]'s project lead").strip(),
                         "daybook/2026/11/2026-11-16.md:8")
        self.assertEqual(self.ok(vault, "post", "daybook/2026/11/2026-11-10.md:9", "apollo#Risks").strip(),
                         "notes/apollo.md:31")
        self.assertEqual(self.ok(vault, "post", "daybook/2026/11/2026-11-10.md:10", "apollo#Decisions").strip(),
                         "notes/apollo.md:35")
        self.assertEqual(self.ok(vault, "post", "daybook/2026/11/2026-11-10.md:11", "marta-kovac").strip(),
                         "notes/marta-kovac.md:14")
        self.assertEqual(self.ok(vault, "post", "daybook/2026/11/2026-11-16.md:8", "marta-kovac").strip(),
                         "notes/marta-kovac.md:15")
        self.assertEqual((vault / "notes/marta-kovac.md").read_text(), (
            "---\ntype: person\nsummary:\naliases: [Marta Kovac]\ncreated: 2026-11-16\n---\n\n# Marta Kovac\n\n"
            "## Next time\n\n## Notes\n\n"
            "- Their new contact is Marta Kovac ([[2026-11-10]])\n"
            "- 09:05 [[marta-kovac|Marta Kovac]] is [[acme|Acme]]'s project lead ([[2026-11-16]])\n"))

    def test_one_post_moves_a_decision_and_the_suffix_comes_off_cleanly(self):
        vault = self.copy("work")
        source = "daybook/2026/11/2026-11-10.md"
        original = (vault / source).read_text().splitlines()[9]
        self.assertEqual(original, "- Decided: we cut the mobile app from the first release")
        out = self.ok(vault, "post", f"{source}:10", "apollo#Decisions").strip()
        self.assertTrue(out.startswith("notes/apollo.md:"), out)
        line = int(out.rsplit(":", 1)[1])
        posted = (vault / "notes/apollo.md").read_text().splitlines()[line - 1]
        self.assertEqual(posted, original + " ([[2026-11-10]])")
        self.assertEqual(posted[: -len(" ([[2026-11-10]])")], original)

    def test_the_family_strike_example_of_the_method(self):
        vault = self.copy("family")
        config = pathlib.Path(self.config_home) / "pkm"
        config.mkdir(exist_ok=True)
        (config / "config").write_text("writer=sam\n")
        lines = (vault / "notes/bathroom.md").read_text().splitlines()
        lines[12] = "- [[joe-bloggs-plumber|Joe]] can start on 2026-12-01 ([[2026-11-09-alex]])"
        (vault / "notes/bathroom.md").write_text("\n".join(lines) + "\n")
        out = self.ok(vault, "strike", "notes/bathroom.md:13", now="20261112090000").strip()
        self.assertEqual(out, "notes/bathroom.md:13")
        method_line = "- ~~[[joe-bloggs-plumber|Joe]] can start on 2026-12-01 ([[2026-11-09-alex]])~~ ([[2026-11-12-sam]])"
        self.assertIn(method_line, (REPO / "docs/method.md").read_text().splitlines())
        self.assertEqual((vault / "notes/bathroom.md").read_text().splitlines()[12], method_line)


if __name__ == "__main__":
    unittest.main()
