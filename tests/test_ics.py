"""pkm upcoming --ics: the vault's events, open tasks with an (at …) and birthdays as an iCalendar file (RFC 5545), and the
plain text of a line (lib/pkm/plain.sh) that gives each its SUMMARY. Run: python3 -m unittest discover -s tests. Names and
data are made up. NOW is Sunday 2026-11-15.
"""

import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

from helpers import BASH, PKM, REPO, VaultCase, pkm_env

NOW = "20261115090000"


def unfold(text):
    return text.replace("\r\n ", "")


def vevents(text):
    """The VEVENTs of a calendar, each as a list of its unfolded lines."""
    events, current = [], None
    for line in unfold(text).split("\r\n"):
        if line == "BEGIN:VEVENT":
            current = []
        elif line == "END:VEVENT":
            events.append(current)
            current = None
        elif current is not None:
            current.append(line)
    return events


def find(events, summary):
    found = [e for e in events if f"SUMMARY:{summary}" in e]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} VEVENTs with SUMMARY:{summary} in {events}")
    return found[0]


class Calendar(VaultCase):
    def ics(self, *extra, now=NOW):
        """The calendar as written, its CRLF line ends kept."""
        return self.ics_bytes(*extra, now=now).decode()

    def ics_bytes(self, *extra, now=NOW):
        environment = pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=self.config_home)
        result = subprocess.run([BASH, str(PKM), "--vault", str(self.root), "upcoming", "--ics", *extra], cwd=self.root,
                                env=environment, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout

    def test_a_vault_with_no_events_is_an_empty_calendar(self):
        out = self.ics()
        self.assertTrue(out.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:"), out)
        self.assertTrue(out.endswith("END:VCALENDAR\r\n"))
        self.assertNotIn("VEVENT", out)

    def test_every_line_ends_with_crlf_and_is_folded_at_75_octets(self):
        long = "Planning the Apollo launch party with Jane Doe, John Roe and the whole Acme team — café, cake and a band"
        self.write("notes/party.md", f"# Party\n\n- {long} (at 2026-11-20 18:00)\n")
        raw = self.ics_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        for line in raw.split(b"\r\n"):
            self.assertLessEqual(len(line), 75, line)
            line.decode()  # a fold never cuts a character in two
        summary = long.replace(",", "\\,")
        find(vevents(raw.decode()), summary)

    def test_times_are_floating_and_a_whole_day_is_a_date(self):
        self.write("daybook/2026/11/2026-11-14.md", "# 2026-11-14\n\n- Sports day (at 2026-11-19)\n"
                   "- Trip to Apollo (at 2026-11-14 to 2026-11-17)\n- Night shift (at 2026-11-19 22:00-06:00)\n"
                   "- 09:10 Dentist (@ tomorrow 10:00)\n")
        events = vevents(self.ics())
        sports = find(events, "Sports day")
        self.assertIn("DTSTART;VALUE=DATE:20261119", sports)
        self.assertIn("DTEND;VALUE=DATE:20261120", sports)
        trip = find(events, "Trip to Apollo")
        self.assertIn("DTSTART;VALUE=DATE:20261114", trip)
        self.assertIn("DTEND;VALUE=DATE:20261118", trip)
        night = find(events, "Night shift")
        self.assertIn("DTSTART:20261119T220000", night)
        self.assertIn("DTEND:20261120T060000", night)
        dentist = find(events, "Dentist")
        self.assertIn("DTSTART:20261115T100000", dentist)
        self.assertFalse([line for line in dentist if line.startswith("DTEND")])
        for event in events:
            self.assertTrue(any(re.match(r"DTSTAMP:\d{8}T\d{6}Z$", line) for line in event), event)
            self.assertFalse([line for line in event if line.startswith(("DTSTART", "DTEND")) and line.endswith("Z")])

    def test_an_event_that_comes_back_is_one_vevent_with_its_rule(self):
        self.write("notes/mia.md", "# Mia\n\n- Football (at 2026-11-03 17:00-18:00) (every 1w) (skip 2026-11-17) (skip 2026-12-22)\n"
                   "- Swimming (at 2026-11-04) (every 2w) (until 2026-12-30)\n"
                   "- Rent day (at 2026-01-31) (every 1m)\n- School fair (at 2025-06-14) (every 1y)\n")
        events = vevents(self.ics())
        football = find(events, "Football")
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=1", football)
        self.assertIn("EXDATE:20261117T170000", football)
        self.assertIn("EXDATE:20261222T170000", football)
        swimming = find(events, "Swimming")
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=2;UNTIL=20261230", swimming)
        rent = find(events, "Rent day")
        self.assertIn("RRULE:RSCALE=GREGORIAN;FREQ=MONTHLY;INTERVAL=1;SKIP=BACKWARD", rent)
        self.assertIn("RRULE:FREQ=YEARLY;INTERVAL=1", find(events, "School fair"))

    def test_a_timed_until_includes_the_last_day(self):
        self.write("notes/mia.md", "# Mia\n\n- Choir (at 2026-11-03 19:00) (every 1w) (until 2026-12-15)\n")
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=1;UNTIL=20261215T235959", find(vevents(self.ics()), "Choir"))

    def test_open_tasks_with_a_time_and_birthdays_are_in_it(self):
        self.write("notes/acme.md", "# Acme Corp\n")
        self.write("notes/apollo.md", "# Apollo\n")
        self.write("notes/jane-doe.md", "---\ntype: person\nbirthday: 1990-11-19\n---\n\n# Jane Doe\n")
        self.write("notes/john-roe.md", "---\ntype: person\nbirthday: 03-04\n---\n\n# John Roe\n")
        self.write("daybook/2026/11/2026-11-12.md", "# 2026-11-12\n\n"
                   "- [ ] Run the [[apollo]] demo for [[acme|the client]] (at 2026-11-20 14:00-15:00) (high)\n"
                   "- [x] Old demo (at 2026-11-10 10:00) (done 2026-11-10)\n- [ ] Call Jane (due friday)\n")
        events = vevents(self.ics())
        demo = find(events, "Run the Apollo demo for the client")
        self.assertIn("DTSTART:20261120T140000", demo)
        self.assertIn("DTEND:20261120T150000", demo)
        jane = find(events, "Birthday: Jane Doe")
        self.assertIn("DTSTART;VALUE=DATE:19901119", jane)
        self.assertIn("RRULE:FREQ=YEARLY;INTERVAL=1", jane)
        self.assertIn("DTSTART;VALUE=DATE:20260304", find(events, "Birthday: John Roe"))
        self.assertEqual(len(events), 3)

    def test_the_summary_is_the_plain_text_escaped(self):
        self.write("notes/school.md", "# School\n")
        self.write("daybook/2026/11/2026-11-14-alex.md", "# 2026-11-14 Alex\n\n"
                   "- 11:40 [[school]]: parents' evening; bring forms, pens (at 2026-11-19 17:30-19:00)\n")
        self.write("notes/sam.md", "# Sam\n\n- Dentist ([[2026-11-12-sam]]) (at 2026-12-04 10:00) 📅 2026-12-01\n"
                   "- Visit [[nowhere]] (at 2026-12-05)\n")
        events = vevents(self.ics())
        find(events, "School: parents' evening\\; bring forms\\, pens")
        find(events, "Dentist")
        find(events, "Visit nowhere")

    def test_the_uid_stays_when_lines_above_move_and_a_repeat_gets_a_number(self):
        self.write("notes/x.md", "# X\n\n- Stand-up (at 2026-11-16 09:30)\n- Stand-up (at 2026-11-17 09:30)\n")
        before = [line for e in vevents(self.ics()) for line in e if line.startswith("UID:")]
        self.write("notes/x.md", "# X\n\nA new paragraph.\n\n- Stand-up (at 2026-11-16 09:30)\n- Stand-up (at 2026-11-17 09:30)\n")
        after = [line for e in vevents(self.ics()) for line in e if line.startswith("UID:")]
        self.assertEqual(before, after)
        self.assertEqual(len(set(before)), 2)
        self.assertTrue(before[1].startswith(before[0][:-len("@pkm")]) and "-2@pkm" in before[1], before)

    def test_left_out_lines_and_days_do_not_apply(self):
        self.write("daybook/2026/11/2026-11-14.md", "# 2026-11-14\n\n- ~~Dentist (at 2026-11-18 10:00)~~\n"
                   "- Gym (at friday 25:00)\n- Lunch (at 2027-03-01 12:00)\n")
        self.write("closes/2026/2026-11-09-week.md", "---\ntype: close\n---\n\n# Week\n\n- Demo (at 2026-11-18)\n")
        self.write("archive/old.md", "# Old\n\n- Old event (at 2026-11-18)\n")
        self.write("notes/course.md", "---\ntype: course\nstatus: done\n---\n\n# Course\n\n- Lecture (at 2026-11-03 10:00) (every 1w)\n")
        out = self.ics()
        self.assertEqual([e for e in vevents(out) if any(line.startswith("SUMMARY:") for line in e)].__len__(), 1)
        find(vevents(out), "Lunch")
        self.assertEqual(self.ics("3"), out)

    def test_it_parses_with_the_icalendar_library_when_installed(self):
        try:
            import icalendar
        except ImportError:
            self.skipTest("icalendar is not installed")
        self.write("notes/mia.md", "# Mia\n\n- Football (at 2026-11-03 17:00-18:00) (every 1w) (skip 2026-11-17)\n")
        calendar = icalendar.Calendar.from_ical(self.ics_bytes())
        self.assertEqual(len(calendar.walk("VEVENT")), 1)


class FamilyExample(unittest.TestCase):
    def test_the_football_is_one_vevent_with_its_rule_and_skip(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as config:
            vault = pathlib.Path(base) / "family"
            shutil.copytree(REPO / "docs/examples/family", vault, ignore=shutil.ignore_patterns("cache"))
            result = subprocess.run([BASH, str(PKM), "--vault", str(vault), "upcoming", "--ics"], cwd=vault,
                                    env=pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=config), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        events = vevents(result.stdout.decode())
        football = [e for e in events if any(line.startswith("SUMMARY:Football training with Joe") for line in e)]
        self.assertEqual(len(football), 1, events)
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=1", football[0])
        self.assertIn("EXDATE:20261117T170000", football[0])
        self.assertIn("DTSTART:20261119T173000", find(events, "School: parents' evening"))
        self.assertIn("DTSTART;VALUE=DATE:19501202", find(events, "Birthday: Nana"))


if __name__ == "__main__":
    unittest.main()
