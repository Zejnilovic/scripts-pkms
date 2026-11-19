"""Tests for since, close and new close, on copies of the work and family examples, plus the unit behaviour of since
(state, arguments, sections, --about, --limit, --json). Run: python3 -m unittest discover -s tests.
Names and data are made up. The work example is read on 2026-11-16 (PKM_NOW 20261116090500).
"""

import json
import pathlib
import re
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

WORK_NOW = "20261116090500"
FAMILY_NOW = "20261115090000"

# The excerpt of the agentic methodology (docs/methodology.md, the digest), with "…" marks removed.
EXCERPT_LOG = [
    "daybook/2026/11/2026-11-10.md:9: - ! They may cancel the contract if the demo slips again",
    "daybook/2026/11/2026-11-10.md:10: - Decided: we cut the mobile app from the first release",
    "daybook/2026/11/2026-11-10.md:11: - Their new contact is Marta Kovac",
    "daybook/2026/11/2026-11-10.md:12: - I'll send them the revised timeline by Thursday",
    "daybook/2026/11/2026-11-12.md:7: - 09:30 Sent [[acme]] the revised timeline",
]
EXCERPT_TASKS = [
    "daybook/2026/11/2026-11-09.md:5: overdue: - [ ] Send [[john-roe]] the Apollo invoice for October (due 2026-11-13) (high)",
    "daybook/2026/11/2026-11-11.md:5: waiting 5 days: - [ ] Budget approval from [[john-roe]] for [[apollo]] (waiting 2026-11-11)",
    "notes/routines.md:7: overdue: - [ ] Send the sprint summary (due 2026-11-15) (every sprint)",
]
EXCERPT_MARKED = [
    "daybook/2026/11/2026-11-10.md:9: - ! They may cancel the contract if the demo slips again",
    "daybook/2026/11/2026-11-10.md:10: - Decided: we cut the mobile app from the first release",
    "daybook/2026/11/2026-11-12.md:9: - 17:40 Decide with the team: should we move the demo to a Tuesday?",
    "daybook/2026/11/2026-11-12.md:10: - 17:55 Idea: a self-service export for [[acme]], maybe next year",
]


def sections(text):
    """The sections of a since output: {header: [lines]}."""
    result, current = {}, None
    for line in text.splitlines():
        if line.startswith("== "):
            current = line[3:].split(" ")[0]
            result[current] = []
        elif current is not None and line:
            result[current].append(line)
    return result


class ExampleCopy(unittest.TestCase):
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

    def pkm(self, vault, *args, now=WORK_NOW, env=None):
        environment = pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=self.config_home, **(env or {}))
        return run_pkm(args, cwd=vault, env=environment, vault=vault)

    def ok(self, vault, *args, **kwargs):
        result = self.pkm(vault, *args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout


class SinceOnTheWorkExample(ExampleCopy):
    def setUp(self):
        super().setUp()
        self.vault = self.copy("work")
        self.out = self.ok(self.vault, "since", "2026-11-09")
        self.parts = sections(self.out)

    def assert_in_order(self, section, expected):
        lines = self.parts[section]
        position = 0
        for want in expected:
            self.assertIn(want, lines[position:], f"{want!r} is missing or out of order in == {section}")
            position = lines.index(want, position) + 1

    def test_the_log_has_the_excerpt_lines_in_order(self):
        self.assert_in_order("log", EXCERPT_LOG)

    def test_the_tasks_have_the_excerpt_lines_in_order(self):
        self.assert_in_order("tasks", EXCERPT_TASKS)

    def test_the_marked_entries_have_the_excerpt_lines_in_order(self):
        self.assert_in_order("marked", EXCERPT_MARKED)

    def test_the_names_have_the_counts_and_last_days_of_the_excerpt(self):
        names = {}
        for line in self.parts["names"]:
            match = re.match(r"^(\S+)\s+(\d+) mentions?\s+last (.+)$", line)
            self.assertTrue(match, line)
            names[match.group(1)] = (int(match.group(2)), match.group(3))
        self.assertEqual(names.get("john-roe"), (4, "today"))
        self.assertEqual(names.get("apollo"), (4, "4 days ago"))
        # Most mentions first; names with as many mentions come by name.
        self.assertEqual(list(names)[:3], ["acme", "apollo", "john-roe"])

    def test_the_sections_are_in_order_and_empty_ones_are_left_out(self):
        self.assertEqual(list(self.parts), ["log", "tasks", "marked", "names"])

    def test_about_keeps_the_lines_under_a_heading_that_links_the_name(self):
        out = sections(self.ok(self.vault, "since", "2026-11-09", "--about", "apollo"))
        self.assertIn("daybook/2026/11/2026-11-10.md:9: - ! They may cancel the contract if the demo slips again", out["log"])
        self.assertIn("daybook/2026/11/2026-11-10.md:12: - I'll send them the revised timeline by Thursday", out["log"])
        self.assertNotIn("daybook/2026/11/2026-11-12.md:7: - 09:30 Sent [[acme]] the revised timeline", out["log"])
        same = self.ok(self.vault, "since", "2026-11-09", "--about", "apollo")
        for name in ["[[apollo]]", "notes/apollo.md"]:
            self.assertEqual(self.ok(self.vault, "since", "2026-11-09", "--about", name), same, name)

    def test_json_gives_a_kind_per_line_and_task_state_and_days(self):
        rows = [json.loads(line) for line in self.ok(self.vault, "since", "2026-11-09", "--json").splitlines()]
        kinds = {row["kind"] for row in rows}
        self.assertTrue({"log", "task", "marked", "name"} <= kinds, kinds)
        overdue = [row for row in rows if row["kind"] == "task" and row["path"] == "notes/routines.md"][0]
        self.assertEqual(overdue["state"], "open")
        self.assertIsNotNone(overdue["days"])
        name = [row for row in rows if row["kind"] == "name" and row.get("name") == "john-roe"][0]
        self.assertEqual(name["count"], 4)
        self.assertEqual(name["last"], "2026-11-16")

    def test_limit_applies_per_section_with_the_footer_on_stderr(self):
        result = self.pkm(self.vault, "since", "2026-11-09", "--limit", "1")
        self.assertEqual(result.returncode, 0)
        for section, lines in sections(result.stdout).items():
            self.assertEqual(len(lines), 1, section)
        self.assertIn("more (use --limit)", result.stderr)

    def test_nothing_since_prints_one_line_and_exits_1(self):
        vault = self.base / "quiet"
        (vault / ".pkm").mkdir(parents=True)
        (vault / "daybook/2026/10").mkdir(parents=True)
        (vault / "daybook/2026/10/2026-10-01.md").write_text("# 2026-10-01\n\n## Log\n\n- Quiet day\n")
        result = self.pkm(vault, "since", "2026-12-01")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "Nothing since 2026-12-01.")


class FrontmatterOutsideSections(VaultCase):
    """A day page's frontmatter is not log, and not a question either: since and close leave it out."""

    def setUp(self):
        super().setUp()
        self.write("daybook/2026/10/2026-10-25.md",
                   "---\nmood: fine\nsummary: is it ok?\n---\n# 2026-10-25\n\n## Log\n\n- 09:00 a real entry\n")

    def test_since_does_not_list_the_frontmatter_as_log(self):
        out = sections(self.ok("since", "2026-10-25"))
        self.assertEqual(out["log"], ["daybook/2026/10/2026-10-25.md:9: - 09:00 a real entry"])

    def test_close_does_not_list_a_frontmatter_question(self):
        out = self.ok("close", now="20261026090000")
        self.assertNotIn("summary: is it ok?", out)
        self.assertNotIn("mood: fine", out)


class SinceState(ExampleCopy):
    def setUp(self):
        super().setUp()
        self.vault = self.copy("work")

    def test_seen_writes_today_and_last_starts_there(self):
        result = self.pkm(self.vault, "since", "--seen")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)
        self.assertIn("2026-11-16", result.stdout)
        # The state keeps the seen time too (requirement change: since last leaves out the entries seen).
        self.assertEqual((self.vault / ".pkm/state").read_text().strip(), "since=2026-11-16 09:05")

    def test_seen_takes_no_other_argument(self):
        self.assertEqual(self.pkm(self.vault, "since", "--seen", "2026-11-09").returncode, 2)

    def test_last_without_state_is_the_last_seven_days(self):
        out = sections(self.ok(self.vault, "since", "last"))
        self.assertIn("daybook/2026/11/2026-11-10.md:9: - ! They may cancel the contract if the demo slips again", out["log"])
        self.assertNotIn("daybook/2026/11/2026-11-09.md", "\n".join(out["log"]))

    def test_a_number_is_today_and_the_days_before(self):
        out = sections(self.ok(self.vault, "since", "3"))
        self.assertNotIn("daybook/2026/11/2026-11-11.md:10: - 14:20 [[john-roe]] says the budget needs his manager's sign-off", out.get("log", []))

    def test_a_cycle_name_is_the_period_holding_yesterday(self):
        out = self.ok(self.vault, "since", "week")
        self.assertIn("daybook/2026/11/2026-11-09.md", out)


class CloseOnTheWorkExample(ExampleCopy):
    def setUp(self):
        super().setUp()
        self.vault = self.copy("work")
        self.out = self.ok(self.vault, "close")
        self.parts = sections(self.out)

    def test_the_first_line_names_the_period_and_its_page(self):
        self.assertRegex(self.out.splitlines()[0],
                         r"^== week 2026-11-09 to 2026-11-15: \d+ entries \(closes/2026/2026-11-09-week\.md\)$")

    def test_tasks_has_the_overdue_invoice_and_the_sprint_summary(self):
        lines = self.parts["tasks"]
        self.assertTrue(any("overdue: - [ ] Send [[john-roe]] the Apollo invoice" in line for line in lines), lines)
        self.assertTrue(any("overdue: - [ ] Send the sprint summary" in line for line in lines), lines)

    def test_open_has_the_budget_wait_and_the_demo_question(self):
        lines = self.parts["open"]
        self.assertTrue(any("waiting 5 days: - [ ] Budget approval" in line for line in lines), lines)
        self.assertTrue(any("question: - 17:40 Decide with the team: should we move the demo to a Tuesday?" in line for line in lines), lines)

    def test_due_has_the_timesheet_and_the_birthday_coming_due(self):
        lines = "\n".join(self.parts["due"])
        self.assertIn("2026-11-20", lines)
        self.assertIn("birthday", lines)

    def test_quiet_is_empty_because_the_vault_is_a_week_old(self):
        self.assertNotIn("quiet", self.parts)

    def test_close_exits_0(self):
        self.assertEqual(self.pkm(self.vault, "close").returncode, 0)


class CloseOnTheFamilyExample(ExampleCopy):
    def test_marked_and_open_are_in_path_then_line_order(self):
        vault = self.copy("family")
        parts = sections(self.ok(vault, "close", now=FAMILY_NOW))
        for section in ["marked", "open"]:
            keys = []
            for line in parts[section]:
                path, number = line.split(":")[0], int(line.split(":")[1])
                keys.append((path, number))
            self.assertEqual(keys, sorted(keys), section)
        self.assertTrue(len(parts["marked"]) >= 2, parts["marked"])

    def test_the_names_use_the_singular_for_one_mention(self):
        vault = self.copy("work")
        out = sections(self.ok(vault, "since", "2026-11-09"))
        names = out["names"]
        self.assertTrue(any(line.endswith("mention  last 5 days ago") for line in names), names)
        self.assertFalse(any(" 1 mentions" in line for line in names), names)

    def test_the_family_close_lists_the_overdue_and_the_coming_due(self):
        vault = self.copy("family")
        parts = sections(self.ok(vault, "close", now=FAMILY_NOW))
        tasks = "\n".join(parts.get("tasks", []))
        open_lines = "\n".join(parts.get("open", []))
        due = "\n".join(parts.get("due", []))
        self.assertIn("overdue", tasks)
        self.assertIn("question: ", open_lines)
        for want in ["2026-11-15", "2026-11-20"]:
            self.assertIn(want, due)


class DoneOnTheWorkExample(ExampleCopy):
    def test_done_moves_the_sprint_summary_to_the_next_period(self):
        vault = self.copy("work")
        out = self.ok(vault, "done", "sprint summary").strip()
        self.assertEqual(out, "notes/routines.md:7: - [ ] Send the sprint summary (due 2026-11-29) (every sprint)")
        self.assertIn("(due 2026-11-29) (every sprint)", (vault / "notes/routines.md").read_text())


class CycleOnTheExamples(ExampleCopy):
    def test_work_sprint_and_family_pay_periods(self):
        vault = self.copy("work")
        self.assertEqual(self.ok(vault, "cycle", "sprint", "--date", "2026-11-16").strip(), "sprint\t2026-11-16\t2026-11-29")
        family = self.copy("family")
        self.assertEqual(self.ok(family, "cycle", "pay", "--date", "2026-11-14", now=FAMILY_NOW).strip(),
                         "pay\t2026-10-15\t2026-11-14")


class NewClose(ExampleCopy):
    def test_new_close_writes_the_close_page_and_refuses_an_existing_one(self):
        vault = self.copy("work")
        path = "closes/2026/2026-11-09-week.md"
        self.assertEqual(self.ok(vault, "new", "close").strip(), path)
        text = (vault / path).read_text()
        self.assertIn("# Week of 2026-11-09", text)
        self.assertTrue(text.rstrip().endswith("# Week of 2026-11-09"), text)
        again = self.pkm(vault, "new", "close")
        self.assertEqual(again.returncode, 1)
        self.assertIn(path, again.stdout)

    def test_new_close_takes_no_title(self):
        vault = self.copy("work")
        self.assertEqual(self.pkm(vault, "new", "close", "Some title").returncode, 2)


if __name__ == "__main__":
    unittest.main()
