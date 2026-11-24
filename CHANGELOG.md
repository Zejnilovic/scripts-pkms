# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.10.0 (unreleased)

- `pkm new` takes `--set key=value` (any frontmatter key; a `part_of` must name a note), `--folder <folder>`, and `--url <address>`. For a `repo`, `--url` fills `url`, `items` and the title from a GitHub, Azure DevOps or GitLab address, also `git@…` and the short `owner/repo`: `pkm new repo --url acme-example/apollo-web --set part_of=acme-portal`. Agents no longer edit YAML by hand.
- `pkm set <note> key=value ...` changes frontmatter values in place, keeping the file's line endings, and refuses a `part_of` that names no note.
- `pkm mv` takes several notes: `pkm mv apollo-web apollo-api notes/apollo`. One that can't move leaves them all in place.
- The `part_of_folders` setting (default `no`): with `yes`, a note that is `part_of` another goes in a folder named after it, next to it (`notes/apollo/` for `notes/apollo.md`). `new` and `set` put notes there, and `check` lists, as notices, the notes that are elsewhere, with the `pkm mv` that moves them. A `folder_<type>` setting wins, so private folders stay private.

## Released

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
