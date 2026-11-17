"""The output contract (docs/contract.md): the commands in help --all are described there, the listing commands give the
same records in plain, --abs, --json and --limit forms, exit codes follow the contract, and the JSON is valid in jq and
in Python. Also the shellcheck lint, which must catch a misspelled global. Run: python3 -m unittest discover -s tests
Names and data are made up.
"""

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

from helpers import BASH, REPO, PKM, VaultCase, pkm_env, run_pkm

CONTRACT = (REPO / "docs/contract.md").read_text()
# names: not yet implemented (step 8 adds it with the cache); the table test skips it until then.
NOT_YET = {"names"}
LISTING_COMMANDS = ["find", "backlinks", "path", "list", "tasks", "check"]


def help_all_names():
    result = subprocess.run([BASH, str(PKM), "help", "--all"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return [line.split("\t") for line in result.stdout.strip().splitlines()]


class ContractDocument(unittest.TestCase):
    def test_every_command_in_help_all_is_in_the_contract(self):
        names = [row[0] for row in help_all_names()]
        self.assertTrue(names)
        for name in names:
            self.assertIn(f"| `{name}` |", CONTRACT, f"{name} is missing from docs/contract.md")

    def test_help_all_lines_are_name_group_summary(self):
        for row in help_all_names():
            self.assertEqual(len(row), 3, row)
            self.assertTrue(all(row), row)

    def test_every_dispatched_command_is_in_help_all(self):
        dispatch = re.search(r"^case \$command in\n(.*?)^esac", (REPO / "bin/pkm").read_text(), re.M | re.S)
        commands = {name for line in re.findall(r"^  '?([a-z|-]+)'?\) ", dispatch.group(1), re.M)
                    for name in line.split("|")}
        listed = {row[0] for row in help_all_names()}
        self.assertFalse(commands - listed - {"help", "-h", "--help", "--version", "*"}, commands - listed)

    def test_the_output_fields_and_options_are_described(self):
        for term in ["`path`", "`line`", "`text`", "`kind`", "`fields`", "--json", "--abs", "--limit", "... N more",
                     "`0`", "`1`", "`2`"]:
            self.assertIn(term, CONTRACT, term)


class Listings(VaultCase):
    """One fixture for the listing commands: records of each shape, with quotes, a backslash, a tab and a non-ASCII name."""

    def setUp(self):
        super().setUp()
        self.write("people/marta-kovac.md", '---\ntype: person\naliases: [Marta Kovač]\n---\n\n# Marta Kovač\n')
        self.write("notes/apollo.md", '---\ntype: project\nstatus: active\n---\n\n# Apollo\n\n'
                                      'He said "launch" and c:\\temp\tdone for Kovač [[marta-kovac]]\n'
                                      '- [ ] Ship the Apollo demo (due 2026-10-30)\n')
        self.write("notes/zeus.md", "---\ntype: project\nstatus: done\n---\n\n# Zeus\n")
        self.write("notes/broken.md", "Lost link [[nobody-here]]\n")

    CASES = {
        "find": (["apollo"], 0),
        "backlinks": (["marta-kovac"], 0),
        "path": (["apollo"], 0),
        "list": (["type=project"], 0),
        "tasks": ([], 0),
        "check": ([], 1),
    }

    def run_listing(self, command, args, *extra):
        return self.pkm(command, *args, *extra)

    def test_plain_output_is_relative_to_the_vault(self):
        for command, (args, _) in self.CASES.items():
            out = self.ok(command, *args) if command != "check" else self.pkm(command).stdout
            for line in out.strip().splitlines():
                self.assertFalse(line.startswith("/"), (command, line))
                self.assertNotIn(str(self.root), line, command)

    def test_abs_gives_absolute_paths(self):
        out = self.pkm("path", "apollo", "--abs").stdout.strip()
        self.assertEqual(out, str(self.root / "notes/apollo.md"))
        self.assertTrue(self.pkm("find", "apollo", "--abs").stdout.startswith(str(self.root)))

    def test_json_lines_parse_in_python_with_the_keys_of_the_contract(self):
        for command, (args, _) in self.CASES.items():
            result = self.pkm(command, *args, "--json")
            self.assertIn(result.returncode, (0, 1), (command, result.stderr))
            for line in result.stdout.strip().splitlines():
                record = json.loads(line)
                for key in ["path", "line", "text"]:
                    self.assertIn(key, record, (command, line))
                self.assertTrue(record["path"] is None or not record["path"].startswith("/"), command)

    def test_json_is_valid_for_jq_and_keeps_quotes_backslashes_tabs_and_non_ascii(self):
        if shutil.which("jq") is None:
            self.skipTest("jq is not installed")
        result = self.pkm("find", "Kovač", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = next(r for r in (json.loads(line) for line in result.stdout.strip().splitlines())
                      if r["path"] == "notes/apollo.md")
        self.assertEqual(record["path"], "notes/apollo.md")
        self.assertEqual(record["line"], 8)
        self.assertEqual(record["text"], 'He said "launch" and c:\\temp\tdone for Kovač [[marta-kovac]]')
        jq = subprocess.run(["jq", "-e", "."], input=result.stdout, capture_output=True, text=True)
        self.assertEqual(jq.returncode, 0, jq.stderr)

    def test_list_json_has_the_fields_after_the_path(self):
        record = json.loads(self.pkm("list", "type=project", "--json", "--show", "status").stdout.splitlines()[0])
        self.assertIsNone(record["line"])
        self.assertEqual(record["fields"][0], "project")

    def test_check_json_has_a_kind_and_keeps_problems_with_no_place(self):
        self.write("notes/alias-a.md", "---\naliases: [Shared]\n---\n# A\n")
        self.write("notes/alias-b.md", "---\naliases: [Shared]\n---\n# B\n")
        records = [json.loads(line) for line in self.pkm("check", "--json").stdout.strip().splitlines()]
        kinds = {record["kind"] for record in records}
        self.assertEqual(kinds, {"problem"})
        self.assertTrue(any(record["path"] is None and "Shared" in record["text"] for record in records))
        self.assertTrue(any(record["path"] == "notes/broken.md" and record["line"] == 1 for record in records))

    def test_limit_prints_that_many_records_and_the_footer_on_stderr_only(self):
        for i in range(4):
            self.write(f"notes/many-{i}.md", "# Many\n\nApollo again\n")
        result = self.pkm("find", "apollo", "--limit", "2")
        self.assertEqual(len(result.stdout.strip().splitlines()), 2)
        self.assertNotIn("more", result.stdout)
        self.assertIn("more (use --limit)", result.stderr)
        self.assertEqual(len(self.pkm("find", "apollo", "--limit", "100").stdout.strip().splitlines()), 6)
        self.assertNotIn("more", self.pkm("find", "apollo", "--limit", "100").stderr)

    def test_the_limit_setting_gives_the_default(self):
        self.write(".pkm/config", "format=1\nlimit=1\n")
        for i in range(3):
            self.write(f"notes/many-{i}.md", "Apollo\n")
        self.assertEqual(len(self.pkm("find", "apollo").stdout.strip().splitlines()), 1)

    def test_exit_codes_follow_the_contract(self):
        self.assertEqual(self.pkm("find", "nothing-matches-this").returncode, 1)
        self.assertEqual(self.pkm("find").returncode, 2)
        self.assertEqual(self.pkm("backlinks").returncode, 2)
        self.assertEqual(self.pkm("path").returncode, 2)
        self.assertEqual(self.pkm("path", "nobody-here").returncode, 1)
        self.assertEqual(self.pkm("list", "type=none").returncode, 1)
        self.assertEqual(self.pkm("find", "apollo", "--limit", "soon").returncode, 2)

    def test_output_options_are_refused_where_there_is_no_listing(self):
        # agenda is no command now. An unknown name is looked up as an extension first (its options belong to it), and
        # with none it is an unknown command, so the options are not checked against pkm's own commands.
        result = self.pkm("agenda", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown command: agenda", result.stderr)
        result = self.pkm("path", "apollo", "--nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("has no option --nope", result.stderr)

    def test_no_vault_is_exit_2_for_a_listing(self):
        outside = pathlib.Path(tempfile.mkdtemp())
        try:
            environment = pkm_env(XDG_CONFIG_HOME=str(outside))
            result = run_pkm(["find", "apollo", "--json"], cwd=outside, env=environment)
            self.assertEqual(result.returncode, 2)
        finally:
            shutil.rmtree(outside)

    def test_json_without_jq_is_exit_2(self):
        bare = self.root / ".bare-bin"
        bare.mkdir()
        import os
        for tool in ["awk", "cat", "date", "dirname", "grep", "head", "mktemp", "rm", "sed", "sort", "tail", "tr", "wc", "rg"]:
            found = shutil.which(tool)
            if found:
                (bare / tool).symlink_to(found)
        result = self.pkm("find", "apollo", "--json", env={"PATH": str(bare)})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("jq", result.stderr)


class OrderAndOptions(VaultCase):
    def setUp(self):
        super().setUp()
        for i in range(25):
            self.write(f"notes/budget-{i % 5}-{i}.md", f"# Note {i}\n\nThe budget line {i}\nAnother budget\n")

    def sorted_key(self, line):
        path, number, _ = line.split(":", 2)
        return (path, int(number))

    def test_find_gives_the_same_sorted_output_on_every_run_in_plain_and_json(self):
        runs = [self.pkm("find", "budget").stdout for _ in range(6)]
        self.assertEqual(len(set(runs)), 1, "find's output changed between runs")
        lines = runs[0].strip().splitlines()
        self.assertEqual(lines, sorted(lines, key=self.sorted_key))
        json_runs = [self.pkm("find", "budget", "--json").stdout for _ in range(6)]
        self.assertEqual(len(set(json_runs)), 1)
        records = [json.loads(line) for line in json_runs[0].strip().splitlines()]
        self.assertEqual([(r["path"], r["line"]) for r in records],
                         sorted([(r["path"], r["line"]) for r in records]))
        self.assertEqual([f"{r['path']}:{r['line']}: {r['text']}" for r in records], lines)

    def test_limit_takes_the_first_records_in_that_order(self):
        full = self.pkm("find", "budget").stdout.strip().splitlines()
        self.assertEqual(self.pkm("find", "budget", "--limit", "3").stdout.strip().splitlines(), full[:3])

    def test_backlinks_and_list_are_sorted_by_path(self):
        self.write("notes/zeta.md", "---\ntype: project\n---\n# Zeta [[budget-0-0]]\n")
        for command, args in [("backlinks", ["budget-0-0"]), ("list", ["type=project"])]:
            out = self.ok(command, *args).strip().splitlines()
            self.assertEqual(out, sorted(out, key=lambda line: line.split(" | ")[0]) if command == "list" else
                             sorted(out, key=self.sorted_key), command)

    def test_the_example_vault_gives_the_same_output_each_time(self):
        import shutil as _shutil
        import tempfile as _tempfile
        copy = pathlib.Path(_tempfile.mkdtemp())
        try:
            _shutil.copytree(REPO / "docs/examples/work", copy / "work")
            (copy / "work").mkdir(exist_ok=True)
            from helpers import run_pkm as _run
            outs = {_run(["find", "budget"], cwd=copy / "work", env=pkm_env(XDG_CONFIG_HOME=str(copy)),
                         vault=copy / "work").stdout for _ in range(6)}
            self.assertEqual(len(outs), 1)
        finally:
            _shutil.rmtree(copy)

    def test_every_command_rejects_an_unknown_option_with_exit_2_and_one_line(self):
        for name in [row[0] for row in help_all_names() if row[0] not in NOT_YET]:
            result = self.pkm(name, "--nope")
            self.assertEqual(result.returncode, 2, (name, result.stderr))
            self.assertEqual(len(result.stderr.strip().splitlines()), 1, (name, result.stderr))
            self.assertIn("--nope", result.stderr, name)


class HelpAllAndLint(unittest.TestCase):
    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck is not installed")
    def test_lint_catches_a_misspelled_global_in_a_command(self):
        with tempfile.TemporaryDirectory() as copy:
            for folder in ["bin", "lib", "share"]:
                shutil.copytree(REPO / folder, pathlib.Path(copy) / folder)
            shutil.copy(REPO / ".shellcheckrc", copy)
            command = pathlib.Path(copy) / "lib/pkm/cmd/vault.sh"
            command.write_text(command.read_text() + '\ncmd_misspelt() {\n  printf "%s\\n" "$tmpp"\n}\n')
            result = subprocess.run(["shellcheck", "-x", "bin/pkm", *[str(p.relative_to(copy)) for p in
                                    sorted(pathlib.Path(copy).glob("lib/pkm/*.sh"))],
                                     *[str(p.relative_to(copy)) for p in sorted(pathlib.Path(copy).glob("lib/pkm/cmd/*.sh"))]],
                                    cwd=copy, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("tmpp", result.stdout)

    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck is not installed")
    def test_the_lint_passes_on_the_real_tree(self):
        files = ["bin/pkm", *[str(p.relative_to(REPO)) for p in sorted((REPO / "lib/pkm").glob("*.sh"))],
                 *[str(p.relative_to(REPO)) for p in sorted((REPO / "lib/pkm/cmd").glob("*.sh"))]]
        result = subprocess.run(["shellcheck", "-x", *files], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
