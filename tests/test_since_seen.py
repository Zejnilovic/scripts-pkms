"""since --seen stores the date and the time; since last starts on that date and leaves out the entries of that day timed at
or before the seen time. Untimed lines on that day stay, and the old date-only state still reads. get --lines clamps an
end past the file. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import unittest

from helpers import VaultCase

DAY_16 = """# 2026-11-16

## Tasks

## Log

- 09:00 Morning call with Acme
- 17:00 Sent the revised timeline
- Untimed line on the sixteenth
"""

DAY_17 = """# 2026-11-17

## Tasks

## Log

- 08:00 Early note on the seventeenth
"""


class SinceSeen(VaultCase):
    def pkm(self, *args, now="20261117120000", **kwargs):
        return super().pkm(*args, now=now, **kwargs)

    def setUp(self):
        super().setUp()
        self.write("daybook/2026/11/2026-11-16.md", DAY_16)
        self.write("daybook/2026/11/2026-11-17.md", DAY_17)

    def state(self):
        return self.read(".pkm/state").strip()

    def test_seen_stores_the_date_and_the_time_and_says_so(self):
        result = self.pkm("since", "--seen", now="20261116120000")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "The next since last starts after 2026-11-16 12:00.\n")
        self.assertEqual(self.state(), "since=2026-11-16 12:00")

    def test_last_leaves_out_the_entries_of_the_seen_day_at_or_before_the_seen_time(self):
        self.ok("since", "--seen", now="20261116120000")
        out = self.ok("since", "last", now="20261117120000")
        self.assertIn("Sent the revised timeline", out)
        self.assertNotIn("Morning call with Acme", out)

    def test_last_keeps_untimed_lines_of_the_seen_day(self):
        self.ok("since", "--seen", now="20261116120000")
        self.assertIn("Untimed line on the sixteenth", self.ok("since", "last", now="20261117120000"))

    def test_last_keeps_the_later_day_in_full(self):
        self.ok("since", "--seen", now="20261116120000")
        self.assertIn("Early note on the seventeenth", self.ok("since", "last", now="20261117120000"))

    def test_seen_on_the_same_day_leaves_nothing_since_when_nothing_is_later(self):
        self.write("daybook/2026/11/2026-11-16.md", "# 2026-11-16\n\n## Tasks\n\n## Log\n\n- 09:00 A\n- 17:00 B\n")
        self.write("daybook/2026/11/2026-11-17.md", "# 2026-11-17\n\n## Tasks\n\n## Log\n")
        self.ok("since", "--seen", now="20261116180000")
        result = self.pkm("since", "last", now="20261116190000")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "Nothing since 2026-11-16.")

    def test_the_old_date_only_state_still_reads_and_starts_on_that_day(self):
        self.write(".pkm/state", "since=2026-11-16\n")
        out = self.ok("since", "last", now="20261117120000")
        self.assertIn("Morning call with Acme", out)
        self.assertIn("Early note on the seventeenth", out)


class GetLinesClamp(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/five.md", "one\ntwo\nthree\nfour\nfive\n")

    def test_an_end_past_the_file_is_clamped_to_its_last_line(self):
        result = self.pkm("get", "five", "--lines", "2-999")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<<<note notes/five.md lines 2-5\ntwo\nthree\nfour\nfive\n>>>end\n")

    def test_a_start_past_the_file_still_exits_2(self):
        result = self.pkm("get", "five", "--lines", "9-12")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside notes/five.md, which has 5 lines", result.stderr)


if __name__ == "__main__":
    unittest.main()
