"""Tests for the settings: the one list, config and its sources, the user config, doctor's checks, and that
docs/settings.md repeats the list. Run: python3 -m unittest discover -s tests
"""

import pathlib
import re
import subprocess
import unittest

from helpers import BASH, REPO, VaultCase


def settings_from_code():
    """The rows of settings_list, as (key, scope, default, meaning)."""
    result = subprocess.run([BASH, "-c", '. "$1"; settings_list', "pkm-test", str(REPO / "lib/pkm/config.sh")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return [tuple(line.split("|", 3)) for line in result.stdout.strip().splitlines()]


def settings_from_docs():
    """The rows of the table in docs/settings.md, as (key, scope, default, meaning)."""
    rows = []
    for line in (REPO / "docs/settings.md").read_text().splitlines():
        match = re.match(r"^\| `([^`]+)` \| ([a-z]+) \| `?([^|`]*?)`? \| (.+?) \|$", line)
        if match:
            rows.append(match.groups())
    return rows


class SettingsList(VaultCase):
    def test_docs_settings_md_lists_the_same_settings_as_the_code(self):
        code = settings_from_code()
        self.assertTrue(code)
        docs = settings_from_docs()
        self.assertEqual(sorted(docs), sorted(code))

    def test_config_lists_every_setting_with_its_value_and_source(self):
        self.write(".pkm/config", "format=1\nshared=yes\nfolder_recipe=kitchen\n")
        out = self.ok("config")
        rows = {line.split("\t")[0]: line.split("\t")[1:] for line in out.strip().splitlines()}
        for key, scope, default, meaning in settings_from_code():
            if "<" not in key:
                self.assertIn(key, rows, key)
        self.assertEqual(rows["shared"], ["yes", "vault"])
        self.assertEqual(rows["folder_recipe"], ["kitchen", "vault"])
        self.assertEqual(rows["format"], ["1", "vault"])
        self.assertEqual(rows["writer"], ["", "default"])

    def test_config_with_a_key_prints_that_setting(self):
        self.write(".pkm/config", "close=week\n")
        self.assertEqual(self.ok("config", "close").strip(), "close\tweek\tvault")
        # The default is notes: new notes of every type go there unless folder_<type> names another folder.
        self.assertEqual(self.ok("config", "folder_recipe").strip(), "folder_recipe\tnotes\tdefault")

    def test_an_unknown_key_exits_2(self):
        result = self.pkm("config", "colour")
        self.assertEqual(result.returncode, 2)
        self.assertIn("colour", result.stderr)

    def test_a_user_only_key_comes_from_the_user_config(self):
        self.write_user("writer=sam\nvault_family=/tmp/family\n")
        self.assertEqual(self.ok("config", "writer").strip(), "writer\tsam\tuser")
        self.assertIn("vault_family\t/tmp/family\tuser", self.ok("config"))

    def test_doctor_reports_unknown_and_malformed_lines_with_their_place(self):
        self.write(".pkm/config", "format=1\ncolour=blue\nthis is not a setting\nwriter=sam\n")
        result = self.pkm("doctor")
        self.assertEqual(result.returncode, 1)
        self.assertIn(".pkm/config:2: unknown setting: colour", result.stdout)
        self.assertIn(".pkm/config:3: not a key=value line", result.stdout)
        self.assertIn(".pkm/config:4: writer belongs in the user config", result.stdout)

    def test_doctor_reports_a_wrong_value(self):
        self.write(".pkm/config", "format=2\nshared=maybe\n")
        result = self.pkm("doctor")
        self.assertEqual(result.returncode, 1)
        self.assertIn(".pkm/config:1: format is 1, got: 2", result.stdout)
        self.assertIn(".pkm/config:2: shared is yes or no", result.stdout)

    def test_doctor_checks_the_user_config_too(self):
        self.write_user("vault_family=/tmp/family\nmystery=1\nfolder_x=kitchen\n")
        result = self.pkm("doctor")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"{self.user_config}:2: unknown setting: mystery", result.stdout)
        self.assertIn(f"{self.user_config}:3: folder_x belongs in the vault's .pkm/config", result.stdout)

    def test_doctor_is_clean_with_good_settings(self):
        self.write(".pkm/config", "format=1\nshared=no\n")
        result = self.pkm("doctor")
        self.assertNotIn("problem", result.stdout)


if __name__ == "__main__":
    unittest.main()
