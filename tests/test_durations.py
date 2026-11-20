"""Durations: time spent, as (1h30), (1h) or (40m) on an entry or a task, or as an entry whose time is a range
(- 09:00-11:30). The marker wins over a range; an event's line is never time spent; a range that ends before it starts
ends the next day. pkm since … --sum lists the lines it keeps that have one, with their duration, and the total. Run:
python3 -m unittest discover -s tests. A made-up freelancer's vault; names and data are made up. NOW is 2026-11-18.
"""

import json
import unittest

from helpers import VaultCase

NOW = "20261118090000"
MON = "daybook/2026/11/2026-11-16.md"
TUE = "daybook/2026/11/2026-11-17.md"


class Durations(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/acme.md", "---\ntype: organization\n---\n\n# Acme\n")
        self.write("notes/apollo.md", "---\ntype: project\n---\n\n# Apollo\n")
        self.write(MON, "# 2026-11-16\n\n## Log\n\n"
                   "- 09:00-11:30 Workshop with [[acme]]\n"          # 5: 2h30
                   "- 11:45 Call with [[acme]] about the invoice (40m)\n"  # 6: 40m
                   "- 13:00–14:00 Lunch\n"                           # 7: 1h, an en dash
                   "- 14:00-17:15 Built the [[apollo]] export\n"     # 8: 3h15
                   "- 18:00 Wrote the [[acme]] proposal (1h30)\n"    # 9: 1h30
                   "- ~~10:00-12:00 Planning for [[acme]]~~ ([[2026-11-17]])\n"  # 10: struck
                   "- Invoice drafted for [[acme]] (1h5)\n")          # 11: not a duration
        self.write(TUE, "# 2026-11-17\n\n## Log\n\n"
                   "- 15:00-17:00 Review for [[apollo]] (1h30)\n\n"  # 5: the marker wins, 1h30
                   "### Retro with [[acme]]\n\n"
                   "- 22:00-01:30 Fixed the deploy overnight\n"     # 9: 3h30, under the heading
                   "- 09:00-10:00 Standup (at 2026-11-18 09:00-10:00)\n"  # 10: an event
                   "- [x] Send the slides (25m)\n")                 # 11: 25m

    def test_since_about_a_name_sums_its_timed_lines(self):
        out = self.ok("since", "2026-11-16", "--about", "acme", "--sum", now=NOW)
        self.assertEqual(out, f"{MON}:5: 2h30: - 09:00-11:30 Workshop with [[acme]]\n"
                              f"{MON}:6: 40m: - 11:45 Call with [[acme]] about the invoice (40m)\n"
                              f"{MON}:9: 1h30: - 18:00 Wrote the [[acme]] proposal (1h30)\n"
                              f"{TUE}:9: 3h30: - 22:00-01:30 Fixed the deploy overnight\n"
                              f"{TUE}:11: 25m: - [x] Send the slides (25m)\n"
                              "Total: 8h35 in 5 lines\n")

    def test_since_without_a_name_sums_every_timed_line(self):
        lines = self.ok("since", "2026-11-16", "--sum", now=NOW).splitlines()
        self.assertEqual(lines[-1], "Total: 14h20 in 8 lines")
        self.assertIn(f"{MON}:7: 1h: - 13:00–14:00 Lunch", lines)
        self.assertIn(f"{TUE}:5: 1h30: - 15:00-17:00 Review for [[apollo]] (1h30)", lines)
        self.assertFalse(any(f"{MON}:10:" in line or f"{MON}:11:" in line or f"{TUE}:10:" in line for line in lines))
        under = self.ok("since", "2026-11-16", "--under", "apollo", "--sum", now=NOW).splitlines()
        self.assertEqual(under[-1], "Total: 4h45 in 2 lines")

    def test_json_gives_the_minutes_and_the_total(self):
        rows = [json.loads(line) for line in
                self.ok("since", "2026-11-16", "--about", "acme", "--sum", "--json", now=NOW).splitlines()]
        self.assertEqual(rows[0], {"kind": "time", "path": MON, "line": 5, "text": "- 09:00-11:30 Workshop with [[acme]]",
                                   "minutes": 150})
        self.assertEqual(rows[-1], {"kind": "total", "path": None, "line": None, "text": None, "minutes": 515})

    def test_nothing_timed_exits_1_and_seen_takes_no_sum(self):
        result = self.pkm("since", "2026-11-18", "--sum", now=NOW)
        self.assertEqual((result.returncode, result.stdout), (1, "Nothing timed since 2026-11-18.\n"))
        self.assertEqual(self.pkm("since", "--seen", "--sum", now=NOW).returncode, 2)

    def test_durations_make_no_tasks_and_no_problems(self):
        self.assertEqual(self.pkm("tasks", now=NOW).returncode, 1)
        self.assertNotIn("Problems:", self.pkm("check", now=NOW).stdout)

if __name__ == "__main__":
    unittest.main()
