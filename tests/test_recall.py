"""Recall questions: (recall YYYY-MM-DD <N>d) at the end of an entry. recall lists the ones due, oldest first; recall
<path:line> yes|no moves the interval one rung up the ladder (1 3 7 14 30 60 120) or back to 1d; check flags a malformed
mark; recall lines never show in tasks, since, close or upcoming. The course template. Run: python3 -m unittest discover -s
tests. Names and data are made up. NOW is 2026-11-16 unless a test says otherwise.
"""

import json
import shutil
import tempfile
import pathlib
import unittest

from helpers import REPO, VaultCase

STATS = """# Stats

- When is the median better than the mean? (recall 2026-11-16 7d)
  - When a few extreme values pull the mean away
- Later question (recall 2026-11-19 3d)
- ~~Old question~~ (recall 2026-11-01 1d)
- Code `Inline (recall 2026-11-01 1d)` stays

```
- Fenced (recall 2026-11-01 1d)
```
"""


class DayCase(VaultCase):
    """The examples use 2026-11-16 (the work example's day), not the helper's default day."""

    def pkm(self, *args, now="20261116090000", **kwargs):
        return super().pkm(*args, now=now, **kwargs)


class RecallList(DayCase):
    def setUp(self):
        super().setUp()
        self.write("notes/stats.md", STATS)

    def test_only_the_questions_due_today_or_earlier_are_listed(self):
        self.assertEqual(self.ok("recall").strip(),
                         "notes/stats.md:3: - When is the median better than the mean? (recall 2026-11-16 7d)")

    def test_on_a_later_day_both_are_listed_oldest_first(self):
        lines = self.ok("recall", now="20261119090000").splitlines()
        self.assertEqual([line.split(":")[1] for line in lines], ["3", "5"])

    def test_struck_fenced_and_code_marks_never_come_up(self):
        out = self.ok("recall", now="20261119090000")
        self.assertNotIn("Old question", out)
        self.assertNotIn("Fenced", out)
        self.assertNotIn("Inline", out)

    def test_none_due_exits_1_with_one_line_saying_when_the_next_is_due(self):
        result = self.pkm("recall", now="20261115090000")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.strip().splitlines(), ["Nothing due. The next recall question is due 2026-11-16 (notes/stats.md:3)."])

    def test_with_no_questions_at_all_it_says_so(self):
        self.write("notes/stats.md", "# Stats\n\n- plain\n")
        result = self.pkm("recall")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No recall questions", result.stderr)

    def test_a_note_argument_limits_the_list(self):
        self.write("notes/other.md", "- Other (recall 2026-11-10 1d)\n")
        self.assertEqual(len(self.ok("recall", "notes/stats.md").splitlines()), 1)
        self.assertEqual(len(self.ok("recall").splitlines()), 2)

    def test_json_and_limit_follow_the_contract(self):
        rows = [json.loads(line) for line in self.ok("recall", "--json", now="20261119090000").splitlines()]
        self.assertEqual(rows[0]["path"], "notes/stats.md")
        self.assertEqual(rows[0]["line"], 3)
        self.assertEqual(len(self.ok("recall", "--limit", "1", now="20261119090000").splitlines()), 1)


class RecallRewrite(DayCase):
    def setUp(self):
        super().setUp()
        self.write("notes/stats.md", STATS)

    def test_yes_moves_the_interval_one_rung_up_and_rewrites_only_the_mark(self):
        result = self.pkm("recall", "notes/stats.md:3", "yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "notes/stats.md:3: - When is the median better than the mean? (recall 2026-11-30 14d)")
        before = STATS.splitlines()
        after = self.read("notes/stats.md").splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual([i for i, (a, b) in enumerate(zip(before, after)) if a != b], [2])

    def test_no_sets_the_interval_to_one_day(self):
        self.assertIn("(recall 2026-11-17 1d)", self.ok("recall", "notes/stats.md:3", "no"))

    def test_the_ladder_steps(self):
        cases = [("5d", "7d"), ("1d", "3d"), ("120d", "120d"), ("60d", "120d"), ("7d", "14d")]
        for old, new in cases:
            with self.subTest(old=old):
                self.write("notes/ladder.md", f"- Q (recall 2026-11-16 {old})\n")
                out = self.ok("recall", "notes/ladder.md:1", "yes")
                self.assertIn(f"(recall ", out)
                self.assertIn(f" {new})", out)

    def test_a_line_without_a_mark_exits_1(self):
        result = self.pkm("recall", "notes/stats.md:1", "yes")
        self.assertEqual(result.returncode, 1)

    def test_a_crlf_note_keeps_its_line_ends(self):
        (self.root / "notes/crlf.md").write_bytes(b"- Q (recall 2026-11-16 7d)\r\n- Other\r\n")
        self.ok("recall", "notes/crlf.md:1", "yes")
        self.assertEqual((self.root / "notes/crlf.md").read_bytes(),
                         b"- Q (recall 2026-11-30 14d)\r\n- Other\r\n")


class RecallCheck(DayCase):
    def test_check_flags_a_malformed_mark_and_a_mark_in_a_task_box(self):
        self.write("notes/bad.md", "- Slash (recall 2026/11/16 7d)\n- No unit (recall 2026-11-16 7)\n"
                   "- Bad date (recall 2026-13-40 7d)\n- [ ] Task (recall 2026-11-16 7d)\n"
                   "- Code `(recall 2026/11/16 7d)` stays\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        for line in ["notes/bad.md:1:", "notes/bad.md:2:", "notes/bad.md:3:", "notes/bad.md:4:"]:
            self.assertIn(line, result.stdout)
        self.assertNotIn("notes/bad.md:5:", result.stdout)
        self.assertIn("malformed recall mark", result.stdout)
        self.assertIn("belongs on a question", result.stdout)

    def test_a_valid_mark_passes_check(self):
        self.write("notes/good.md", "- Q (recall 2026-11-16 7d)\n")
        self.assertEqual(self.pkm("check").returncode, 0)


class RecallElsewhere(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/stats.md", "# Stats\n\n- Q (recall 2026-11-10 1d)\n- ! Important (recall 2026-11-10 1d)\n")

    def test_recall_lines_never_show_in_tasks_since_close_or_upcoming(self):
        self.write("daybook/2026/11/2026-11-10.md", "# 2026-11-10\n\n## Tasks\n\n## Log\n\n- 09:00 Entry (recall 2026-11-10 1d)\n")
        for args in [["tasks"], ["since", "2026-11-01"], ["close"], ["upcoming", "30"]]:
            with self.subTest(command=args[0]):
                out = self.pkm(*args).stdout
                self.assertNotIn("recall", out)


class CourseTemplate(VaultCase):
    def test_new_course_writes_the_course_template(self):
        out = self.ok("new", "course", "Stats 101").strip()
        self.assertEqual(out, "notes/stats-101.md")
        text = self.read(out)
        for line in ["type: course\n", "status: active\n", "# Stats 101\n", "## Modules\n", "## Questions\n"]:
            self.assertIn(line, text)


class RecallAcceptance(unittest.TestCase):
    """The study example of the methodology, on copies of the work example (PKM_NOW 2026-11-16)."""

    def setUp(self):
        from helpers import pkm_env, run_pkm
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        self.run_pkm, self.pkm_env = run_pkm, pkm_env
        self.base = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def vault(self, name):
        dest = self.base / name
        shutil.copytree(REPO / "docs/examples/work", dest)
        return dest

    def pkm_run(self, vault, *args, now="20261116090500"):
        env = self.pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=self._config.name)
        return self.run_pkm(list(args), cwd=vault, env=env, vault=vault)

    def test_recall_lists_only_the_question_due_today(self):
        result = self.pkm_run(self.vault("a"), "recall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "notes/statistics-101.md:18: - When is the median better than the mean? (recall 2026-11-16 7d)")

    def test_yes_moves_it_to_14_days_and_no_to_one_day(self):
        vault = self.vault("b")
        self.assertIn("(recall 2026-11-30 14d)", self.pkm_run(vault, "recall", "notes/statistics-101.md:18", "yes").stdout)
        fresh = self.vault("c")
        self.assertIn("(recall 2026-11-17 1d)", self.pkm_run(fresh, "recall", "notes/statistics-101.md:18", "no").stdout)

    def test_on_the_19th_both_are_due_and_the_older_comes_first(self):
        lines = self.pkm_run(self.vault("d"), "recall", now="20261119090500").stdout.splitlines()
        self.assertEqual([line.split(":")[1] for line in lines], ["18", "16"])


if __name__ == "__main__":
    unittest.main()
