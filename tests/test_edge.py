"""Edge cases that real input produces: names with spaces, unicode and apostrophes, CRLF files, a BOM, notes without
frontmatter, code spans and fences, an empty vault, a vault folder with spaces, month ends, leap days, the year boundary,
tabs and struck tasks, LC_ALL=C order, and greps over bin/ and lib/ for bash 4 and GNU-only syntax. A test that fails
shows a bug in bin/ or lib/; none is skipped. Run: python3 -m unittest discover -s tests
Names and data are made up. NOW is 2026-10-25 14:30:12, the helpers' default.
"""

import json
import pathlib
import re
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

NOW = "20261025143012"
DAY = "daybook/2026/10/2026-10-25.md"
# Line 8 is the task, line 13 the second log entry.
CRLF_DAY = (b"---\r\ntype: day\r\n---\r\n# 2026-10-25\r\n\r\n## Tasks\r\n\r\n- [ ] Crlf task (due 2026-10-30)\r\n"
            b"\r\n## Log\r\n\r\n- 09:00 first entry\r\n- 10:00 second entry\r\n")
CRLF_APOLLO = b"---\r\ntype: project\r\n---\r\n# Apollo\r\n\r\n## Decisions\r\n\r\n- Old decision\r\n"
CODE_NOTE = (
    "# Code\n\n"
    "```\n[[ghost]]\n- [ ] fenced task\nhttps://example.test/fenced\n```\n\n"
    "Inline `[[ghost]]` and `- [ ] inline` and `https://example.test/inline`.\n\n"
    "~~~\n[[ghost2]]\n~~~\n\n"
    "Real address https://example.test/real\n\n"
    "- [ ] Real task\n")


class EdgeCase(VaultCase):
    def put(self, rel, data):
        """Writes bytes, so CRLF and a BOM reach the file exactly as written here."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def raw(self, rel):
        return (self.root / rel).read_bytes()


class NamesAndFiles(EdgeCase):
    def test_a_name_with_an_apostrophe_and_unicode_is_linked_by_its_words(self):
        result = self.pkm("new", "person", "Zoë O'Brien")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "notes/zoe-o-brien.md")
        self.assertIn("aliases: [Zoë O'Brien]", self.read("notes/zoe-o-brien.md"))
        self.write("notes/meeting.md", "Met [[Zoë O'Brien]] today\n")
        check = self.pkm("check")
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertNotIn("broken link", check.stdout)
        self.assertIn("notes/meeting.md:1:", self.ok("backlinks", "zoe-o-brien"))

    def test_a_file_name_with_a_space_is_read_through_the_cache(self):
        self.write("notes/my note.md", "---\ntype: person\n---\n# My note\n")
        self.assertIn("notes/my note.md", self.ok("names", "--type", "person"))
        self.write("notes/my note.md", "---\ntype: project\n---\n# My note\n")
        self.ok("index")
        self.assertNotIn("notes/my note.md", self.pkm("names", "--type", "person").stdout)
        self.assertIn("notes/my note.md", self.ok("names", "--type", "project"))

    def test_a_note_whose_file_name_has_a_space_is_renamed_and_its_links_follow(self):
        self.write("notes/my note.md", "# My note\n")
        self.write("notes/link.md", "See [[my note]] and [[my note|the note]]\n")
        self.ok("rename", "my note", "my-note")
        self.assertFalse(self.exists("notes/my note.md"))
        self.assertTrue(self.exists("notes/my-note.md"))
        self.assertEqual(self.read("notes/link.md"), "See [[my-note]] and [[my-note|the note]]\n")
        self.assertEqual(self.pkm("check").returncode, 0)

    def test_path_finds_a_unicode_name_under_lc_all_c(self):
        self.write("notes/zoë.md", "# Zoë\n")
        result = self.pkm("path", "zoë", env={"LC_ALL": "C", "LANG": "C"})
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "notes/zoë.md"), result.stderr)

    def test_listings_sort_by_bytes_under_lc_all_c(self):
        for name in ("Zebra", "apple", "Émile"):
            self.write(f"notes/{name}.md", f"# {name}\n")
        lines = self.ok("list", env={"LC_ALL": "C"}).splitlines()
        self.assertEqual([line.split("\t")[0] for line in lines],
                         ["notes/Zebra.md", "notes/apple.md", "notes/Émile.md"])


class CarriageReturns(EdgeCase):
    """Files saved with Windows line endings: every command reads them and edits keep the line ending last."""

    def test_tasks_read_a_crlf_day_page(self):
        self.put(DAY, CRLF_DAY)
        self.assertIn(f"{DAY}:8: - [ ] Crlf task (due 2026-10-30)", self.ok("tasks"))

    def test_task_and_find_records_in_json_have_no_carriage_return(self):
        self.put(DAY, CRLF_DAY)
        tasks = [json.loads(line) for line in self.ok("tasks", "--json").splitlines()]
        self.assertEqual([record["text"] for record in tasks], ["- [ ] Crlf task (due 2026-10-30)"])
        found = [json.loads(line) for line in self.ok("find", "--json", "Crlf").splitlines()]
        self.assertEqual([record["text"] for record in found], ["- [ ] Crlf task (due 2026-10-30)"])

    def test_since_reads_the_log_of_a_crlf_day_page(self):
        self.put(DAY, CRLF_DAY)
        records = [json.loads(line) for line in self.ok("since", "2026-10-25", "--json").splitlines()]
        log = [record["text"] for record in records if record["kind"] == "log"]
        self.assertIn("- 09:00 first entry", log)
        self.assertIn("- 10:00 second entry", log)

    def test_add_on_a_crlf_day_page_appends_to_its_one_log_section(self):
        self.put(DAY, CRLF_DAY)
        path, line = self.ok("add", "third entry").strip().rsplit(":", 1)
        self.assertEqual(path, DAY)
        text = self.raw(DAY).decode()
        self.assertEqual(text.count("## Log"), 1, text)
        self.assertEqual(text.splitlines()[int(line) - 1], "- 14:30 third entry")

    def test_post_puts_the_suffix_before_the_line_end_of_a_crlf_line(self):
        self.put(DAY, CRLF_DAY)
        self.put("notes/apollo.md", CRLF_APOLLO)
        self.ok("post", f"{DAY}:13", "notes/apollo.md#Decisions")
        self.assertRegex(self.raw("notes/apollo.md"), rb"- 10:00 second entry \(\[\[2026-10-25\]\]\)\r?\n")

    def test_done_puts_the_date_before_the_line_end_of_a_crlf_task(self):
        self.put("notes/r.md", b"# R\r\n\r\n- [ ] Open CRLF item\r\n")
        self.ok("done", "notes/r.md:3")
        self.assertRegex(self.raw("notes/r.md"), rb"- \[x\] Open CRLF item \(done 2026-10-25\)\r?\n")

    def test_strike_wraps_a_crlf_line_before_its_line_end(self):
        self.put("notes/s.md", b"# S\r\n\r\n- [ ] Struck CRLF item\r\n")
        self.ok("strike", "notes/s.md:3")
        self.assertRegex(self.raw("notes/s.md"), rb"- \[ \] ~~Struck CRLF item~~ \(\[\[2026-10-25\]\]\)\r?\n")

    def test_get_reads_a_section_of_a_crlf_note(self):
        self.put("notes/apollo.md", CRLF_APOLLO)
        result = self.pkm("get", "apollo#Decisions")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("- Old decision", result.stdout)


class FrontmatterAndBom(EdgeCase):
    def test_a_bom_before_the_frontmatter_is_read(self):
        self.put("people/bom-person.md", b"\xef\xbb\xbf---\ntype: person\naliases: [Bom Person]\n---\n# Bom Person\n")
        result = self.pkm("names", "--type", "person")
        self.assertIn("bom-person\tperson\tpeople/bom-person.md\tBom Person", result.stdout.splitlines(), result.stdout)

    def test_a_note_without_frontmatter_is_a_plain_note_that_still_works(self):
        self.write("people/bom-person.md", "---\ntype: person\n---\n# Bom Person\n")
        self.write("notes/plain.md", "Plain note, no frontmatter\n\n- [ ] Plain task\n\nSee [[bom-person]]\n")
        fields = {line.split("\t")[0]: line.split("\t") for line in self.ok("names").splitlines()}
        self.assertEqual(fields["plain"][1:], ["note", "notes/plain.md", ""])
        self.assertIn("notes/plain.md:3: - [ ] Plain task", self.ok("tasks"))
        self.assertIn("notes/plain.md:5:", self.ok("backlinks", "bom-person"))
        check = self.pkm("check")
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertIn("No problems found.", check.stdout)


class CodeIsNotText(EdgeCase):
    """Links, tasks and web addresses inside fences and code spans are code, not links, tasks or sources."""

    def setUp(self):
        super().setUp()
        self.write("notes/code.md", CODE_NOTE)

    def test_links_inside_code_are_not_links(self):
        check = self.pkm("check")
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertNotIn("broken link", check.stdout)
        self.assertEqual(self.pkm("backlinks", "ghost").returncode, 1)
        self.assertEqual(self.pkm("backlinks", "ghost2").returncode, 1)

    def test_tasks_and_since_skip_code(self):
        tasks = [line for line in self.ok("tasks").splitlines() if "code.md" in line]
        self.assertEqual(tasks, ["notes/code.md:17: - [ ] Real task"])
        self.put(DAY, "# 2026-10-25\n\n## Log\n\n- 09:00 Inline `[[ghost]]` only\n")
        result = self.pkm("since", "2026-10-25", "--about", "ghost")
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_web_addresses_inside_code_are_not_links(self):
        result = self.pkm("links", "--external")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "notes/code.md:15: https://example.test/real")

    def test_evidence_does_not_take_a_web_address_in_code_as_a_source(self):
        self.write("notes/now.md", "## Now\n\n- Point with code `https://example.test/a`\n- Point sourced https://example.test/b\n")
        result = self.pkm("evidence", "notes/now.md")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(result.stdout.strip(), "notes/now.md:3: - Point with code `https://example.test/a`")


class EmptyVault(unittest.TestCase):
    """A vault where only pkm init has run."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self._config = tempfile.TemporaryDirectory()
        self.env = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=self._config.name)
        init = run_pkm(["init"], cwd=self.root, env=self.env, vault=self.root)
        self.assertEqual(init.returncode, 0, init.stderr)

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def test_read_commands_exit_as_the_contract_says(self):
        cases = [
            (["names"], 1), (["find", "budget"], 1), (["backlinks", "budget"], 1), (["path", "budget"], 1),
            (["tasks"], 1), (["list"], 1), (["get", "budget"], 1), (["since"], 1), (["links", "--external"], 1),
            (["check"], 0), (["check", "--json"], 0), (["close"], 0), (["tags"], 0), (["upcoming"], 0),
        ]
        for args, code in cases:
            with self.subTest(command=" ".join(args)):
                result = run_pkm(args, cwd=self.root, env=self.env, vault=self.root)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)


class VaultPath(EdgeCase):
    def test_commands_run_from_a_subfolder_of_a_vault_in_a_folder_with_spaces(self):
        vault = self.root / "my vault"
        (vault / ".pkm").mkdir(parents=True)
        (vault / ".pkm/config").write_text("format=1\n")
        cwd = vault / "notes"
        cwd.mkdir()
        env = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=self.config_home)
        added = run_pkm(["add", "spaced entry"], cwd=cwd, env=env)
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertTrue(added.stdout.startswith(DAY + ":"), added.stdout)
        self.assertTrue((vault / DAY).exists())
        self.assertEqual(run_pkm(["find", "spaced"], cwd=cwd, env=env).returncode, 0)
        self.assertEqual(run_pkm(["check"], cwd=cwd, env=env).returncode, 0)


class MonthsCyclesAndYears(EdgeCase):
    def test_a_monthly_routine_from_the_31st_lands_on_the_month_end(self):
        self.write("notes/rent.md", "# Rent\n\n- [ ] Pay rent (due 2026-01-31) (every 1m)\n")
        self.ok("done", "notes/rent.md:3", now="20260201090000")
        self.assertIn("- [ ] Pay rent (due 2026-02-28) (every 1m)", self.read("notes/rent.md"))

    def test_a_monthly_routine_clamps_to_a_short_month_and_takes_a_leap_february(self):
        self.write("notes/mar.md", "# Mar\n\n- [ ] March (due 2026-03-31) (every 1m)\n")
        self.write("notes/jan.md", "# Jan\n\n- [ ] January (due 2028-01-31) (every 1m)\n")
        self.ok("done", "notes/mar.md:3", now="20260201090000")
        self.ok("done", "notes/jan.md:3", now="20260201090000")
        self.assertIn("(due 2026-04-30)", self.read("notes/mar.md"))
        self.assertIn("(due 2028-02-29)", self.read("notes/jan.md"))

    def test_a_cycle_from_the_28th_in_a_leap_february(self):
        self.write(".pkm/config", "format=1\ncycle_pay=1m from 28\n")
        self.assertEqual(self.ok("cycle", "pay", "--date", "2028-02-29").strip(), "pay\t2028-02-28\t2028-03-27")
        self.assertEqual(self.ok("cycle", "pay", "--date", "2028-01-31").strip(), "pay\t2028-01-28\t2028-02-27")

    def test_a_dated_cycle_routine_moves_a_month_on_and_an_undated_one_takes_the_next_period_end(self):
        self.write(".pkm/config", "format=1\ncycle_pay=1m from 28\n")
        self.write("notes/cyc.md", "# Cyc\n\n- [ ] Dated (due 2028-02-28) (every pay)\n- [ ] Undated (every pay)\n")
        self.ok("done", "notes/cyc.md:3", now="20280229090000")
        self.assertIn("- [ ] Dated (due 2028-03-28) (every pay)", self.read("notes/cyc.md"))
        self.ok("done", "notes/cyc.md:4", now="20260201090000")
        self.assertIn("(due 2026-03-27) (every pay)", self.read("notes/cyc.md"))

    def test_new_close_for_the_week_holding_1_january_goes_in_the_folder_of_its_first_day_year(self):
        out = self.ok("new", "close", now="20270102235900")
        self.assertEqual(out.strip(), "closes/2026/2026-12-28-week.md")
        self.assertIn("# Week of 2026-12-28", self.read("closes/2026/2026-12-28-week.md"))

    def test_new_close_takes_the_date_option_the_contract_names(self):
        result = self.pkm("new", "close", "--date", "2027-01-01", now="20270102235900")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.exists("closes/2026/2026-12-28-week.md"))

    def test_since_from_late_december_covers_both_years(self):
        self.put("daybook/2026/12/2026-12-30.md", "# 2026-12-30\n\n## Log\n\n- 09:00 late december entry\n")
        self.put("daybook/2027/01/2027-01-01.md", "# 2027-01-01\n\n## Log\n\n- 09:00 new year entry\n")
        out = self.ok("since", "2026-12-30", now="20270102235900")
        self.assertIn("daybook/2026/12/2026-12-30.md:5: - 09:00 late december entry", out)
        self.assertIn("daybook/2027/01/2027-01-01.md:5: - 09:00 new year entry", out)

    def test_add_at_2359_lands_on_that_days_page(self):
        out = self.ok("add", "late entry", now="20270102235900")
        self.assertTrue(out.startswith("daybook/2027/01/2027-01-02.md:"), out)
        self.assertIn("- 23:59 late entry", self.read("daybook/2027/01/2027-01-02.md"))


class TabsAndStrikes(EdgeCase):
    def test_a_tab_indented_task_is_listed_and_a_struck_one_is_not(self):
        self.write("notes/tabs.md", "# Tabs\n\n\t- [ ] Tab indented task (due 2026-10-20)\n- [ ] ~~Struck task~~\n")
        out = self.ok("tasks")
        self.assertIn("Tab indented task", out)
        self.assertNotIn("Struck task", out)
        self.assertIn("notes/tabs.md:4:", self.ok("find", "Struck"))


PORTABLE_SOURCES = [REPO / "bin/pkm", *sorted((REPO / "lib/pkm").rglob("*.sh"))]
BASH4 = [
    r"\bmapfile\b", r"\breadarray\b", r"\$\{[^}]*(,,|\^\^)", r"\bdeclare\s+-[A-Za-z]*[Alnu]\b", r"\blocal\s+-[A-Za-z]*n\b",
    r"\|&", r"&>>", r"\bcoproc\b", r";;&", r"\[\[\s+-v\s", r"\$\{[^}]*@[QEPAa]\}", r"\bwait\s+-n\b", r"%\([^)]*\)T",
]
GAWK = [
    r"\bgensub\b", r"\basorti?\b", r"\bstrftime\b", r"\bsystime\b", r"\bmktime\b", r"\bPROCINFO\b",
    r"\bIGNORECASE\b", r"\bBEGINFILE\b",
]
GNU_ONLY = [r"\bsed\s+-i\b", r"\breadlink\s+-f\b", r"-printf\b", r"\bsort\s+-[A-Za-z]*V\b", r"\bgrep\s+-[A-Za-z]*P\b",
            r"\bsed\s+-r\b", r"\bxargs\s+-r\b"]
# The flavour checks: date and stat differ between GNU and BSD, and only these two files choose between them.
FLAVOUR = [r"\bdate\s+-[dvj]\b", r"\bstat\s+-[cf]\b"]
FLAVOUR_FILES = {"dates.sh", "index.sh"}


def violations(patterns, skip_files=()):
    """The lines of pkm's scripts that match a pattern, skipping comment lines and the files in skip_files."""
    found = []
    for path in PORTABLE_SOURCES:
        if path.name in skip_files:
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if any(re.search(pattern, line) for pattern in patterns):
                found.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    return found


class Portability(unittest.TestCase):
    """Greps over the scripts: the suite runs them on bash 3.2 and BSD tools, so bash 4 and GNU-only syntax fails here."""

    def test_no_bash_4_syntax(self):
        self.assertEqual(violations(BASH4), [])

    def test_no_gawk_only_awk(self):
        self.assertEqual(violations(GAWK), [])

    def test_no_gnu_only_flags_outside_the_flavour_checks(self):
        self.assertEqual(violations(GNU_ONLY), [])
        self.assertEqual(violations(FLAVOUR, skip_files=FLAVOUR_FILES), [])


if __name__ == "__main__":
    unittest.main()
