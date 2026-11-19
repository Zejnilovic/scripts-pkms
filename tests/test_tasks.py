"""Tasks: what counts as one, the order of pkm tasks, relative dates on day pages, done (including interval routines),
todo, upcoming, check's problems, and the acceptance runs on temporary copies of the two example vaults.
Run: python3 -m unittest discover -s tests
"""

import json
import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm


class NovemberCase(VaultCase):
    """Runs pkm on 2026-11-16 at 08:30, the week of the examples, unless a test says otherwise."""

    def pkm(self, *args, now="20261116083000", env=None, stdin=None):
        return super().pkm(*args, now=now, env=env, stdin=stdin)


class TaskDefinition(VaultCase):
    def test_a_task_is_a_box_in_any_note_outside_code(self):
        self.write("notes/apollo.md", "# Apollo\n\n- [ ] In a note (due 2026-10-30)\n\n```\n- [ ] In code\n```\n")
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n- [ ] On a day page\n")
        out = self.ok("tasks")
        self.assertIn("notes/apollo.md:3: - [ ] In a note", out)
        self.assertIn("daybook/2026/10/2026-10-25.md:3: - [ ] On a day page", out)
        self.assertNotIn("In code", out)

    def test_boxes_in_a_list_note_and_struck_lines_are_not_tasks(self):
        self.write("notes/groceries.md", "---\ntype: list\n---\n\n- [ ] Milk\n")
        self.write("notes/old.md", "- ~~[ ] Joe can start~~\n- [ ] ~~Dropped idea~~\n")
        result = self.pkm("tasks")
        self.assertEqual(result.returncode, 1, "no tasks is a 1 in the output contract")
        self.assertEqual(result.stdout, "")

    def test_done_and_dropped_boxes_are_not_open(self):
        self.write("notes/x.md", "- [x] Finished\n- [-] Dropped\n- [ ] Open\n")
        out = self.ok("tasks")
        self.assertIn("Open", out)
        self.assertNotIn("Finished", out)
        self.assertNotIn("Dropped", out)


class OrderOfTasks(NovemberCase):
    def setUp(self):
        super().setUp()
        self.now_day = "2026-11-16"
        self.write("daybook/2026/11/2026-11-10.md", "# 2026-11-10\n\n- [ ] Old overdue (due 2026-11-12)\n")
        self.write("daybook/2026/11/2026-11-14.md", "# 2026-11-14\n\n- [ ] Due soon (due 2026-11-19)\n")
        self.write("daybook/2026/11/2026-11-09.md", "# 2026-11-09\n\n- [ ] Waited long (waiting 2026-11-01)\n")
        self.write("daybook/2026/11/2026-11-15.md", "# 2026-11-15\n\n- [ ] Waited short (waiting 2026-11-12)\n- [ ] Later (due 2026-12-20)\n- [ ] Undated\n")

    def test_overdue_then_due_soon_then_waiting_long_then_the_rest(self):
        records = [json.loads(line) for line in self.pkm("tasks", "--json").stdout.strip().splitlines()]
        names = [r["text"].split("] ")[1].split(" (")[0] for r in records]
        self.assertEqual(names[:3], ["Old overdue", "Due soon", "Waited long"])
        self.assertEqual([r["group"] for r in records[:3]], ["overdue", "due_soon", "waiting_long"])

    def test_the_rest_is_by_due_then_the_day_then_path_and_line_undated_last(self):
        records = [json.loads(line) for line in self.pkm("tasks", "--json").stdout.strip().splitlines()]
        rest = [r["text"].split("] ")[1].split(" (")[0] for r in records if r["group"] == "other"]
        self.assertEqual(rest, ["Later", "Waited short", "Undated"])

    def test_the_plain_order_is_the_json_order(self):
        plain = self.ok("tasks").strip().splitlines()
        jsonl = [json.loads(line) for line in self.pkm("tasks", "--json").stdout.strip().splitlines()]
        self.assertEqual(plain, [f"{r['path']}:{r['line']}: {r['text']}" for r in jsonl])


class RelativeDates(VaultCase):
    def test_a_relative_date_resolves_against_its_day_page(self):
        self.write("daybook/2026/11/2026-11-10-sam.md", "# 2026-11-10 Sam\n\n- [ ] Call (due friday)\n- [ ] Soon (due +3d)\n")
        records = [json.loads(line) for line in self.pkm("tasks", "--json", "--all").stdout.strip().splitlines()]
        dues = {r["text"].split("] ")[1].split(" (")[0]: r["due"] for r in records}
        self.assertEqual(dues["Call"], "2026-11-13")
        self.assertEqual(dues["Soon"], "2026-11-13")

    def test_today_and_tomorrow_resolve_against_the_page(self):
        self.write("daybook/2026/11/2026-11-10.md", "- [ ] Today (due today)\n- [ ] Tomorrow (due tomorrow)\n")
        records = [json.loads(line) for line in self.pkm("tasks", "--json").stdout.strip().splitlines()]
        dues = {r["text"].split("] ")[1].split(" (")[0]: r["due"] for r in records}
        self.assertEqual(dues, {"Today": "2026-11-10", "Tomorrow": "2026-11-11"})

    def test_a_relative_date_outside_a_day_page_is_a_check_problem(self):
        self.write("notes/x.md", "- [ ] Call (due friday)\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/x.md:1: relative date friday is outside a day page", result.stdout)

    def test_a_marker_that_cannot_be_read_is_a_check_problem(self):
        self.write("daybook/2026/11/2026-11-10.md", "- [ ] Broken (due 2026-13-45)\n- [ ] Vague (due soon-ish)\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("2026-11-10.md:1: cannot read the due date 2026-13-45", result.stdout)
        self.assertIn("2026-11-10.md:2: cannot read the due date soon-ish", result.stdout)

    def test_the_emoji_due_date_counts(self):
        self.write("daybook/2026/11/2026-11-10.md", "- [ ] Emoji \U0001F4C5 2026-11-20\n")
        records = [json.loads(line) for line in self.pkm("tasks", "--json").stdout.strip().splitlines()]
        self.assertEqual(records[0]["due"], "2026-11-20")


class Views(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", "- [ ] Plain\n- [ ] Waiting on John (waiting 2026-11-01)\n- [ ] Maybe (someday)\n")
        self.write("archive/daily/2026/2026-01-02.md", "- [ ] Archived task\n- [x] Finished (done 2026-11-14)\n")
        self.write("notes/zeus.md", "- [ ] About [[apollo]]\n")

    def test_waiting_and_someday_views(self):
        self.assertIn("Waiting on John", self.ok("tasks", "waiting"))
        self.assertNotIn("Plain", self.ok("tasks", "waiting"))
        self.assertIn("Maybe", self.ok("tasks", "someday"))
        self.assertNotIn("Plain", self.ok("tasks", "someday"))

    def test_the_archive_is_left_out_unless_all(self):
        self.assertNotIn("Archived", self.ok("tasks"))
        self.assertIn("Archived", self.ok("tasks", "--all"))

    def test_done_since_a_day_lists_the_finished_ones(self):
        out = self.ok("tasks", "done", "2026-11-10")
        self.assertIn("Finished", out)
        self.assertEqual(self.pkm("tasks", "done", "2026-11-20").returncode, 1)

    def test_link_filters_to_tasks_about_a_note(self):
        self.write("notes/other.md", "- [ ] Unrelated\n")
        out = self.ok("tasks", "--link", "apollo")
        self.assertIn("About [[apollo]]", out)
        self.assertIn("Plain", out)
        self.assertNotIn("Unrelated", out)

    def test_no_tasks_is_exit_1(self):
        self.write("notes/empty.md", "# Nothing\n")
        self.assertEqual(self.pkm("tasks", "--link", "nobody").returncode, 1)


class DoneTask(NovemberCase):
    def setUp(self):
        super().setUp()
        self.write("daybook/2026/11/2026-11-16.md", "# 2026-11-16\n\n- [ ] Send the invoice (due 2026-11-13)\n"
                                                       "- [ ] Call the bank\n- [ ] Call the vet\n")
        self.write("notes/routines.md", "# Routines\n\n- [ ] Pay the rent (due 2026-12-01) (every 1m)\n"
                                        "- [ ] Water the plants (every 1w)\n- [ ] Sprint summary (every sprint)\n")

    def test_done_marks_the_task_and_dates_it(self):
        result = self.pkm("done", "invoice")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md:3: - [x] Send the invoice (due 2026-11-13) (done 2026-11-16)")

    def test_done_by_place_and_drop(self):
        self.assertEqual(self.pkm("done", "daybook/2026/11/2026-11-16.md:4", "--drop").returncode, 0)
        self.assertIn("- [-] Call the bank (dropped 2026-11-16)", self.read("daybook/2026/11/2026-11-16.md"))

    def test_more_than_one_match_changes_nothing(self):
        before = self.read("daybook/2026/11/2026-11-16.md")
        result = self.pkm("done", "call")
        self.assertEqual(result.returncode, 1)
        self.assertIn("2 open tasks match", result.stderr)
        self.assertEqual(self.read("daybook/2026/11/2026-11-16.md"), before)

    def test_no_match_fails(self):
        self.assertEqual(self.pkm("done", "nothing-like-this").returncode, 1)

    def test_an_interval_routine_moves_its_due_date_and_stays_open(self):
        result = self.pkm("done", "rent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "notes/routines.md:3: - [ ] Pay the rent (due 2027-01-01) (every 1m)")

    def test_a_weekly_routine_moves_seven_days_from_the_old_due_date(self):
        self.write("notes/weekly.md", "- [ ] Bins (due 2026-11-20) (every 1w)\n")
        self.ok("done", "bins")
        self.assertIn("(due 2026-11-27)", self.read("notes/weekly.md"))

    def test_a_rule_that_is_neither_an_interval_nor_a_cycle_is_refused_in_one_line(self):
        self.write("notes/rule.md", "- [ ] Sort the post (every fortnight-ish)\n")
        result = self.pkm("done", "sort the post")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("cycle name", result.stderr)


class Todo(VaultCase):
    def test_todo_writes_under_the_tasks_section_with_its_markers_and_prints_path_line(self):
        result = self.pkm("todo", "Send the offer", "--due", "friday", "--high")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "daybook/2026/10/2026-10-25.md:5")
        self.assertIn("- [ ] Send the offer (due 2026-10-30) (high)", self.read("daybook/2026/10/2026-10-25.md"))

    def test_waiting_is_marked_with_today(self):
        self.ok("todo", "Wait on the quote", "--waiting")
        self.assertIn("- [ ] Wait on the quote (waiting 2026-10-25)", self.read("daybook/2026/10/2026-10-25.md"))

    def test_no_task_lists_are_made(self):
        self.ok("todo", "One")
        self.assertFalse(self.exists("tasks.md"))


class UpcomingList(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/jane-doe.md", "---\ntype: person\nbirthday: 1990-10-30\n---\n# Jane\n")
        self.write("projects/apollo.md", "---\ntype: project\ntarget: 2026-11-02\n---\n# Apollo\n")
        self.write("notes/routines.md", "- [ ] Pay the rent (due 2026-10-28) (every 1m)\n"
                                        "- [ ] Far away (due 2026-12-20)\n")

    def test_due_tasks_routines_birthdays_and_targets_in_the_window(self):
        out = self.ok("upcoming", "7")
        self.assertIn("2026-10-28 due notes/routines.md:1:", out)
        self.assertIn("2026-10-30 birthday notes/jane-doe.md:3: birthday: 1990-10-30", out)
        self.assertNotIn("Far away", out)
        self.assertNotIn("apollo", out)
        self.assertIn("2026-11-02 target projects/apollo.md:3", self.ok("upcoming", "30"))


class CheckKeepsTasksClean(VaultCase):
    def test_a_clean_vault_of_tasks_passes(self):
        self.write("daybook/2026/10/2026-10-25.md", "- [ ] Call (due 2026-10-30)\n- [ ] Ask (due friday)\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)


class ExampleVaultsAcceptance(unittest.TestCase):
    """The method's example vaults: the acceptance runs, on temporary copies (the examples are not changed)."""

    def copy(self, name):
        target = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "docs/examples" / name, target / name)
        return target / name

    def run_in(self, vault, args, now):
        config = tempfile.mkdtemp()
        try:
            return run_pkm(list(args), cwd=vault, env=pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=config), vault=vault)
        finally:
            shutil.rmtree(config)

    def test_work_tasks_upcoming_and_done(self):
        vault = self.copy("work")
        try:
            tasks = self.run_in(vault, ["tasks"], "20261116083000").stdout.splitlines()
            self.assertEqual(tasks[0], "daybook/2026/11/2026-11-09.md:5: - [ ] Send [[john-roe]] the Apollo invoice for October (due 2026-11-13) (high)")
            self.assertIn("notes/routines.md:8: - [ ] Submit the timesheet (due 2026-11-20) (every 1w)", tasks[:3])
            up = self.run_in(vault, ["upcoming", "7"], "20261116083000").stdout
            self.assertIn("notes/routines.md:8:", up)
            self.assertIn("2026-11-19 birthday notes/jane-doe.md:4: birthday: 1990-11-19", up)
            done = self.run_in(vault, ["done", "invoice"], "20261116083000")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("(done 2026-11-16)", done.stdout)
            self.assertIn("- [x] Send [[john-roe]] the Apollo invoice for October (due 2026-11-13) (high) (done 2026-11-16)",
                          (vault / "daybook/2026/11/2026-11-09.md").read_text().split("\n")[4])
        finally:
            shutil.rmtree(vault.parent)

    def test_family_tasks_upcoming_and_a_routine_moved_on(self):
        vault = self.copy("family")
        try:
            tasks = self.run_in(vault, ["tasks"], "20261115200000").stdout.splitlines()
            self.assertIn("daybook/2026/11/2026-11-09-alex.md:5", tasks[0])
            self.assertFalse(any("groceries" in line for line in tasks))
            self.assertFalse(any("Quote from" in line for line in tasks))
            up = self.run_in(vault, ["upcoming", "7"], "20261115200000").stdout
            self.assertIn("2026-11-15 due daybook/2026/11/2026-11-10-sam.md:5", up)
            self.assertIn("2026-11-15 due notes/routines.md:11", up)
            self.assertIn("2026-11-20 due notes/routines.md:9", up)
            done = self.run_in(vault, ["done", "electricity"], "20261115200000")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual((vault / "notes/routines.md").read_text().split("\n")[7],
                             "- [ ] Pay the electricity bill (due 2027-01-11) (every 1m)")
        finally:
            shutil.rmtree(vault.parent)


if __name__ == "__main__":
    unittest.main()
