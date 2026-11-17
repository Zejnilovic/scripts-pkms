"""Tests for finding the vault and running pkm from anywhere: the order of --vault, -V, PKM_VAULT, the folder
above, and vault= in the user config; the exit 2 message; named vaults; writer=; a symlink on PATH; and the
templates pkm ships. Run: python3 -m unittest discover -s tests

Names and folders are made up. Each test uses its own temporary folders and its own user config.
"""

import os
import pathlib
import subprocess
import tempfile
import unittest

from helpers import BASH, REPO, PKM, pkm_env, run_pkm

NOW = "20261025143012"
TODAY_NOTE = "daybook/2026/10/2026-10-25.md"


class DiscoveryCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # Resolved, so relative links are computed from the real folder (macOS keeps temp folders under a link).
        self.tmp = pathlib.Path(os.path.realpath(self._tmp.name))
        self.config_home = self.tmp / "config"
        self.config_home.mkdir()
        self.outside = self.tmp / "outside"
        self.outside.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def make_vault(self, name):
        folder = self.tmp / name
        (folder / ".pkm").mkdir(parents=True)
        return folder

    def write_config(self, text):
        (self.config_home / "pkm").mkdir(exist_ok=True)
        (self.config_home / "pkm/config").write_text(text)

    def run_from(self, cwd, *args, vault=None, **extra):
        environment = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=str(self.config_home), **extra)
        return run_pkm(list(args), cwd=cwd, env=environment, vault=vault)


class FindingTheVault(DiscoveryCase):
    def test_the_vault_option_comes_first(self):
        chosen = self.make_vault("chosen")
        from_env = self.make_vault("from-env")
        above = self.make_vault("above")
        here = above / "here"
        here.mkdir()
        self.write_config(f"vault={self.make_vault('config')}\n")
        result = self.run_from(here, "day", vault=chosen, PKM_VAULT=str(from_env))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), TODAY_NOTE)
        self.assertTrue((chosen / TODAY_NOTE).exists())
        self.assertFalse((from_env / TODAY_NOTE).exists())
        self.assertFalse((above / TODAY_NOTE).exists())

    def test_PKM_VAULT_comes_before_the_folder_above_and_the_config(self):
        from_env = self.make_vault("from-env")
        above = self.make_vault("above")
        here = above / "here"
        here.mkdir()
        self.write_config(f"vault={self.make_vault('config')}\n")
        result = self.run_from(here, "day", PKM_VAULT=str(from_env))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((from_env / TODAY_NOTE).exists())
        self.assertFalse((above / TODAY_NOTE).exists())

    def test_the_nearest_folder_holding_pkm_wins(self):
        outer = self.make_vault("outer")
        inner = outer / "inner"
        (inner / ".pkm").mkdir(parents=True)
        deep = inner / "a" / "b"
        deep.mkdir(parents=True)
        result = self.run_from(deep, "day")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((inner / TODAY_NOTE).exists())
        self.assertFalse((outer / TODAY_NOTE).exists())

    def test_the_config_vault_line_is_used_last(self):
        vault = self.make_vault("home")
        self.write_config(f"# my vault\nvault={vault}\n")
        result = self.run_from(self.outside, "day")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((vault / TODAY_NOTE).exists())

    def test_no_vault_exits_2_with_one_line_on_stderr(self):
        result = self.run_from(self.outside, "day")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("No vault found", result.stderr)
        self.assertFalse((self.outside / "day").exists())

    def test_a_vault_option_without_a_pkm_folder_exits_2(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        result = self.run_from(self.outside, "day", vault=plain)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertFalse((plain / "day").exists())

    def test_help_and_version_need_no_vault(self):
        self.assertEqual(self.run_from(self.outside, "version").returncode, 0)
        self.assertIn("Usage:", self.run_from(self.outside, "help").stdout)


class NamedVaults(DiscoveryCase):
    def setUp(self):
        super().setUp()
        self.family = self.make_vault("family")
        self.work = self.make_vault("work")
        self.write_config(f"vault_family={self.family}\nvault_work={self.work}\n")

    def test_dash_V_chooses_the_named_vault_from_anywhere(self):
        result = self.run_from(self.outside, "-V", "family", "day")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.family / TODAY_NOTE).exists())
        self.assertFalse((self.work / TODAY_NOTE).exists())

    def test_dash_V_beats_the_vault_the_folder_is_in(self):
        here = self.work / "notes"
        here.mkdir()
        result = self.run_from(here, "-V", "family", "day")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.family / TODAY_NOTE).exists())
        self.assertFalse((self.work / TODAY_NOTE).exists())

    def test_an_unknown_name_exits_2_with_one_line_on_stderr(self):
        result = self.run_from(self.outside, "-V", "school", "day")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("school", result.stderr)

    def test_a_name_with_odd_characters_exits_2(self):
        result = self.run_from(self.outside, "-V", "../family", "day")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)

    def test_vault_and_dash_V_together_exit_2(self):
        result = self.run_from(self.outside, "-V", "family", "day", vault=self.work)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.family / TODAY_NOTE).exists())


class WriterSetting(DiscoveryCase):
    def read_writer(self):
        environment = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "XDG_CONFIG_HOME": str(self.config_home)}
        # As bin/pkm does: pkm_home is set before a module is sourced, since modules source lib/pkm/globals.sh.
        script = 'set -u; pkm_home=$2; . "$1"; user_config_value writer'
        result = subprocess.run([BASH, "-c", script, "pkm-test", str(REPO / "lib/pkm/config.sh"), str(REPO)],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_writer_is_read_from_the_user_config(self):
        self.write_config("vault_family=/tmp/family\nwriter=sam\n")
        self.assertEqual(self.read_writer(), "sam")

    def test_writer_is_empty_when_unset(self):
        self.write_config("vault_family=/tmp/family\n")
        self.assertEqual(self.read_writer(), "")


class SymlinkOnPath(DiscoveryCase):
    def test_a_symlink_to_bin_pkm_on_PATH_runs_from_a_subfolder_of_a_vault(self):
        vault = self.make_vault("vault")
        deep = vault / "notes" / "deep"
        deep.mkdir(parents=True)
        bin_folder = self.tmp / "bin"
        bin_folder.mkdir()
        # A relative link, as a package manager or a person makes one.
        os.symlink(os.path.relpath(PKM, bin_folder), bin_folder / "pkm")
        environment = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=str(self.config_home),
                              PATH=f"{bin_folder}{os.pathsep}{os.environ['PATH']}")
        result = subprocess.run(["pkm", "day"], cwd=deep, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), TODAY_NOTE)
        self.assertTrue((vault / TODAY_NOTE).exists())
        result = subprocess.run(["pkm", "help"], cwd=deep, env=environment, capture_output=True, text=True)
        self.assertIn("Usage:", result.stdout, result.stderr)


class PackagedTemplates(DiscoveryCase):
    def test_a_vault_without_templates_uses_the_ones_pkm_ships(self):
        vault = self.make_vault("bare")
        result = self.run_from(vault, "day")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((vault / TODAY_NOTE).read_text().startswith("# 2026-10-25\n"))


if __name__ == "__main__":
    unittest.main()
