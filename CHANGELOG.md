# Changelog

What changed in pkm. The next version's changes are collected here; each released version's notes, including manual steps for existing vaults, are on its GitHub release, linked below.

Version numbers: **major** when a command, option, output format, note name, link syntax, frontmatter field or folder is renamed or removed, since agentic-pkms skills, editors and existing notes depend on them; **minor** for new commands, options and templates; **patch** for fixes. Before 1.0, a minor version may also need manual changes; its notes list them under "Manual steps". Each release is a git tag (`v0.1.0`), and `pkm version` shows which one is installed.

## 0.9.0 (unreleased)

- `pkm help <command>` and `pkm <command> --help` print one command: its summary, its usage and its options. They work outside a vault, and `pkm help <Tab>` completes the command names. An unknown option now points to `pkm help <command>`.
- The site has a command reference, [docs/commands.md](docs/commands.md), made from `pkm help` by `scripts/commands.py`; `scripts/check.py` fails when it is out of date.
- `pkm example [<name>] [<folder>]` copies an example vault, work or family, into a new folder to try the commands on. The examples ship with pkm in `share/pkm/examples`: `make install` and `make dist` copy them there, and nothing is downloaded.
- The `now` vault setting fixes a vault's clock at `YYYY-MM-DD HH:MM`; `PKM_NOW` wins over it. The example vaults set it, so they open on their own day, and `pkm doctor` says when it is set.
- The site has a First steps page, [docs/start.md](docs/start.md): from installing to an example vault, your own vault and your first close, and the tools that go well with pkm.
- On a terminal, a command missing its text, task or note asks for it instead of printing its usage: `pkm done` and `pkm moved` pick an open task, `get`, `backlinks` and `path` pick a note, `new` picks a type and asks the title, and `todo`, `add` and `find` ask for the text. `pkm done <words>` that match several tasks lets you pick one. It picks with fzf when it is installed, else from a numbered list where words narrow the list. The new `picker` setting (auto, fzf, list or off) chooses; scripts, editors and agents, which don't run on a terminal, get the usage error as before. `pkm doctor` lists fzf.
- Tab completion offers the open tasks after `pkm done` and `pkm moved`: the word typed so far keeps the tasks that have it, and Tab puts the task's path:line in its place. zsh shows each task's text in the menu.
- Items in a tool: a note can carry `url` (its address outside the vault) and `items` (the start of its items' addresses), and `[[apollo-web]]#42`, a link followed by `#` and a number, is item 42 of that note: the `items` value with the number added. It works for any tool that numbers its items, such as GitHub, Jira or Azure Boards, with no plugin. See docs/method.md (Links) and docs/format.md (Links 6).
- `pkm url <[[name]]#number | name>` prints an item's address, or a note's `url`, for an editor to open in a browser. It prints only `http(s)` addresses and never goes online. `pkm links --external` lists items by their address, and `pkm check` reports an item whose note has no `items` line, and a `url` or `items` value that is not one `http(s)` address. Manual step: a vault whose notes already use a `url` key for something other than an address gets a check problem for it; rename that key.
- A `repo` template, for a code repository you work on: Now, Decisions and Notes, with `part_of`, `url` and `items`. `pkm overview` shows a repo with the projects, or under the note it is `part_of`. The work example has one, apollo-web, with an item on Thursday's page; the Neovim recipe in docs/editors.md opens an item with `gf`.
- `app` and `team` templates. An app note is software you build or run, which outlasts its projects: Now, Links, Decisions and Notes, and its repositories and projects are `part_of` it, so `--under` finds them all. Its IDs in other systems go in `aliases`, so `[[APP-1001]]` links it. A team note has Now, Next time, People and Links. `pkm overview` shows an app with the projects. In the work example, Apollo and apollo-web are now part of the Acme Portal app, and the web team runs it. See docs/method.md (Where a note belongs).
- Fix: `pkm done` with no words stopped with "ref: unbound variable" under bash 4 and 5 (Linux, or a Mac whose `bash` is Homebrew's) instead of printing its usage.
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
