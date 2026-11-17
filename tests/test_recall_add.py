"""pkm recall add: a question written at the end of a note's ## Questions section, with its answers indented below it, marked
(recall <tomorrow> 1d). Refuses a day or close page, a question already in the note, and an unknown note. Run:
python3 -m unittest discover -s tests. Names and data are made up. TODAY is 2026-11-16 (so tomorrow is 2026-11-17).
"""

import unittest

from helpers import VaultCase

COURSE = """# Statistics 101

## Modules

- Descriptive statistics

## Questions

- Old question (recall 2026-11-10 3d)
  - Old answer

## Notes

- Something else
"""


class RecallAdd(VaultCase):
    def pkm(self, *args, now="20261116090000", **kwargs):
        return super().pkm(*args, now=now, **kwargs)

    def setUp(self):
        super().setUp()
        self.write("notes/statistics-101.md", COURSE)

    def test_writes_at_the_end_of_the_questions_section_with_tomorrows_mark(self):
        out = self.ok("recall", "add", "statistics-101", "When is the median better than the mean?",
                      "--answer", "When a few extreme values pull the mean away")
        self.assertEqual(out, "notes/statistics-101.md:11\n")
        self.assertEqual(self.read("notes/statistics-101.md"), COURSE.replace(
            "  - Old answer\n\n## Notes",
            "  - Old answer\n- When is the median better than the mean? (recall 2026-11-17 1d)\n"
            "  - When a few extreme values pull the mean away\n\n## Notes"))

    def test_each_answer_is_an_indented_line_below_the_question(self):
        self.ok("recall", "add", "statistics-101", "Q?", "--answer", "First", "--answer", "Second")
        lines = self.read("notes/statistics-101.md").splitlines()
        i = lines.index("- Q? (recall 2026-11-17 1d)")
        self.assertEqual(lines[i + 1:i + 3], ["  - First", "  - Second"])

    def test_no_answer_writes_the_question_alone(self):
        self.ok("recall", "add", "statistics-101", "Q?")
        lines = self.read("notes/statistics-101.md").splitlines()
        i = lines.index("- Q? (recall 2026-11-17 1d)")
        self.assertFalse(lines[i + 1].startswith("  - "))

    def test_creates_the_questions_section_at_the_end_when_missing(self):
        self.write("notes/plain.md", "# Plain\n\n## Modules\n\n- One\n")
        out = self.ok("recall", "add", "plain", "Q?", "--answer", "A")
        self.assertEqual(out, "notes/plain.md:9\n")
        self.assertEqual(self.read("notes/plain.md"),
                         "# Plain\n\n## Modules\n\n- One\n\n## Questions\n\n- Q? (recall 2026-11-17 1d)\n  - A\n")

    def test_keeps_the_files_crlf_line_ends(self):
        self.write("notes/crlf.md", "# Crlf\r\n\r\n## Questions\r\n\r\n- Old (recall 2026-11-10 3d)\r\n")
        self.ok("recall", "add", "crlf", "New?", "--answer", "Yes")
        text = (self.root / "notes/crlf.md").read_bytes().decode()
        self.assertIn("- New? (recall 2026-11-17 1d)\r\n  - Yes\r\n", text)
        self.assertEqual(text.count("\n"), text.count("\r\n"))

    def test_a_day_page_is_refused(self):
        self.write("daybook/2026/11/2026-11-16.md", "# 2026-11-16\n\n## Log\n\n- 09:00 Entry\n")
        before = self.read("daybook/2026/11/2026-11-16.md")
        result = self.pkm("recall", "add", "2026-11-16", "Q?")
        self.assertEqual(result.returncode, 1)
        self.assertIn("is a day page", result.stderr + result.stdout)
        self.assertEqual(self.read("daybook/2026/11/2026-11-16.md"), before)

    def test_a_close_page_is_refused(self):
        self.write("closes/2026/2026-11-09-week.md", "---\ntype: close\n---\n\n# Week\n")
        before = self.read("closes/2026/2026-11-09-week.md")
        result = self.pkm("recall", "add", "2026-11-09-week", "Q?")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.read("closes/2026/2026-11-09-week.md"), before)

    def test_a_question_already_in_the_note_is_refused_with_its_place(self):
        before = self.read("notes/statistics-101.md")
        result = self.pkm("recall", "add", "statistics-101", "Old question")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("notes/statistics-101.md:9", result.stderr)
        self.assertEqual(self.read("notes/statistics-101.md"), before)

    def test_an_unknown_note_exits_1(self):
        result = self.pkm("recall", "add", "nowhere", "Q?")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No note named nowhere", result.stderr)

    def test_a_missing_question_is_a_usage_error(self):
        result = self.pkm("recall", "add", "statistics-101")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage: pkm recall add <note> <question> [--answer <text>]", result.stderr)

    def test_a_question_that_is_due_is_listed_by_recall_the_next_day(self):
        self.ok("recall", "add", "statistics-101", "Q?", "--answer", "A")
        lines = self.ok("recall", "statistics-101", now="20261117090000").splitlines()
        self.assertIn("notes/statistics-101.md:11: - Q? (recall 2026-11-17 1d)", lines)


if __name__ == "__main__":
    unittest.main()
