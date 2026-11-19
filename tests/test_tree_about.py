"""Two shared pieces: trees (lib/pkm/tree.sh), the notes under a note by part_of, and the lines about a name
(lib/pkm/about.sh), a line that links the name and every line under a ### heading that does. overview, since --about and
later --under and backlinks use them. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import os
import subprocess
import unittest

from helpers import BASH, REPO, VaultCase

MODULES = "core dates config vault links index sections tree about"


class Shared(VaultCase):
    def run_lib(self, body, *args):
        script = (f'pkm_home="$1"; shift; for f in {MODULES}; do . "$pkm_home/lib/pkm/$f.sh"; done; '
                  f'vault=$PWD; tmp=$(mktemp -d); {body}; status=$?; rm -rf "$tmp"; exit $status')
        result = subprocess.run([BASH, "-c", script, "pkm", str(REPO), *args], cwd=self.root, capture_output=True,
                                text=True, env={**os.environ, "PKM_NOW": "20261119090000"})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout


class Trees(Shared):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", "---\ntype: project\naliases: [Apollo]\n---\n\n# Apollo\n")
        self.write("notes/apollo-design.md", "---\ntype: topic\npart_of: Apollo\n---\n\n# Design\n")
        self.write("notes/apollo-review.md", "---\npart_of: \"[[apollo-design|Design]]\"\n---\n\n# Review\n")
        self.write("notes/apollo-budget.md", "---\npart_of: [[apollo]]\n---\n\n# Budget\n")
        self.write("notes/apollo-old.md", "---\npart_of: [apollo, acme]\n---\n\n# Old\n")
        self.write("archive/apollo-2025.md", "---\npart_of: apollo\n---\n\n# Apollo 2025\n")
        self.write("daybook/2026/11/2026-11-12.md", "---\npart_of: apollo\n---\n\n# 2026-11-12\n")
        self.write("notes/loop-a.md", "---\npart_of: loop-b\n---\n\n# A\n")
        self.write("notes/loop-b.md", "---\npart_of: loop-a\n---\n\n# B\n")
        self.write("notes/self.md", "---\npart_of: self\n---\n\n# Self\n")

    def paths(self, note):
        return self.run_lib('tree_paths "$1" "$tmp/out" && cat "$tmp/out"', note).splitlines()

    def test_a_tree_is_the_note_and_every_note_under_it(self):
        self.assertEqual(self.paths("notes/apollo.md"), ["notes/apollo-budget.md", "notes/apollo-design.md",
                                                         "notes/apollo-review.md", "notes/apollo.md"])
        self.assertEqual(self.paths("notes/apollo-design.md"), ["notes/apollo-design.md", "notes/apollo-review.md"])
        self.assertEqual(self.paths("notes/apollo-review.md"), ["notes/apollo-review.md"])

    def test_a_loop_or_a_note_that_names_itself_ends(self):
        self.assertEqual(self.paths("notes/loop-a.md"), ["notes/loop-a.md", "notes/loop-b.md"])
        self.assertEqual(self.paths("notes/self.md"), ["notes/self.md"])

    def test_the_parents_leave_out_day_pages_the_archive_and_lists(self):
        out = self.run_lib('tree_parents "$tmp/out" && LC_ALL=C sort "$tmp/out"').splitlines()
        self.assertEqual(out, ["notes/apollo-budget.md\tnotes/apollo.md", "notes/apollo-design.md\tnotes/apollo.md",
                               "notes/apollo-review.md\tnotes/apollo-design.md", "notes/loop-a.md\tnotes/loop-b.md",
                               "notes/loop-b.md\tnotes/loop-a.md"])


class LinesAbout(Shared):
    def setUp(self):
        super().setUp()
        self.write("notes/jane-doe.md", "---\ntype: person\naliases: [Jane]\n---\n\n# Jane Doe\n")
        self.day = "daybook/2026/11/2026-11-12.md"
        self.write(self.day, "# 2026-11-12\n\n## Log\n\n### Call with [[jane-doe]] about [[apollo]]\n\n"
                   "- She wants the budget by Friday\n- I'll send it\n\n### Lunch\n\n- Talked to [[Jane]]\n"
                   "- Then the bus\n\n## Tasks\n\n- [ ] Plan it\n")
        self.write("notes/apollo.md", "# Apollo\n\n### Meeting with [[jane-doe]]\n\n- Scope agreed\n\n## Next\n\n- Ship\n")

    def test_each_line_gets_its_own_names_and_those_of_its_heading(self):
        out = self.run_lib('printf "%s\\n" "$1" "notes/apollo.md" > "$tmp/files"; about_pages "$tmp/files" "$tmp/pages"; '
                           'about_names "$tmp/pages" "$tmp/names"; tr "\\037" "|" < "$tmp/names"', self.day)
        rows = set(out.splitlines())
        for row in [f"{self.day}|5|jane-doe|1|", f"{self.day}|5|apollo|1|", f"{self.day}|7|jane-doe|0|2026-11-12",
                    f"{self.day}|8|apollo|0|2026-11-12", f"{self.day}|12|jane-doe|1|",
                    "notes/apollo.md|3|jane-doe|1|", "notes/apollo.md|5|jane-doe|0|"]:
            self.assertIn(row, rows)
        for line in (13, 17):
            self.assertFalse(any(r.startswith(f"{self.day}|{line}|") for r in rows), line)
        self.assertFalse(any(r.startswith("notes/apollo.md|9|") for r in rows))

    def test_the_pages_have_the_date_of_a_day_page_only(self):
        out = self.run_lib('printf "%s\\n" "$1" "notes/apollo.md" > "$tmp/files"; about_pages "$tmp/files" "$tmp/pages"; '
                           'tr "\\037" "|" < "$tmp/pages"', self.day).splitlines()
        self.assertIn(f"{self.day}|2026-11-12|1|t|# 2026-11-12", out)
        self.assertIn(f"{self.day}|2026-11-12|3|x|## Log", out)
        self.assertIn("notes/apollo.md||3|l|### Meeting with [[jane-doe]]", out)

    def test_a_name_is_a_notes_name_or_the_slug_of_one_not_written_yet(self):
        for name, key in [("Jane", "jane-doe"), ("[[jane-doe]]", "jane-doe"), ("Jane Doe", "jane-doe"),
                          ("Bob Smith", "bob-smith"), ("notes/apollo.md", "apollo")]:
            self.assertEqual(self.run_lib('about_key "$1"', name).strip(), key, name)


if __name__ == "__main__":
    unittest.main()
