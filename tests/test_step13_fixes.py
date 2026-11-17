"""Documenter's fixes for step 13: a title inside a code fence is not the title; folder_<type> defaults to notes, as new
notes of every type do; the VS Code find task passes its words as separate arguments. Run: python3 -m unittest discover -s tests.
Names and data are made up.
"""

import json
import unittest

from helpers import REPO, VaultCase

FENCED = "---\ntype: topic\n---\n```\n# In fence\n```\n~~~\n# Also in fence\n~~~\n# Real title\n\nBody\n"


class TitleSkipsFences(VaultCase):
    def test_a_heading_inside_a_fence_is_not_the_title(self):
        self.write("notes/fenced.md", FENCED)
        lines = {line.split("\t")[0]: line.split("\t") for line in self.ok("list").splitlines()}
        self.assertEqual(lines["notes/fenced.md"][2], "Real title")


class FolderDefault(VaultCase):
    def test_the_registry_and_the_doc_say_new_notes_go_to_notes(self):
        self.assertIn("\tnotes\tdefault", self.ok("config", "folder_person"))
        docs = (REPO / "docs/settings.md").read_text()
        self.assertRegex(docs, r"\| `folder_<type>` \| vault \| `notes` \|")


class FindTask(unittest.TestCase):
    def test_the_find_task_passes_the_words_as_separate_arguments(self):
        data = json.loads((REPO / "share/pkm/editors/vscode/tasks.json").read_text())
        task = [t for t in data["tasks"] if t["label"] == "pkm: find"][0]
        self.assertEqual(task["type"], "shell")
        self.assertRegex(task["command"], r"^pkm find \$\{input:words\}$")
        self.assertNotIn("args", task)


if __name__ == "__main__":
    unittest.main()
