"""Tests for templates at three levels (vault, user, pkm's own), templates eject, version --require, vault and
vaults. Run: python3 -m unittest discover -s tests
"""

import pathlib
import unittest

from helpers import PKM, REPO, VaultCase, pkm_env, run_pkm


class TemplatesTest(VaultCase):
    def last_note(self, folder):
        """The name of the newest note in a folder: new names notes after the clock, so the last one is the new one."""
        return sorted(path.name for path in (self.root / folder).glob("*.md"))[-1]

    def test_the_vault_templates_folder_beats_the_user_and_the_default(self):
        self.write("templates/note.md", "---\ntype: note\n---\n\n# {{title}} from the vault\n")
        self.write_user("")
        (pathlib.Path(self.config_home) / "pkm/templates").mkdir(parents=True, exist_ok=True)
        (pathlib.Path(self.config_home) / "pkm/templates/note.md").write_text("# {{title}} from the user\n")
        self.ok("new", "note", "Ideas")
        self.assertIn("from the vault", self.read("notes/" + self.last_note("notes")))

    def test_the_user_templates_beat_the_default_when_the_vault_has_none(self):
        (self.root / "templates/day.md").unlink()
        (pathlib.Path(self.config_home) / "pkm/templates").mkdir(parents=True, exist_ok=True)
        (pathlib.Path(self.config_home) / "pkm/templates/day.md").write_text("# {{title}} from the user\n")
        self.ok("day")
        self.assertEqual(self.read("daybook/2026/10/2026-10-25.md"), "# 2026-10-25 from the user\n")

    def test_a_templates_setting_names_the_vault_folder(self):
        self.write(".pkm/config", "templates=tpl\n")
        self.write("tpl/note.md", "---\ntype: note\n---\n\n# {{title}} from tpl\n")
        self.ok("new", "note", "Ideas")
        self.assertIn("from tpl", self.read("notes/" + self.last_note("notes")))

    def test_templates_lists_each_type_with_where_it_comes_from(self):
        self.write("templates/recipe.md", "---\ntype: recipe\n---\n")
        (self.root / "templates/topic.md").unlink()
        rows = dict(line.split("\t") for line in self.ok("templates").strip().splitlines())
        self.assertEqual(rows["recipe"], "vault")
        self.assertEqual(rows["day"], "vault")
        self.assertEqual(rows["topic"], "default")

    def test_templates_eject_copies_the_default_and_never_overwrites(self):
        (self.root / "templates/topic.md").unlink()
        self.assertEqual(self.ok("templates", "eject", "topic").strip(), "templates/topic.md")
        self.assertIn("type: topic", self.read("templates/topic.md"))
        result = self.pkm("templates", "eject", "topic")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not overwritten", result.stderr)

    def test_templates_eject_user_writes_to_the_user_folder(self):
        result = self.pkm("templates", "eject", "source", "--user")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((pathlib.Path(self.config_home) / "pkm/templates/source.md").exists())

    def test_templates_eject_refuses_a_type_pkm_ships_no_template_for(self):
        self.assertEqual(self.pkm("templates", "eject", "spaceship").returncode, 2)


class VersionTest(VaultCase):
    def test_require_exits_0_when_the_release_is_new_enough(self):
        self.assertEqual(self.pkm("version", "--require", "0.1").returncode, 0)
        self.assertEqual(self.pkm("version", "--require", "0.1.0").returncode, 0)

    def test_require_exits_1_with_no_output_when_too_old(self):
        result = self.pkm("version", "--require", "0.3")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (1, "", ""))

    def test_require_exits_2_on_a_bad_argument(self):
        self.assertEqual(self.pkm("version", "--require", "soon").returncode, 2)

    def test_version_prints_bare_semver(self):
        self.assertRegex(self.ok("version").strip(), r"^\d+\.\d+\.\d+$")


class VaultsTest(VaultCase):
    def test_vault_prints_the_root(self):
        self.assertEqual(self.ok("vault").strip(), str(self.root))

    def test_vaults_lists_named_vaults_with_ok_or_missing(self):
        family = self.root / "family"
        (family / ".pkm").mkdir(parents=True)
        self.write_user(f"vault_family={family}\nvault_work=/no/such/vault\n")
        out = self.ok("vaults")
        self.assertIn(f"family\t{family}\tok", out)
        self.assertIn("work\t/no/such/vault\tmissing", out)

    def test_init_works_outside_a_vault(self):
        plain = self.root / "plain"
        plain.mkdir()
        environment = pkm_env(XDG_CONFIG_HOME=self.config_home)
        result = run_pkm(["init"], cwd=plain, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((plain / ".pkm/config").exists())
        self.assertTrue((plain / ".pkmignore").exists())


if __name__ == "__main__":
    unittest.main()
