"""Golden output: what tasks, upcoming, close, since and check print on the two example vaults and on tests/golden/zoo, a
vault of edge cases (relative dates, waiting forms, routines, struck lines, code, lists, CRLF and a byte order mark). The
expected output is in tests/golden/out/<vault>/<name>.out, with the exit code on its first line. A change that alters it on
purpose rewrites the files with PKM_GOLDEN=update, and the diff shows what changed. Run: python3 -m unittest discover -s
tests. Names and data are made up.
"""

import os
import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, pkm_env, run_pkm

GOLDEN = REPO / "tests/golden"
VAULTS = {
    "work": (REPO / "docs/examples/work", "20261116090500", "2026-11-09"),
    "family": (REPO / "docs/examples/family", "20261115090000", "2026-11-09"),
    "zoo": (GOLDEN / "zoo", "20261111090000", "2026-11-09"),
}


def commands(since):
    return {
        "tasks": ["tasks", "--all"],
        "tasks-open": ["tasks"],
        "tasks-waiting": ["tasks", "waiting", "--all"],
        "tasks-someday": ["tasks", "someday", "--all"],
        "tasks-done": ["tasks", "done", "--all"],
        "tasks-stale": ["tasks", "--stale", "0", "--all"],
        "upcoming": ["upcoming", "60"],
        "close": ["close"],
        "close-json": ["close", "--json"],
        "since": ["since", since],
        "check": ["check"],
    }


class Golden(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def run_vault(self, name):
        source, now, since = VAULTS[name]
        vault = pathlib.Path(self._tmp.name) / name
        shutil.copytree(source, vault, ignore=shutil.ignore_patterns("cache"))
        environment = pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=self._config.name)
        update = os.environ.get("PKM_GOLDEN") == "update"
        for label, args in commands(since).items():
            result = run_pkm(args, cwd=vault, env=environment, vault=vault)
            got = f"exit {result.returncode}\n{result.stdout}"
            path = GOLDEN / "out" / name / f"{label}.out"
            if update:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(got)
                continue
            with self.subTest(vault=name, command=" ".join(args)):
                self.assertEqual(got, path.read_text(), f"pkm {' '.join(args)} on {name} changed")

    def test_the_work_example(self):
        self.run_vault("work")

    def test_the_family_example(self):
        self.run_vault("family")

    def test_the_zoo_of_edge_cases(self):
        self.run_vault("zoo")


if __name__ == "__main__":
    unittest.main()
