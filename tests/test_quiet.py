"""Tests for list --quiet n: the notes the other filters match that no day page in the last n days links. Day and close
pages are never listed. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

from helpers import VaultCase


class ListQuiet(VaultCase):
    """NOW is 2026-10-25: the last 3 days are 10-23, 10-24 and 10-25."""

    def setUp(self):
        super().setUp()
        self.write("people/jane-doe.md", "---\ntype: person\n---\n\n# Jane Doe\n")
        self.write("people/john-roe.md", "---\ntype: person\n---\n\n# John Roe\n")
        self.write("notes/apollo.md", "---\ntype: project\n---\n\n# Apollo\n")
        self.write("daybook/2026/10/2026-10-24.md", "# 2026-10-24\n\n- Met [[jane-doe]]\n")
        self.write("daybook/2026/09/2026-09-01.md", "# 2026-09-01\n\n- Met [[john-roe]]\n")

    def paths(self, *args):
        return [line.split("\t")[0] for line in self.ok("list", "--quiet", *args).splitlines()]

    def test_a_person_no_day_in_the_window_links_is_listed(self):
        self.assertEqual(self.paths("3", "type=person"), ["people/john-roe.md"])

    def test_day_and_close_pages_are_never_listed(self):
        self.write("closes/week-43.md", "# Week 43\n")
        paths = self.paths("3")
        self.assertIn("notes/apollo.md", paths)
        self.assertIn("people/john-roe.md", paths)
        self.assertNotIn("people/jane-doe.md", paths)
        self.assertFalse([p for p in paths if p.startswith("daybook/") or p.startswith("closes/")], paths)

    def test_the_window_is_today_and_the_days_before(self):
        self.assertEqual(self.paths("1", "type=person"), ["people/jane-doe.md", "people/john-roe.md"])

    def test_the_count_must_be_a_whole_number(self):
        self.assertEqual(self.pkm("list", "--quiet", "x").returncode, 2)


if __name__ == "__main__":
    import unittest

    unittest.main()
