"""Where a note belongs: the area template, part_of as a link (backlinks, check, rename, the cache), todo --in,
add --file and overview. Run: python3 -m unittest discover -s tests. Names are made up. NOW is 2026-10-25 14:30.
"""

import json
import pathlib
import tempfile

from helpers import VaultCase

HOME = "---\ntype: area\nsummary: Our flat\n---\n\n# Home\n\n## Now\n\n## Routines\n\n- [ ] Rent (due 2026-12-01) (every 1m)\n\n## People\n"
BATHROOM = "---\ntype: project\nstatus: active\npart_of: home\n---\n\n# Bathroom\n"


class AreaTemplate(VaultCase):
    def test_new_area_has_its_type_and_sections(self):
        out = self.ok("new", "area", "Home").strip()
        self.assertEqual(out, "notes/home.md")
        text = self.read("notes/home.md")
        self.assertIn("type: area\n", text)
        self.assertIn("part_of:\n", text)
        for section in ["## Now", "## Routines", "## People", "## Links", "## Ideas"]:
            self.assertIn("\n" + section + "\n", text)

    def test_an_empty_part_of_is_no_link_and_no_problem(self):
        self.ok("new", "project", "Apollo")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.pkm("backlinks", "part_of").returncode, 1)


class PartOfIsALink(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/home.md", HOME)
        self.write("notes/bathroom.md", BATHROOM)

    def test_backlinks_list_the_part_of_line(self):
        out = self.ok("backlinks", "home")
        self.assertIn("notes/bathroom.md:4: part_of: home", out)

    def test_the_link_form_counts_once(self):
        self.write("notes/bathroom.md", BATHROOM.replace("part_of: home", 'part_of: "[[home]]"'))
        lines = [line for line in self.ok("backlinks", "home").splitlines() if line.startswith("notes/bathroom.md")]
        self.assertEqual(lines, ['notes/bathroom.md:4: part_of: "[[home]]"'])

    def test_an_alias_or_a_title_finds_the_parent(self):
        self.write("notes/home.md", HOME.replace("summary: Our flat", "summary: Our flat\naliases: [Our Flat]"))
        self.write("notes/bathroom.md", BATHROOM.replace("part_of: home", "part_of: Our Flat"))
        self.assertIn("notes/bathroom.md:4: part_of: Our Flat", self.ok("backlinks", "home"))

    def test_check_flags_a_parent_that_does_not_exist(self):
        self.write("notes/bathroom.md", BATHROOM.replace("part_of: home", "part_of: house"))
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("- notes/bathroom.md:4: broken link [[house]]", result.stdout)

    def test_check_flags_more_than_one_parent(self):
        self.write("notes/car.md", "---\ntype: area\n---\n\n# Car\n")
        self.write("notes/bathroom.md", BATHROOM.replace("part_of: home", "part_of: [home, car]"))
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("- notes/bathroom.md:4: part_of names one note: keep one, and link the others", result.stdout)

    def test_check_flags_a_note_that_is_part_of_itself(self):
        self.write("notes/bathroom.md", BATHROOM.replace("part_of: home", "part_of: bathroom"))
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("- notes/bathroom.md:4: part_of names the note itself", result.stdout)

    def test_check_flags_a_circle(self):
        self.write("notes/home.md", HOME.replace("type: area", "type: area\npart_of: bathroom"))
        result = self.pkm("check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("part_of goes round in a circle: bathroom, home, bathroom", result.stdout)

    def test_rename_rewrites_part_of(self):
        self.ok("rename", "home", "flat")
        self.assertIn("\npart_of: flat\n", self.read("notes/bathroom.md"))
        self.assertEqual(self.pkm("check").returncode, 0)

    def test_rename_keeps_the_link_form(self):
        self.write("notes/bathroom.md", BATHROOM.replace("part_of: home", 'part_of: "[[home]]"'))
        self.ok("rename", "home", "flat")
        self.assertIn('\npart_of: "[[flat]]"\n', self.read("notes/bathroom.md"))

    def test_rename_dry_run_lists_the_part_of_line(self):
        out = self.ok("rename", "home", "flat", "--dry-run")
        self.assertIn("notes/bathroom.md:4: part_of: home -> part_of: flat", out)

    def test_an_older_cache_is_read_again(self):
        self.ok("index")
        cache = self.root / ".pkm/cache"
        (cache / "version").unlink()
        links = (cache / "links.tsv").read_text().splitlines()
        (cache / "links.tsv").write_text("".join(line + "\n" for line in links if "\thome" not in line))
        self.assertIn("notes/bathroom.md:4: part_of: home", self.ok("backlinks", "home"))


class TodoIn(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/home.md", HOME)

    def test_a_routine_goes_to_the_notes_routines_section(self):
        out = self.ok("todo", "Service the boiler", "--every", "1y", "--due", "2027-03-01", "--in", "home").strip()
        self.assertEqual(out, "notes/home.md:13")
        lines = self.read("notes/home.md").splitlines()
        self.assertEqual(lines[12], "- [ ] Service the boiler (due 2027-03-01) (every 1y)")
        self.assertEqual(lines[14], "## People")
        self.assertFalse(self.exists("notes/routines.md"))

    def test_a_missing_routines_section_is_made(self):
        self.write("notes/car.md", "---\ntype: area\n---\n\n# Car\n")
        out = self.ok("todo", "Renew the insurance", "--every", "1y", "--due", "2027-05-10", "--in", "car").strip()
        self.assertEqual(out, "notes/car.md:9")
        self.assertTrue(self.read("notes/car.md").endswith("# Car\n\n## Routines\n\n- [ ] Renew the insurance (due 2027-05-10) (every 1y)\n"))

    def test_the_note_is_found_by_alias(self):
        self.write("notes/home.md", HOME.replace("summary: Our flat", "summary: Our flat\naliases: [Flat]"))
        out = self.ok("todo", "Service the boiler", "--every", "1y", "--in", "Flat").strip()
        self.assertTrue(out.startswith("notes/home.md:"), out)

    def test_in_needs_a_routine(self):
        result = self.pkm("todo", "Call Jane", "--in", "home")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--in", result.stderr)

    def test_in_needs_a_note_that_exists(self):
        result = self.pkm("todo", "Service the boiler", "--every", "1y", "--in", "house")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No note named house", result.stderr)

    def test_in_refuses_a_day_page(self):
        self.ok("day")
        result = self.pkm("todo", "Water plants", "--every", "1w", "--in", "2026-10-25")
        self.assertEqual(result.returncode, 1)
        self.assertIn("day page", result.stderr)

    def test_a_routine_in_a_note_is_a_task(self):
        self.ok("todo", "Service the boiler", "--every", "1y", "--due", "2026-10-30", "--in", "home")
        self.assertIn("notes/home.md:13", self.ok("tasks"))


class AddFile(VaultCase):
    def setUp(self):
        super().setUp()
        self._outside = tempfile.TemporaryDirectory()
        self.outside = pathlib.Path(self._outside.name)
        (self.outside / "Pipes Quote.PDF").write_bytes(b"%PDF-1.4 made up\n")

    def tearDown(self):
        self._outside.cleanup()
        super().tearDown()

    def test_the_file_is_copied_and_linked_from_todays_page(self):
        source = self.outside / "Pipes Quote.PDF"
        out = self.ok("add", "--file", str(source), "Quote from [[joe-bloggs]]").strip()
        self.assertEqual(out, "daybook/2026/10/2026-10-25.md:7")
        copied = self.root / "files/2026/10/2026-10-25-pipes-quote.pdf"
        self.assertEqual(copied.read_bytes(), b"%PDF-1.4 made up\n")
        self.assertTrue(source.exists())
        page = self.read("daybook/2026/10/2026-10-25.md").splitlines()
        self.assertEqual(page[6], "- 14:30 Quote from [[joe-bloggs]]: [pipes-quote.pdf](../../../files/2026/10/2026-10-25-pipes-quote.pdf)")

    def test_without_text_the_entry_is_the_link(self):
        self.ok("add", "--file", str(self.outside / "Pipes Quote.PDF"))
        self.assertIn("- 14:30 [pipes-quote.pdf](../../../files/2026/10/2026-10-25-pipes-quote.pdf)\n",
                      self.read("daybook/2026/10/2026-10-25.md"))

    def test_another_day_files_it_in_that_days_month(self):
        out = self.ok("add", "--day", "2026-09-30", "--file", str(self.outside / "Pipes Quote.PDF"), "Quote").strip()
        self.assertEqual(out.split(":")[0], "daybook/2026/09/2026-09-30.md")
        self.assertTrue(self.exists("files/2026/09/2026-09-30-pipes-quote.pdf"))

    def test_an_existing_file_is_never_overwritten(self):
        self.write("files/2026/10/2026-10-25-pipes-quote.pdf", "older\n")
        result = self.pkm("add", "--file", str(self.outside / "Pipes Quote.PDF"), "Quote")
        self.assertEqual(result.returncode, 1)
        self.assertIn("files/2026/10/2026-10-25-pipes-quote.pdf", result.stderr)
        self.assertEqual(self.read("files/2026/10/2026-10-25-pipes-quote.pdf"), "older\n")
        self.assertFalse(self.exists("daybook/2026/10/2026-10-25.md"))

    def test_a_missing_file_is_a_wrong_call(self):
        result = self.pkm("add", "--file", str(self.outside / "nope.pdf"), "Quote")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.exists("daybook/2026/10/2026-10-25.md"))

    def test_a_file_goes_with_one_line_only(self):
        result = self.pkm("add", "--file", str(self.outside / "Pipes Quote.PDF"), "-", stdin="one\ntwo\n")
        self.assertEqual(result.returncode, 2)

    def test_check_stays_clean(self):
        self.ok("add", "--file", str(self.outside / "Pipes Quote.PDF"), "Quote")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)


class Overview(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/home.md", HOME)
        self.write("notes/bathroom.md", BATHROOM)
        self.write("notes/groceries.md", "---\ntype: list\npart_of: home\n---\n\n# Groceries\n")
        self.write("notes/learning.md", "---\ntype: area\n---\n\n# Learning\n")
        self.write("notes/mba.md", "---\ntype: project\nstatus: idea\npart_of: learning\n---\n\n# MBA\n")
        self.write("notes/strategy.md", "---\ntype: course\nstatus: active\npart_of: mba\n---\n\n# Strategy\n")
        self.write("notes/apollo.md", "---\ntype: project\nstatus: active\n---\n\n# Apollo\n")
        self.write("notes/old-release.md", "---\ntype: project\nstatus: done\n---\n\n# Old release\n")
        self.write("notes/statistics.md", "---\ntype: course\nstatus: active\n---\n\n# Statistics\n")
        self.write("notes/jane-doe.md", "---\ntype: person\n---\n\n# Jane Doe\n")
        self.write("archive/balcony.md", "---\ntype: project\nstatus: done\npart_of: home\n---\n\n# Balcony\n")

    def test_the_sections_and_the_tree(self):
        out = self.ok("overview")
        self.assertEqual(out.splitlines(), [
            "== areas",
            "notes/home.md:6: Home (area)",
            "notes/bathroom.md:7: Home / Bathroom (project, active)",
            "notes/groceries.md:6: Home / Groceries (list)",
            "notes/learning.md:5: Learning (area)",
            "notes/mba.md:7: Learning / MBA (project, idea)",
            "notes/strategy.md:7: Learning / MBA / Strategy (course, active)",
            "== projects",
            "notes/apollo.md:6: Apollo (project, active)",
            "== resources",
            "notes/statistics.md:6: Statistics (course, active)",
            "== archive",
            "1 note in archive/",
        ])

    def test_json_gives_kind_depth_and_parent(self):
        records = [json.loads(line) for line in self.ok("overview", "--json").splitlines()]
        self.assertEqual(records[1], {"kind": "area", "path": "notes/bathroom.md", "line": 7,
                                      "text": "Home / Bathroom (project, active)", "type": "project",
                                      "status": "active", "parent": "notes/home.md", "depth": 1})
        self.assertEqual(records[0]["parent"], None)
        self.assertEqual(records[-1], {"kind": "archive", "path": None, "line": None,
                                       "text": "1 note in archive/", "count": 1})

    def test_a_note_under_a_parent_of_another_kind_is_shown_under_it(self):
        self.write("notes/gift-ideas.md", "---\ntype: list\npart_of: jane-doe\n---\n\n# Gift ideas\n")
        out = self.ok("overview").splitlines()
        i = out.index("== other")
        self.assertEqual(out[i + 1:i + 3], ["notes/jane-doe.md:5: Jane Doe (person)",
                                            "notes/gift-ideas.md:6: Jane Doe / Gift ideas (list)"])

    def test_a_circle_never_loops(self):
        self.write("notes/home.md", HOME.replace("type: area", "type: area\npart_of: bathroom"))
        result = self.pkm("overview")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Home", result.stdout)

    def test_an_empty_vault_has_nothing_to_show(self):
        for path in self.root.joinpath("notes").iterdir():
            path.unlink()
        self.root.joinpath("archive/balcony.md").unlink()
        result = self.pkm("overview")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
