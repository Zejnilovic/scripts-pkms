# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.3.0 (unreleased)

- The method has events: `(at <when>)`, or `(@ <when>)`, at the end of an entry, for something that happens at a time and is never overdue. With a task box, it is a task with a time. An event in a note can come back with `(every …)`, `(until …)` and `(skip …)`. The example vaults have a parents' evening, Mia's football and the Apollo demo.
- pkm reads the dates of tasks in awk, so a vault with many relative dates (`(due friday)`, `(due +3d)`) no longer starts a process per task. A date that isn't on the calendar, such as `2026-02-30`, is now a `check` problem on macOS too, where BSD `date` had accepted it.
- pkm reads every marked line of the vault in one pass, which events and later features build on. The output of `tasks`, `upcoming`, `close`, `since` and `check` is unchanged.
- TODO: pkm reads events in `upcoming`, `close` and `check`, and `pkm upcoming --ics` writes them as a calendar file.

## Released

- [0.2.1](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.2.1) (2026-11-19)
- [0.2.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.2.0) (2026-11-19)
- [0.1.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.1.0) (2026-11-18)
