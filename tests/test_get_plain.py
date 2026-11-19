"""pkm get <note>[#Section] --plain: the text as someone outside the vault reads it, to paste into an email: [[a|b]] as b,
[[a]] as the title of the note it names, without the links to the day pages its lines came from, the markers, the
frontmatter, struck lines, or the header and footer. Code is left as it is. Run: python3 -m unittest discover -s tests.
Names and data are made up.
"""

import unittest

from helpers import VaultCase

NOTE = """---
type: project
---

# Apollo

## Now

- Budget approved by [[john-roe|John]] ([[2026-11-11]])
- Demo moved to Tuesday, see [[acme]] ([[2026-11-12-sam]])
- ~~Launch in March~~ ([[2026-11-19]])
  - [ ] Send [[jane-doe]] the plan (due 2026-11-27) (high)
- Talk to [[Bob Smith]] about [[apollo#Risks]], 📅 2026-12-01

```
[[not-a-link]] (due 2026-01-01)
```

## Risks

- Late hardware ([[2026-11-10]])
"""


class GetPlain(VaultCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", NOTE)
        self.write("notes/john-roe.md", "---\ntype: person\n---\n\n# John Roe\n")
        self.write("notes/jane-doe.md", "# Jane Doe\n")
        self.write("notes/acme.md", "---\ntype: organization\n---\n\n# Acme Corp\n")

    def test_a_section_reads_without_links_sources_and_markers(self):
        out = self.ok("get", "apollo#Now", "--plain")
        self.assertEqual(out, "## Now\n\n- Budget approved by John\n- Demo moved to Tuesday, see Acme Corp\n"
                              "  - [ ] Send Jane Doe the plan\n- Talk to Bob Smith about Apollo,\n\n"
                              "```\n[[not-a-link]] (due 2026-01-01)\n```\n")

    def test_the_whole_note_leaves_out_its_frontmatter(self):
        out = self.ok("get", "[[apollo]]", "--plain").splitlines()
        self.assertEqual(out[0], "# Apollo")
        self.assertEqual(out[-1], "- Late hardware")
        self.assertNotIn("type: project", out)

    def test_lines_narrow_it_and_the_exits_stay(self):
        self.assertEqual(self.ok("get", "apollo", "--lines", "9-10", "--plain"),
                         "- Budget approved by John\n- Demo moved to Tuesday, see Acme Corp\n")
        self.assertEqual(self.ok("get", "apollo", "--lines", "1-3", "--plain"), "")
        self.assertEqual(self.pkm("get", "apollo#Nowhere", "--plain").returncode, 1)
        self.assertEqual(self.pkm("get", "nobody", "--plain").returncode, 1)
        self.assertTrue(self.ok("get", "apollo#Now").startswith("<<<note notes/apollo.md lines 7-"))


if __name__ == "__main__":
    unittest.main()
