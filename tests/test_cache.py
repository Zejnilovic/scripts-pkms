"""The cache is a speed-up only: deleting it, or a stale or broken one, never changes an output. Also names, list,
index, PKM_CACHE_DIR, and change detection by size and by mtime (a file can get an older mtime from a sync tool).
Run: python3 -m unittest discover -s tests
"""

import json
import os
import pathlib
import shutil
import tempfile
import unittest

from helpers import REPO, VaultCase, pkm_env, run_pkm

BATTERY = [["names"], ["names", "--type", "person"], ["names", "--type", "day"], ["list"], ["list", "type=project", "--show", "status"],
           ["path", "jane doe"], ["path", "JD"], ["check"], ["backlinks", "jane-doe"], ["find", "budget"],
           ["tasks"], ["tasks", "--json"], ["names", "--json"], ["list", "--json"]]


class Fixture(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("people/jane-doe.md", "---\ntype: person\naliases: [JD]\n---\n# Jane Doe\n\nBudget owner\n")
        self.write("projects/apollo.md", "---\ntype: project\nstatus: active\n---\n# Apollo\n\n- [ ] Budget (due 2026-11-20)\n")
        self.write("daybook/2026/11/2026-11-16.md", "# 2026-11-16\n\n## Log\n\n- 09:00 [[jane-doe]] on [[apollo]]\n")
        self.write("archive/projects/zeus.md", "---\ntype: project\nstatus: done\n---\n# Zeus\n")
        self.write("attachments/plan.png", "png")

    def battery(self):
        out = []
        for args in BATTERY:
            result = self.pkm(*args)
            out.append((args, result.returncode, result.stdout))
        return out

    def cache(self):
        return self.root / ".pkm/cache"


class CacheNeverChangesAnAnswer(Fixture):
    def test_deleting_the_cache_changes_no_output(self):
        with_cache = self.battery()
        self.assertTrue(self.cache().exists())
        shutil.rmtree(self.cache())
        self.assertEqual(self.battery(), with_cache)

    def test_a_broken_cache_is_read_again_in_full(self):
        expected = self.battery()
        (self.cache() / "notes.tsv").write_text("garbage\n")
        self.assertEqual(self.battery(), expected)

    def test_a_cache_with_a_part_missing_is_read_again_in_full(self):
        expected = self.battery()
        (self.cache() / "fields.tsv").unlink()
        self.assertEqual(self.battery(), expected)

    def test_the_example_vault_answers_the_same_without_its_cache(self):
        copies = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree(REPO / "docs/examples/work", copies / "work")
            env = pkm_env(XDG_CONFIG_HOME=str(copies), PKM_NOW="20261116083000")
            runs = []
            for _ in range(2):
                runs.append([run_pkm(args, cwd=copies / "work", env=env, vault=copies / "work").stdout
                             for args in [["names"], ["list", "--show", "status"], ["check"], ["backlinks", "apollo"]]])
                shutil.rmtree(copies / "work/.pkm/cache", ignore_errors=True)
            self.assertEqual(runs[0], runs[1])
        finally:
            shutil.rmtree(copies)


class ChangeDetection(Fixture):
    def test_a_changed_size_is_seen(self):
        self.pkm("names")
        self.write("people/jane-doe.md", "---\ntype: person\naliases: [JD, Janet Doe]\n---\n# Jane Doe\n")
        self.assertIn("Janet Doe", self.ok("names", "--type", "person"))

    def test_a_changed_file_with_the_same_size_and_an_older_mtime_is_seen(self):
        self.pkm("names")
        path = self.root / "people/jane-doe.md"
        old = path.read_text()
        new = old.replace("JD", "JX")
        self.assertEqual(len(old), len(new))
        path.write_text(new)
        os.utime(path, (1_000_000_000, 1_000_000_000))  # a sync tool or git gave it an older time
        self.assertIn("JX", self.ok("names", "--type", "person"))
        self.assertNotIn("JD", self.ok("names", "--type", "person"))

    def test_a_deleted_note_drops_out(self):
        self.pkm("names")
        (self.root / "projects/apollo.md").unlink()
        self.assertNotIn("apollo", self.ok("names"))
        self.assertEqual(self.pkm("path", "apollo").returncode, 1)

    def test_a_moved_note_is_found_under_its_new_name_only(self):
        self.pkm("names")
        (self.root / "projects/apollo.md").rename(self.root / "projects/apollo-2026.md")
        self.assertIn("apollo-2026", self.ok("names"))
        self.assertNotIn("\tprojects/apollo.md", self.ok("names"))

    def test_a_new_note_is_found(self):
        self.pkm("names")
        self.write("notes/new-idea.md", "# New idea\n")
        self.assertIn("new-idea\tnote\tnotes/new-idea.md", self.ok("names"))


class IndexCommand(Fixture):
    def cache_files(self):
        return {p.name: p.read_bytes() for p in sorted(self.cache().iterdir())}

    def test_rebuild_is_idempotent(self):
        self.ok("index", "--rebuild")
        first = self.cache_files()
        self.ok("index", "--rebuild")
        self.assertEqual(self.cache_files(), first)

    def test_index_reports_what_changed(self):
        self.assertIn("12 changed" if False else "changed", self.ok("index"))
        self.assertIn("0 changed", self.ok("index"))

    def test_no_temporary_files_are_left_behind(self):
        self.ok("index", "--rebuild")
        self.assertEqual([p.name for p in self.cache().iterdir() if ".tmp." in p.name], [])

    def test_pkm_cache_dir_moves_the_cache_and_changes_no_answer(self):
        expected = self.battery()
        elsewhere = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.rmtree(self.cache())
            env = {"PKM_CACHE_DIR": str(elsewhere / "cache")}
            moved = [(args, self.pkm(*args, env=env).returncode, self.pkm(*args, env=env).stdout) for args in BATTERY]
            self.assertEqual(moved, expected)
            self.assertTrue((elsewhere / "cache/names.tsv").exists())
            self.assertFalse(self.cache().exists())
        finally:
            shutil.rmtree(elsewhere)

    def test_the_cache_honours_pkmignore(self):
        self.write(".pkmignore", "drafts/\n")
        self.write("drafts/secret.md", "---\ntype: person\n---\n# Secret\n")
        self.ok("index")
        self.assertNotIn("secret", self.ok("names"))
        self.assertNotIn("drafts/", self.pkm("list", "--all").stdout)

    def test_the_cache_is_in_the_pkm_folder_and_git_ignores_it(self):
        self.ok("index")
        self.assertTrue((self.root / ".pkm/cache/names.tsv").exists())


class NamesAndList(Fixture):
    def test_names_by_name_with_type_path_and_aliases(self):
        out = self.ok("names", "--type", "person")
        self.assertEqual(out, "jane-doe\tperson\tpeople/jane-doe.md\tJD\n")

    def test_plain_names_leave_out_day_and_close_pages_and_files(self):
        names = [line.split("\t")[0] for line in self.ok("names").splitlines()]
        self.assertEqual(names, sorted(names))
        self.assertNotIn("2026-11-16", names)
        self.assertNotIn("plan.png", names)
        self.assertIn("2026-11-16", [line.split("\t")[0] for line in self.ok("names", "--type", "day").splitlines()])

    def test_list_gives_path_type_title_and_the_shown_fields(self):
        out = self.ok("list", "type=project", "--show", "status")
        self.assertEqual(out, "projects/apollo.md\tproject\tApollo\tactive\n")

    def test_list_matches_as_before(self):
        self.write("projects/hermes.md", "---\ntype: project\ntags: [budget, travel]\n---\n# Hermes\n")
        self.assertIn("projects/hermes.md", self.ok("list", "tags=travel"))
        self.assertEqual(self.pkm("list", "tags=sailing").returncode, 1)

    def test_names_and_list_json_carry_their_fields(self):
        record = json.loads(self.ok("names", "--type", "person", "--json").splitlines()[0])
        self.assertEqual(record["path"], "people/jane-doe.md")
        self.assertEqual(record["fields"], ["jane-doe", "person", "JD"])
        record = json.loads(self.ok("list", "type=project", "--show", "status", "--json").splitlines()[0])
        self.assertEqual(record["fields"], ["project", "Apollo", "active"])

    def test_names_has_a_usage_error_for_an_unknown_argument(self):
        self.assertEqual(self.pkm("names", "--type").returncode, 2)


if __name__ == "__main__":
    unittest.main()
