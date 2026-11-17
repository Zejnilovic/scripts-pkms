"""Tests for cycles: their definitions and periods, cycle, cycle routines (tasks, upcoming, done, check), and the
settings' validation. Run: python3 -m unittest discover -s tests. Names and data are made up. NOW is 2026-11-16.
"""

import unittest

from helpers import VaultCase

NOW = "20261116090000"
CONFIG = "cycle_sprint=2w from 2026-11-02\ncycle_pay=1m from 15\ncycle_trash=1w from friday\n"


class CycleDefinitions(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(".pkm/config", "format=1\n" + CONFIG)

    def test_each_kind_of_cycle_gives_its_period(self):
        self.assertEqual(self.ok("cycle", "sprint", "--date", "2026-11-16", now=NOW).strip(), "sprint\t2026-11-16\t2026-11-29")
        self.assertEqual(self.ok("cycle", "pay", "--date", "2026-11-16", now=NOW).strip(), "pay\t2026-11-15\t2026-12-14")
        self.assertEqual(self.ok("cycle", "trash", "--date", "2026-11-16", now=NOW).strip(), "trash\t2026-11-13\t2026-11-19")
        self.assertEqual(self.ok("cycle", "week", "--date", "2026-11-16", now=NOW).strip(), "week\t2026-11-16\t2026-11-22\tclose")

    def test_a_period_holding_a_date_before_the_anchor_runs_backwards(self):
        self.assertEqual(self.ok("cycle", "sprint", "--date", "2026-10-31", now=NOW).strip(), "sprint\t2026-10-19\t2026-11-01")
        self.assertEqual(self.ok("cycle", "pay", "--date", "2026-11-14", now=NOW).strip(), "pay\t2026-10-15\t2026-11-14")

    def test_no_name_prints_every_cycle_with_the_close_one_marked(self):
        lines = self.ok("cycle", "--date", "2026-11-16", now=NOW).splitlines()
        self.assertEqual([line.split("\t")[0] for line in lines], ["week", "pay", "sprint", "trash"])
        self.assertEqual(lines[0].split("\t")[3], "close")
        self.assertEqual(len(lines[2].split("\t")), 3)

    def test_an_unknown_name_exits_1(self):
        self.assertEqual(self.pkm("cycle", "nope", now=NOW).returncode, 1)

    def test_doctor_reports_a_weekday_for_more_than_one_week_and_a_reserved_name(self):
        self.write(".pkm/config", "format=1\ncycle_bad=2w from monday\ncycle_week=1w from monday\ncycle_Big=1w from 2026-11-02\n")
        out = self.pkm("doctor", now=NOW).stdout
        self.assertIn("cycle_bad", out)
        self.assertIn("cycle_week", out)
        self.assertIn("cycle_Big", out)


class CycleRoutines(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(".pkm/config", "format=1\n" + CONFIG)
        self.write("notes/routines.md", "# Routines\n\n- [ ] Sprint summary (due 2026-11-15) (every sprint)\n"
                   "- [ ] Expenses report (every sprint)\n")

    def test_an_undated_routine_is_due_on_the_last_day_of_the_current_period(self):
        out = self.ok("upcoming", "30", now=NOW)
        self.assertIn("2026-11-29 due notes/routines.md:4: - [ ] Expenses report (every sprint)", out)

    def test_done_moves_a_dated_routine_to_the_period_after_its_due_date(self):
        out = self.ok("done", "Sprint summary", now=NOW).strip()
        self.assertEqual(out, "notes/routines.md:3: - [ ] Sprint summary (due 2026-11-29) (every sprint)")
        self.assertIn("- [ ] Sprint summary (due 2026-11-29) (every sprint)", self.read("notes/routines.md"))

    def test_done_moves_an_undated_routine_to_the_next_period(self):
        self.ok("done", "Expenses report", now=NOW)
        self.assertIn("- [ ] Expenses report (due 2026-12-13) (every sprint)", self.read("notes/routines.md"))

    def test_a_dated_monthly_routine_moves_one_month_on_the_same_day(self):
        self.write("notes/savings.md", "- [ ] Move 200 (due 2026-11-15) (every pay)\n")
        self.ok("done", "Move 200", now=NOW)
        self.assertIn("- [ ] Move 200 (due 2026-12-15) (every pay)", self.read("notes/savings.md"))

    def test_a_dated_weekly_cycle_moves_seven_days_for_each_week_of_its_length(self):
        self.write("notes/routines.md", "- [ ] Sprint summary (due 2026-11-15) (every sprint)\n")
        self.ok("done", "Sprint summary", now=NOW)
        self.assertIn("(due 2026-11-29) (every sprint)", self.read("notes/routines.md"))

    def test_a_monthly_routine_on_the_31st_is_clamped_to_the_month_end(self):
        self.write(".pkm/config", "format=1\ncycle_1m-cycle=1m from 15\n")
        self.write("notes/clamp.md", "- [ ] Pay the bill (due 2026-01-31) (every 1m-cycle)\n")
        self.ok("done", "Pay the bill", now=NOW)
        self.assertIn("- [ ] Pay the bill (due 2026-02-28) (every 1m-cycle)", self.read("notes/clamp.md"))

    def test_check_flags_a_routine_naming_no_cycle(self):
        self.write("notes/routines.md", "- [ ] Water (every fortnight-ish)\n")
        result = self.pkm("check", now=NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("names no cycle", result.stdout)

    def test_a_cycle_routine_is_no_longer_refused_as_a_step_11_task(self):
        self.assertEqual(self.pkm("done", "Sprint summary", now=NOW).returncode, 0)


if __name__ == "__main__":
    unittest.main()
