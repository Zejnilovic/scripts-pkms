"""pkm help <command> and pkm <command> --help: one command's usage and options, from the usage text at the top of
bin/pkm, outside a vault too. Run: python3 -m unittest discover -s tests
"""

import tempfile
import unittest

from helpers import pkm_env, run_pkm


def pkm(*args):
    with tempfile.TemporaryDirectory() as elsewhere, tempfile.TemporaryDirectory() as config:
        return run_pkm(list(args), cwd=elsewhere, env=pkm_env(XDG_CONFIG_HOME=config))


def builtins():
    rows = [line.split("\t") for line in pkm("help", "--all").stdout.splitlines()]
    return [row[0] for row in rows if row[1] != "Extension"]


class HelpForOneCommand(unittest.TestCase):
    def test_it_gives_the_summary_the_usage_and_nothing_of_other_commands(self):
        result = pkm("help", "post")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "pkm post (Notes): copies lines of a page into a note's section, with the page as "
                                   "their source")
        self.assertIn("  post <path:line[-line]> <note>[#Section]", lines)
        self.assertIn("copies those lines into the section", result.stdout)
        self.assertNotIn("strike <path:line>", result.stdout)
        self.assertNotIn("Usage:", result.stdout)

    def test_a_name_is_matched_whole(self):
        out = pkm("help", "vault").stdout
        self.assertIn("  vault ", out)
        self.assertNotIn("vaults [--json]", out)

    def test_every_entry_of_the_command_is_given(self):
        out = pkm("help", "recall").stdout
        self.assertIn("  recall [note]", out)
        self.assertIn("  recall add <note> <question>", out)
        out = pkm("help", "templates").stdout
        self.assertIn("  templates eject <type> [--user]", out)

    def test_it_lists_the_options(self):
        self.assertIn("\nOptions: --lines --plain\n", pkm("help", "get").stdout)
        self.assertNotIn("Options:", pkm("help", "init").stdout)

    def test_every_command_has_a_usage_entry(self):
        names = builtins()
        self.assertGreater(len(names), 30)
        for name in names:
            result = pkm("help", name)
            self.assertEqual(result.returncode, 0, name + result.stderr)
            self.assertIn(f"\n  {name}", result.stdout, f"the usage text at the top of bin/pkm has no entry for {name}")

    def test_an_unknown_command_is_a_usage_error(self):
        result = pkm("help", "nosuch")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("pkm help --all", result.stderr)

    def test_the_help_option_after_a_command_gives_the_same(self):
        expected = pkm("help", "post").stdout
        for args in (["post", "--help"], ["post", "daybook/x.md:3", "--help"]):
            result = pkm(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)

    def test_help_all_keeps_a_bar_in_the_summary(self):
        recall = [line for line in pkm("help", "--all").stdout.splitlines() if line.startswith("recall\t")]
        self.assertEqual(len(recall[0].split("\t")), 3)
        self.assertIn("yes|no moves a question on the ladder", recall[0])

    def test_help_and_help_all_are_unchanged(self):
        self.assertTrue(pkm("help").stdout.startswith("Usage: pkm "))
        self.assertTrue(pkm("help", "--all").stdout.startswith("day\tCapture\t"))

    def test_an_unknown_option_points_to_the_commands_help(self):
        result = pkm("get", "x", "--nosuch")
        self.assertEqual(result.returncode, 2)
        self.assertIn("pkm help get", result.stderr)


class Completion(unittest.TestCase):
    def test_help_completes_the_command_names(self):
        result = pkm("__complete", "help", "")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = [line.split("\t")[0] for line in pkm("help", "--all").stdout.splitlines()]
        self.assertEqual(sorted(result.stdout.split()), sorted(listed))


if __name__ == "__main__":
    unittest.main()
