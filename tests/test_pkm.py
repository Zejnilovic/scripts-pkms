"""Behavior tests for pkm (bin/pkm). Run: python3 -m unittest discover -s tests

Each test builds a vault in a temporary folder, with its templates copied from share/pkm/templates, and runs
bin/pkm with --vault pointing there. It fixes the clock with PKM_NOW so dates are predictable. Names and data
are made up.

"""
import datetime
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import REPO, SHARE_TEMPLATES, VaultCase, pkm_env, run_pkm

NOW = "20261025143012"  # Sunday 2026-10-25, 14:30:12, in ISO week 2026-W43


def week(day):
    year, number, _ = datetime.date.fromisoformat(day).isocalendar()
    return f"{year}-W{number:02d}"


CONFLICT = "<<<<<<< yours\n## Gratitude\n=======\n## Notes\n>>>>>>> agentic-pkms 0.1.1\n"


PREVIOUS_DAY = """# 2026-10-23

## Tasks

- [ ] Call the bank
    - ask about the fees
- [x] Send the slides
- [ ] Renew the passport (since 2026-10-01)
- [-] Book the venue

## Log

- 10:00 Met [[jane-doe]] about [[apollo]]
"""


class DailyTest(VaultCase):
    def test_creates_today_from_the_template(self):
        self.assertEqual(self.ok("day").strip(), "daybook/2026/10/2026-10-25.md")
        text = self.read("daybook/2026/10/2026-10-25.md")
        self.assertTrue(text.startswith("# 2026-10-25\n"))
        self.assertIn("## Tasks", text)
        self.assertIn("## Log", text)

    def test_leaves_an_existing_daily_alone(self):
        self.write("daybook/2026/10/2026-10-25.md", "mine\n")
        self.assertEqual(self.ok("day").strip(), "daybook/2026/10/2026-10-25.md")
        self.assertEqual(self.read("daybook/2026/10/2026-10-25.md"), "mine\n")

    def test_a_past_day_is_created_without_carrying(self):
        self.write("daybook/2026/10/2026-10-23.md", PREVIOUS_DAY)
        self.assertEqual(self.ok("day", "2026-10-20").strip(), "daybook/2026/10/2026-10-20.md")
        self.assertNotIn("Call the bank", self.read("daybook/2026/10/2026-10-20.md"))
        self.assertEqual(self.read("daybook/2026/10/2026-10-23.md"), PREVIOUS_DAY)

    def test_rejects_a_bad_date(self):
        self.assertEqual(self.pkm("day", "25.10.2026").returncode, 2)


class TodoTest(VaultCase):
    def test_adds_the_task_after_the_last_one(self):
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n## Tasks\n\n- [ ] First\n    - detail\n\n## Log\n\n- note\n")
        self.ok("todo", "Email [[jane-doe]] about the offer")
        self.assertEqual(self.read("daybook/2026/10/2026-10-25.md"),
                         "# 2026-10-25\n\n## Tasks\n\n- [ ] First\n    - detail\n"
                         "- [ ] Email [[jane-doe]] about the offer\n\n## Log\n\n- note\n")

    def test_creates_the_daily_when_missing(self):
        self.ok("todo", "Water the plants")
        text = self.read("daybook/2026/10/2026-10-25.md")
        self.assertIn("## Tasks\n\n- [ ] Water the plants\n", text)
        self.assertLess(text.index("Water the plants"), text.index("## Log"))

    def test_keeps_special_characters(self):
        self.ok("todo", r"Pay 50 & check C:\path \n literally")
        self.assertIn(r"- [ ] Pay 50 & check C:\path \n literally", self.read("daybook/2026/10/2026-10-25.md"))

    def test_needs_text(self):
        self.assertEqual(self.pkm("todo").returncode, 2)


class NewTest(VaultCase):
    def test_a_person_matches_the_method_example(self):
        result = self.pkm("new", "person", "Marta Kovac", now="20261116083000")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "notes/marta-kovac.md")
        self.assertEqual(self.read("notes/marta-kovac.md"),
                         "---\ntype: person\nsummary:\naliases: [Marta Kovac]\ncreated: 2026-11-16\n---\n\n# Marta Kovac\n")

    def test_a_taken_name_fails_with_the_path_and_a_suggestion_and_writes_nothing(self):
        self.write("archive/projects/apollo.md", "# Apollo\n")
        result = self.pkm("new", "project", "Apollo")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "archive/projects/apollo.md")
        self.assertIn("apollo-<word>", result.stderr)
        self.assertFalse(self.exists("notes/apollo.md"))

    def test_a_title_that_differs_from_the_name_becomes_an_alias(self):
        self.ok("new", "project", "Apollo")
        self.assertIn("aliases: [Apollo]\n", self.read("notes/apollo.md"))
        self.ok("new", "topic", "apollo-budget")
        self.assertIn("aliases: []\n", self.read("notes/apollo-budget.md"))

    def test_a_project_has_its_sections_in_order_and_no_health_or_board(self):
        text = self.read(self.ok("new", "project", "Hermes").strip())
        self.assertIn("status: active\n", text)
        self.assertIn("target:\n", text)
        headings = [line for line in text.split("\n") if line.startswith("## ")]
        self.assertEqual(headings, ["## Now", "## Goals", "## People", "## Links", "## Risks", "## Decisions", "## Later"])
        self.assertNotIn("health", text)
        self.assertNotIn("board", text)

    def test_a_list_has_type_list(self):
        self.assertIn("type: list\n", self.read(self.ok("new", "list", "Packing").strip()))

    def test_person_topic_and_source_end_after_the_heading(self):
        for kind in ["person", "topic", "source"]:
            text = self.read(self.ok("new", kind, f"Note {kind}").strip())
            self.assertTrue(text.endswith(f"# Note {kind}\n"), kind)

    def test_notes_go_to_notes_and_a_folder_setting_moves_a_type(self):
        self.assertEqual(self.ok("new", "source", "A source").strip(), "notes/a-source.md")
        self.write(".pkm/config", "folder_coaching=team\n")
        self.assertEqual(self.ok("new", "coaching", "Jane Doe").strip(), "team/jane-doe-coaching.md")

    def test_an_organization_is_a_note_with_its_type(self):
        self.assertEqual(self.ok("new", "org", "Acme").strip(), "notes/acme.md")
        self.assertIn("type: org\n", self.read("notes/acme.md"))

    def test_an_unknown_type_is_made_from_the_note_template(self):
        self.assertEqual(self.ok("new", "spaceship", "Enterprise").strip(), "notes/enterprise.md")
        self.assertIn("type: spaceship\n", self.read("notes/enterprise.md"))

    def test_an_own_type_uses_its_template_and_folder(self):
        self.write("templates/recipe.md", "---\ntype: recipe\n---\n\n# {{title}}\n")
        self.assertEqual(self.ok("new", "recipe", "Plum dumplings").strip(), "notes/plum-dumplings.md")
        self.write(".pkm/config", "folder_recipe=kitchen\n")
        self.assertEqual(self.ok("new", "recipe", "Goulash").strip(), "kitchen/goulash.md")

    def test_an_explicit_name_wins_and_keeps_the_title_as_alias(self):
        self.assertEqual(self.ok("new", "person", "Иван Петровић", "--name", "ivan-petrovic").strip(),
                         "notes/ivan-petrovic.md")
        self.assertIn("# Иван Петровић\n", self.read("notes/ivan-petrovic.md"))

    def test_slug_drops_diacritics_and_punctuation(self):
        self.assertEqual(self.ok("new", "person", "Šárka Nováková-Čížek, Jr.").strip(),
                         "notes/sarka-novakova-cizek-jr.md")

    def test_a_title_with_no_name_needs_a_name(self):
        self.assertEqual(self.pkm("new", "person", "!!!").returncode, 2)

    def test_refuses_daily_and_missing_titles(self):
        self.assertEqual(self.pkm("new", "day", "Something").returncode, 2)
        self.assertEqual(self.pkm("new", "person").returncode, 2)


class ConflictTest(VaultCase):
    """A merge can leave conflict markers in a file; pkm never copies them into notes."""

    def conflicted(self, template):
        path = self.root / "templates" / template
        path.write_text(path.read_text() + CONFLICT)

    def test_daily_refuses_a_template_with_markers(self):
        self.conflicted("day.md")
        for args in [("day",), ("todo", "Water the plants")]:
            result = self.pkm(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertIn("day.md", result.stderr)
            self.assertIn("<<<<<<<", result.stderr)
        self.assertFalse(self.exists("daybook/2026/10/2026-10-25.md"))

    def test_new_refuses_a_template_with_markers_and_creates_nothing(self):
        self.conflicted("person.md")
        result = self.pkm("new", "person", "Jane Doe")
        self.assertEqual(result.returncode, 2)
        self.assertIn("templates/person.md", result.stderr)
        self.assertFalse(self.exists("people/jane-doe.md"))

    def test_check_reports_markers_in_templates_notes_and_instructions(self):
        self.conflicted("day.md")
        self.write("notes/202610011200-merged.md", "# Merged\n\n" + CONFLICT)
        self.write("AGENTS.md", "# Working agreement\n\n" + CONFLICT)
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("templates/day.md:6: merge conflict", result.stdout)
        self.assertIn("notes/202610011200-merged.md:3: merge conflict", result.stdout)
        self.assertIn("AGENTS.md:3: merge conflict", result.stdout)

    def test_markers_shown_as_code_and_setext_headings_are_fine(self):
        self.write("notes/202610011200-git.md", "Conflicts look like this:\n\n```\n" + CONFLICT + "```\n\n"
                                                 "A heading\n=======\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)


class BacklinksTest(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("daybook/2026/10/2026-10-20.md", "# 2026-10-20\n\n- Met [[jane-doe]] today\n")
        self.write("notes/202610011200-trust.md", "See [[jane-doe|Jane]] and [[jane-doe#Goals]].\n")
        self.write("projects/apollo.md", '---\ntype: project\npeople: ["[[jane-doe]]"]\n---\n\n# Apollo\n')
        self.write("team/jane-doe-coaching.md", "# Jane Doe: coaching\n\n[[jane-doe-coaching]] is not her\n")
        self.write("archive/daily/2026/2026-01-02.md", "# 2026-01-02\n\n- Hired [[jane-doe]]\n")

    def test_finds_every_link_form_including_the_archive(self):
        out = self.ok("backlinks", "jane-doe")
        for expected in ["daybook/2026/10/2026-10-20.md:3: ", "notes/202610011200-trust.md:1: ", "projects/apollo.md:3: ",
                         "archive/daily/2026/2026-01-02.md:3: "]:
            self.assertIn(expected, out)
        self.assertNotIn("is not her", out)

    def test_since_filters_dated_files_only(self):
        out = self.ok("backlinks", "jane-doe", "--since", "2026-10-01")
        self.assertIn("daybook/2026/10/2026-10-20.md", out)
        self.assertIn("notes/202610011200-trust.md", out)
        self.assertNotIn("2026-01-02", out)

    def test_resolves_names_written_as_words_and_aliases(self):
        self.write("people/jane-doe.md", "---\ntype: person\naliases: [Jane Doe, JD]\n---\n\n# Jane Doe\n")
        self.write("notes/planning.md", "With [[Jane Doe]] and [[JD|Jane]]\n")
        out = self.ok("backlinks", "jane-doe")
        self.assertIn("notes/planning.md:1: With [[Jane Doe]] and [[JD|Jane]]", out)
        self.assertIn("daybook/2026/10/2026-10-20.md:3:", out)

    def test_an_unknown_name_exits_1(self):
        self.assertEqual(self.pkm("backlinks", "nobody-here").returncode, 1)


class CheckTest(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("projects/apollo.md", "---\ntype: project\n---\n\n# Apollo\n")
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n- Worked on [[apollo]] and [[apollo|it]]\n")

    def test_a_clean_vault_passes(self):
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("No problems found", result.stdout)

    def test_reports_a_broken_link_with_its_place(self):
        self.write("daybook/2026/10/2026-10-24.md", "# 2026-10-24\n\n- Lunch with [[nobody]]\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("daybook/2026/10/2026-10-24.md:3: broken link [[nobody]]", result.stdout)

    def test_ignores_links_in_code(self):
        self.write("notes/202610011200-syntax.md", "Write `[[name]]` like this:\n\n```\n[[example]]\n```\n")
        self.assertEqual(self.pkm("check").returncode, 0)

    def test_links_to_attachments_resolve(self):
        self.write("attachments/2026-10-25-receipt.pdf", "pdf")
        self.write("items/kettle.md", "---\ntype: item\n---\n\n# Kettle\n\n![[2026-10-25-receipt.pdf]]\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)

    def test_templates_and_tool_folders_are_not_checked(self):
        self.write(".claude/skills/x/SKILL.md", "[[missing-in-a-skill]]\n")
        self.write("AGENTS.md", "Link like [[this]].\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)

    def test_reports_duplicate_names(self):
        self.write("notes/apollo.md", "# Another apollo\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate name apollo", result.stdout)
        self.assertIn("notes/apollo.md", result.stdout)
        self.assertIn("projects/apollo.md", result.stdout)

    def test_reports_a_secret_without_showing_it(self):
        self.write("daybook/2026/10/2026-10-24.md", "# 2026-10-24\n\nAPI_KEY = sk-abcdefghijklmnopqrstuvwxyz123456\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("daybook/2026/10/2026-10-24.md:3: looks like a secret", result.stdout)
        self.assertNotIn("abcdefghij", result.stdout)

    def test_a_secret_said_in_words_is_a_secret(self):
        self.write("daybook/2026/10/2026-10-24.md", "# 2026-10-24\n\nThe password is hunter22secret\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("daybook/2026/10/2026-10-24.md:3: looks like a secret", result.stdout)

    def test_words_after_a_secret_word_are_not_a_secret(self):
        self.write("notes/202610011200-words.md", "The password is in the manager\nThe token is expired\nThe secret is 3 days old\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)

    def test_a_secret_with_words_before_the_value_is_a_secret(self):
        self.write("daybook/2026/10/2026-10-24.md", "# 2026-10-24\n\nThe wifi password at the office is summer2026office\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("daybook/2026/10/2026-10-24.md:3: looks like a secret", result.stdout)
        self.assertNotIn("summer2026", result.stdout)

    def test_a_marked_line_is_not_a_secret(self):
        self.write("notes/202610011200-keys.md", "password: correct-horse-42 <!-- pkm-ignore-secret -->\n")
        self.assertEqual(self.pkm("check").returncode, 0)

    def test_the_same_line_without_the_mark_is_a_secret(self):
        self.write("notes/202610011200-keys.md", "password: correct-horse-42\n")
        self.assertEqual(self.pkm("check").returncode, 1)

    def test_a_link_after_a_secret_word_is_not_a_secret(self):
        self.write("notes/202610011200-tokens.md", "token: [[apollo]]\npassword: in the password manager\n")
        self.assertEqual(self.pkm("check").returncode, 0, self.pkm("check").stdout)

    def test_notices_do_not_fail(self):
        self.write("people/Jane Doe.md", "# Jane\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Notices:", result.stdout)


class ListTest(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("projects/apollo.md", '---\ntype: project\nstatus: active\npeople: ["[[jane-doe]]"]\n---\n\n# Apollo\n')
        self.write("projects/zeus.md", "---\ntype: project\nstatus: done\n---\n\n# Zeus\n")
        self.write("people/jane-doe.md", "---\ntype: person\nbirthday: 1990-10-30\ntags:\n  - team\n---\n\n# Jane Doe\n")
        self.write("archive/projects/hermes.md", "---\ntype: project\nstatus: active\n---\n\n# Hermes\n")

    def test_filters_by_fields(self):
        out = self.ok("list", "type=project", "status=active")
        self.assertIn("projects/apollo.md\tproject\tApollo", out)
        self.assertNotIn("zeus", out)
        self.assertNotIn("hermes", out)

    def test_all_includes_the_archive(self):
        self.assertIn("archive/projects/hermes.md", self.ok("list", "type=project", "--all"))

    def test_matches_links_and_list_items(self):
        self.assertIn("projects/apollo.md", self.ok("list", "people=jane-doe"))
        self.assertIn("people/jane-doe.md", self.ok("list", "tags=team"))

    def test_shows_extra_fields(self):
        self.assertIn("\t1990-10-30", self.ok("list", "type=person", "--show", "birthday"))


class FindTest(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("projects/apollo.md", "# Apollo\n\nLaunch plan with the mobile app\n")
        self.write("archive/daily/2026/2026-01-02.md", "Apollo kickoff\n")

    def test_finds_every_word_on_a_line_in_any_order(self):
        out = self.ok("find", "mobile", "launch")
        self.assertIn("projects/apollo.md:3: Launch plan with the mobile app", out)
        self.assertEqual(self.pkm("find", "mobile", "kickoff").returncode, 1)

    def test_searches_the_archive_unless_live(self):
        self.assertIn("archive/daily/2026/2026-01-02.md:1: Apollo kickoff", self.ok("find", "kickoff"))
        self.assertEqual(self.pkm("find", "--live", "kickoff").returncode, 1)

    def test_smart_case_holds_in_a_utf8_locale(self):
        # In en_US.UTF-8, bash 3.2 lets [A-Z] match lowercase letters, and LC_ALL overrides everything else.
        for env in ({"LANG": "en_US.UTF-8"}, {"LC_ALL": "en_US.UTF-8"}):
            self.assertIn("projects/apollo.md", self.ok("find", "apollo", env=env), env)

    def test_smart_case(self):
        self.assertIn("projects/apollo.md", self.ok("find", "apollo"))
        self.assertEqual(self.pkm("find", "Apollo").returncode, 0)
        self.assertEqual(self.pkm("find", "Launch").returncode, 0)
        self.assertEqual(self.pkm("find", "APOLLO").returncode, 1)

    def test_skips_templates_and_tool_folders(self):
        self.write(".claude/notes.md", "Apollo hidden\n")
        out = self.ok("find", "apollo")
        self.assertNotIn("templates/", out)
        self.assertNotIn(".claude", out)

    def test_needs_a_word(self):
        self.assertEqual(self.pkm("find").returncode, 2)

    def test_searches_the_vault_when_stdin_is_a_pipe(self):
        result = self.pkm("find", "apollo", stdin=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("projects/apollo.md", result.stdout)

    def test_old_names_are_gone(self):
        self.assertEqual(self.pkm("grep", "apollo").returncode, 2)
        self.assertEqual(self.pkm("links", "apollo").returncode, 2)


class ToolsTest(VaultCase):
    def without_tools(self):
        """A PATH with what the script itself needs to start, and none of the tools vaults expect."""
        folder = self.root / ".bare-bin"
        folder.mkdir()
        for tool in ["awk", "cat", "date", "dirname", "grep", "head", "mktemp", "rm", "sed", "sort", "tail", "tr"]:
            (folder / tool).symlink_to(shutil.which(tool))
        return {"PATH": str(folder)}

    def test_doctor_passes_with_the_tools(self):
        out = self.ok("doctor")
        for tool in ["rg", "jq", "git"]:
            self.assertIn(tool, out)

    def test_doctor_names_what_is_missing(self):
        result = self.pkm("doctor", env=self.without_tools())
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing  rg", result.stdout)
        self.assertIn("missing  jq", result.stdout)
        self.assertIn("brew install", result.stdout)

    def test_find_says_how_to_get_ripgrep(self):
        result = self.pkm("find", "apollo", env=self.without_tools())
        self.assertEqual(result.returncode, 2)
        self.assertIn("ripgrep", result.stderr)
        self.assertIn("doctor", result.stderr)


class PathTest(VaultCase):
    def test_finds_a_note_by_name_anywhere(self):
        self.write("archive/projects/apollo.md", "# Apollo\n")
        self.assertEqual(self.ok("path", "apollo").strip(), "archive/projects/apollo.md")
        self.assertEqual(self.ok("path", "[[apollo|the portal]]").strip(), "archive/projects/apollo.md")

    def test_finds_attachments_and_fails_for_unknown_names(self):
        self.write("attachments/2026-10-25-receipt.pdf", "pdf")
        self.assertEqual(self.ok("path", "2026-10-25-receipt.pdf").strip(), "attachments/2026-10-25-receipt.pdf")
        self.assertEqual(self.pkm("path", "nobody").returncode, 1)


class OtherCommandsTest(VaultCase):
    def test_init_creates_its_three_files_and_refuses_to_overwrite_them(self):
        self.ok("init")
        self.assertEqual(self.read(".pkm/config"), "format=1\n")
        self.assertEqual(self.read(".pkm/.gitignore"), "cache/\nstate\n")
        self.assertIn("gitignore syntax", self.read(".pkmignore"))
        self.assertFalse(self.exists("daily"))
        self.write(".pkm/config", "shared=yes\n")
        result = self.pkm("init")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.read(".pkm/config"), "shared=yes\n")

    def test_help_and_unknown_commands(self):
        self.assertIn("pkm day", self.ok("help"))
        self.assertEqual(self.pkm("fly").returncode, 2)

    def test_version_prints_the_release(self):
        # Skills and editors depend on the commands; they read this to tell which ones a vault has.
        self.assertEqual(self.ok("version"), (REPO / "VERSION").read_text().strip() + "\n")
        self.assertEqual(self.ok("--version"), self.ok("version"))

    def test_runs_from_any_folder(self):
        (self.root / "notes").mkdir()
        environment = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=self.config_home)
        result = run_pkm(["day"], cwd=self.root / "notes", env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.exists("daybook/2026/10/2026-10-25.md"))
        result = run_pkm(["help"], cwd=self.root / "notes", env=environment)
        self.assertIn("pkm day", result.stdout, result.stderr)


if __name__ == "__main__":
    unittest.main()
