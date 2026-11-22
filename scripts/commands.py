#!/usr/bin/env python3
"""Writes docs/commands.md, the command reference, from what pkm prints: pkm help, pkm help --all and pkm help <command>.

Run it after changing the usage text at the top of bin/pkm, or the command table or options in lib/pkm/cmd/help.sh:
python3 scripts/commands.py. With --check it writes nothing and exits 1 when the page is out of date (scripts/check.py
runs that). Extensions on PATH are left out: they belong to one machine, not to pkm.
"""

import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PAGE = REPO / "docs/commands.md"
BASH = "/bin/bash" if pathlib.Path("/bin/bash").exists() else "bash"

INTRO = """# Commands

<!-- Made by scripts/commands.py from pkm's own help; run it again instead of editing this page. -->

Every pkm command with its usage and options, as `pkm help <command>` prints it in the terminal (`pkm <command> --help`
prints the same). `pkm help` prints them all at once, and `pkm help --all` one line per command.
[The output contract](contract.md) says what each command prints and its exit codes, [the file format](format.md) what
it reads, and [Settings](settings.md) every setting. Commands work from any folder in the vault.
"""


def pkm(*args):
    environment = {key: value for key, value in os.environ.items() if key != "PKM_VAULT"}
    result = subprocess.run([BASH, str(REPO / "bin/pkm"), *args], capture_output=True, text=True, env=environment)
    if result.returncode != 0:
        sys.exit(f"pkm {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def prose(text):
    """A summary from the command table as a sentence, safe in Markdown."""
    text = text[0].upper() + text[1:]
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text if text.endswith(".") else text + "."


def dedent(lines):
    return [line[2:] if line.startswith("  ") else line for line in lines]


def page():
    usage = pkm("help").splitlines()
    first_entry = next(i for i, line in enumerate(usage) if re.match(r"^  [a-z]", line))
    tail = next(i for i, line in enumerate(usage) if line.startswith("Listings:"))
    head = [line for line in usage[:first_entry] if line.strip()]

    out = [INTRO, "## Calling pkm", "", "The options before the command say which vault to use.", "", "```text",
           *head, "```", ""]
    rows = [line.split("\t") for line in pkm("help", "--all").splitlines()]
    rows = [row for row in rows if row[1] != "Extension"]
    groups = list(dict.fromkeys(row[1] for row in rows))
    rows.sort(key=lambda row: groups.index(row[1]))  # each group in the order it first appears; stable within it
    group = None
    for name, row_group, summary in rows:
        if row_group != group:
            group = row_group
            out += [f"## {group}", ""]
        lines = pkm("help", name).splitlines()[2:]
        options = [line for line in lines if line.startswith("Options: ")]
        entry = [line for line in lines if line.strip() and not line.startswith("Options: ")]
        out += [f"### {name}", "", prose(summary), "", "```text", *dedent(entry), "```", ""]
        if options:
            out += ["Options: " + " ".join(f"`{option}`" for option in options[0].split()[1:]), ""]
    out += ["## Listings, settings and the clock", "", "```text", *[line for line in usage[tail:]], "```", ""]
    return "\n".join(out)


def main():
    text = page()
    if "--check" in sys.argv[1:]:
        if not PAGE.exists() or PAGE.read_text() != text:
            print("docs/commands.md is out of date: run python3 scripts/commands.py")
            sys.exit(1)
        return
    PAGE.write_text(text)
    print(f"wrote {PAGE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
