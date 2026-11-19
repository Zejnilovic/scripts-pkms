"""Tab completion: pkm completion bash|zsh prints the script, and pkm __complete <words> <word at the cursor> prints
the candidates the script offers, one a line, or :dirs or :files for the shell to complete paths itself. Run:
python3 -m unittest discover -s tests. Names and data are made up.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import BASH, PKM, REPO, VaultCase, pkm_env, run_pkm


def commands():
    out = subprocess.run([BASH, str(PKM), "help", "--all"], capture_output=True, text=True, env=pkm_env()).stdout
    return [line.split("\t")[0] for line in out.splitlines()]


class Script(unittest.TestCase):
    def run_pkm(self, *args):
        with tempfile.TemporaryDirectory() as elsewhere:
            return run_pkm(list(args), cwd=elsewhere, env=pkm_env())

    def test_bash_prints_a_script_that_bash_reads(self):
        result = self.run_pkm("completion", "bash")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("complete -F _pkm pkm", result.stdout)
        check = subprocess.run([BASH, "-n"], input=result.stdout, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_zsh_prints_a_compdef_script(self):
        result = self.run_pkm("completion", "zsh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("#compdef pkm\n"), result.stdout[:40])
        if shutil.which("zsh"):
            check = subprocess.run(["zsh", "-n"], input=result.stdout, capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_another_shell_is_a_usage_error(self):
        result = self.run_pkm("completion", "fish")
        self.assertEqual(result.returncode, 2)
        self.assertIn("bash", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_completion_is_a_listed_command_and_complete_is_not(self):
        listed = commands()
        self.assertIn("completion", listed)
        self.assertNotIn("__complete", listed)


class OutsideAVault(unittest.TestCase):
    def complete(self, *words):
        with tempfile.TemporaryDirectory() as elsewhere, tempfile.TemporaryDirectory() as config:
            return run_pkm(["__complete", *words], cwd=elsewhere, env=pkm_env(XDG_CONFIG_HOME=config))

    def test_the_first_word_is_every_command(self):
        result = self.complete("")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(result.stdout.split()), sorted(commands()))

    def test_a_dash_first_offers_the_global_options(self):
        self.assertEqual(self.complete("-").stdout.split(), ["--vault", "-V", "--vaults", "--help", "--version"])

    def test_a_dash_after_a_command_offers_its_options(self):
        self.assertEqual(self.complete("find", "--").stdout.split(), ["--live", "--json", "--abs", "--limit"])

    def test_the_vault_option_completes_folders(self):
        self.assertEqual(self.complete("--vault", "").stdout.strip(), ":dirs")

    def test_fixed_words(self):
        self.assertEqual(self.complete("completion", "").stdout.split(), ["bash", "zsh"])
        self.assertEqual(self.complete("tasks", "").stdout.split(), ["open", "waiting", "someday", "done"])
        self.assertEqual(self.complete("todo", "Call", "--due", "").stdout.split()[:2], ["today", "tomorrow"])

    def test_note_names_need_a_vault_and_fail_silently_without_one(self):
        result = self.complete("backlinks", "")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))


class InAVault(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", "---\ntype: project\naliases: [Apollo]\n---\n# Apollo\n")
        self.write("notes/jane-doe.md", "---\ntype: person\n---\n# Jane Doe\n")
        self.write(".pkm/config", "cycle_sprint=2w from 2026-11-02\n")

    def complete(self, *words):
        return self.pkm("__complete", *words).stdout.split()

    def test_note_names_for_commands_that_take_a_note(self):
        for words in (["backlinks", ""], ["path", ""], ["get", ""], ["rename", ""], ["mv", ""],
                      ["post", "daybook/2026/10/2026-10-25.md:3", ""], ["recall", "add", ""],
                      ["tasks", "--link", ""], ["since", "--about", ""]):
            self.assertIn("apollo", self.complete(*words), words)
            self.assertIn("jane-doe", self.complete(*words), words)

    def test_template_types_for_new_and_the_type_option(self):
        self.assertIn("person", self.complete("new", ""))
        self.assertIn("close", self.complete("new", ""))
        self.assertIn("project", self.complete("names", "--type", ""))

    def test_cycles_for_close_cycle_since_and_every(self):
        self.assertIn("sprint", self.complete("close", "--cycle", ""))
        self.assertIn("sprint", self.complete("cycle", ""))
        self.assertIn("sprint", self.complete("since", ""))
        self.assertIn("last", self.complete("since", ""))
        self.assertIn("sprint", self.complete("todo", "Pay", "--every", ""))
        self.assertIn("1m", self.complete("todo", "Pay", "--every", ""))

    def test_paths_and_folders_are_left_to_the_shell(self):
        self.assertEqual(self.complete("post", ""), [":files"])
        self.assertEqual(self.complete("strike", ""), [":files"])
        self.assertEqual(self.complete("mv", "apollo", ""), [":dirs"])

    def test_an_option_value_is_not_counted_as_an_argument(self):
        self.assertEqual(self.complete("backlinks", "--since", "2026-10-01", ""), self.complete("backlinks", ""))

    def test_named_vaults_for_dash_v_and_their_notes(self):
        self.write_user(f"vault_work={self.root}\n")
        environment = pkm_env(XDG_CONFIG_HOME=self.config_home)
        with tempfile.TemporaryDirectory() as elsewhere:
            names = run_pkm(["__complete", "-V", ""], cwd=elsewhere, env=environment).stdout.split()
            notes = run_pkm(["__complete", "-V", "work", "backlinks", ""], cwd=elsewhere, env=environment).stdout.split()
        self.assertEqual(names, ["work"])
        self.assertIn("apollo", notes)

    def test_vaults_offers_the_named_vaults_and_its_commands(self):
        self.write_user(f"vault_work={self.root}\n")
        environment = pkm_env(XDG_CONFIG_HOME=self.config_home)
        with tempfile.TemporaryDirectory() as elsewhere:
            first = run_pkm(["__complete", "--vaults", ""], cwd=elsewhere, env=environment).stdout.split()
            after = run_pkm(["__complete", "--vaults", "work", ""], cwd=elsewhere, env=environment).stdout.split()
            opts = run_pkm(["__complete", "--vaults", "tasks", "--"], cwd=elsewhere, env=environment).stdout.split()
        self.assertEqual(first, ["work", "tasks", "upcoming", "since"])
        self.assertEqual(after, ["tasks", "upcoming", "since"])
        self.assertIn("--under", opts)


class BashTabPress(VaultCase):
    """Runs the printed script in bash, the way a Tab press does, and reads COMPREPLY."""

    def press(self, line):
        script = subprocess.run([BASH, str(PKM), "completion", "bash"], capture_output=True, text=True).stdout
        folder = pathlib.Path(self._tmp.name) / "bin"
        folder.mkdir(exist_ok=True)
        link = folder / "pkm"
        if not link.exists():
            link.symlink_to(PKM)
        program = script + f'\nCOMP_LINE={line!r}; COMP_POINT=${{#COMP_LINE}}; _pkm; printf "%s\\n" "${{COMPREPLY[@]}}"\n'
        environment = pkm_env(PATH=f"{folder}{os.pathsep}{os.environ['PATH']}", XDG_CONFIG_HOME=self.config_home)
        result = subprocess.run([BASH, "-c", program], cwd=self.root, capture_output=True, text=True, env=environment)
        self.assertEqual(result.stderr, "")
        return result.stdout.split()

    def test_a_command_prefix(self):
        self.assertEqual(self.press("pkm ba"), ["backlinks"])

    def test_a_note_name_in_the_vault(self):
        self.write("notes/apollo.md", "---\ntype: project\n---\n# Apollo\n")
        self.assertEqual(self.press("pkm backlinks ap"), ["apollo"])

    def test_a_word_with_a_colon_is_kept_whole(self):
        self.write("notes/apollo.md", "---\ntype: project\n---\n# Apollo\n")
        self.assertEqual(self.press("pkm post daybook/2026/10/2026-10-25.md:3 ap"), ["apollo"])


class Packaging(unittest.TestCase):
    def test_the_formula_follows_brew_audit_style(self):
        # brew audit --strict, which the release runs: "Command-line" in the description, and dependencies sorted.
        text = (REPO / "packaging/pkm.rb").read_text()
        desc = text.split('desc "')[1].split('"')[0]
        self.assertNotRegex(desc, r"(?i)command line")
        self.assertLessEqual(len(desc), 80)
        self.assertFalse(desc.startswith(("A ", "An ", "The ")), desc)
        deps = [line.split('"')[1] for line in text.splitlines() if line.strip().startswith("depends_on")]
        self.assertEqual(deps, sorted(deps))

    def test_the_formula_installs_the_completions_and_tests_them(self):
        text = (REPO / "packaging/pkm.rb").read_text()
        self.assertIn('generate_completions_from_executable(bin/"pkm", "completion", shells: [:bash, :zsh])', text)
        self.assertIn("pkm completion bash", text)

    def test_install_sh_says_how_to_turn_completion_on(self):
        self.assertIn("pkm completion", (REPO / "install.sh").read_text())


if __name__ == "__main__":
    unittest.main()
