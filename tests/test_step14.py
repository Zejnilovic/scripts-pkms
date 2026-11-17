"""Later task kinds (step 14): (start D) hides a task until D, (someday) keeps it out of the weekly views and shows it in
tasks someday and the quarterly close, routines live in notes (a routine on a day page is a problem), the old rules are no
longer routines, and todo --every takes only the routine forms. Run: python3 -m unittest discover -s tests.
Names and data are made up. NOW is 2026-10-25 unless a test says otherwise.
"""

from helpers import VaultCase

PLANS = """# Plans

- [ ] Hidden until spring (start 2027-03-01)
- [ ] Visible task (due 2026-11-20)
- [ ] Idea to decide (someday)
- [ ] Someday to spring (someday) (start 2027-03-01)
- [ ] Started already (start 2026-10-01)
"""


class StartAndSomeday(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/plans.md", PLANS)

    def test_tasks_hides_a_task_until_its_start_and_keeps_the_someday_ones_out(self):
        out = self.ok("tasks")
        self.assertIn("notes/plans.md:4: - [ ] Visible task (due 2026-11-20)", out)
        self.assertIn("notes/plans.md:7: - [ ] Started already (start 2026-10-01)", out)
        for hidden in ["Hidden until spring", "Idea to decide", "Someday to spring"]:
            self.assertNotIn(hidden, out)

    def test_tasks_all_shows_a_hidden_task_marked_with_its_start(self):
        out = self.ok("tasks", "--all")
        self.assertIn("notes/plans.md:3: starts 2027-03-01: - [ ] Hidden until spring (start 2027-03-01)", out)
        self.assertNotIn("Idea to decide", out)

    def test_tasks_someday_shows_the_someday_tasks(self):
        out = self.ok("tasks", "someday")
        self.assertIn("Idea to decide", out)
        self.assertIn("Someday to spring", out)
        self.assertNotIn("Visible task", out)

    def test_a_someday_task_with_a_start_comes_back_as_an_ordinary_task_on_that_day(self):
        out = self.ok("tasks", now="20270301090000")
        self.assertIn("Someday to spring", out)
        self.assertIn("Hidden until spring", out)
        self.assertNotIn("Someday to spring", self.ok("tasks", "someday", now="20270301090000"))

    def test_upcoming_lists_a_hidden_task_whose_start_falls_in_the_window(self):
        out = self.ok("upcoming", "10", now="20270225090000").splitlines()
        self.assertIn("2027-03-01 start notes/plans.md:3: - [ ] Hidden until spring (start 2027-03-01)", out)
        self.assertIn("2027-03-01 start notes/plans.md:6: - [ ] Someday to spring (someday) (start 2027-03-01)", out)

    def test_upcoming_leaves_the_someday_task_out_of_its_due_lines(self):
        self.write("notes/plans.md", PLANS + "- [ ] Someday due (someday) (due 2026-11-02)\n")
        self.assertNotIn("Someday due", self.ok("upcoming", "30"))

    def test_close_leaves_hidden_and_someday_tasks_out_of_its_task_sections(self):
        out = self.ok("close", "--quarter", now="20261026090000")
        self.assertNotIn("Hidden until spring", out)
        self.assertIn("== ideas", out)
        self.assertIn("someday: - [ ] Idea to decide", out)

    def test_since_leaves_hidden_and_someday_tasks_out_of_its_tasks(self):
        # since lists only the overdue and the waiting tasks, so with none of those it says there is nothing to show.
        self.write("notes/plans.md", PLANS + "- [ ] Overdue hidden (start 2027-03-01) (due 2026-10-01)\n"
                   "- [ ] Overdue someday (someday) (due 2026-10-01)\n- [ ] Overdue plain (due 2026-10-01)\n")
        out = self.pkm("since", "2026-10-01").stdout
        self.assertNotIn("Overdue hidden", out)
        self.assertNotIn("Overdue someday", out)
        self.assertIn("Overdue plain", out)


class RoutinesLiveInNotes(VaultCase):
    def test_check_flags_a_routine_on_a_day_page(self):
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n## Tasks\n\n- [ ] Water (every 1w)\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("daybook/2026/10/2026-10-25.md:5: ", result.stdout)
        self.assertIn("a routine belongs in a note", result.stdout)

    def test_the_old_rules_are_flagged_with_how_to_write_them_now(self):
        self.write("notes/old.md", "- [ ] Water (every monday, thursday)\n- [ ] Rent (every day)\n"
                   "- [ ] Report (every month on 15)\n- [ ] Plan (every friday)\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("(every monday, thursday) is no longer a routine: write it as (every 1w) with a due date, or name a cycle", result.stdout)
        for line in ["notes/old.md:1:", "notes/old.md:2:", "notes/old.md:3:", "notes/old.md:4:"]:
            self.assertIn(line, result.stdout)

    def test_an_old_rule_task_is_still_an_open_task_but_not_a_routine(self):
        self.write("notes/old.md", "- [ ] Water (every monday, thursday)\n")
        self.assertIn("notes/old.md:1: - [ ] Water (every monday, thursday)", self.ok("tasks"))
        self.assertNotIn("due", self.ok("upcoming", "60"))


class TodoEvery(VaultCase):
    def test_todo_every_takes_an_interval_or_a_cycle_name(self):
        self.write(".pkm/config", "format=1\ncycle_sprint=2w from 2026-11-02\n")
        for rule, written in [("1w", "(every 1w)"), ("2m", "(every 2m)"), ("sprint", "(every sprint)"), ("week", "(every week)")]:
            with self.subTest(rule=rule):
                self.ok("todo", f"Task {rule}", "--every", rule)
                self.assertIn(f"Task {rule} {written}", self.read("notes/routines.md"))  # a routine goes to the routines note

    def test_todo_every_refuses_the_old_rules_with_exit_2(self):
        for rule in ["day", "monday", "month on 15"]:
            with self.subTest(rule=rule):
                result = self.pkm("todo", "Old", "--every", rule)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(f"Not a routine: {rule}", result.stderr)


class TwentyOneDaysFromStart(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("daybook/2026/09/2026-09-01.md",
                   "# 2026-09-01\n\n## Tasks\n\n- [ ] Plain old\n- [ ] Started late (start 2026-10-10)\n"
                   "- [ ] Someday old (someday)\n")

    def test_the_21_day_rule_counts_from_the_start_date_and_skips_someday(self):
        out = self.ok("close")
        self.assertIn("daybook/2026/09/2026-09-01.md:5: open 54 days: - [ ] Plain old", out)
        self.assertNotIn("Started late", out)
        self.assertNotIn("Someday old", out)

    def test_a_start_date_more_than_21_days_back_counts_from_it(self):
        self.write("daybook/2026/09/2026-09-01.md", "# 2026-09-01\n\n## Tasks\n\n- [ ] Long wait (start 2026-09-01)\n")
        self.assertIn("daybook/2026/09/2026-09-01.md:5: open 54 days: - [ ] Long wait", self.ok("close"))
        self.write("daybook/2026/09/2026-09-01.md", "# 2026-09-01\n\n## Tasks\n\n- [ ] Recent (start 2026-10-10)\n")
        self.assertNotIn("Recent", self.ok("close"))
