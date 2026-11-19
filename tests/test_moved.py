"""Dates that move: pkm done --next <day> for a routine done early or late, and pkm moved <path:line> <when>, which strikes
a task or an event whose date changed and writes it again with the new date: in a note right below the old line, from
a day page on today's page, linking the day it came from. Run: python3 -m unittest discover -s tests. Names and data are
made up. NOW is Thursday 2026-11-19, 14:30.
"""

import unittest

from helpers import VaultCase

NOW = "20261119143000"
TODAY = "daybook/2026/11/2026-11-19.md"


class DoneNext(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/routines.md", "# Routines\n\n- [ ] Service the car (due 2027-03-01) (every 1y)\n"
                   "- [ ] Water the plants (every 1w)\n- [ ] Call Jane Doe (due 2026-11-25)\n")

    def test_a_routine_done_early_is_next_due_on_the_day_given(self):
        out = self.ok("done", "Service the car", "--next", "2027-11-19", now=NOW).strip()
        self.assertEqual(out, "notes/routines.md:3: - [ ] Service the car (due 2027-11-19) (every 1y)")
        out = self.ok("done", "Service the car", now="20271119090000").strip()
        self.assertEqual(out, "notes/routines.md:3: - [ ] Service the car (due 2028-11-19) (every 1y)")

    def test_next_takes_a_day_word_and_dates_an_undated_routine(self):
        out = self.ok("done", "notes/routines.md:4", "--next", "monday", now=NOW).strip()
        self.assertEqual(out, "notes/routines.md:4: - [ ] Water the plants (due 2026-11-23) (every 1w)")

    def test_next_is_only_for_a_routine_and_needs_a_day(self):
        result = self.pkm("done", "Call Jane", "--next", "friday", now=NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pkm moved", result.stderr)
        self.assertEqual(self.pkm("done", "Service", "--next", "soon", now=NOW).returncode, 2)
        self.assertEqual(self.pkm("done", "Service", "--next", now=NOW).returncode, 2)
        self.assertEqual(self.pkm("done", "Service", "--drop", "--next", "friday", now=NOW).returncode, 2)
        self.assertIn("(due 2027-03-01)", self.read("notes/routines.md"))


class Moved(VaultCase):
    def setUp(self):
        super().setUp()
        self.page = "daybook/2026/11/2026-11-12.md"
        self.day = ("# 2026-11-12\n\n## Tasks\n\n- [ ] Call Jane Doe about [[apollo]] (due friday) (high)\n"
                    "- [ ] Rehearse the demo (at 2026-11-20 10:00) (due 2026-11-18)\n\n## Log\n\n"
                    "- 11:40 [[school]]: parents' evening (at 2026-11-19 17:30-19:00)\n- Dentist for Mia (@ 2026-12-04 10:00)\n"
                    "- Trip to Acme (at 2026-11-24 to 2026-11-26)\n- [x] Old (done 2026-11-12)\n- Plain entry\n")
        self.write(self.page, self.day)

    def lines(self, rel):
        return self.read(rel).splitlines()

    def test_a_task_on_a_day_page_moves_to_todays_tasks_linking_its_day(self):
        out = self.ok("moved", f"{self.page}:5", "2026-11-27", now=NOW).strip()
        new = "- [ ] Call Jane Doe about [[apollo]] ([[2026-11-12]]) (due 2026-11-27) (high)"
        self.assertTrue(out.startswith(f"{TODAY}:") and out.endswith(f": {new}"), out)
        self.assertIn(new, self.lines(TODAY))
        self.assertIn("## Tasks", self.read(TODAY))
        old = self.lines(self.page)
        self.assertEqual(old[4], "- [ ] ~~Call Jane Doe about [[apollo]] (due friday) (high)~~ ([[2026-11-19]])")
        expected = self.day.splitlines()
        expected[4] = old[4]
        self.assertEqual(old, expected)

    def test_an_event_moves_to_todays_log_with_the_time_now_and_keeps_its_hours(self):
        out = self.ok("moved", f"{self.page}:10", "2026-11-26", now=NOW).strip()
        new = "- 14:30 [[school]]: parents' evening ([[2026-11-12]]) (at 2026-11-26 17:30-19:00)"
        self.assertTrue(out.endswith(f": {new}"), out)
        self.assertIn(new, self.lines(TODAY))
        self.assertIn("- ~~11:40 [[school]]: parents' evening (at 2026-11-19 17:30-19:00)~~ ([[2026-11-19]])", self.lines(self.page))
        upcoming = self.ok("upcoming", "14", now=NOW)
        self.assertNotIn("2026-11-19 event", upcoming)
        self.assertIn("2026-11-26 event", upcoming)

    def test_the_marker_keeps_its_form_and_a_new_time_replaces_the_old(self):
        out = self.ok("moved", f"{self.page}:11", "friday 09:15", now=NOW).strip()
        self.assertTrue(out.endswith(": - 14:30 Dentist for Mia ([[2026-11-12]]) (@ 2026-11-20 09:15)"), out)

    def test_a_several_day_event_keeps_its_length(self):
        out = self.ok("moved", f"{self.page}:12", "2026-12-01", now=NOW).strip()
        self.assertTrue(out.endswith("(at 2026-12-01 to 2026-12-03)"), out)

    def test_a_task_with_a_time_moves_its_time_and_keeps_its_due(self):
        out = self.ok("moved", f"{self.page}:6", "2026-11-23 11:00", now=NOW).strip()
        self.assertTrue(out.endswith(": - [ ] Rehearse the demo ([[2026-11-12]]) (at 2026-11-23 11:00) (due 2026-11-18)"), out)

    def test_in_a_note_the_new_line_goes_right_below_the_old_one(self):
        self.write("notes/apollo.md", "# Apollo\r\n\r\n## Next\r\n\r\n  - [ ] Ship the build 📅 2026-11-25\r\n- Review (at 2026-11-30)\r\n")
        out = self.ok("moved", "notes/apollo.md:5", "+2w", now=NOW).strip()
        self.assertEqual(out, "notes/apollo.md:6: - [ ] Ship the build (due 2026-12-03)")
        raw = (self.root / "notes/apollo.md").read_bytes().decode()
        self.assertEqual(raw.split("\r\n")[4:7], ["  - [ ] ~~Ship the build 📅 2026-11-25~~ ([[2026-11-19]])",
                                                  "  - [ ] Ship the build (due 2026-12-03)", "- Review (at 2026-11-30)"])

    def test_a_task_with_no_date_gets_one(self):
        self.write("notes/x.md", "# X\n\n- [ ] Book the room\n")
        self.assertEqual(self.ok("moved", "notes/x.md:3", "2026-12-01", now=NOW).strip(), "notes/x.md:4: - [ ] Book the room (due 2026-12-01)")

    def test_a_line_on_todays_page_moves_below_itself(self):
        self.write(TODAY, "# 2026-11-19\n\n## Log\n\n- 09:00 Call with Acme (at 2026-11-19 16:00)\n")
        out = self.ok("moved", f"{TODAY}:5", "today 17:00", now=NOW).strip()
        self.assertEqual(out, f"{TODAY}:6: - 09:00 Call with Acme (at 2026-11-19 17:00)")

    def test_what_moved_refuses(self):
        self.write("notes/mia.md", "# Mia\n\n- Football (at 2026-11-03 17:00) (every 1w)\n")
        self.write("closes/2026/2026-11-09-week.md", "---\ntype: close\n---\n\n# Week\n\n- [ ] Carry on (due 2026-11-20)\n")
        for spec, code in [(f"{self.page}:13", 1), (f"{self.page}:14", 1), (f"{self.page}:1", 1), ("notes/mia.md:3", 1),
                           ("closes/2026/2026-11-09-week.md:7", 1), (f"{self.page}:5", 2), (f"{self.page}:99", 2),
                           ("nowhere.md:1", 2)]:
            args = [spec, "2026-12-01"] if spec != f"{self.page}:5" else [spec, "someday"]
            result = self.pkm("moved", *args, now=NOW)
            self.assertEqual(result.returncode, code, f"{spec}: {result.stderr}")
        self.assertIn("(skip", self.pkm("moved", "notes/mia.md:3", "2026-11-25", now=NOW).stderr)
        self.assertEqual(self.pkm("moved", f"{self.page}:5", "2026-11-27 10:00", now=NOW).returncode, 2)
        self.assertEqual(self.pkm("moved", f"{self.page}:5", now=NOW).returncode, 2)
        self.assertEqual(self.read(self.page), self.day)
        self.assertFalse(self.exists(TODAY))


if __name__ == "__main__":
    unittest.main()
