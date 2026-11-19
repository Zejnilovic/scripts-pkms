# pkm

pkm is a command line for plain Markdown vaults. A vault is a folder of Markdown files kept by the [Daybook Method](docs/method.md): one page a day, short entries, tasks, links between notes and a close each week. pkm finds the day's page, the open tasks, the links and what the close leaves open. It needs no AI, no editor and no account. Editors, scripts and agents can call the same commands.

The method, its example vaults and these docs are also a site: [zejnilovic.github.io/scripts-pkms](https://zejnilovic.github.io/scripts-pkms/).

## Install

```bash
brew install zejnilovic/tap/pkm
```

Homebrew installs ripgrep and jq with it, and tab completion for bash and zsh. Without Homebrew, pkm needs bash (macOS and Linux; Git Bash on Windows), [ripgrep](https://github.com/BurntSushi/ripgrep) and [jq](https://jqlang.org):

- **From a clone:** `make install` copies pkm to `~/.local` and links `~/.local/bin/pkm`. Use `make install PREFIX=<folder>` for another place.
- **From a release tarball:** unpack `pkm-<version>.tar.gz` and run `sh install.sh [--prefix <folder>]`. It installs from the folder it is in and downloads nothing.

Without Homebrew, turn on tab completion in your shell's startup file: `source <(pkm completion zsh)` in `~/.zshrc` (after `compinit`), or `source <(pkm completion bash)` in `~/.bashrc`. It completes commands, options, note names, template types, cycles and named vaults.

Then run `pkm doctor`. It lists the tools pkm uses and any setting it does not understand. Exit 0 means it is ready.

## Start

```bash
cd ~/notes
pkm init                                   # makes this folder a vault: .pkm/ and .pkmignore
pkm day                                    # today's page; prints its path
pkm add "Call with Jane Doe about Apollo"  # an entry at the end of today's Log
pkm find Apollo                            # lines that have every word
pkm tasks                                  # open tasks: overdue, due soon, waiting, the rest
pkm close                                  # what the week leaves open; pkm new close writes the page
```

pkm finds the vault from the current folder upward, or from `--vault <folder>`, `PKM_VAULT`, or a named vault. The [Daybook Method](docs/method.md#the-practice) explains the pages.

## Several vaults

Keep one vault for each part of your life, such as work and family. Name them in your user config, `~/.config/pkm/config`, with `vault_work=<folder>` lines, then choose one with `-V`: `pkm -V family add "Paid the rent"`. `pkm vaults` shows each one. Vaults never link to each other.

## Settings and ignored files

Settings are `key=value` lines in the vault's `.pkm/config` or in your user config. `pkm config` shows each value and where it comes from. [docs/settings.md](docs/settings.md) lists every key. A `.pkmignore` in the vault hides files and folders from pkm, in `.gitignore` syntax; pkm does not read `.gitignore`.

## Extensions

A program named `pkm-<name>` on your PATH runs as `pkm <name>`, with the same arguments, the same as git does. `pkm help --all` lists the ones it finds. Built-in commands always win. pkm looks for extensions on PATH only, never in the vault: a vault cloned from git could otherwise carry a script that runs when someone mistypes a command.

## Editors

Neovim, VS Code and Obsidian all call the same commands. [docs/editors.md](docs/editors.md) has a recipe for each, and a Neovim plugin is planned in this repo.

## The interface

The commands, what they print, their exit codes and their options are the interface, and [docs/contract.md](docs/contract.md) describes all of them. Exit 0 means it worked, 1 means a check found problems or nothing matched, and 2 means a wrong call. Changing any of it is a major version; [CHANGELOG.md](CHANGELOG.md) says which.

The files pkm reads are described in [docs/format.md](docs/format.md) (Format 1).

## Commands

Run `pkm help` for the usage, or `pkm help --all` for the list. Commands work from any folder in the vault.

| Command | Does |
|---|---|
| `day [YYYY-MM-DD] [--edit]` | The day's page, `daybook/<year>/<month>/<date>.md`, created when missing; prints its path. In a shared vault the page is `<date>-<writer>.md`. `--edit` opens it in `$EDITOR` |
| `add [--day <date>] [--file <path>] <text\|->` | An entry at the end of the day's Log, `- HH:MM text`; prints `path:line`. Several lines, or `-` for stdin, go under `### HH:MM` verbatim. `--file` copies a file to `files/<year>/<month>/<date>-<name>`, never over another, and the entry links it |
| `todo <text> [--due <day>] [--high\|--low] [--waiting\|--someday\|--start <day>\|--every <N>d\|w\|m\|y or cycle [--in <note>]]` | Adds a task under the Tasks section of the day's page; prints `path:line`. `--every` takes an interval (`1w`) or a cycle name, and writes the routine to the note named `routines` (created when missing), not to the day's page; with `--in <note>`, to that note's Routines section |
| `done <words\|path:line> [--drop]` | Marks the one open task that matches as done, or dropped with `--drop`. A routine with an interval, such as `(every 1m)`, keeps its box and moves its due date on |
| `tasks [open\|waiting\|someday\|done [<since>]] [--link <name>] [--stale <days>] [--all]` | Open tasks of every note, in groups: overdue, due soon, waiting, the rest. `--all` includes `archive/` |
| `upcoming [<days>] [--ics]` | Due tasks, routines included, events, and birthdays, target and warranty dates in the next days; `--ics` writes the events, tasks with a time and birthdays as a calendar file |
| `new <type> <title> [--name <name>]` | A note in `notes/`, or the type's folder from its setting, made from its template; prints its path. `new close` writes the close page |
| `names [--type <type>]` | Every note's name, type, path and aliases, from the cache. `--type person` lists the people |
| `backlinks <name> [--since <date>]` | Every line that links a note, by its file name, slug or alias |
| `path <name>` | The file a name, slug, alias or link points to |
| `find [--live] <word> [<word>...]` | Lines with every word, in any order, as `path:line: text`. Smart case. Searches `archive/` unless `--live` |
| `list [<field>=<value> ...] [--show <fields>] [--quiet <days>]` | Notes whose frontmatter matches, from the cache: path, type, title, then the fields asked for. `--quiet <days>` lists notes that no day page has linked in that many days |
| `overview [--json]` | The shape of the vault: each area with the notes that are `part_of` it, as a tree, then projects, resources (courses, topics, sources) and other notes with notes under them, then the archive's count. A line is `path:<title line>: <titles from the top> (<type>, <status>)` |
| `tags` | Every tag with its count |
| `index [--rebuild]` | Brings the cache in `.pkm/cache` up to date. The cache is a speed-up only |
| `rename <old> <new> [--dry-run] [--no-alias]` | Renames a note and rewrites every link to it, keeping the shown text. The old name becomes an alias unless `--no-alias`. `--dry-run` writes nothing |
| `mv <note> <folder>` | Moves a note into a folder, keeping its name and its links working |
| `check [--urls]` | Broken links, duplicate names, alias clashes, secrets and merge conflicts; notices for links that work only by slug or alias. `--urls` also checks that web addresses answer (needs curl) |
| `evidence [--verify] <note\|->` | Each summary line, such as a note's `## Now`, must link its source. `--verify` checks that the links and lines exist |
| `links --external [note]` | Each web address in the notes, outside code, as `path:line: address` |
| `cycle [name] [--date D]` | The period of a cycle holding a date: its name, first and last day. The week is built in; your own cycles are set in `.pkm/config` |
| `since [last\|YYYY-MM-DD\|N\|cycle] [--about NAME] [--limit n] [--json]` | What happened since a date: notes, log lines, tasks, marked entries and names. `since --seen` marks where the next `since last` starts |
| `close [--cycle name] [--date D] [--quarter] [--json]` | The close of the period holding yesterday: tasks, open questions, what is due, marked entries, names with no note, quiet projects and people, and ideas |
| `get <name>[#Section] [--lines a-b]` | A note, or one section of it, between `<<<note` and `>>>end` lines |
| `post <path:line[-line]> <note>[#Section]` | Copies those lines verbatim into the section, with `([[day]])` after the last one |
| `strike <path:line>` | Wraps the line in `~~` and adds `([[today's page]])`, for a line that is no longer true |
| `init` | Sets up a vault in this folder: `.pkm/config`, `.pkm/.gitignore` and `.pkmignore`. Never overwrites them |
| `vault`, `vaults` | The vault's folder; the named vaults in your config, each `ok` or `missing` |
| `config [<key>]` | Every setting with its value and where it comes from |
| `recall [note]`, `recall <path:line> yes\|no`, `recall add <note> <question>` | The recall questions due today or earlier, as `path:line: text`, oldest first. `recall <path:line> yes` moves a question up the ladder (1, 3, 7, 14, 30, 60, 120 days) and `no` back to 1 day. `recall add` writes a question at the end of a note's `## Questions`, due tomorrow, with its answers indented below. A question ends with `(recall YYYY-MM-DD <N>d)` |
| `templates`, `templates eject <type> [--user]` | Each template and where it comes from; `eject` copies a default so you can change it |
| `doctor` | The tools pkm uses, and the settings: what is missing or wrong |
| `version [--require <x.y>]` | The pkm release; with `--require`, exit 0 when it is at least `x.y` |
| `help [--all]` | The usage text, or every command with its group |
| `completion bash\|zsh` | The shell's tab completion script; Homebrew installs it for you |

## Templates

New notes are made from templates in the vault's `templates/` folder, then your `~/.config/pkm/templates/`, then the defaults: [day](share/pkm/templates/day.md), [note](share/pkm/templates/note.md), [person](share/pkm/templates/person.md), [project](share/pkm/templates/project.md), [area](share/pkm/templates/area.md), [topic](share/pkm/templates/topic.md), [source](share/pkm/templates/source.md), [list](share/pkm/templates/list.md), [close](share/pkm/templates/close.md), [course](share/pkm/templates/course.md), [coaching](share/pkm/templates/coaching.md), [writing](share/pkm/templates/writing.md) and [item](share/pkm/templates/item.md). `pkm templates eject <type>` copies one into the vault to change it. A type of your own needs only a template with `type: <type>` in it.

## Maintaining pkm

Rules for contributors are in [AGENTS.md](AGENTS.md). Run `make check` before committing.
