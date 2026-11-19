"""Whose move it is: (for <who>) on a task or a question, with a link or the name of a writer of a shared vault.
pkm tasks --for <who> lists them, a writer's own tasks included, and the close groups them by person in == for. Run:
python3 -m unittest discover -s tests. Names and data are made up. NOW is Monday 2026-11-16.
"""

import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

NOW = "20261116090000"
ALEX = "daybook/2026/11/2026-11-12-alex.md"
SAM = "daybook/2026/11/2026-11-13-sam.md"


class ForWho(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(".pkm/config", "format=1\nshared=yes\n")
        self.write("notes/jane-doe.md", "---\ntype: person\naliases: [Jane]\n---\n\n# Jane Doe\n")
        self.write(ALEX, "# 2026-11-12 Alex\n\n## Tasks\n\n- [ ] Book the boiler service (for sam) (due 2026-11-27)\n"
                   "- [ ] Pick up the photos\n- [ ] Draft the release plan (for [[jane-doe]]) (due 2026-11-10)\n"
                   "- [ ] Ask about the budget (for [[jane-doe|Jane]]) (waiting 2026-11-09)\n- [ ] Rest a bit (for now)\n"
                   "- [ ] Call Bob (for bob)\n\n## Log\n\n"
                   "- 11:50 Should we ask the plumber about a stair rail? (for sam)\n- 12:00 Is the demo on Tuesday? (for [[jane-doe]])\n")
        self.write(SAM, "# 2026-11-13 Sam\n\n## Tasks\n\n- [ ] Renew the parking permit\n- [ ] Plan the trip (for alex)\n")

    def test_tasks_for_a_writer_lists_theirs_and_those_for_them(self):
        out = self.ok("tasks", "--for", "sam", now=NOW).splitlines()
        self.assertEqual(sorted(line.split(": ", 1)[1] for line in out), [
            "- 11:50 Should we ask the plumber about a stair rail? (for sam)",
            "- [ ] Book the boiler service (for sam) (due 2026-11-27)",
            "- [ ] Renew the parking permit",
        ])

    def test_tasks_for_alex_takes_the_unassigned_tasks_on_alexs_pages(self):
        out = self.ok("tasks", "--for", "Alex", now=NOW)
        for text in ["Pick up the photos", "Rest a bit (for now)", "Call Bob (for bob)", "Plan the trip (for alex)"]:
            self.assertIn(text, out)
        self.assertNotIn("boiler", out)
        self.assertNotIn("release plan", out)

    def test_tasks_for_a_note_takes_its_links_and_aliases(self):
        for who in ["jane-doe", "Jane", "[[jane-doe]]"]:
            out = self.ok("tasks", "--for", who, now=NOW).splitlines()
            self.assertEqual([line.split(":")[1] for line in out], ["7", "8", "15"], who)
        self.assertEqual(self.pkm("tasks", "--for", "nobody", now=NOW).returncode, 1)
        self.assertEqual(self.pkm("tasks", "--for", now=NOW).returncode, 2)

    def test_the_close_groups_them_by_person(self):
        out = self.ok("close", now=NOW)
        part = out.split("== for\n")[1].split("\n== ")[0].splitlines()
        self.assertEqual(part, [
            f"{SAM}:6: for Alex: - [ ] Plan the trip (for alex)",
            f"{ALEX}:7: for Jane Doe, overdue: - [ ] Draft the release plan (for [[jane-doe]]) (due 2026-11-10)",
            f"{ALEX}:8: for Jane Doe, waiting 7 days: - [ ] Ask about the budget (for [[jane-doe|Jane]]) (waiting 2026-11-09)",
            f"{ALEX}:15: for Jane Doe, question: - 12:00 Is the demo on Tuesday? (for [[jane-doe]])",
            f"{ALEX}:5: for Sam, due 2026-11-27: - [ ] Book the boiler service (for sam) (due 2026-11-27)",
            f"{ALEX}:14: for Sam, question: - 11:50 Should we ask the plumber about a stair rail? (for sam)",
        ])
        rest = out.split("== for\n")[0]
        self.assertNotIn("release plan", rest)
        self.assertNotIn("Ask about the budget", rest)
        self.assertNotIn("stair rail", rest)

    def test_check_reports_for_on_a_line_that_is_neither_a_task_nor_a_question(self):
        self.write("daybook/2026/11/2026-11-14-sam.md", "# 2026-11-14 Sam\n\n- Dentist (at 2026-11-20 10:00) (for alex)\n"
                   "- Talked to Jane (for [[jane-doe]])\n- A note for Bob (for bob)\n")
        out = self.pkm("check", now=NOW).stdout
        self.assertIn("daybook/2026/11/2026-11-14-sam.md:3: (for …) belongs on a task or a question", out)
        self.assertIn("daybook/2026/11/2026-11-14-sam.md:4: (for …) belongs on a task or a question", out)
        self.assertNotIn("2026-11-14-sam.md:5", out)
        self.assertNotIn(ALEX, out)


class FamilyExample(unittest.TestCase):
    def test_sams_moves_on_the_family_vault(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as config:
            vault = pathlib.Path(base) / "family"
            shutil.copytree(REPO / "docs/examples/family", vault, ignore=shutil.ignore_patterns("cache"))
            env = pkm_env(PKM_NOW="20261115090000", XDG_CONFIG_HOME=config)
            tasks = run_pkm(["tasks", "--for", "sam"], cwd=vault, env=env, vault=vault)
            close = run_pkm(["close"], cwd=vault, env=env, vault=vault)
        self.assertEqual(tasks.returncode, 0, tasks.stderr)
        self.assertIn("Book the boiler service (for sam)", tasks.stdout)
        self.assertIn("stair rail", tasks.stdout)
        self.assertIn("== for\n", close.stdout)
        self.assertIn("for Sam, question:", close.stdout)


if __name__ == "__main__":
    unittest.main()
