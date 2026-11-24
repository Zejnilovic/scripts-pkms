# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.11.0 (unreleased)

- `pkm config <key> <value> [--user]` sets a setting, in `.pkm/config` or the user config, by the key's scope: `pkm config part_of_folders yes`. Agents no longer append to the settings by hand.
- `pkm set <note> part_of=<name>` with `part_of_folders=yes` moves the note's own folder along with it, so a project put under an application takes its notes: `notes/hermes/` becomes `notes/acme-portal/hermes/`. A file in the way moves nothing.
- `pkm check` notices: a live note whose `part_of` is in `archive/` (it has dropped out of its tree), two live notes with one `url` (one thing, two notes), and a person, team, application or area that is `part_of` a project (they belong to many things: link them from the project). The folder notice no longer tells such a note to move into the project's folder.

## Released

- [0.10.1](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.10.1) (2026-11-24)
- [0.10.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.10.0) (2026-11-24)
- [0.9.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.9.0) (2026-11-23)
- [0.8.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.8.0) (2026-11-20)
- [0.7.1](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.7.1) (2026-11-20)
- [0.7.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.7.0) (2026-11-20)
- [0.6.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.6.0) (2026-11-20)
- [0.5.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.5.0) (2026-11-19)
- [0.4.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.4.0) (2026-11-19)
- [0.3.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.3.0) (2026-11-19)
- [0.2.1](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.2.1) (2026-11-19)
- [0.2.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.2.0) (2026-11-19)
- [0.1.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.1.0) (2026-11-18)
