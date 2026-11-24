"""Organizing notes: new with --set, --folder and --url, set, mv with several notes, and the part_of_folders setting."""

import unittest

from helpers import VaultCase


class NewWithValues(VaultCase):
    def test_set_fills_the_template_keys_and_adds_others(self):
        self.ok("new", "project", "Apollo")
        path = self.ok("new", "project", "Hermes", "--set", "status=idea", "--set", "part_of=apollo",
                       "--set", "summary=A second try: smaller", "--set", "jira=HER").strip()
        text = self.read(path)
        self.assertIn("\nstatus: idea\n", text)
        self.assertIn("\npart_of: apollo\n", text)
        self.assertIn("\nsummary: A second try: smaller\n", text)
        self.assertIn("\njira: HER\n---\n", text)
        self.assertEqual(text.count("status:"), 1)
        self.assertIn("aliases: [Hermes]", text)

    def test_set_refuses_a_part_of_that_names_no_note(self):
        result = self.pkm("new", "repo", "apollo-web", "--set", "part_of=apollo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("apollo", result.stderr)
        self.assertFalse(self.exists("notes/apollo-web.md"))

    def test_set_refuses_a_bad_key_type_and_a_bad_address(self):
        self.assertEqual(self.pkm("new", "note", "A", "--set", "Bad Key=x").returncode, 2)
        self.assertEqual(self.pkm("new", "note", "A", "--set", "nokey").returncode, 2)
        self.assertEqual(self.pkm("new", "note", "A", "--set", "type=project").returncode, 2)
        self.assertEqual(self.pkm("new", "note", "A", "--set", "url=github.com/acme").returncode, 2)
        self.assertFalse(self.exists("notes/a.md"))

    def test_folder_puts_the_note_there(self):
        self.assertEqual(self.ok("new", "note", "Plan", "--folder", "notes/apollo").strip(), "notes/apollo/plan.md")
        self.assertEqual(self.pkm("new", "note", "Other", "--folder", "../out").returncode, 2)

    def test_a_name_is_unique_across_folders(self):
        self.ok("new", "note", "Plan", "--folder", "notes/apollo")
        self.assertEqual(self.pkm("new", "note", "Plan").returncode, 1)


class NewRepoFromUrl(VaultCase):
    def test_github_address_gives_name_url_and_items(self):
        path = self.ok("new", "repo", "--url", "https://github.com/acme-example/apollo-web.git/").strip()
        self.assertEqual(path, "notes/apollo-web.md")
        text = self.read(path)
        self.assertIn("\nurl: https://github.com/acme-example/apollo-web\n", text)
        self.assertIn("\nitems: https://github.com/acme-example/apollo-web/issues/\n", text)
        self.assertIn("# apollo-web\n", text)
        self.assertIn("aliases: []", text)

    def test_ssh_and_short_forms(self):
        text = self.read(self.ok("new", "repo", "--url", "git@github.com:acme-example/apollo-api.git").strip())
        self.assertIn("url: https://github.com/acme-example/apollo-api\n", text)
        text = self.read(self.ok("new", "repo", "--url", "acme-example/apollo-docs").strip())
        self.assertIn("items: https://github.com/acme-example/apollo-docs/issues/\n", text)

    def test_azure_devops_and_gitlab(self):
        text = self.read(self.ok("new", "repo", "--url", "https://dev.azure.com/acme-example/apollo/_git/apollo-etl").strip())
        self.assertIn("url: https://dev.azure.com/acme-example/apollo/_git/apollo-etl\n", text)
        self.assertIn("items: https://dev.azure.com/acme-example/apollo/_git/apollo-etl/pullrequest/\n", text)
        text = self.read(self.ok("new", "repo", "--url", "https://gitlab.com/acme-example/tools/apollo-cli").strip())
        self.assertIn("items: https://gitlab.com/acme-example/tools/apollo-cli/-/issues/\n", text)

    def test_a_title_and_name_win_over_the_address(self):
        path = self.ok("new", "repo", "Apollo Web", "--name", "apollo-web-repo", "--url",
                       "https://github.com/acme-example/apollo-web").strip()
        self.assertEqual(path, "notes/apollo-web-repo.md")
        self.assertIn("# Apollo Web\n", self.read(path))

    def test_a_clash_names_the_qualified_name(self):
        self.ok("new", "project", "apollo-web")
        result = self.pkm("new", "repo", "--url", "https://github.com/acme-example/apollo-web")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--name apollo-web-", result.stderr)

    def test_other_hosts_and_types_keep_the_address_only(self):
        text = self.read(self.ok("new", "repo", "--url", "https://git.acme.example/apollo/apollo-web").strip())
        self.assertIn("url: https://git.acme.example/apollo/apollo-web\n", text)
        self.assertIn("\nitems:\n", text)
        text = self.read(self.ok("new", "app", "Acme Portal", "--url", "https://portal.acme.example").strip())
        self.assertIn("url: https://portal.acme.example\n", text)
        self.assertIn("\nitems:\n", text)

    def test_a_type_without_a_title_needs_an_address(self):
        self.assertEqual(self.pkm("new", "repo", "--url", "not an address").returncode, 2)


class SetValues(VaultCase):
    def setUp(self):
        super().setUp()
        self.ok("new", "app", "Acme Portal")
        self.ok("new", "repo", "--url", "https://github.com/acme-example/apollo-web")

    def test_set_changes_and_adds_keys_and_prints_each_line(self):
        out = self.ok("set", "apollo-web", "part_of=acme-portal", "jira=APW")
        self.assertIn("notes/apollo-web.md:3: part_of: acme-portal", out)
        self.assertIn(": jira: APW", out)
        text = self.read("notes/apollo-web.md")
        self.assertIn("\npart_of: acme-portal\n", text)
        self.assertIn("\njira: APW\n---\n", text)
        self.assertEqual(self.ok("list", "part_of=acme-portal").count("notes/apollo-web.md"), 1)

    def test_an_empty_value_clears_and_a_list_value_replaces_its_lines(self):
        self.write("notes/x.md", "---\ntype: note\ntags:\n  - one\n  - two\nsummary: old\n---\n\n# X\n")
        self.ok("set", "x", "tags=[three]", "summary=")
        self.assertEqual(self.read("notes/x.md"), "---\ntype: note\ntags: [three]\nsummary:\n---\n\n# X\n")

    def test_a_note_without_frontmatter_gets_one(self):
        self.write("notes/y.md", "# Y\n\nText.\n")
        self.ok("set", "y", "status=active")
        self.assertEqual(self.read("notes/y.md"), "---\nstatus: active\n---\n# Y\n\nText.\n")

    def test_line_endings_and_byte_order_mark_are_kept(self):
        self.write("notes/z.md", "﻿---\r\ntype: note\r\n---\r\n\r\n# Z\r\n")
        self.ok("set", "z", "status=idea")
        self.assertEqual((self.root / "notes/z.md").read_bytes(),
                         "﻿---\r\ntype: note\r\nstatus: idea\r\n---\r\n\r\n# Z\r\n".encode())

    def test_set_refuses_what_would_make_a_mess(self):
        self.assertEqual(self.pkm("set", "apollo-web", "part_of=nothing-here").returncode, 1)
        self.assertEqual(self.pkm("set", "no-such-note", "status=idea").returncode, 1)
        self.assertEqual(self.pkm("set", "apollo-web").returncode, 2)
        self.assertEqual(self.pkm("set", "apollo-web", "items=nowhere").returncode, 2)
        self.assertEqual(self.pkm("set", "apollo-web", "a=b\tc").returncode, 2)
        self.ok("day")
        self.assertEqual(self.pkm("set", "2026-10-25", "status=idea").returncode, 1)
        self.assertNotIn("nothing-here", self.read("notes/apollo-web.md"))

    def test_type_can_be_set(self):
        self.ok("set", "apollo-web", "type=app")
        self.assertIn("\ntype: app\n", self.read("notes/apollo-web.md"))


class MoveSeveral(VaultCase):
    def test_mv_moves_each_note_and_prints_each_path(self):
        for name in ("a", "b", "c"):
            self.ok("new", "note", name)
        out = self.ok("mv", "a", "b", "notes/group")
        self.assertEqual(out.splitlines(), ["notes/group/a.md", "notes/group/b.md"])
        self.assertTrue(self.exists("notes/c.md"))
        self.assertEqual(self.read(".pkm/moves.tsv").count("notes/group/"), 2)

    def test_one_bad_note_moves_none(self):
        self.ok("new", "note", "a")
        self.assertEqual(self.pkm("mv", "a", "missing", "notes/group").returncode, 1)
        self.assertTrue(self.exists("notes/a.md"))
        self.assertFalse(self.exists("notes/group"))


class PartOfFolders(VaultCase):
    def setUp(self):
        super().setUp()
        self.write(".pkm/config", "part_of_folders=yes\n")
        self.ok("new", "project", "project-v9")

    def test_new_goes_into_the_folder_of_its_parent(self):
        path = self.ok("new", "repo", "--url", "https://github.com/acme-example/project-v9-api",
                       "--set", "part_of=project-v9").strip()
        self.assertEqual(path, "notes/project-v9/project-v9-api.md")
        path = self.ok("new", "note", "Load test", "--set", "part_of=project-v9-api").strip()
        self.assertEqual(path, "notes/project-v9/project-v9-api/load-test.md")
        self.assertIn("Checked", self.ok("check"))

    def test_folder_and_a_type_folder_win(self):
        self.write(".pkm/config", "part_of_folders=yes\nfolder_coaching=team\n")
        self.assertEqual(self.ok("new", "note", "Odd", "--set", "part_of=project-v9", "--folder", "notes").strip(),
                         "notes/odd.md")
        self.assertEqual(self.ok("new", "coaching", "Jane Doe", "--set", "part_of=project-v9").strip(),
                         "team/jane-doe-coaching.md")

    def test_set_part_of_moves_the_note_and_says_where(self):
        self.ok("new", "note", "Budget")
        out = self.ok("set", "budget", "part_of=project-v9")
        self.assertIn("notes/project-v9/budget.md:", out)
        self.assertTrue(self.exists("notes/project-v9/budget.md"))
        self.assertFalse(self.exists("notes/budget.md"))

    def test_check_notes_a_note_outside_its_parents_folder(self):
        self.write("notes/stray.md", "---\ntype: note\npart_of: project-v9\n---\n\n# Stray\n")
        self.write("archive/old.md", "---\ntype: note\npart_of: project-v9\n---\n\n# Old\n")
        out = self.pkm("check").stdout
        self.assertIn("notes/stray.md:3: part_of project-v9, so it belongs in notes/project-v9/: "
                      "pkm mv stray notes/project-v9", out)
        self.assertNotIn("archive/old.md", out)

    def test_without_the_setting_nothing_moves(self):
        self.write(".pkm/config", "")
        self.assertEqual(self.ok("new", "note", "Flat", "--set", "part_of=project-v9").strip(), "notes/flat.md")
        self.assertNotIn("belongs in", self.pkm("check").stdout)


if __name__ == "__main__":
    unittest.main()
