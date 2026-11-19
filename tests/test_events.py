"""Events (docs/format.md, Events): a line with (at <when>) or (@ <when>). upcoming and the close's == due list them on
their days, by start time; tasks never show them; one in a note can come back with (every), (until) and (skip); a task
with an (at …) is due on its day; check reports what it can't read; post refuses one. Run: python3 -m unittest discover
-s tests. Names and data are made up. NOW is Sunday 2026-11-15.
"""

import unittest

from helpers import VaultCase

NOW = "20261115090000"
PAGE = "daybook/2026/11/2026-11-14-alex.md"


class EventsInUpcoming(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(".pkm/config", "format=1\ncycle_sprint=2w from 2026-11-02\n")

    def upcoming(self, days="14", now=NOW):
        return self.ok("upcoming", days, now=now).splitlines()

    def test_events_come_by_start_time_with_whole_day_ones_first(self):
        self.write(PAGE, "# 2026-11-14 Alex\n\n- 11:40 [[school]]: parents' evening (at 2026-11-19 17:30-19:00)\n"
                   "- Sports day (at 2026-11-19)\n- Dentist for Mia (@ 2026-11-19 09:00)\n- [ ] Pack the kit (due 2026-11-19)\n")
        self.assertEqual(self.upcoming(), [
            f"2026-11-19 due {PAGE}:6: - [ ] Pack the kit (due 2026-11-19)",
            f"2026-11-19 event {PAGE}:4: - Sports day (at 2026-11-19)",
            f"2026-11-19 event {PAGE}:5: - Dentist for Mia (@ 2026-11-19 09:00)",
            f"2026-11-19 event {PAGE}:3: - 11:40 [[school]]: parents' evening (at 2026-11-19 17:30-19:00)",
        ])

    def test_an_event_is_never_a_task_and_never_overdue(self):
        self.write(PAGE, "# 2026-11-14 Alex\n\n- Concert (at 2026-11-10 19:00)\n- Lunch with Jane Doe (at 2026-11-16 12:00)\n")
        self.assertEqual(self.upcoming(), [f"2026-11-16 event {PAGE}:4: - Lunch with Jane Doe (at 2026-11-16 12:00)"])
        self.assertEqual(self.pkm("tasks", "--all", now=NOW).stdout, "")

    def test_a_relative_date_counts_from_its_day_page_and_today_is_still_listed(self):
        self.write("daybook/2026/11/2026-11-12.md", "# 2026-11-12\n\n- Call Acme (at friday 10:00)\n- Review (at +3d)\n")
        self.write("daybook/2026/11/2026-11-15.md", "# 2026-11-15\n\n- Breakfast (at today 07:00)\n")
        self.assertEqual(self.upcoming(), [
            "2026-11-15 event daybook/2026/11/2026-11-12.md:4: - Review (at +3d)",
            "2026-11-15 event daybook/2026/11/2026-11-15.md:3: - Breakfast (at today 07:00)",
        ])

    def test_a_several_day_event_is_listed_on_each_of_its_days_from_today(self):
        self.write(PAGE, "# 2026-11-14 Alex\n\n- Trip to Apollo (at 2026-11-14 to 2026-11-17)\n")
        self.assertEqual([line[:16] for line in self.upcoming()], ["2026-11-15 event", "2026-11-16 event", "2026-11-17 event"])

    def test_a_range_may_use_an_en_dash(self):
        self.write(PAGE, "# 2026-11-14 Alex\n\n- Choir (at 2026-11-19 17:30–19:00)\n")
        self.assertEqual(self.upcoming(), [f"2026-11-19 event {PAGE}:3: - Choir (at 2026-11-19 17:30–19:00)"])
        self.assertNotIn("Choir", self.pkm("check", now=NOW).stdout)

    def test_a_night_shift_is_listed_on_the_day_it_starts(self):
        self.write(PAGE, "# 2026-11-14 Alex\n\n- Night shift (at 2026-11-19 22:00-06:00)\n")
        self.assertEqual(self.upcoming(), [f"2026-11-19 event {PAGE}:3: - Night shift (at 2026-11-19 22:00-06:00)"])
        self.assertNotIn("Night shift", self.pkm("check", now=NOW).stdout)

    def test_an_event_in_a_note_comes_back_but_not_on_a_skipped_day(self):
        self.write("notes/mia.md", "# Mia\n\n- Football (at 2026-11-03 17:00-18:00) (every 1w) (skip 2026-11-17)\n")
        days = [line[:10] for line in self.upcoming("21")]
        self.assertEqual(days, ["2026-11-24", "2026-12-01"])

    def test_until_is_the_last_day_it_can_happen(self):
        self.write("notes/mia.md", "# Mia\n\n- Swimming (at 2026-11-03 16:00) (every 1w) (until 2026-11-24)\n")
        self.assertEqual([line[:10] for line in self.upcoming("30")], ["2026-11-17", "2026-11-24"])

    def test_a_monthly_event_is_counted_from_its_anchor(self):
        self.write("notes/rent.md", "# Rent\n\n- Rent day (at 2026-01-31) (every 1m)\n")
        days = [line[:10] for line in self.upcoming("60", now="20260201090000")]
        self.assertEqual(days, ["2026-02-28", "2026-03-31"])

    def test_a_yearly_several_day_event_that_began_before_today(self):
        self.write("notes/fair.md", "# Fair\n\n- Book fair (at 2025-11-13 to 2025-11-16) (every 1y)\n")
        self.assertEqual([line[:10] for line in self.upcoming("3")], ["2026-11-15", "2026-11-16"])

    def test_struck_lines_close_pages_archive_and_closed_notes_are_not_events(self):
        self.write(PAGE, "# 2026-11-14 Alex\n\n- ~~Dentist (at 2026-11-18 10:00)~~ ([[2026-11-15]])\n")
        self.write("closes/2026/2026-11-09-week.md", "---\ntype: close\n---\n\n# Week\n\n- Demo (at 2026-11-18)\n")
        self.write("archive/old.md", "# Old\n\n- Old event (at 2026-11-18)\n")
        self.write("notes/course.md", "---\ntype: course\nstatus: done\n---\n\n# Course\n\n- Lecture (at 2026-11-03 10:00) (every 1w)\n")
        self.assertEqual(self.upcoming(), [])

    def test_a_task_with_a_time_is_due_on_its_day_unless_it_has_its_own_due(self):
        self.write("daybook/2026/11/2026-11-12.md", "# 2026-11-12\n\n- [ ] Run the [[apollo]] demo (at 2026-11-20 14:00-15:00)\n"
                   "- [ ] Rehearse (at 2026-11-20 10:00) (due 2026-11-18)\n- [ ] Missed call (at 2026-11-13 10:00)\n"
                   "- [ ] Prepare for Acme (at friday)\n")
        out = self.upcoming()
        self.assertIn("2026-11-20 due daybook/2026/11/2026-11-12.md:3: - [ ] Run the [[apollo]] demo (at 2026-11-20 14:00-15:00)", out)
        self.assertIn("2026-11-18 due daybook/2026/11/2026-11-12.md:4: - [ ] Rehearse (at 2026-11-20 10:00) (due 2026-11-18)", out)
        self.assertIn("2026-11-13 overdue daybook/2026/11/2026-11-12.md:5: - [ ] Missed call (at 2026-11-13 10:00)", out)
        self.assertIn("2026-11-13 overdue daybook/2026/11/2026-11-12.md:6: - [ ] Prepare for Acme (at friday)", out)
        self.assertNotIn(" event ", "\n".join(out))
        self.assertIn("Run the [[apollo]] demo", self.ok("tasks", now=NOW))

    def test_the_close_lists_events_in_due_and_never_in_tasks(self):
        self.write("daybook/2026/11/2026-11-10.md", "# 2026-11-10\n\n- Concert (at 2026-11-11 19:00)\n"
                   "- Parents' evening (at 2026-11-19 17:30)\n")
        out = self.ok("close", now="20261116090000")
        self.assertIn("== due\n2026-11-19 event daybook/2026/11/2026-11-10.md:4: - Parents' evening (at 2026-11-19 17:30)", out)
        self.assertNotIn("== tasks", out)


class EventProblems(VaultCase):
    def test_check_reports_what_it_cannot_read(self):
        self.write("daybook/2026/11/2026-11-12.md", "# 2026-11-12\n\n"
                   "- Gym (at friday 25:00)\n"
                   "- Call (at 2026-11-19 10:00-10:00)\n"
                   "- Yoga (at 2026-11-19 07:00) (every 1w)\n"
                   "- [ ] Stand-up (at 2026-11-16 09:30) (every 1w)\n"
                   "- Meet at Acme (at the office)\n"
                   "- Trip (at 2026-11-20 to 2026-11-18)\n"
                   "- [ ] Odd (at friday 9h)\n")
        self.write("notes/x.md", "# X\n\n- Lunch (at friday)\n- Sprint review (at 2026-11-13) (every sprint)\n"
                   "- Plain entry (until 2026-11-20)\n- Choir (at 2026-11-03 19:00) (every 1w) (skip soon)\n"
                   "- Choir again (at 2026-11-04 19:00) (every 1w) (skip 2026-11-18) (until 2026-12-23)\n")
        out = self.pkm("check", now=NOW).stdout
        p = "daybook/2026/11/2026-11-12.md"
        for expected in [f"{p}:3: cannot read the event time friday 25:00",
                         f"{p}:4: a time range ends when it starts: 2026-11-19 10:00-10:00",
                         f"{p}:5: an event comes back only from a note",
                         f"{p}:6: (every 1w) with an (at …) in a task box",
                         f"{p}:8: an event ends before it starts: 2026-11-20 to 2026-11-18",
                         f"{p}:9: cannot read the event time friday 9h",
                         "notes/x.md:3: relative date friday is outside a day page",
                         "notes/x.md:4: an event comes back on an interval",
                         "notes/x.md:5: (until …) belongs on an event that comes back",
                         "notes/x.md:6: cannot read the date in (skip soon)"]:
            self.assertIn(expected, out)
        self.assertNotIn(f"{p}:7:", out)
        self.assertNotIn("notes/x.md:7:", out)

    def test_post_refuses_an_event(self):
        self.write("daybook/2026/11/2026-11-12.md", "# 2026-11-12\n\n- Dentist (at 2026-12-04 10:00)\n- Meet (at the office)\n")
        self.write("notes/sam.md", "---\ntype: person\n---\n\n# Sam\n")
        result = self.pkm("post", "daybook/2026/11/2026-11-12.md:3", "sam", now=NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("event", result.stderr)
        self.assertEqual(self.pkm("post", "daybook/2026/11/2026-11-12.md:4", "sam", now=NOW).returncode, 0)


if __name__ == "__main__":
    unittest.main()
