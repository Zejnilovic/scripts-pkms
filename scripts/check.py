#!/usr/bin/env python3
"""Consistency checks for pkm and its templates. Run before committing: python3 scripts/check.py

Checks links, README coverage of commands and templates, the usage text, templates, the version, the changelog
and shell script syntax. Exits 1 if any problem is found.
"""

import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO / "share/pkm/templates"
SCRIPT = REPO / "bin/pkm"
LIB = REPO / "lib/pkm"

problems = []


def rel(path):
    return path.relative_to(REPO).as_posix()


def without_code(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)


for path in [REPO / "README.md", REPO / "CHANGELOG.md", REPO / "AGENTS.md", *REPO.glob("docs/*.md")]:
    for link in re.findall(r"\]\(([^)#\s]+)", without_code(path.read_text())):
        if not re.match(r"[a-z]+:", link) and not (path.parent / link).exists():
            problems.append(f"{rel(path)}: broken link '{link}'")

# The commands are an interface: agentic-pkms skills and editors call them, so each is documented twice,
# in the usage text at the top of the script and in the README's table.
readme = (REPO / "README.md").read_text()
script = SCRIPT.read_text()
dispatch = re.search(r"^case \$command in\n(.*?)^esac", script, re.M | re.S)
commands = [] if not dispatch else [
    name.split("|")[0] for name in re.findall(r"^  '?([a-z|-]+)'?\) ", dispatch.group(1), re.M)]
if not commands:
    problems.append("bin/pkm: no 'case $command in' dispatch found")
for command in commands:
    if command == "help":
        continue
    if not re.search(rf"^#   {command}\b", script, re.M):
        problems.append(f"bin/pkm: the usage text at the top doesn't describe '{command}'")
    if not re.search(rf"`{command}[ `]", readme):
        problems.append(f"README.md: the command table doesn't list '{command}'")

for path in TEMPLATES_DIR.glob("*.md"):
    if rel(path) not in readme:
        problems.append(f"README.md doesn't list {rel(path)}")

# Templates: notes copy them, so they carry no marker. Each typed template names its type, and every
# type pkm knows has a template.
for path in sorted(TEMPLATES_DIR.glob("*.md")):
    text = path.read_text()
    for marker in ("From scripts-pkms", "From agentic-pkms"):
        if marker in text:
            problems.append(f"{rel(path)}: templates must not carry the '{marker}' marker: every new note would copy it")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if match:
        found = re.search(r"^type: *(\S+)$", match.group(1), re.M)
        expected = "review" if path.stem.startswith("review-") else path.stem
        if not found or found.group(1) != expected:
            problems.append(f"{rel(path)}: frontmatter needs 'type: {expected}'")
    elif path.stem != "day":
        problems.append(f"{rel(path)}: no frontmatter; only day pages go without")
version = (REPO / "VERSION").read_text().strip()
core = (LIB / "core.sh").read_text()
script_version = re.search(r"^pkm_version=(\S+)$", core, re.M)
if not script_version or script_version.group(1) != version:
    problems.append(f"lib/pkm/core.sh: pkm_version doesn't match VERSION {version} (scripts/bump.sh sets both)")

# CHANGELOG.md holds at most one entry, for the unreleased VERSION; released versions are links
# under "## Released" to their GitHub releases (scripts/release.py moves an entry there).
changelog = (REPO / "CHANGELOG.md").read_text()
entries = re.findall(r"^## (\d+\.\d+\.\d+)([^\n]*)\n(.*?)(?=^## |\Z)", changelog, re.M | re.S)
for entry_version, entry_heading, _ in entries:
    if entry_version != version or entry_heading != " (unreleased)":
        problems.append(f"CHANGELOG.md: '## {entry_version}{entry_heading}' isn't the unreleased VERSION {version}; "
                        f"released versions belong under '## Released' as links")
released_links = set(re.findall(r"^- \[(\d+\.\d+\.\d+)\]\(https://github\.com/[^)\s]+/releases/tag/v\1\) "
                                r"\(\d{4}-\d{2}-\d{2}\)$", changelog, re.M))


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def check_unreleased_entry():
    entry = next((body for v, heading, body in entries if v == version and heading == " (unreleased)"), None)
    if entry is None:
        problems.append(f"CHANGELOG.md has no '## {version} (unreleased)' entry for VERSION {version}")
    elif not re.search(r"^- \S", entry, re.M):
        problems.append(f"CHANGELOG.md's {version} entry has no bullet points describing the change")
    elif "TODO" in entry:
        problems.append(f"CHANGELOG.md's {version} entry still has a TODO: describe the change")


# Release rule: once VERSION is tagged as released, any change to pkm's code or templates needs a new version.
tag = f"v{version}"
in_git = git("rev-parse", "--git-dir").returncode == 0
if not in_git:
    release_note = "release rule skipped (not a git repository)"
    if version not in released_links:
        check_unreleased_entry()
elif git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0:
    release_note = f"released as {tag}"
    if any(v == version for v, _, _ in entries):
        problems.append(f"CHANGELOG.md: {version} is released as {tag}, so its entry belongs in the GitHub release, "
                        f"not under '## {version}'")
    released = ("bin", "lib", "share")
    changed = sorted(set(git("diff", "--name-only", tag, "--", *released).stdout.splitlines())
                     | set(git("ls-files", "--others", "--exclude-standard", "--", *released).stdout.splitlines()))
    if changed:
        listed = ", ".join(changed[:3]) + (f" and {len(changed) - 3} more" if len(changed) > 3 else "")
        problems.append(f"bin/, lib/ or share/ changed since {tag} was released ({listed}). Start a new version with "
                        f"'bash scripts/bump.sh <version>': patch for fixes, minor for new commands, options or "
                        f"templates, major for renamed or removed ones and changed output")
else:
    release_note = f"not released yet (no tag {tag})"
    check_unreleased_entry()

# Every released (tagged) version is linked under "## Released".
if in_git:
    for released in git("tag", "-l", "v*").stdout.split():
        if released[1:] not in released_links:
            problems.append(f"CHANGELOG.md: {released[1:]} is released as {released}, so '## Released' needs "
                            f"'- [{released[1:]}](https://github.com/<owner>/<repo>/releases/tag/{released}) (YYYY-MM-DD)'")

for script_path in [SCRIPT, *LIB.rglob("*.sh"), *(REPO / "scripts").glob("*.sh")]:
    result = subprocess.run(["bash", "-n", str(script_path)], capture_output=True, text=True)
    if result.returncode != 0:
        problems.append(f"{rel(script_path)}: syntax error: {result.stderr.strip()}")

print(f"Checked {len([c for c in commands if c != 'help'])} commands,{len(list(TEMPLATES_DIR.glob('*.md')))} templates, "
      f"version {version} {release_note}.")
if problems:
    print("\nProblems:")
    for problem in problems:
        print(f"- {problem}")
    sys.exit(1)
print("No problems found.")
