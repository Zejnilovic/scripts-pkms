"""The awk date library (lib/pkm/dates.sh awk_dates): day numbers, weekdays, months, and the day words of the method
(today, tomorrow, +3d, +2w, friday) read against a day page's date. It is checked against Python's calendar for years
of dates, and against the bash parse_day for a few. Run: python3 -m unittest discover -s tests. The awk on PATH is the
one tested: the Linux images run these tests with mawk and with gawk.
"""

import datetime
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import BASH, REPO, VaultCase

WEEKDAYS = {"mon": 1, "monday": 1, "tue": 2, "tues": 2, "tuesday": 2, "wed": 3, "wednesday": 3, "thu": 4,
            "thur": 4, "thurs": 4, "thursday": 4, "fri": 5, "friday": 5, "sat": 6, "saturday": 6, "sun": 7,
            "sunday": 7}
READABLE = ["today", "tomorrow", "+0d", "+1d", "+3d", "+10d", "+400d", "+1w", "+2w", "+5", "Friday", "TODAY",
            " friday ", *WEEKDAYS]
UNREADABLE = ["", "soon", "+", "+w", "+3x", "-3d", "next friday", "2026-13-45", "2026-02-30", "2026-02-29",
              "1900-02-29", "2026-1-05", "20261105"]


def days(first, last):
    day = datetime.date.fromisoformat(first)
    while day <= datetime.date.fromisoformat(last):
        yield day
        day += datetime.timedelta(days=1)


# A year of days, a leap day, the turn of a century that isn't a leap year, and one that is.
PAGES = [*days("2026-01-01", "2026-12-31"), *days("2028-02-20", "2028-03-05"), *days("2099-12-20", "2100-03-05"),
         *days("1999-12-25", "2000-03-05")]


def expected(word, page):
    """What a day word means on the day page of the date page: the method's rule, written in Python."""
    w = " ".join(word.lower().split())
    if w == "today":
        return page.isoformat()
    if w == "tomorrow":
        return (page + datetime.timedelta(days=1)).isoformat()
    if w.startswith("+"):
        n, per = w[1:], 1
        if n.endswith("w"):
            n, per = n[:-1], 7
        elif n.endswith("d"):
            n = n[:-1]
        if not n.isdigit():
            return ""
        return (page + datetime.timedelta(days=int(n) * per)).isoformat()
    if w in WEEKDAYS:
        ahead = (WEEKDAYS[w] - page.isoweekday()) % 7 or 7
        return (page + datetime.timedelta(days=ahead)).isoformat()
    try:
        if len(w) == 10 and datetime.date.fromisoformat(w).isoformat() == w:
            return w
    except ValueError:
        pass
    return ""


def months_later(day, n):
    index = day.year * 12 + day.month - 1 + n
    year, month = divmod(index, 12)
    month += 1
    following = datetime.date(year + (month == 12), month % 12 + 1, 1)
    last = (following - datetime.timedelta(days=1)).day
    return datetime.date(year, month, min(day.day, last)).isoformat()


def awk(program, rows):
    """Runs an awk program with awk_dates in front of it, on tab-separated rows; returns its output lines."""
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as handle:
        handle.write("".join("\t".join(row) + "\n" for row in rows))
        name = handle.name
    try:
        script = f'pkm_home="$1"; . "$1/lib/pkm/core.sh"; . "$1/lib/pkm/dates.sh"; awk -F "\\t" "$(awk_dates)"\'{program}\' "$2"'
        result = subprocess.run([BASH, "-c", script, "pkm", str(REPO), name], capture_output=True, text=True,
                                env={**os.environ, "PKM_NOW": "20261025143012"})
    finally:
        os.unlink(name)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.splitlines()


class DayNumbers(unittest.TestCase):
    def test_weekday_and_day_number_match_the_calendar(self):
        out = awk("{ z = ymd($1); print iso(z), wday(z), z }", [[d.isoformat()] for d in PAGES])
        epoch = datetime.date(1970, 1, 1)
        self.assertEqual(out, [f"{d.isoformat()} {d.isoweekday()} {(d - epoch).days}" for d in PAGES])

    def test_a_day_is_a_calendar_date_written_yyyy_mm_dd(self):
        words = ["2026-11-19", "2028-02-29", "2000-02-29", *UNREADABLE]
        out = awk("{ print is_day($1) }", [[w] for w in words])
        self.assertEqual(out, ["1", "1", "1"] + ["0"] * len(UNREADABLE))

    def test_months_keep_the_day_or_take_the_last_day_of_a_shorter_month(self):
        rows = [[d.isoformat(), str(n)] for d in PAGES[::5] for n in (-13, -1, 0, 1, 2, 11, 12, 25)]
        out = awk("{ print add_months($1, $2) }", rows)
        self.assertEqual(out, [months_later(datetime.date.fromisoformat(d), int(n)) for d, n in rows])


class DayWords(unittest.TestCase):
    def test_every_day_word_on_every_page_date_matches_the_method(self):
        rows = [[w, d.isoformat()] for d in PAGES for w in READABLE + UNREADABLE]
        out = awk('{ print "[" day_word($1, $2) "]" }', rows)
        self.assertEqual(out, [f"[{expected(w, datetime.date.fromisoformat(d))}]" for w, d in rows])

    def test_a_relative_word_is_one_that_needs_a_page_date(self):
        words = ["today", "tomorrow", "+3d", "+2w", "+5", "friday", "Sun", "2026-11-19", "soon", "+w", "2026-02-30"]
        out = awk("{ print relative_word($1) }", [[w] for w in words])
        self.assertEqual(out, ["1"] * 7 + ["0"] * 4)

    def test_awk_and_the_bash_parse_day_agree(self):
        pages = ["2026-11-19", "2026-12-27", "2028-02-27", "2026-03-01"]
        words = [w for w in READABLE if w.strip() == w]
        script = ('pkm_home="$1"; . "$1/lib/pkm/core.sh"; . "$1/lib/pkm/cycles.sh"; . "$1/lib/pkm/dates.sh"; shift; '
                  'for today in ' + " ".join(pages) + '; do for w in "$@"; do parse_day "$w" || echo; done; done')
        result = subprocess.run([BASH, "-c", script, "pkm", str(REPO), *words], capture_output=True, text=True,
                                env={**os.environ, "PKM_NOW": "20261025143012"})
        self.assertEqual(result.returncode, 0, result.stderr)
        out = awk("{ print day_word($1, $2) }", [[w, p] for p in pages for w in words])
        self.assertEqual(out, result.stdout.splitlines())


class NoDateProcessPerTask(VaultCase):
    """task_records reads every date in awk: the number of date processes doesn't grow with the tasks."""

    def date_calls(self, tasks):
        bin_dir = self.root.parent / (self.root.name + "-bin")
        bin_dir.mkdir(exist_ok=True)
        log = bin_dir / "log"
        log.write_text("")
        real = shutil.which("date")
        (bin_dir / "date").write_text(f'#!/bin/sh\necho "$*" >> "{log}"\nexec "{real}" "$@"\n')
        (bin_dir / "date").chmod(0o755)
        body = "".join(f"- [ ] Task {i} (due {w})\n" for i, w in enumerate(tasks))
        self.write("daybook/2026/11/2026-11-10.md", "# 2026-11-10\n\n" + body)
        self.write("notes/routines.md", "# Routines\n\n- [ ] Pay rent (due 2026-11-01) (every 1m)\n")
        path = f"{bin_dir}:{os.environ['PATH']}"
        self.ok("tasks", "--all", env={"PATH": path})
        self.pkm("check", env={"PATH": path})
        return len(log.read_text().splitlines())

    def test_relative_dates_start_no_date_process(self):
        few = self.date_calls(["friday"])
        many = self.date_calls(["friday", "+3d", "tomorrow", "today", "+2w", "mon", "sunday", "2026-11-30"] * 5)
        self.assertEqual(few, many)


class TaskDatesStillRead(VaultCase):
    def test_relative_dates_resolve_against_their_page_and_bad_ones_are_problems(self):
        self.write("daybook/2026/11/2026-11-10.md", "# 2026-11-10\n\n- [ ] Call Jane Doe (due friday)\n"
                   "- [ ] Send the Apollo notes (due +2w)\n- [ ] Book the room (due 2026-02-30)\n"
                   "- [ ] Ask Acme (waiting 2026-02-31)\n- [ ] Plan (start 2026-11-3)\n")
        self.write("notes/x.md", "# X\n\n- [ ] Read it (due tomorrow)\n")
        out = self.ok("tasks", "--all")
        self.assertIn("Call Jane Doe", out)
        self.assertIn("2026-11-13", self.ok("upcoming", "30", now="20261110090000"))
        self.assertIn("2026-11-24", self.ok("upcoming", "30", now="20261110090000"))
        problems = self.pkm("check").stdout
        self.assertIn("2026-11-10.md:5: cannot read the due date 2026-02-30", problems)
        self.assertIn("2026-11-10.md:6: cannot read the waiting date 2026-02-31", problems)
        self.assertIn("2026-11-10.md:7: cannot read the start date 2026-11-3", problems)
        self.assertIn("notes/x.md:3: relative date tomorrow is outside a day page", problems)


if __name__ == "__main__":
    unittest.main()
