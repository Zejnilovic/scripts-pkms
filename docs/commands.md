# Commands

<!-- Made by scripts/commands.py from pkm's own help; run it again instead of editing this page. -->

Every pkm command with its usage and options, as `pkm help <command>` prints it in the terminal (`pkm <command> --help`
prints the same). `pkm help` prints them all at once, and `pkm help --all` one line per command.
[The output contract](contract.md) says what each command prints and its exit codes, [the file format](format.md) what
it reads, and [Settings](settings.md) every setting. Commands work from any folder in the vault.

## Calling pkm

The options before the command say which vault to use.

```text
Usage: pkm [--vault <folder>] [-V <name>] <command> [arguments]
       pkm --vaults [<name>,<name>...] tasks|upcoming|since [arguments]
                                the command in each named vault (or those of vaults= in the user config), each under
                                == vault <name> with its own paths; --json adds vault to each record
```

## Capture

### day

The day's page, created when missing; prints its path.

```text
day [YYYY-MM-DD] [--edit]     the day's page, daybook/<year>/<month>/<date>.md, created when missing; prints its
                              path. --edit opens it in $EDITOR. In a shared vault the page is <date>-<writer>.md
```

Options: `--edit`

### add

An entry at the end of the day's Log, printed as path:line.

```text
add [--day <date>] [--file <path>] <text|->
                              an entry at the end of the day's Log: "- HH:MM text", printed as path:line. Several lines,
                              or - for stdin, go under a "### HH:MM" heading, verbatim. --file copies a file to
                              files/<year>/<month>/<date>-<name> (never over another) and the entry links it
```

Options: `--day` `--file`

## Tasks

### todo

A task for today, under its Tasks section; prints path:line.

```text
todo <text> [--due <day>] [--high | --low] [--waiting | --someday | --start <day> | --every <N>d|w|m|y or cycle [--in <note>]]
                              a task for today, under the Tasks section of its page. A day is YYYY-MM-DD, today, tomorrow, +3d,
                              +2w or a weekday. --every makes a routine: 1d, 1w, 1m or 1y, or a cycle from the settings. It goes
                              to the note named routines (created when missing), not to today's page, or with --in <note> to
                              that note's Routines section. --start hides the task
                              until that day; --someday keeps it out of the weekly views
```

Options: `--due` `--high` `--low` `--waiting` `--someday` `--start` `--every` `--in`

### done

Marks the one open task that matches as done, or as dropped with --drop; moves a routine on, or to the day --next gives.

```text
done [<words | path:line>] [--drop | --next <day>]
                              marks the one open task that matches as done ([x]), or as dropped ([-]) with --drop.
                              On a terminal, no words, or words that match several tasks, pick from a list.
                              A routine with an interval, such as (every 1m), keeps its box and moves its due date on
                              (--next <day>: to that day, for a routine done early or late)
```

Options: `--drop` `--next`

### moved

Strikes a task or an event whose date changed and writes it again with the new date; prints path:line: text.

```text
moved <path:line> <when>      strikes a task or an event whose date changed and writes it again with the new date:
                              below it in a note, on today's page from another day's page, linking that day. On a
                              terminal, pkm moved alone picks the task and asks when
```

### tasks

The open tasks of every note, in groups: overdue, due soon, waiting, the rest.

```text
tasks [open | waiting | someday | done [YYYY-MM-DD]] [--link <name>] [--for <who>] [--under <note>] [--stale <days>] [--all]
                              the open tasks of every note, in groups: overdue, due soon, waiting, the rest
                              (docs/contract.md gives the order). A task is a "- [ ]" line outside code
```

Options: `--all` `--link` `--for` `--under` `--stale` `--json` `--abs` `--limit`

## Review

### upcoming

Birthdays, due tasks, events and dates in the next days.

```text
upcoming [<days>] [--ics | --json]
                              due tasks (routines too), events, birthdays, target and warranty dates in the next <days> (14);
                              --ics prints the events, tasks with a time and birthdays as a calendar file
```

Options: `--ics` `--json`

### cycle

The period of a cycle holding a date: its first and last day.

```text
cycle [name] [--date D] [--json]
                              the period of a cycle holding a date (today): name, first and last day; cycles are set in
                              .pkm/config as cycle_<name>=2w from <weekday|date> or cycle_<name>=1m from <day 1-28|date>
```

Options: `--date` `--json`

### since

What happened since a date: notes, log, tasks, marked entries and names.

```text
since [last | YYYY-MM-DD | N | cycle] [--about NAME] [--under <note>] [--sum] [--limit n] [--json]
                              what happened since then, in sections: notes, log, tasks, marked, names; since --seen
                              marks where the next since last starts (.pkm/state)
```

Options: `--about` `--under` `--seen` `--sum` `--json` `--limit`

### close

The close of a period: tasks, open questions, what is due, marked entries, names, quiet notes and ideas.

```text
close [--cycle name] [--date D] [--quarter] [--json]
                              the close of the period holding yesterday: tasks, open questions, due, marked, names,
                              quiet and ideas; new close [--cycle name] [--date D] writes its close page
```

Options: `--cycle` `--date` `--quarter` `--json`

### recall

The recall questions due today or earlier; recall &lt;path:line&gt; yes|no moves a question on the ladder; recall add &lt;note&gt; &lt;question&gt; writes one.

```text
recall [note] [--json] [--limit n]
                              the recall questions due today or earlier, oldest first: path:line: text. A question ends
                              with (recall YYYY-MM-DD <N>d); recall <path:line> yes|no moves it one rung up the ladder
                              (1 3 7 14 30 60 120 days), or back to 1 day
recall add <note> <question> [--answer <text>]...
                              writes a question at the end of the note's ## Questions section, marked to ask tomorrow,
                              with each answer indented below it; prints path:line. Refuses a day or close page, and a
                              question the note already has
```

Options: `--json` `--abs` `--limit` `--answer`

## Notes

### new

A note of a type, made from its template; --set fills its frontmatter, --url a repository's.

```text
new <type> <title> [--name <name>] [--folder <folder>] [--url <address>] [--set key=value ...]
                              a note in notes/ (or folder_<type> from the settings), made from its template; a type with
                              no template is made from the note template. An existing name fails (exit 1) and says so.
                              --set fills a frontmatter key (a part_of must name a note); --folder puts it there;
                              --url fills url, and for a repo also items and the title from a GitHub, Azure DevOps or
                              GitLab address. With part_of_folders=yes a note goes in its parent's folder
```

Options: `--name` `--folder` `--url` `--set`

### set

Sets frontmatter values of a note, such as part_of or status.

```text
set <note> <key=value> ...    sets frontmatter values of a note: replaced in place, or added at the end; an empty
                              value clears one. With part_of_folders=yes a new part_of moves the note into its
                              parent's folder, and the folder of the notes under it goes along. Prints path:line: text
                              of each written line
```

### rename

Renames a note and rewrites every link that names it; --dry-run lists the changes.

```text
rename <old> <new> [--dry-run] [--no-alias]
                              renames a note and rewrites every link that names it, outside code; the old name
                              becomes an alias unless --no-alias; --dry-run lists the changes and writes nothing
```

Options: `--dry-run` `--no-alias`

### mv

Moves notes into a folder; their links keep working.

```text
mv <note> ... <folder>        moves notes into a folder; their links keep working. Both record the move in .pkm/moves.tsv
```

### get

A note, or one section of it, between a header and a footer; --lines takes a range.

```text
get <name>[#Section] [--lines a-b] [--plain]
                              a note, or one section (its heading to the next of the same or a higher level), between
                              "<<<note path lines a-b" and ">>>end"; --lines takes the note's own line numbers;
                              --plain prints it for a reader outside the vault: links as text, no sources or markers
```

Options: `--lines` `--plain`

### post

Copies lines of a page into a note's section, with the page as their source.

```text
post <path:line[-line]> <note>[#Section]
                              copies those lines into the section, verbatim, with " ([[page]])" after the last one,
                              and prints path:line; a missing section is made at the end. Refuses a heading, an open
                              task, or a day or close page as the target (exit 1)
```

### strike

Strikes a line through when it is no longer true, and links today's page.

```text
strike <path:line>            wraps the line's text in ~~ and adds " ([[today's page]])", making today's page if it is
                              missing; refuses a blank line, a heading or a struck line (exit 1)
```

## Find

### backlinks

Every line that links a note, by name, slug or alias.

```text
backlinks <name> [--since YYYY-MM-DD] [--under <note>]
                              every line that links a note, by its file name, slug or alias, archive included, and
                              the lines under a ### heading that links it
```

Options: `--since` `--under` `--json` `--abs` `--limit`

### names

Every note's name, type, path and aliases, by name, from the cache.

```text
names [--type <type>]         every note's name, type, path and aliases, by name, from the cache. Day and close pages
                              are left out unless --type says them: names --type person lists the people
```

Options: `--type` `--json` `--abs` `--limit`

### index

Brings the cache up to date; --rebuild starts it again.

```text
index [--rebuild]             brings the cache (.pkm/cache, or PKM_CACHE_DIR) up to date and says what changed
```

Options: `--rebuild`

### path

The file a name, slug, alias or link points to.

```text
path <name>                   the path of the note, attachment or alias a [[name]] link points to, archive included
```

Options: `--json` `--abs` `--limit`

### url

The address outside the vault an item ([[name]]#42) or a note's url line points to.

```text
url <[[name]]#number | name>  the address outside the vault: an item's (the note's items line and the number), or the
                              note's url line; prints only http(s) addresses and never goes online
```

### find

The lines with every word, in any order.

```text
find [--live] <word> [<word>...]
                              the lines with every word, in any order, as path:line: text. Smart case: a word
                              with a capital letter matches exactly. The archive is searched too, unless --live
```

Options: `--live` `--json` `--abs` `--limit`

### list

The notes whose frontmatter matches.

```text
list [<field>=<value> ...] [--show <field>,...] [--all] [--quiet <days>] [--under <note>]
                              notes whose frontmatter matches, from the cache: path, type, title, then the --show fields;
                              --quiet lists those no day page in the last <days> days links
```

Options: `--all` `--show` `--quiet` `--under` `--json` `--abs` `--limit`

### overview

The shape of the vault: areas, projects and resources, each with the notes that are part of it.

```text
overview [--json]             the shape of the vault: each area with the notes that are part_of it, then projects,
                              resources (courses, topics, sources) and other notes with notes under them, then the
                              archive's count; a line is path:<title line>: <titles from the top> (<type>, <status>)
```

Options: `--json`

### tags

Every tag with its count.

```text
tags [--json]                 every tag with its count
```

Options: `--json`

### links

Each web address in the notes, with its place (links --external).

```text
links --external [note]       each http(s) address outside code, as path:line: address (links to notes: backlinks)
```

Options: `--external` `--json` `--abs` `--limit`

## Check

### check

Broken links, duplicate names, alias clashes, secrets, merge conflicts and notices.

```text
check [--urls]                broken links, duplicate names, secrets and merge conflicts (exit 1), and notices;
                              --urls also GETs each web address (curl, 5 s, 8 at once): no answer, 404 or 410 (exit 1)
```

Options: `--json` `--abs` `--limit` `--urls`

### evidence

Each summary line must link its source; --verify checks the links, paths and lines.

```text
evidence [--verify] <note | ->
                              each summary line (## Now, a close page whole, or stdin) must link its source (exit 1):
                              a day page, a source note, or path:line; --verify checks the links and lines exist
```

Options: `--verify`

## Setup

### doctor

The tools pkm uses, and the settings.

```text
doctor                        the tools pkm uses and the settings: what is missing or wrong (exit 1)
```

### init

Sets up a vault: .pkm/config, .pkm/.gitignore and .pkmignore.

```text
init                          sets up a vault in this folder, or in the one --vault names: .pkm/config, .pkm/.gitignore, .pkmignore; refuses
                              to overwrite any of them
```

### example

Copies an example vault that ships with pkm into a new folder, to try the commands on.

```text
example [<name>] [<folder>]   copies an example vault that ships with pkm, work (the default) or family, into a new
                              folder (pkm-example-<name>), to try the commands on a vault with weeks in it; its
                              .pkm/config sets now, so it opens on its own day. Refuses a folder that exists (exit 1)
```

### vault

The vault's folder.

```text
vault                         the vault's folder
```

### vaults

The named vaults of the user config.

```text
vaults [--json]               the named vaults of the user config, each with ok or missing
```

Options: `--json`

### config

Every setting, its value and where it comes from; config &lt;key&gt; &lt;value&gt; sets one.

```text
config [<key>]                every setting with its value and where it comes from (vault, user or default), or one
config <key> <value> [--user] sets one: in .pkm/config, or the user config for a user setting (--user for one of
                              both); replaces its line or appends one, and prints <file>:<line>: key=value
```

Options: `--user`

### templates

Each template type and where it comes from.

```text
templates                     each template type with where it comes from (vault, user or default)
templates eject <type> [--user]
                              copies the default template into the vault's templates folder (or the user's), and
                              never overwrites one (exit 1)
```

Options: `--user`

### version

The pkm release; --require checks a minimum.

```text
version [--require <x.y>]     the pkm release; with --require, exit 0 when it is at least x.y, else 1 and no output
```

Options: `--require`

### help

The usage text; --all lists every command.

```text
help [--all | <command>]      this text; --all lists every command as name<TAB>group<TAB>summary; <command> gives
                              its summary, usage and options, the same as pkm <command> --help
```

Options: `--all`

### completion

The shell's tab completion script, for bash or zsh.

```text
completion bash|zsh           the shell's tab completion script, for example in ~/.zshrc: source <(pkm completion zsh)
```

## Listings, settings and the clock

```text
Listings: find, backlinks, path, list, tasks and check take --json (JSON Lines), --abs (absolute paths) and --limit n
(default 30). A listing with no results exits 1. since, close, overview, upcoming, tags, cycle and vaults take --json. docs/contract.md is the interface; pkm help --all lists the commands, docs/commands.md describes each.
On a terminal, a command missing its text, task or note asks for it: done, moved, todo, add, find, get, backlinks,
path and new. It picks with fzf when installed, else from a numbered list (the picker setting; off never asks).
Without a terminal, as in scripts, editors and agents, a missing argument is a usage error (exit 2).
Settings: docs/settings.md lists every key. .pkm/config is the vault's, the user's config is ~/.config/pkm/config.
.pkmignore in the vault hides files and folders from pkm, in gitignore syntax; .gitignore is not followed.
PKM_NOW=YYYYMMDDHHMMSS fixes the clock, for tests and for backfilling.

Examples: pkm day
          pkm todo "Send [[jane-doe]] the offer" --due friday --high
          pkm new person "Jane Doe"
          pkm list type=project status=active
```
