"""The line scanner (lib/pkm/lines.sh line_records): which lines are records, their kind, markers, day page date, writer,
and the note's type and status. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import os
import subprocess
import unittest

from helpers import BASH, REPO, VaultCase


class LineRecords(VaultCase):
    def records(self, archive="no"):
        script = ('pkm_home="$1"; for f in core dates config vault lines; do . "$pkm_home/lib/pkm/$f.sh"; done; '
                  'vault=$PWD; tmp=$(mktemp -d); line_records "$2"; rm -rf "$tmp"')
        result = subprocess.run([BASH, "-c", script, "pkm", str(REPO), archive], cwd=self.root, capture_output=True,
                                text=True, env={**os.environ, "PKM_NOW": "20261111090000"})
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {}
        for line in result.stdout.splitlines():
            f = line.split("\x1f")
            self.assertEqual(len(f), 10, line)
            rows[f"{f[0]}:{f[1]}"] = f[2:]
        return rows

    def test_kinds_markers_and_writers(self):
        self.write("daybook/2026/11/2026-11-14-alex.md", "# 2026-11-14 Alex\n\n"
                   "- 11:40 [[school]]: parents' evening (at 2026-11-19 17:30-19:00)\n"
                   "- Lunch with Jane Doe (@ friday 12:00)\n"
                   "- [ ] Run the [[apollo]] demo for [[acme]] (at 2026-11-20 14:00-15:00) (high)\n"
                   "- Meet at Acme (at the office)\n"
                   "- Keep it (for now)\n"
                   "- Plain entry with (parentheses)\n"
                   "- What does Apollo cost? (recall 2026-11-20 3d)\n"
                   "- [ ] Boxed question (recall 2026-11-20 3d)\n"
                   "- ! Decided: ship it (due friday)\n")
        rows = self.records()
        p = "daybook/2026/11/2026-11-14-alex.md"
        self.assertEqual(rows[f"{p}:3"][:5], ["event", "", "at 2026-11-19 17:30-19:00", "2026-11-14", "alex"])
        self.assertEqual(rows[f"{p}:4"][:3], ["event", "", "at friday 12:00"])
        self.assertEqual(rows[f"{p}:5"][:3], ["task", "open", "at 2026-11-20 14:00-15:00\thigh"])
        for n in (6, 7, 8):
            self.assertNotIn(f"{p}:{n}", rows)
        self.assertEqual(rows[f"{p}:9"][:2], ["question", ""])
        self.assertEqual(rows[f"{p}:10"][:2], ["question", "open"])
        self.assertEqual(rows[f"{p}:11"][:3], ["entry", "", "due friday"])
        self.assertEqual(rows[f"{p}:11"][-1], "- ! Decided: ship it (due friday)")

    def test_a_note_gives_its_type_and_status_and_has_no_page_date(self):
        self.write("notes/mia.md", "---\ntitle: Mia\ntype: person\nstatus: active\nlater: (at 2026-11-19)\n---\n\n# Mia\n\n"
                   "- Football (at 2026-11-03 17:00-18:00) (every 1w) (skip 2026-11-17)\n")
        rows = self.records()
        self.assertEqual(rows["notes/mia.md:10"][:7],
                         ["event", "", "at 2026-11-03 17:00-18:00\tevery 1w\tskip 2026-11-17", "", "", "person", "active"])
        self.assertEqual(len(rows), 1)

    def test_code_headings_struck_lines_and_list_boxes_are_not_records(self):
        self.write("daybook/2026/11/2026-11-12.md", "# 2026-11-12 (at 2026-11-19)\n\n"
                   "- ~~Dentist (at 2026-12-01)~~ ([[2026-11-13]])\n"
                   "- [ ] ~~Old task (due today)~~\n"
                   "```\n- Lunch (at friday)\n- [ ] In code\n```\n"
                   "- [?] Odd box\n")
        self.write("notes/shopping.md", "---\ntype: list\n---\n\n# Shopping\n\n- [ ] Milk (due today)\n- Bread (due friday)\n")
        rows = self.records()
        self.assertEqual(sorted(rows), ["notes/shopping.md:8"])
        self.assertEqual(rows["notes/shopping.md:8"][0], "entry")

    def test_a_close_page_has_no_writer_and_archive_is_read_only_when_asked(self):
        self.write("closes/2026/2026-11-09-week.md", "---\ntype: close\n---\n\n# Week\n\n- [ ] Carry on (due 2026-11-20)\n")
        self.write("archive/old.md", "# Old\n\n- [ ] Archived (due 2026-10-01)\n")
        self.write("daybook/2026/11/2026-11-13.md", "﻿# 2026-11-13\r\n\r\n- Call (at today 10:00)\r\n")
        rows = self.records()
        self.assertEqual(rows["closes/2026/2026-11-09-week.md:7"][:6], ["task", "open", "due 2026-11-20", "2026-11-09", "", "close"])
        self.assertNotIn("archive/old.md:3", rows)
        self.assertEqual(rows["daybook/2026/11/2026-11-13.md:3"][-1], "- Call (at today 10:00)")
        self.assertIn("archive/old.md:3", self.records("yes"))

    def test_a_date_with_the_calendar_emoji_is_a_due_marker(self):
        self.write("notes/x.md", "# X\n\n- [ ] Pay 📅 2026-11-12\n- [ ] Both (due 2026-11-13) 📅 2026-11-12\n")
        rows = self.records()
        self.assertEqual(rows["notes/x.md:3"][2], "due 2026-11-12")
        self.assertEqual(rows["notes/x.md:4"][2], "due 2026-11-13")

    def test_time_spent_is_a_duration_marker_or_a_range_at_the_start(self):
        self.write("daybook/2026/11/2026-11-16.md", "# 2026-11-16\n\n- 09:00-11:30 Workshop\n- 11:45 Call (40m)\n"
                   "- 13:00 Lunch\n- 25:00-26:00 Not a time\n- 10:00-10:00 Nothing\n- Talk (1h5) (2 h)\n"
                   "- 14:00–15:00 With an en dash (1h)\n")
        rows = self.records()
        p = "daybook/2026/11/2026-11-16.md"
        self.assertEqual(rows[f"{p}:3"][:3], ["entry", "", ""])
        self.assertEqual(rows[f"{p}:4"][:3], ["entry", "", "40m"])
        self.assertEqual(rows[f"{p}:9"][:3], ["entry", "", "1h"])
        for n in (5, 6, 7, 8):
            self.assertNotIn(f"{p}:{n}", rows)


if __name__ == "__main__":
    unittest.main()
