"""Where a ### block ends: at the next heading, or at a blank line after the block's lines that is followed by an entry
(- HH:MM). The lines in it are about what its heading links (since --about, backlinks, --under); an entry after it is
not. pkm add, and pkm moved, write a blank line before an entry that follows a block. Run:
python3 -m unittest discover -s tests. Names and data are made up. NOW is Thursday 2026-11-19.
"""

import unittest

from helpers import VaultCase

NOW = "20261119190000"
DAY = "daybook/2026/11/2026-11-19.md"


class BlockEnd(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/incident-2026-11-19.md", "# Incident 2026-11-19\n")
        self.write("notes/boiler.md", "# Boiler\n")
        self.write(DAY, "# 2026-11-19\n\n## Log\n\n### 10:05 Incident: payments timeouts, [[incident-2026-11-19]]\n\n"
                   "- 10:05 Alerts: p95 at 4 s on checkout\n- 10:30 It is the connection pool\n\n"
                   "- Decided: keep 100 until the migration\n\n"
                   "- 18:30 [[joe-bloggs-plumber|Joe]] can start on 2026-12-08\n- 18:50 The [[boiler]] is making the noise again\n")

    def lines(self, out):
        return [int(line.split(":")[1]) for line in out.splitlines() if line.startswith(DAY)]

    def test_the_block_ends_at_a_blank_line_and_an_entry(self):
        self.assertEqual(self.lines(self.ok("backlinks", "incident-2026-11-19", now=NOW)), [5, 7, 8, 10])
        about = self.ok("since", "2026-11-19", "--about", "incident-2026-11-19", now=NOW)
        self.assertEqual(self.lines(about.split("== log\n")[1].split("\n== ")[0]), [5, 7, 8, 10])
        self.assertEqual(self.lines(self.ok("backlinks", "boiler", now=NOW)), [13])

    def test_add_after_a_block_leaves_a_blank_line_so_the_entry_is_not_in_it(self):
        self.write(DAY, "# 2026-11-19\n\n## Log\n\n### 10:00\n\nNotes from the call with [[acme]]\nThey want it Friday\n")
        out = self.ok("add", "Lunch with [[jane-doe]]", now="20261119120000").strip()
        self.assertEqual(out, f"{DAY}:10")
        self.assertTrue(self.read(DAY).endswith("They want it Friday\n\n- 12:00 Lunch with [[jane-doe]]\n"))
        self.assertNotIn("Lunch", self.ok("backlinks", "acme", now=NOW))
        # The next entry follows the last one, with no blank line: the block has ended.
        self.ok("add", "Called the school", now="20261119130000")
        self.assertTrue(self.read(DAY).endswith("- 12:00 Lunch with [[jane-doe]]\n- 13:00 Called the school\n"))

    def test_an_entry_on_a_page_without_a_block_stays_right_below(self):
        self.write(DAY, "# 2026-11-19\n\n## Log\n\n- 09:00 Coffee\n")
        self.ok("add", "Tea", now="20261119100000")
        self.assertTrue(self.read(DAY).endswith("- 09:00 Coffee\n- 10:00 Tea\n"))


if __name__ == "__main__":
    unittest.main()
