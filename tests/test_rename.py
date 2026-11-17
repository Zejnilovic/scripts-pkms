"""Tests for rename and mv: link forms rewritten outside code, display text kept, aliases, refusals, rollback that
restores every byte, the moves record, and the acceptance runs on temporary copies of the example vaults.
Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

JOHN = "---\ntype: person\n---\n\n# John Roe\n\n## Budget\n"
FORMS = """---
owner: "[[john-roe]]"
---

# Forms

[[john-roe]] and [[john-roe|John]]
[[john-roe#Budget]] and [[john-roe^b1]] and ![[john-roe]]
Met [[John Roe]] today, not [[Jane Doe]]
Code `[[john-roe]]` stays
~~[[john-roe|John]] left~~

```
[[john-roe]]
```
"""
FORMS_AFTER = """---
owner: "[[john-roe-finance]]"
---

# Forms

[[john-roe-finance]] and [[john-roe-finance|John]]
[[john-roe-finance#Budget]] and [[john-roe-finance^b1]] and ![[john-roe-finance]]
Met [[john-roe-finance|John Roe]] today, not [[Jane Doe]]
Code `[[john-roe]]` stays
~~[[john-roe-finance|John]] left~~

```
[[john-roe]]
```
"""


def snapshot(root):
    """Every file under root as bytes, except the cache, which pkm may fill in as a speed-up."""
    found = {}
    for path in sorted(pathlib.Path(root).rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith(".pkm/cache/"):
            found[rel] = path.read_bytes()
    return found


class RenameCase(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("people/john-roe.md", JOHN)
        self.write("people/jane-doe.md", "# Jane Doe\n")
        self.write("notes/forms.md", FORMS)
        self.write("notes/other.md", "Budget with [[john-roe]] and [[Jane Doe]]\n")


class RenameRewrites(RenameCase):
    def test_every_form_is_rewritten_outside_code_and_display_text_is_kept(self):
        self.ok("rename", "john-roe", "john-roe-finance")
        self.assertEqual(self.read("notes/forms.md"), FORMS_AFTER)
        self.assertEqual(self.read("notes/other.md"), "Budget with [[john-roe-finance]] and [[Jane Doe]]\n")
        self.assertFalse(self.exists("people/john-roe.md"))
        self.assertEqual(self.read("people/john-roe-finance.md"),
                         "---\ntype: person\naliases: [john-roe]\n---\n\n# John Roe\n\n## Budget\n")

    def test_no_alias_leaves_the_frontmatter_alone(self):
        self.ok("rename", "john-roe", "john-roe-finance", "--no-alias")
        self.assertEqual(self.read("people/john-roe-finance.md"), JOHN)

    def test_the_old_name_still_finds_the_note_through_its_alias(self):
        self.ok("rename", "john-roe", "john-roe-finance")
        self.assertEqual(self.ok("path", "john-roe").strip(), "people/john-roe-finance.md")
        self.assertEqual(self.ok("path", "john-roe-finance").strip(), "people/john-roe-finance.md")
        self.ok("check")

    def test_the_moves_record_gets_one_line(self):
        self.ok("rename", "john-roe", "john-roe-finance")
        self.assertEqual(self.read(".pkm/moves.tsv"), "2026-10-25\tjohn-roe\tjohn-roe-finance\n")

    def test_dry_run_lists_each_change_and_writes_nothing(self):
        before = snapshot(self.root)
        result = self.pkm("rename", "john-roe", "john-roe-finance", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("notes/other.md:1: Budget with [[john-roe]] and [[Jane Doe]] -> Budget with [[john-roe-finance]] and",
                      result.stdout)
        self.assertIn("notes/forms.md:9: ", result.stdout)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse(self.exists(".pkm/moves.tsv"))


class RenameRefusals(RenameCase):
    def test_a_taken_new_name_is_refused_and_nothing_is_written(self):
        before = snapshot(self.root)
        result = self.pkm("rename", "john-roe", "jane-doe")
        self.assertEqual(result.returncode, 1)
        self.assertIn("already uses the name jane-doe", result.stdout + result.stderr)
        self.assertEqual(snapshot(self.root), before)

    def test_a_missing_note_is_refused(self):
        before = snapshot(self.root)
        result = self.pkm("rename", "nobody-here", "someone")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(snapshot(self.root), before)

    def test_a_day_page_is_refused(self):
        self.write("daybook/2026/10/2026-10-25.md", "# 2026-10-25\n\n## Tasks\n\n## Log\n")
        before = snapshot(self.root)
        result = self.pkm("rename", "2026-10-25", "some-day")
        self.assertEqual(result.returncode, 1)
        self.assertIn("day page", result.stdout + result.stderr)
        self.assertEqual(snapshot(self.root), before)

    def test_a_bad_new_name_is_a_usage_error(self):
        before = snapshot(self.root)
        result = self.pkm("rename", "john-roe", "bad name")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(snapshot(self.root), before)


class RenameRollback(RenameCase):
    def test_a_failure_part_way_restores_every_byte(self):
        # Moves: notes/forms.md, notes/other.md, the note, then the note's content. Each point must roll back.
        for point in range(1, 5):
            with self.subTest(fail_after=point):
                before = snapshot(self.root)
                result = self.pkm("rename", "john-roe", "john-roe-finance", env={"PKM_RENAME_FAIL_AFTER": str(point)})
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("Every file is as it was.", result.stderr)
                self.assertEqual(snapshot(self.root), before)
                self.assertFalse(self.exists(".pkm/moves.tsv"))
                self.assertEqual(list(pathlib.Path(self.root, ".pkm").glob("rename.*")), [])


class MvCase(RenameCase):
    def test_mv_moves_the_note_into_a_folder_and_links_keep_working(self):
        self.write("notes/apollo.md", "# Apollo\n")
        self.write("notes/plan.md", "[[apollo]] is the plan\n")
        self.assertEqual(self.ok("mv", "apollo", "archive").strip(), "archive/apollo.md")
        self.assertFalse(self.exists("notes/apollo.md"))
        self.assertTrue(self.exists("archive/apollo.md"))
        self.assertEqual(self.read("notes/plan.md"), "[[apollo]] is the plan\n")
        self.assertEqual(self.ok("path", "apollo").strip(), "archive/apollo.md")
        self.ok("check")
        self.assertEqual(self.read(".pkm/moves.tsv"), "2026-10-25\tnotes/apollo.md\tarchive/apollo.md\n")

    def test_mv_refuses_a_name_already_there_and_a_folder_outside_the_vault(self):
        before = snapshot(self.root)
        self.assertEqual(self.pkm("mv", "john-roe", "people").returncode, 1)
        self.assertEqual(self.pkm("mv", "john-roe", "../elsewhere").returncode, 2)
        self.assertEqual(snapshot(self.root), before)


class PathArguments(RenameCase):
    def test_mv_takes_a_vault_path_with_or_without_md(self):
        self.write("archive/.keep", "")
        self.assertEqual(self.ok("mv", "people/jane-doe.md", "archive").strip(), "archive/jane-doe.md")
        self.assertTrue(self.exists("archive/jane-doe.md"))
        self.assertEqual(self.ok("mv", "archive/jane-doe", "people").strip(), "people/jane-doe.md")

    def test_rename_takes_a_vault_path(self):
        self.ok("rename", "people/john-roe.md", "john-roe-finance")
        self.assertTrue(self.exists("people/john-roe-finance.md"))
        self.assertIn("[[john-roe-finance]]", self.read("notes/other.md"))

    def test_a_missing_path_is_still_no_single_note(self):
        result = self.pkm("mv", "notes/nothing-here.md", "archive")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No single note is named notes/nothing-here.md.", result.stderr)


class DryRunAliasLine(RenameCase):
    def test_an_added_alias_line_shows_as_it_will_be_written(self):
        self.write("notes/statistics-101.md", "---\ntype: source\nsummary: a course\nstatus: active\n---\n# Statistics\n")
        result = self.pkm("rename", "statistics-101", "stats-101", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("notes/statistics-101.md:5: + aliases: [statistics-101]", result.stdout.splitlines())
        self.assertNotIn("->", result.stdout)


class CrlfNotes(RenameCase):
    """Notes saved with Windows line endings: every line rename writes ends the same way the note did."""

    def put(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def assert_all_crlf(self, data):
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), data)

    def test_rename_keeps_crlf_on_the_alias_list_and_the_rewritten_links(self):
        self.put("people/jane-doe.md", b"---\r\ntype: person\r\naliases: [Jane]\r\n---\r\n# Jane Doe\r\n\r\nSee [[jane-doe]]\r\n")
        self.put("notes/link.md", b"Met [[jane-doe]] today\r\n- [[jane-doe|Jane]]\r\n")
        self.ok("rename", "jane-doe", "jane-roe")
        note = (self.root / "people/jane-roe.md").read_bytes()
        self.assertEqual(note, b"---\r\ntype: person\r\naliases: [Jane, jane-doe]\r\n---\r\n# Jane Doe\r\n\r\nSee [[jane-roe]]\r\n")
        self.assert_all_crlf(note)
        link = (self.root / "notes/link.md").read_bytes()
        self.assertEqual(link, b"Met [[jane-roe]] today\r\n- [[jane-roe|Jane]]\r\n")

    def test_rename_adds_crlf_alias_lines_to_a_crlf_note_without_aliases(self):
        self.put("people/bob.md", b"---\r\ntype: person\r\n---\r\n# Bob\r\n")
        self.ok("rename", "bob", "bob-smith")
        note = (self.root / "people/bob-smith.md").read_bytes()
        self.assertEqual(note, b"---\r\ntype: person\r\naliases: [bob]\r\n---\r\n# Bob\r\n")
        self.assert_all_crlf(note)

    def test_rename_dry_run_shows_a_crlf_line_without_its_carriage_return(self):
        self.put("people/jane-doe.md", b"---\r\ntype: person\r\naliases: [Jane]\r\n---\r\n# Jane Doe\r\n")
        self.put("notes/link.md", b"Met [[jane-doe]] today\r\n")
        result = self.pkm("rename", "jane-doe", "jane-roe", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("\r", result.stdout)
        self.assertIn("notes/link.md:1: Met [[jane-doe]] today -> Met [[jane-roe]] today", result.stdout.splitlines())

    def test_mv_keeps_a_crlf_note_byte_for_byte(self):
        data = b"---\r\ntype: person\r\n---\r\n# Jane Doe\r\n\r\nNotes\r\n"
        self.put("people/jane-doe.md", data)
        self.ok("mv", "jane-doe", "archive")
        self.assertEqual((self.root / "archive/jane-doe.md").read_bytes(), data)


class ExampleCopies(unittest.TestCase):
    """Runs rename and mv on temporary copies of the example vaults; the examples are never changed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._config = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self._tmp.name)
        self.config_home = self._config.name

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def copy(self, name):
        vault = self.base / name
        shutil.copytree(REPO / "docs/examples" / name, vault)
        return vault

    def pkm(self, vault, *args, env=None):
        environment = pkm_env(PKM_NOW="20261116090500", XDG_CONFIG_HOME=self.config_home, **(env or {}))
        return run_pkm(args, cwd=vault, env=environment, vault=vault)

    def test_work_rename_rewrites_every_link_to_john_roe_and_nothing_else(self):
        vault = self.copy("work")
        original = snapshot(vault)
        before = self.pkm(vault, "backlinks", "john-roe").stdout
        self.assertTrue(before.strip())
        result = self.pkm(vault, "rename", "john-roe", "john-roe-finance")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        now = snapshot(vault)
        self.assertFalse((vault / "notes/john-roe.md").exists())
        self.assertTrue((vault / "notes/john-roe-finance.md").exists())
        for rel, data in original.items():
            if rel.startswith(".pkm/"):
                continue
            expected = data.decode().replace("[[john-roe", "[[john-roe-finance")
            if rel == "notes/john-roe.md":
                body = expected.split("---", 2)[2]
                self.assertEqual(now["notes/john-roe-finance.md"].decode().split("---", 2)[2], body)
                self.assertIn("aliases: [John, John Roe, john-roe]\n", now["notes/john-roe-finance.md"].decode())
                continue
            self.assertEqual(now[rel].decode(), expected, rel)
        self.assertEqual(self.pkm(vault, "check").returncode, 0)
        after = self.pkm(vault, "backlinks", "john-roe-finance").stdout
        self.assertEqual(sorted(line.split(":")[0:2].__str__() for line in after.splitlines()),
                         sorted(line.split(":")[0:2].__str__() for line in before.splitlines()))

    def test_work_mv_apollo_to_archive_keeps_path_and_check_clean(self):
        vault = self.copy("work")
        self.assertEqual(self.pkm(vault, "mv", "apollo", "archive").returncode, 0)
        self.assertTrue((vault / "archive/apollo.md").exists())
        self.assertFalse((vault / "notes/apollo.md").exists())
        self.assertEqual(self.pkm(vault, "path", "apollo").stdout.strip(), "archive/apollo.md")
        self.assertEqual(self.pkm(vault, "check").returncode, 0)

    def test_family_dry_run_lists_bathroom_line_twelve_and_writes_nothing(self):
        vault = self.copy("family")
        before = snapshot(vault)
        result = self.pkm(vault, "rename", "joe-bloggs-plumber", "joe-bloggs-plumbing", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("notes/bathroom.md:12: ", result.stdout)
        self.assertEqual(snapshot(vault), before)


if __name__ == "__main__":
    unittest.main()
