# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.5.0 (unreleased)

- `pkm get <note>[#Section] --plain`: the text to paste for someone outside the vault, with each link as its shown text or the note's title, and without the links to day pages, the markers, the frontmatter and struck lines.
- `pkm --vaults [<a,b>] tasks|upcoming|since`: the command in each named vault, each under `== vault <name>` with its own paths, and `vault` added in `--json`. With no names it takes the new user setting `vaults=` (such as `vaults=work,family`). It only reads; nothing is copied between vaults.
- `--json` on `upcoming` (with `date`, `kind`, `time` and `end`), `tags`, `cycle` and `vaults`. `since` and `close` now say how to get jq when `--json` needs it.
- `--under <note>` on `tasks`, `since`, `list` and `backlinks`: only the lines of the notes in that note's tree (`part_of`), and the lines of day pages about one of them, a line under a `###` heading that links one included. `list --under` keeps the notes of the tree.
- `backlinks` also lists the lines under a `###` heading that links the name, in any file, so the notes of a call under `### Call with [[jane-doe]]` are among Jane's backlinks. Scripts that read `backlinks` get more lines.
- `since --about` also takes a `[[link]]` or a note's path in the vault, as well as a name, a slug or an alias.
- Inside: the `part_of` trees (`lib/pkm/tree.sh`) and the lines about a name (`lib/pkm/about.sh`) are shared pieces now, taken out of `overview` and `since`, for `--under` and the backlinks of headings to come. Their output is unchanged.

## Released

- [0.4.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.4.0) (2026-11-19)
- [0.3.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.3.0) (2026-11-19)
- [0.2.1](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.2.1) (2026-11-19)
- [0.2.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.2.0) (2026-11-19)
- [0.1.0](https://github.com/Zejnilovic/scripts-pkms/releases/tag/v0.1.0) (2026-11-18)
