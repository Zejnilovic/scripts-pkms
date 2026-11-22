# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.9.0 (unreleased)

- `pkm help <command>` and `pkm <command> --help` print one command: its summary, its usage and its options. They work outside a vault, and `pkm help <Tab>` completes the command names. An unknown option now points to `pkm help <command>`.
- The site has a command reference, [docs/commands.md](docs/commands.md), made from `pkm help` by `scripts/commands.py`; `scripts/check.py` fails when it is out of date.
- Fix: `pkm help --all` cut a summary at its first `|`, so recall's summary ended at `yes`.

## Released

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
