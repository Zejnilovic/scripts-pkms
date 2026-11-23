"""Items in a tool: the repo template, [[note]]#42 as an item of a note's items line, pkm url, links --external, check
and overview. pkm only prints addresses; nothing here goes online. Run: python3 -m unittest discover -s tests.
Names and data are made up. NOW is 2026-10-25 14:30.
"""

import json

from helpers import VaultCase

ITEMS = "https://github.com/acme-example/apollo-web/issues/"
URL = "https://github.com/acme-example/apollo-web"
REPO = (f"---\ntype: repo\npart_of: apollo\nurl: {URL}\nitems: {ITEMS}\naliases: [portal]\n---\n\n"
        "# apollo-web\n\n## Now\n\n## Decisions\n\n## Notes\n")
APOLLO = "---\ntype: project\nstatus: active\n---\n\n# Apollo\n"
JANE = "---\ntype: person\n---\n\n# Jane Doe\n"
DAY = ("# 2026-10-25\n\n## Tasks\n\n- [ ] Review [[apollo-web]]#51\n\n## Log\n\n"
       "- 10:15 Reviewed [[apollo-web]]#42, needs a test\n"
       "- 10:20 See [[apollo-web#Risks]]#7 and `[[apollo-web]]#8`\n"
       "- 10:30 [[apollo-web|the portal]]#43 and [[apollo-web]]#44 both\n")


class ItemsCase(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo-web.md", REPO)
        self.write("notes/apollo.md", APOLLO)
        self.write("notes/jane-doe.md", JANE)


class RepoTemplate(VaultCase):
    def test_new_repo_has_its_type_keys_and_sections(self):
        out = self.ok("new", "repo", "apollo-web").strip()
        self.assertEqual(out, "notes/apollo-web.md")
        text = self.read("notes/apollo-web.md")
        for key in ["type: repo\n", "part_of:\n", "url:\n", "items:\n"]:
            self.assertIn(key, text)
        for section in ["## Now", "## Decisions", "## Notes"]:
            self.assertIn("\n" + section + "\n", text)

    def test_an_empty_repo_note_has_no_problems(self):
        self.ok("new", "repo", "apollo-web")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)


class Url(ItemsCase):
    def test_an_item_is_items_and_the_number(self):
        for ref in ["[[apollo-web]]#42", "[[apollo-web|the portal]]#42", "apollo-web#42", "[[portal]]#42"]:
            self.assertEqual(self.ok("url", ref), ITEMS + "42\n", ref)

    def test_a_note_or_a_link_gives_its_url(self):
        for ref in ["apollo-web", "[[apollo-web]]", "portal"]:
            self.assertEqual(self.ok("url", ref), URL + "\n", ref)

    def test_a_quoted_value_works(self):
        self.write("notes/apollo-web.md", REPO.replace(f"items: {ITEMS}", f'items: "{ITEMS}"'))
        self.assertEqual(self.ok("url", "[[apollo-web]]#42"), ITEMS + "42\n")

    def test_a_note_without_items_or_url_fails(self):
        result = self.pkm("url", "[[jane-doe]]#3")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("items", result.stderr)
        result = self.pkm("url", "jane-doe")
        self.assertEqual(result.returncode, 1)
        self.assertIn("url", result.stderr)

    def test_an_unknown_note_fails(self):
        result = self.pkm("url", "[[nobody]]#3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("nobody", result.stderr)

    def test_only_web_addresses_are_printed(self):
        for value in ["javascript:alert(1)", "file:///etc/passwd", "https://a.example/ b"]:
            self.write("notes/apollo-web.md", REPO.replace(f"items: {ITEMS}", f"items: {value}"))
            result = self.pkm("url", "[[apollo-web]]#42")
            self.assertEqual(result.returncode, 1, value)
            self.assertEqual(result.stdout, "", value)

    def test_a_section_link_is_not_an_item(self):
        result = self.pkm("url", "[[apollo-web#Risks]]#7")
        self.assertEqual(result.returncode, 2)

    def test_no_argument_is_a_usage_error(self):
        self.assertEqual(self.pkm("url").returncode, 2)


class Links(ItemsCase):
    def setUp(self):
        super().setUp()
        self.write("daybook/2026/10/2026-10-25.md", DAY)

    def test_items_are_listed_by_their_address(self):
        out = self.ok("links", "--external")
        page = "daybook/2026/10/2026-10-25.md"
        for line in [f"{page}:5: {ITEMS}51", f"{page}:9: {ITEMS}42", f"{page}:11: {ITEMS}43", f"{page}:11: {ITEMS}44"]:
            self.assertIn(line, out)

    def test_a_section_link_or_code_is_not_an_item(self):
        out = self.ok("links", "--external")
        self.assertNotIn(ITEMS + "7", out)
        self.assertNotIn(ITEMS + "8", out)

    def test_items_follow_the_listing_order(self):
        lines = [line for line in self.ok("links", "--external").splitlines() if line.startswith("daybook/")]
        self.assertEqual(lines, sorted(lines, key=lambda l: int(l.split(":")[1])))

    def test_the_item_line_is_a_backlink(self):
        self.assertIn("daybook/2026/10/2026-10-25.md:9:", self.ok("backlinks", "apollo-web"))


class Check(ItemsCase):
    def test_items_of_a_note_with_items_are_fine(self):
        self.write("daybook/2026/10/2026-10-25.md", DAY)
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_an_item_of_a_note_without_items_is_a_problem(self):
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n## Log\n\n- 10:15 Asked [[jane-doe]]#3\n")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("- daybook/2026/10/2026-10-25.md:5: [[jane-doe]]#3 is an item, but jane-doe has no items line", result.stdout)

    def test_an_item_of_a_missing_note_is_only_a_broken_link(self):
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n## Log\n\n- 10:15 Asked [[nobody]]#3\n")
        result = self.pkm("check")
        self.assertIn("broken link [[nobody]]", result.stdout)
        self.assertNotIn("is an item", result.stdout)

    def test_a_value_that_is_not_a_web_address_is_a_problem(self):
        self.write("notes/apollo-web.md", REPO.replace(f"items: {ITEMS}", "items: javascript:alert(1)")
                   .replace(f"url: {URL}", "url: github.com/acme-example/apollo-web"))
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("- notes/apollo-web.md:4: url is not one http:// or https:// address", result.stdout)
        self.assertIn("- notes/apollo-web.md:5: items is not one http:// or https:// address", result.stdout)


class Overview(ItemsCase):
    def test_a_repo_without_a_parent_is_with_the_projects(self):
        self.write("notes/apollo-web.md", REPO.replace("part_of: apollo\n", ""))
        records = [json.loads(line) for line in self.ok("overview", "--json").splitlines()]
        repo = [r for r in records if r["path"] == "notes/apollo-web.md"]
        self.assertEqual(len(repo), 1)
        self.assertEqual((repo[0]["kind"], repo[0]["type"], repo[0]["depth"]), ("project", "repo", 0))

    def test_a_repo_with_a_parent_is_under_it(self):
        records = [json.loads(line) for line in self.ok("overview", "--json").splitlines()]
        repo = [r for r in records if r["path"] == "notes/apollo-web.md"]
        self.assertEqual((repo[0]["parent"], repo[0]["depth"]), ("notes/apollo.md", 1))

    def test_an_archived_repo_is_left_out(self):
        self.write("notes/apollo-web.md", REPO.replace("part_of: apollo\n", "status: archived\n"))
        self.assertNotIn("apollo-web", self.ok("overview"))
