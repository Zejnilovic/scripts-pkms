"""--json on upcoming, tags, cycle and vaults, and pkm --vaults [<a,b>] tasks|upcoming|since: each vault in its own
section, == vault <name>, with paths relative to that vault, and a vault field in --json. Nothing is copied between
vaults. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import json
import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

NOW = "20261116090500"


class Json(VaultCase):
    def rows(self, *args, now="20261119090000"):
        return [json.loads(line) for line in self.ok(*args, now=now).splitlines()]

    def test_upcoming_gives_date_kind_place_and_an_events_time(self):
        self.write("notes/mia.md", "---\nbirthday: 2015-11-21\n---\n\n# Mia\n\n- Football (at 2026-11-20 17:00-18:00)\n"
                   "- Trip (at 2026-11-22 to 2026-11-23)\n- [ ] Pack (due 2026-11-21)\n")
        rows = self.rows("upcoming", "5", "--json")
        self.assertIn({"date": "2026-11-20", "kind": "event", "path": "notes/mia.md", "line": 7,
                       "text": "- Football (at 2026-11-20 17:00-18:00)", "time": "17:00", "end": "18:00"}, rows)
        self.assertIn({"date": "2026-11-21", "kind": "birthday", "path": "notes/mia.md", "line": 2,
                       "text": "birthday: 2015-11-21", "time": None, "end": None}, rows)
        self.assertIn({"date": "2026-11-22", "kind": "event", "path": "notes/mia.md", "line": 8,
                       "text": "- Trip (at 2026-11-22 to 2026-11-23)", "time": None, "end": None}, rows)
        self.assertEqual(len([r for r in rows if r["kind"] == "event" and r["line"] == 8]), 2)
        plain = self.ok("upcoming", "5", now="20261119090000").splitlines()
        self.assertEqual(len(plain), len(rows))
        self.assertEqual(self.pkm("upcoming", "--json", "--ics", now="20261119090000").returncode, 2)

    def test_tags_cycle_and_vaults(self):
        self.write("notes/a.md", "---\ntags: [home, bills]\n---\n\n# A #home\n")
        self.assertEqual(self.rows("tags", "--json"), [{"tag": "home", "count": 2}, {"tag": "bills", "count": 1}])
        self.write(".pkm/config", "format=1\nclose=week\ncycle_sprint=2w from 2026-11-02\n")
        rows = self.rows("cycle", "--json")
        self.assertEqual(rows[0], {"name": "week", "first": "2026-11-16", "last": "2026-11-22", "close": True})
        self.assertEqual(rows[1], {"name": "sprint", "first": "2026-11-16", "last": "2026-11-29", "close": False})
        self.assertEqual(self.rows("cycle", "sprint", "--json"), rows[1:])
        self.write_user(f"vault_here={self.root}\nvault_gone={self.root}/nowhere\n")
        self.assertEqual(self.rows("vaults", "--json"), [{"name": "here", "path": str(self.root), "state": "ok"},
                                                         {"name": "gone", "path": f"{self.root}/nowhere", "state": "missing"}])


class Vaults(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        base = pathlib.Path(self._tmp.name)
        self.paths = {}
        for name in ("work", "family"):
            self.paths[name] = base / name
            shutil.copytree(REPO / "docs/examples" / name, self.paths[name], ignore=shutil.ignore_patterns("cache"))
        self.elsewhere = base / "elsewhere"
        self.elsewhere.mkdir()
        self.user(f"vault_work={self.paths['work']}\nvault_family={self.paths['family']}\nvaults=family,work\n")

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def user(self, text):
        folder = pathlib.Path(self._config.name) / "pkm"
        folder.mkdir(exist_ok=True)
        (folder / "config").write_text(text)

    def pkm(self, *args):
        env = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=self._config.name)
        return run_pkm(list(args), cwd=self.elsewhere, env=env)

    def one(self, name, *args):
        result = self.pkm("-V", name, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_each_vault_has_its_section_with_its_own_paths(self):
        for command in (["tasks"], ["upcoming", "30"], ["since", "2026-11-09"]):
            result = self.pkm("--vaults", "work,family", *command)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = "== vault work\n" + self.one("work", *command) + "== vault family\n" + self.one("family", *command)
            self.assertEqual(result.stdout, expected, command)
        self.assertNotIn(str(self.paths["work"]), self.pkm("--vaults", "work,family", "tasks").stdout)

    def test_with_no_names_it_takes_the_vaults_setting(self):
        out = self.pkm("--vaults", "tasks").stdout
        self.assertLess(out.index("== vault family\n"), out.index("== vault work\n"))

    def test_json_adds_the_vault(self):
        out = self.pkm("--vaults", "work,family", "tasks", "--json").stdout
        rows = [json.loads(line) for line in out.splitlines()]
        work = [json.loads(line) for line in self.one("work", "tasks", "--json").splitlines()]
        self.assertEqual([r for r in rows if r["vault"] == "work"], [{**r, "vault": "work"} for r in work])
        self.assertEqual({r["vault"] for r in rows}, {"work", "family"})
        rows = [json.loads(line) for line in self.pkm("--vaults", "upcoming", "30", "--json").stdout.splitlines()]
        self.assertTrue(all("date" in r and r["vault"] in ("work", "family") for r in rows))

    def test_a_vault_with_nothing_is_left_out_and_none_exits_1(self):
        result = self.pkm("--vaults", "work,family", "tasks", "--stale", "3000")
        self.assertEqual((result.returncode, result.stdout), (1, ""))

    def test_what_it_refuses(self):
        for args in (["--vaults", "work,nobody", "tasks"], ["--vaults", "work", "-V", "family", "tasks"],
                     ["-V", "family", "--vaults", "work", "tasks"], ["--vaults", "work", "find", "boiler"],
                     ["--vaults", "work", "upcoming", "--ics"], ["--vaults", "work,", "tasks"]):
            result = self.pkm(*args)
            self.assertEqual((result.returncode, result.stdout), (2, ""), args)
        self.user(f"vault_work={self.paths['work']}\n")
        self.assertEqual(self.pkm("--vaults", "tasks").returncode, 2)
        self.assertIn("vaults=", self.pkm("--vaults", "tasks").stderr)


if __name__ == "__main__":
    unittest.main()
