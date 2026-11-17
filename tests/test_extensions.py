"""Extensions: an unknown command runs pkm-<name> from PATH with its arguments and PKM_VAULT, built-in names always win,
names must match [a-z0-9][a-z0-9-]*, help --all lists the extensions found. Run: python3 -m unittest discover -s tests.
Names and data are made up.
"""

import os
import pathlib
import shutil
import tempfile

from helpers import REPO, VaultCase


class Extensions(VaultCase):
    def setUp(self):
        super().setUp()
        self.bindir = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.bindir, True)
        self.script("pkm-hello", '#!/bin/sh\necho "args:$*"\necho "vault:$PKM_VAULT"\nexit 3\n')

    def script(self, name, body):
        path = self.bindir / name
        path.write_text(body)
        path.chmod(0o755)

    def env(self):
        return {"PATH": f"{self.bindir}{os.pathsep}{os.environ['PATH']}"}

    def test_an_extension_runs_with_its_arguments_and_the_vault_and_its_exit_code(self):
        result = self.pkm("hello", "a", "b c", env=self.env())
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "args:a b c")
        self.assertEqual(os.path.realpath(lines[1].removeprefix("vault:")), os.path.realpath(self.root))

    def test_options_after_the_name_go_to_the_extension_unchanged(self):
        result = self.pkm("hello", "--nope", "--json", env=self.env())
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], "args:--nope --json")

    def test_a_built_in_name_is_never_overridden(self):
        self.script("pkm-version", "#!/bin/sh\necho fake\n")
        self.assertEqual(self.ok("version", env=self.env()).strip(), (REPO / "VERSION").read_text().strip())

    def test_an_unknown_name_without_an_extension_exits_2_with_the_usual_message(self):
        result = self.pkm("nope", env=self.env())
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown command: nope", result.stderr)

    def test_a_name_outside_the_pattern_is_not_run(self):
        self.script("pkm-Bad", "#!/bin/sh\necho ran\nexit 0\n")
        self.script("pkm-bad_x", "#!/bin/sh\necho ran\nexit 0\n")
        for name in ["Bad", "bad_x"]:
            with self.subTest(name=name):
                result = self.pkm(name, env=self.env())
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertNotIn("ran", result.stdout)

    def test_help_all_lists_the_extensions_found_in_the_extension_group(self):
        rows = [line.split("\t") for line in self.ok("help", "--all", env=self.env()).splitlines()]
        self.assertIn("hello", [row[0] for row in rows if row[1] == "Extension"])


if __name__ == "__main__":
    import unittest

    unittest.main()
