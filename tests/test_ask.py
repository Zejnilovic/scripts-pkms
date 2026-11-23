"""On a terminal, a command missing its text, task or note asks for it; without one it is a usage error (exit 2).

pkm asks only when stdin and stderr are a terminal, so these tests run it on a pseudo terminal: they wait for each
prompt on the terminal, then type the answer. The picker setting chooses fzf or a numbered list; most tests use
picker=list, and the fzf ones put a fake fzf on PATH.
"""

import os
import pathlib
import pty
import subprocess
import tempfile
import threading
import time
import unittest

from helpers import BASH, NOW, PKM, VaultCase, pkm_env

DAY = "daybook/2026/10/2026-10-25.md"
PAGE = """# 2026-10-25

## Tasks

- [ ] Send the Apollo report to [[jane-doe]]
- [ ] Review the Acme contract (due 2026-10-27)
- [ ] Book the Acme venue

## Log
"""

# A fake fzf: prints the first line of its input that has FAKE_PICK in it, and the arguments it got into FAKE_ARGS.
FAKE_FZF = """#!/bin/sh
printf '%s\\n' "$@" > "$FAKE_ARGS"
line=$(grep -F -- "$FAKE_PICK" | head -n 1)
[ -n "$line" ] || exit 130
printf '%s\\n' "$line"
"""


class AskCase(VaultCase):
    def setUp(self):
        super().setUp()
        self.write_user("picker=list\n")

    def tty(self, *args, answers=(), env=None, timeout=10):
        """Runs pkm with stdin and stderr on a pseudo terminal. For each (prompt, text) in answers it waits until the
        prompt is on the terminal, then types the text and Enter. Returns (exit code, stdout, what the terminal showed).
        """
        environment = pkm_env(PKM_NOW=NOW, XDG_CONFIG_HOME=self.config_home, **(env or {}))
        master, slave = pty.openpty()
        process = subprocess.Popen(
            [BASH, str(PKM), "--vault", str(self.root), *args], cwd=self.root, env=environment,
            stdin=slave, stderr=slave, stdout=subprocess.PIPE, start_new_session=True)
        os.close(slave)
        # macOS drops what is left on the terminal when the program ends, so a thread reads it all the time.
        shown = bytearray()

        def read_terminal():
            while True:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    return
                if not chunk:
                    return
                shown.extend(chunk)

        reader = threading.Thread(target=read_terminal, daemon=True)
        reader.start()
        # The next prompt may repeat the last one, so only what the terminal shows after an answer counts for it.
        start = 0
        try:
            for prompt, text in answers:
                deadline = time.time() + timeout
                while prompt.encode() not in bytes(shown[start:]):
                    if time.time() > deadline or process.poll() is not None:
                        time.sleep(0.2)
                        if prompt.encode() in bytes(shown[start:]):
                            break
                        self.fail(f"no prompt {prompt!r}; the terminal showed:\n{bytes(shown).decode(errors='replace')}")
                    time.sleep(0.02)
                start = len(shown)
                os.write(master, text.encode() + b"\r")
            try:
                out, _ = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                self.fail(f"pkm {' '.join(args)} still waits; the terminal showed:\n{bytes(shown).decode(errors='replace')}")
            reader.join(timeout=1)
        finally:
            if process.poll() is None:
                process.kill()
            os.close(master)
        shown = bytes(shown)
        return process.returncode, out.decode(), shown.decode(errors="replace")

    def fake_fzf(self, pick):
        folder = pathlib.Path(tempfile.mkdtemp(dir=self.root.parent))
        (folder / "fzf").write_text(FAKE_FZF)
        (folder / "fzf").chmod(0o755)
        self.fzf_args = folder / "args"
        return {"PATH": f"{folder}{os.pathsep}{os.environ['PATH']}", "FAKE_PICK": pick, "FAKE_ARGS": str(self.fzf_args)}


class DoneAsks(AskCase):
    def setUp(self):
        super().setUp()
        self.write(DAY, PAGE)

    def test_done_with_no_words_lists_the_open_tasks_and_marks_the_one_picked(self):
        code, out, shown = self.tty("done", answers=[("Done", "2")])
        self.assertEqual(code, 0, shown)
        self.assertIn("Review the Acme contract", shown)
        self.assertIn("Book the Acme venue", shown)
        page = self.read(DAY)
        self.assertIn("- [x] Send the Apollo report to [[jane-doe]] (done 2026-10-25)", page)
        self.assertIn("- [ ] Review the Acme contract", page)
        self.assertEqual(out, f"{DAY}:5: - [x] Send the Apollo report to [[jane-doe]] (done 2026-10-25)\n")

    def test_the_list_is_in_the_order_of_pkm_tasks(self):
        _, _, shown = self.tty("done", answers=[("Done", "")])
        due = shown.index("Review the Acme contract")
        self.assertLess(due, shown.index("Send the Apollo report"))
        self.assertLess(due, shown.index("Book the Acme venue"))
        self.assertIn(f"{DAY}:6", shown)

    def test_words_that_match_several_tasks_ask_which_one(self):
        code, out, shown = self.tty("done", "acme", answers=[("Done", "2")])
        self.assertEqual(code, 0, shown)
        self.assertNotIn("Send the Apollo report", shown)
        self.assertIn("- [x] Book the Acme venue (done 2026-10-25)", self.read(DAY))
        self.assertIn("- [ ] Review the Acme contract", self.read(DAY))

    def test_words_typed_at_the_prompt_narrow_the_list(self):
        code, _, shown = self.tty("done", answers=[("Done", "venue"), ("Done", "1")])
        self.assertEqual(code, 0, shown)
        self.assertIn("- [x] Book the Acme venue", self.read(DAY))

    def test_drop_asks_too(self):
        code, _, shown = self.tty("done", "--drop", answers=[("Drop", "3")])
        self.assertEqual(code, 0, shown)
        self.assertIn("- [-] Book the Acme venue (dropped 2026-10-25)", self.read(DAY))

    def test_an_empty_answer_cancels_and_changes_nothing(self):
        code, out, shown = self.tty("done", answers=[("Done", "")])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Cancelled", shown)
        self.assertEqual(self.read(DAY), PAGE)

    def test_a_number_outside_the_list_asks_again(self):
        code, _, shown = self.tty("done", answers=[("Done", "9"), ("Done", "1")])
        self.assertEqual(code, 0, shown)
        self.assertIn("from 1 to 3", shown)

    def test_without_a_terminal_it_is_still_a_usage_error(self):
        result = self.pkm("done")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage: pkm done", result.stderr)
        result = self.pkm("done", "acme")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.read(DAY), PAGE)

    def test_picker_off_never_asks(self):
        self.write_user("picker=off\n")
        code, _, shown = self.tty("done")
        self.assertEqual(code, 2)
        self.assertIn("Usage: pkm done", shown)

    def test_a_wrong_picker_setting_says_so(self):
        self.write_user("picker=menu\n")
        code, _, shown = self.tty("done")
        self.assertEqual(code, 2)
        self.assertIn("picker", shown)

    def test_with_no_open_tasks_it_says_so(self):
        self.write(DAY, "# 2026-10-25\n\n## Tasks\n\n- [x] Old (done 2026-10-20)\n")
        code, _, shown = self.tty("done")
        self.assertEqual(code, 1)
        self.assertIn("No open tasks", shown)

    def test_fzf_picks_when_the_setting_is_auto(self):
        self.write_user("picker=auto\n")
        code, out, shown = self.tty("done", env=self.fake_fzf("venue"))
        self.assertEqual(code, 0, shown)
        self.assertIn("- [x] Book the Acme venue", self.read(DAY))
        self.assertEqual(out, f"{DAY}:7: - [x] Book the Acme venue (done 2026-10-25)\n")
        self.assertIn("--prompt", self.fzf_args.read_text())

    def test_fzf_cancelled_changes_nothing(self):
        self.write_user("picker=fzf\n")
        code, _, _ = self.tty("done", env=self.fake_fzf("no such task"))
        self.assertEqual(code, 1)
        self.assertEqual(self.read(DAY), PAGE)


class MovedAsks(AskCase):
    def test_moved_with_nothing_picks_a_task_and_asks_when(self):
        self.write(DAY, PAGE)
        code, out, shown = self.tty("moved", answers=[("Move", "3"), ("To when", "friday")])
        self.assertEqual(code, 0, shown)
        self.assertIn("~~Book the Acme venue~~", self.read(DAY))
        self.assertIn("Book the Acme venue (due 2026-10-30)", out)

    def test_moved_with_a_line_asks_when(self):
        self.write(DAY, PAGE)
        code, out, shown = self.tty("moved", f"{DAY}:7", answers=[("To when", "+2d")])
        self.assertEqual(code, 0, shown)
        self.assertIn("(due 2026-10-27)", out)


class TextAsks(AskCase):
    def test_todo_asks_for_the_text_and_keeps_the_options(self):
        code, out, shown = self.tty("todo", "--due", "friday", answers=[("Task", "Call [[jane-doe]]")])
        self.assertEqual(code, 0, shown)
        self.assertIn("- [ ] Call [[jane-doe]] (due 2026-10-30)", self.read(DAY))
        self.assertTrue(out.startswith(f"{DAY}:"))

    def test_todo_cancelled_writes_nothing(self):
        code, _, _ = self.tty("todo", answers=[("Task", "")])
        self.assertEqual(code, 1)
        self.assertFalse(self.exists(DAY))

    def test_add_asks_for_the_entry(self):
        code, _, shown = self.tty("add", answers=[("Log", "Met Jane about Apollo")])
        self.assertEqual(code, 0, shown)
        self.assertIn("- 14:30 Met Jane about Apollo", self.read(DAY))

    def test_add_without_a_terminal_is_still_a_usage_error(self):
        self.assertEqual(self.pkm("add").returncode, 2)
        self.assertEqual(self.pkm("todo").returncode, 2)

    def test_find_asks_for_the_words(self):
        self.write(DAY, PAGE)
        code, out, shown = self.tty("find", answers=[("Find", "acme venue")])
        self.assertEqual(code, 0, shown)
        self.assertEqual(out, f"{DAY}:7: - [ ] Book the Acme venue\n")


class NoteAsks(AskCase):
    def setUp(self):
        super().setUp()
        self.write("notes/apollo.md", "---\ntype: project\n---\n# Apollo\n\nThe launch.\n")
        self.write("notes/jane-doe.md", "---\ntype: person\n---\n# Jane Doe\n")
        self.write(DAY, PAGE)

    def test_get_picks_a_note(self):
        code, out, shown = self.tty("get", answers=[("Note", "apollo"), ("Note", "1")])
        self.assertEqual(code, 0, shown)
        self.assertIn("jane-doe", shown)
        self.assertIn("The launch.", out)

    def test_backlinks_picks_a_note(self):
        code, out, shown = self.tty("backlinks", answers=[("Note", "2")])
        self.assertEqual(code, 0, shown)
        self.assertIn("Send the Apollo report", out)

    def test_path_picks_a_note(self):
        code, out, shown = self.tty("path", answers=[("Note", "1")])
        self.assertEqual(code, 0, shown)
        self.assertEqual(out, "notes/apollo.md\n")

    def test_new_picks_a_type_and_asks_the_title(self):
        code, out, shown = self.tty("new", answers=[("Type", "person"), ("Type", "1"), ("Title", "John Roe")])
        self.assertEqual(code, 0, shown)
        self.assertEqual(out.strip(), "notes/john-roe.md")

    def test_new_with_a_type_asks_the_title(self):
        code, out, shown = self.tty("new", "project", answers=[("Title", "Zephyr")])
        self.assertEqual(code, 0, shown)
        self.assertEqual(out.strip(), "notes/zephyr.md")
        self.assertIn("type: project", self.read("notes/zephyr.md"))

    def test_without_a_terminal_they_are_still_usage_errors(self):
        for command in ("get", "backlinks", "path", "new", "moved"):
            self.assertEqual(self.pkm(command).returncode, 2, command)


if __name__ == "__main__":
    unittest.main()
