"""--under <note> on tasks, since, list and backlinks: only the lines of the notes in that note's tree (part_of), and the
day page lines about one of them (a line that links it, or sits under a ### heading that does). And backlinks include the
lines under a ### heading that links the name. Run: python3 -m unittest discover -s tests. Names and data are made up.
NOW is Thursday 2026-11-19.
"""

import json
import unittest

from helpers import VaultCase

NOW = "20261119090000"
DAY = "daybook/2026/11/2026-11-12.md"


class Vault(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", "---\ntype: project\n---\n\n# Apollo\n")
        self.write("notes/apollo-design.md", "---\ntype: topic\npart_of: apollo\ncreated: 2026-11-12\n---\n\n# Design\n\n"
                   "- [ ] Draw the diagram\n")
        self.write("notes/acme.md", "---\ntype: topic\ncreated: 2026-11-12\n---\n\n# Acme\n\n- [ ] Send the invoice\n\n"
                   "### About [[apollo-design]]\n\n- Shared costs\n\n## Next\n\n- Later\n")
        self.write("archive/apollo-old.md", "---\npart_of: apollo\n---\n\n# Old\n\n- [ ] Old task\n")
        self.write(DAY, "# 2026-11-12\n\n## Log\n\n### Call with [[apollo-design]]\n\n- [ ] Book the room\n"
                   "- Decided: two screens\n\n### Lunch\n\n- [ ] Buy bread\n- Talked about the [[apollo]] budget\n"
                   "- [ ] Pay [[acme]]\n")

    def texts(self, out):
        return [line.split(": ", 1)[1] for line in out.splitlines() if ": " in line and not line.startswith("== ")]


class Under(Vault):
    def test_tasks_under_a_note_keep_its_tree_and_the_day_lines_about_it(self):
        self.assertEqual(sorted(self.texts(self.ok("tasks", "--under", "apollo", now=NOW))),
                         ["- [ ] Book the room", "- [ ] Draw the diagram"])
        self.assertEqual(self.texts(self.ok("tasks", "--under", "[[acme]]", now=NOW)),
                         ["- [ ] Send the invoice", "- [ ] Pay [[acme]]"])
        self.assertEqual(self.texts(self.ok("tasks", "--under", "apollo", "--all", now=NOW)).count("- [ ] Old task"), 0)

    def test_since_under_keeps_the_day_lines_about_the_tree_and_its_new_notes(self):
        out = self.ok("since", "2026-11-12", "--under", "apollo", now=NOW)
        log = out.split("== log\n")[1].split("\n== ")[0].splitlines()
        self.assertEqual(log, [f"{DAY}:5: ### Call with [[apollo-design]]", f"{DAY}:7: - [ ] Book the room",
                               f"{DAY}:8: - Decided: two screens", f"{DAY}:13: - Talked about the [[apollo]] budget"])
        notes = out.split("== notes\n")[1].split("\n== ")[0].splitlines()
        self.assertEqual(notes, ["notes/apollo-design.md:7: # Design"])

    def test_list_under_keeps_the_notes_of_the_tree(self):
        out = self.ok("list", "--under", "apollo", now=NOW).splitlines()
        self.assertEqual([line.split("\t")[0] for line in out], ["notes/apollo-design.md", "notes/apollo.md"])
        out = self.ok("list", "type=topic", "--under", "apollo", now=NOW).splitlines()
        self.assertEqual([line.split("\t")[0] for line in out], ["notes/apollo-design.md"])

    def test_backlinks_under_a_note(self):
        out = self.ok("backlinks", "apollo-design", "--under", "acme", now=NOW).splitlines()
        self.assertEqual(out, ["notes/acme.md:10: ### About [[apollo-design]]", "notes/acme.md:12: - Shared costs"])

    def test_under_needs_a_note(self):
        for cmd in (["tasks"], ["since", "7"], ["list"], ["backlinks", "acme"]):
            self.assertEqual(self.pkm(*cmd, "--under", "nobody", now=NOW).returncode, 1, cmd)
            self.assertEqual(self.pkm(*cmd, "--under", now=NOW).returncode, 2, cmd)


class HeadingBacklinks(Vault):
    def test_backlinks_include_the_lines_under_a_heading_that_links_the_name(self):
        out = self.ok("backlinks", "apollo-design", now=NOW).splitlines()
        self.assertEqual(out, [f"{DAY}:5: ### Call with [[apollo-design]]", f"{DAY}:7: - [ ] Book the room",
                               f"{DAY}:8: - Decided: two screens", "notes/acme.md:10: ### About [[apollo-design]]",
                               "notes/acme.md:12: - Shared costs"])
        self.assertNotIn(f"{DAY}:12: - [ ] Buy bread", out)
        self.assertNotIn("notes/acme.md:16: - Later", out)

    def test_since_and_json_apply_to_them_too(self):
        out = self.ok("backlinks", "apollo-design", "--since", "2026-11-13", now=NOW).splitlines()
        self.assertFalse(any(line.startswith("daybook/") for line in out), out)
        rows = [json.loads(line) for line in self.ok("backlinks", "apollo-design", "--json", now=NOW).splitlines()]
        self.assertIn({"path": DAY, "line": 7, "text": "- [ ] Book the room"},
                      [{k: row[k] for k in ("path", "line", "text")} for row in rows])

    def test_a_name_with_no_note_yet_gets_its_heading_lines(self):
        self.write("daybook/2026/11/2026-11-13.md", "# 2026-11-13\n\n### Ideas for [[Bob Smith]]\n\n- A book\n")
        out = self.ok("backlinks", "Bob Smith", now=NOW).splitlines()
        self.assertEqual(out, ["daybook/2026/11/2026-11-13.md:3: ### Ideas for [[Bob Smith]]",
                               "daybook/2026/11/2026-11-13.md:5: - A book"])


if __name__ == "__main__":
    unittest.main()
