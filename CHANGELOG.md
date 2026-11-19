# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.2.0 (unreleased)

- **Areas and `part_of`.** A new template, `area`, for what you look after with no end (a home, a car, a team, your learning), with Now, Routines, People, Links and Ideas. A note names the one note it belongs to with `part_of: <name>` (or `"[[name]]"`); the project, course, writing and area templates have the key. `part_of` is a link: `backlinks` lists it, `rename` rewrites it, and `check` reports one that names no note, a list of several, a note that names itself and a circle.
- **`pkm overview [--json]`**: the shape of the vault, as trees of `part_of`: areas, projects, resources (courses, topics, sources) and other notes with notes under them, then the archive's count.
- **`pkm todo --every <rule> --in <note>`** writes a routine to that note's `## Routines` section, made when missing, instead of the note named `routines`.
- **`pkm add --file <path> [text]`** copies a file to `files/<year>/<month>/<date>-<name>`, never over another, and writes an entry on the day's page that links it.
- **The cache** has a version file, and a cache without it (from 0.1.0) is read again in full on the first command, so `part_of` lines are counted as links.
- The method adds areas, `part_of`, ideas that grow on their note (`status: idea`), files linked from their day, routines in their area, and Building a Second Brain to its sources. The family example vault has a `home` area with the bathroom and the groceries in it, and the plumber's quote as a file.
- Format 1 gains `part_of` and `files/`, both optional; vaults need no change.

## Released

- [0.1.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.1.0) (2026-11-18)
