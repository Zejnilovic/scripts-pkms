"""todo --every writes the routine to the note named routines (created from the note template when missing), not to
today's page; a plain todo still goes on today's page. Run: python3 -m unittest discover -s tests. Names are made up.
NOW is 2026-10-25.
"""

from helpers import VaultCase

ROUTINES = "# Routines\n\n- [ ] Rent (due 2026-12-01) (every 1m)\n"


class RoutineNote(VaultCase):
    def test_a_routine_lands_at_the_end_of_an_existing_routines_note(self):
        self.write("notes/routines.md", ROUTINES)
        out = self.ok("todo", "Water plants", "--every", "1w").strip()
        self.assertEqual(out, "notes/routines.md:4")
        self.assertEqual(self.read("notes/routines.md"), ROUTINES + "- [ ] Water plants (every 1w)\n")
        self.assertFalse(self.exists("daybook/2026/10/2026-10-25.md"))

    def test_the_routines_note_is_found_by_its_name_in_any_folder(self):
        self.write("projects/routines.md", "# Routines\n\n- [ ] Rent (every 1m)\n")
        self.assertEqual(self.ok("todo", "Water plants", "--every", "1w").strip(), "projects/routines.md:4")
        self.assertFalse(self.exists("notes/routines.md"))

    def test_a_missing_routines_note_is_created_from_the_template(self):
        out = self.ok("todo", "Water plants", "--every", "1w").strip()
        self.assertTrue(out.startswith("notes/routines.md:"), out)
        text = self.read("notes/routines.md")
        self.assertIn("type: note\n", text)
        self.assertIn("summary: What comes back; when one is done, its date moves on\n", text)
        self.assertIn("\n# Routines\n", text)
        self.assertTrue(text.endswith("- [ ] Water plants (every 1w)\n"), text)
        self.assertEqual(out.rsplit(":", 1)[1], str(text.splitlines().index("- [ ] Water plants (every 1w)") + 1))

    def test_check_stays_clean_after_a_routine_is_written(self):
        self.write(".pkm/config", "format=1\ncycle_sprint=2w from 2026-11-02\n")
        self.ok("todo", "Water plants", "--every", "sprint")
        result = self.pkm("check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("belongs in a note", result.stdout)

    def test_a_crlf_routines_note_keeps_its_line_ends(self):
        (self.root / "notes").mkdir()
        (self.root / "notes/routines.md").write_bytes(b"# Routines\r\n\r\n- [ ] Rent (every 1m)\r\n")
        self.ok("todo", "Water plants", "--every", "1w")
        data = (self.root / "notes/routines.md").read_bytes()
        self.assertEqual(data, b"# Routines\r\n\r\n- [ ] Rent (every 1m)\r\n- [ ] Water plants (every 1w)\r\n")

    def test_a_plain_todo_still_lands_on_todays_page(self):
        self.write("notes/routines.md", ROUTINES)
        out = self.ok("todo", "Call Jane").strip()
        self.assertEqual(out, "daybook/2026/10/2026-10-25.md:" + out.rsplit(":", 1)[1])
        self.assertIn("- [ ] Call Jane", self.read("daybook/2026/10/2026-10-25.md"))
        self.assertEqual(self.read("notes/routines.md"), ROUTINES)


if __name__ == "__main__":
    import unittest

    unittest.main()
