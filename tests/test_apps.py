"""Applications and teams: the app and team templates, repositories and projects part_of an app, an app's IDs as
aliases, a key of the owner's own, and overview. Run: python3 -m unittest discover -s tests.
Names and data are made up. NOW is 2026-10-25 14:30.
"""

import json

from helpers import VaultCase

APP = ("---\ntype: app\nsummary: The ordering portal of Acme\naliases: [Acme Portal, APP-1001, CI-2002]\n---\n\n"
       "# Acme Portal\n\n## Now\n\n## Links\n\n## Decisions\n\n## Notes\n")
REPO = ("---\ntype: repo\npart_of: acme-portal\nitems: https://github.com/acme-example/apollo-web/issues/\n---\n\n"
        "# apollo-web\n")
PROJECT = "---\ntype: project\nstatus: active\npart_of: acme-portal\n---\n\n# Apollo\n"
DAY = ("# 2026-10-25\n\n## Tasks\n\n- [ ] Review [[apollo-web]]#51\n- [ ] Book the [[apollo]] demo\n"
       "- [ ] Send the timesheet\n\n## Log\n\n- 10:15 [[APP-1001]] has a slow login, [[jane-doe]] looks at it\n")


class Templates(VaultCase):
    def test_new_app_has_its_type_keys_and_sections(self):
        self.assertEqual(self.ok("new", "app", "Acme Portal").strip(), "notes/acme-portal.md")
        text = self.read("notes/acme-portal.md")
        for key in ["type: app\n", "part_of:\n", "url:\n", "items:\n", "aliases: [Acme Portal]\n"]:
            self.assertIn(key, text)
        for section in ["## Now", "## Links", "## Decisions", "## Notes"]:
            self.assertIn("\n" + section + "\n", text)

    def test_new_team_has_its_type_keys_and_sections(self):
        self.assertEqual(self.ok("new", "team", "Web team").strip(), "notes/web-team.md")
        text = self.read("notes/web-team.md")
        for key in ["type: team\n", "part_of:\n", "url:\n", "aliases: [Web team]\n"]:
            self.assertIn(key, text)
        for section in ["## Now", "## Next time", "## People", "## Links", "## Notes"]:
            self.assertIn("\n" + section + "\n", text)

    def test_the_templates_name_no_key_of_one_employer(self):
        for kind in ["app", "team"]:
            self.ok("new", kind, f"Some {kind}")
            keys = [line.split(":")[0] for line in self.read(f"notes/some-{kind}.md").split("---")[1].splitlines() if line]
            self.assertEqual(set(keys) - {"type", "part_of", "url", "items", "summary", "aliases", "created"}, set())

    def test_empty_app_and_team_notes_have_no_problems(self):
        self.ok("new", "app", "Acme Portal")
        self.ok("new", "team", "Web team")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)


class AppTree(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/acme-portal.md", APP)
        self.write("notes/apollo-web.md", REPO)
        self.write("notes/apollo.md", PROJECT)
        self.write("notes/jane-doe.md", "---\ntype: person\n---\n\n# Jane Doe\n")
        self.write("daybook/2026/10/2026-10-25.md", DAY)

    def test_tasks_under_the_app_has_those_of_its_repo_and_its_project(self):
        out = self.ok("tasks", "--under", "acme-portal")
        self.assertIn("Review [[apollo-web]]#51", out)
        self.assertIn("Book the [[apollo]] demo", out)
        self.assertNotIn("timesheet", out)

    def test_backlinks_of_the_app_has_what_belongs_to_it_and_a_line_that_links_an_id(self):
        out = self.ok("backlinks", "acme-portal")
        self.assertIn("notes/apollo-web.md:3: part_of: acme-portal", out)
        self.assertIn("notes/apollo.md:4: part_of: acme-portal", out)
        self.assertIn("daybook/2026/10/2026-10-25.md:11:", out)

    def test_each_id_in_aliases_names_the_app(self):
        for name in ["APP-1001", "CI-2002", "Acme Portal"]:
            self.assertEqual(self.ok("path", name), "notes/acme-portal.md\n")
        self.assertEqual(self.pkm("check").returncode, 0)

    def test_since_under_the_app_has_the_day_line_about_it(self):
        self.assertIn("[[APP-1001]] has a slow login", self.ok("since", "2026-10-25", "--under", "acme-portal"))

    def test_overview_shows_the_app_with_the_projects_and_its_notes_under_it(self):
        records = {r["path"]: r for r in (json.loads(line) for line in self.ok("overview", "--json").splitlines())
                   if r.get("path")}
        app = records["notes/acme-portal.md"]
        self.assertEqual((app["kind"], app["type"], app["depth"]), ("project", "app", 0))
        for path in ["notes/apollo.md", "notes/apollo-web.md"]:
            self.assertEqual((records[path]["parent"], records[path]["depth"]), ("notes/acme-portal.md", 1))

    def test_a_done_app_is_left_out_of_overview(self):
        self.write("notes/acme-portal.md", APP.replace("type: app\n", "type: app\nstatus: archived\n"))
        self.assertNotIn("notes/acme-portal.md", self.pkm("overview").stdout)


class OwnKeys(VaultCase):
    def test_list_finds_a_value_of_a_key_of_your_own_also_in_a_list(self):
        self.write("notes/apollo-web.md", "---\ntype: repo\nasset_id: [CI-2002, CI-3003]\n---\n\n# apollo-web\n")
        self.write("notes/apollo-api.md", "---\ntype: repo\nasset_id:\n  - CI-2002\n---\n\n# apollo-api\n")
        self.write("notes/billing.md", "---\ntype: repo\nasset_id: CI-4004\n---\n\n# billing\n")
        out = self.ok("list", "asset_id=CI-2002")
        self.assertIn("notes/apollo-web.md", out)
        self.assertIn("notes/apollo-api.md", out)
        self.assertNotIn("billing", out)

    def test_a_part_of_an_id_matches_nothing(self):
        self.write("notes/apollo-web.md", "---\ntype: repo\nasset_id: [CI-2002, CI-3003]\n---\n\n# apollo-web\n")
        self.assertNotIn("apollo-web", self.pkm("list", "asset_id=CI-20").stdout)
