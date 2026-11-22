"""pkm example: copies an example vault that ships with pkm into a new folder; and the now setting, which fixes a vault's
clock so an example shows its own day. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import REPO, pkm_env, run_pkm


def env(config, **extra):
    environment = pkm_env(XDG_CONFIG_HOME=config, **extra)
    environment.pop("PKM_NOW", None)
    environment.update(extra)
    return environment


class Example(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def pkm(self, *args, cwd=None, **extra):
        return run_pkm(list(args), cwd=cwd or self.root, env=env(self._config.name, **extra))

    def test_it_copies_the_work_vault_into_a_new_folder_and_says_what_to_try(self):
        result = self.pkm("example")
        self.assertEqual(result.returncode, 0, result.stderr)
        vault = self.root / "pkm-example-work"
        self.assertTrue((vault / ".pkm/config").is_file())
        self.assertTrue((vault / "notes/apollo.md").is_file())
        self.assertFalse((vault / ".pkm/cache").exists())
        self.assertEqual(result.stdout.splitlines()[0], "pkm-example-work")
        self.assertIn("pkm tasks", result.stdout)
        self.assertIn("pkm example family", result.stdout)

    def test_a_name_and_a_folder(self):
        result = self.pkm("example", "family", "home/sandbox")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "home/sandbox/.pkm/config").is_file())
        self.assertIn("shared=yes", (self.root / "home/sandbox/.pkm/config").read_text())
        self.assertIn("writer=<name>", result.stdout)
        self.assertNotIn("  pkm day ", result.stdout)

    def test_the_copy_is_the_shipped_vault_file_for_file(self):
        self.pkm("example", "work", "copy")
        source = REPO / "docs/examples/work"
        shipped = sorted(p.relative_to(source).as_posix() for p in source.rglob("*")
                         if p.is_file() and "/.pkm/cache" not in p.as_posix() and not p.name == "state")
        copied = sorted(p.relative_to(self.root / "copy").as_posix() for p in (self.root / "copy").rglob("*")
                        if p.is_file())
        self.assertEqual(copied, shipped)

    def test_it_never_writes_into_something_that_exists(self):
        (self.root / "taken").mkdir()
        (self.root / "taken/mine.md").write_text("mine\n")
        result = self.pkm("example", "work", "taken")
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(sorted(os.listdir(self.root / "taken")), ["mine.md"])

    def test_an_unknown_example_is_a_usage_error(self):
        result = self.pkm("example", "zoo")
        self.assertEqual(result.returncode, 2)
        self.assertIn("work", result.stderr)
        self.assertIn("family", result.stderr)
        self.assertFalse(list(self.root.iterdir()))

    def test_the_example_opens_on_its_own_day(self):
        self.pkm("example", "work", "w")
        result = self.pkm("day", cwd=self.root / "w")
        self.assertEqual(result.stdout.strip(), "daybook/2026/11/2026-11-16.md", result.stderr)
        close = self.pkm("close", cwd=self.root / "w")
        self.assertEqual(close.returncode, 0, close.stderr)
        self.assertIn("2026-11-09", close.stdout.splitlines()[0])

    def test_an_installed_pkm_finds_the_examples_in_share(self):
        if not shutil.which("make"):
            self.skipTest("make is not installed")
        prefix = self.root / "prefix"
        subprocess.run(["make", "-C", str(REPO), "install", f"PREFIX={prefix}"], check=True, capture_output=True)
        version = (REPO / "VERSION").read_text().strip()
        self.assertTrue((prefix / f"lib/pkm-{version}/share/pkm/examples/work/.pkm/config").is_file())
        self.assertFalse((prefix / f"lib/pkm-{version}/share/pkm/examples/work/.pkm/cache").exists())
        result = subprocess.run([str(prefix / "bin/pkm"), "example", "family", "fam"], cwd=self.root,
                                capture_output=True, text=True, env=env(self._config.name))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "fam/.pkm/config").is_file())


class Now(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        (self.root / ".pkm").mkdir()

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def pkm(self, *args, **extra):
        return run_pkm(list(args), cwd=self.root, env=env(self._config.name, **extra), vault=self.root)

    def test_the_setting_fixes_the_clock(self):
        (self.root / ".pkm/config").write_text("format=1\nnow=2026-11-16 08:30\n")
        self.assertEqual(self.pkm("day").stdout.strip(), "daybook/2026/11/2026-11-16.md")
        self.pkm("add", "Started the example")
        self.assertIn("- 08:30 Started the example", (self.root / "daybook/2026/11/2026-11-16.md").read_text())

    def test_pkm_now_wins_over_the_setting(self):
        (self.root / ".pkm/config").write_text("now=2026-11-16 08:30\n")
        result = self.pkm("day", PKM_NOW="20261201090000")
        self.assertEqual(result.stdout.strip(), "daybook/2026/12/2026-12-01.md", result.stderr)

    def test_a_wrong_value_is_a_usage_error_and_a_doctor_problem(self):
        (self.root / ".pkm/config").write_text("now=16.11.2026\n")
        result = self.pkm("day")
        self.assertEqual(result.returncode, 2)
        self.assertIn("YYYY-MM-DD HH:MM", result.stderr)
        doctor = self.pkm("doctor")
        self.assertIn("now", doctor.stdout)
        self.assertEqual(doctor.returncode, 1)

    def test_doctor_says_the_clock_is_fixed(self):
        (self.root / ".pkm/config").write_text("format=1\nnow=2026-11-16 08:30\n")
        doctor = self.pkm("doctor")
        self.assertIn("now=2026-11-16 08:30", doctor.stdout)

    def test_the_setting_belongs_in_the_vault(self):
        folder = pathlib.Path(self._config.name, "pkm")
        folder.mkdir()
        (folder / "config").write_text("now=2026-11-16 08:30\n")
        self.assertIn("belongs in the vault", self.pkm("doctor").stdout)
        self.assertNotIn("2026-11-16", self.pkm("day").stdout)


if __name__ == "__main__":
    unittest.main()
