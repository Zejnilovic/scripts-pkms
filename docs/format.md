# The pkm file format: Format 1

This is the file format pkm reads and writes, version 1. A vault says which version it uses in `.pkm/config` (`format=1`, written by `pkm init`). pkm reads Format 1 only, and `pkm doctor` reports any other value. A change to any rule here is a new format number and a major pkm release, except a new key or folder that vaults may use or leave out, which keeps the number: pkm 0.2.0 added `part_of` and `files/` to Format 1. The reasons are in [method.md](method.md).

## 1. Text

1. Files are UTF-8. Names may contain accents; pkm sorts by bytes (`LC_ALL=C`).
2. A line ends in LF or CRLF. pkm reads both, and a line it adds uses the line ending of the file's first line.
3. A byte order mark at the start of a file is ignored when reading and kept when editing.
4. Code is not read for links, tasks or web addresses: a fenced block (```` ``` ```` or `~~~`) or an inline code span.

## 2. Folders and files

| Path | What it is |
|---|---|
| `daybook/<YYYY>/<MM>/<YYYY-MM-DD>.md` | A day page. In a shared vault, `<YYYY-MM-DD>-<writer>.md` |
| `notes/<name>.md` | A note. A type's new notes go in the folder its `folder_<type>` setting names, when it is set; otherwise in `notes/` |
| `closes/<YYYY>/<first day>-<cycle>.md` | A close page |
| `archive/` | Finished notes, moved here with their names kept |
| `files/<YYYY>/<MM>/<YYYY-MM-DD>-<name>` | A file that arrived on a day, linked from that day's page (`add --file`). Any other file in the vault works too: a link names it by its file name |
| `templates/` | The vault's templates (the folder is set by `templates`) |
| `.pkm/config` | The vault's settings |
| `.pkm/cache/`, `.pkm/state`, `.pkm/moves.tsv` | pkm's own files: the cache (a speed-up that is safe to delete), the date of the last `since --seen`, and the log of renames and moves |
| `.pkmignore` | Files and folders pkm skips, in `.gitignore` syntax |

Dot files and folders, and `node_modules/`, are always skipped. Files named `AGENTS.md` and `CLAUDE.md`, and `*.proposal.md`, are not notes.

## 3. Names

1. A note's name is its file name without `.md`.
2. Names are unique in the vault, in any folder. Two things with one name are told apart as `<name>-<word>`.
3. `pkm new` makes names of lowercase ASCII words joined by hyphens, with accents removed. Other names work, and `check` gives a notice for them.

## 4. Pages and entries

A day page has the sections `## Tasks` and `## Log`. A `## ` section runs to the next `## ` heading or the end of the file.

1. An entry is a list line in the Log: `- HH:MM text`, with a 24-hour time.
2. A block of several lines is an `### HH:MM` heading, then the lines as written. It ends at the next heading, or at a blank line after its lines that is followed by an entry (`- HH:MM …`); a blank line, then an untimed line such as `- Decided: …`, stays in it. Its lines are about what its heading links. `add` writes a blank line before an entry that follows a block.
3. A mark follows the time: `- 09:12 ! text` (important), `Decided:` (a decision), `Idea:` (an idea). An entry ending in `?` is an open question.
4. A struck line is `~~text~~`, with the day it was learned in a link after it: `([[2026-11-12]])`.
5. A posted line ends with the day it came from: `text ([[2026-11-10]])`.

## 5. Frontmatter

A note may start with frontmatter: a line `---`, the keys, and a closing line `---`. These keys have meaning to pkm:

| Key | Use |
|---|---|
| `type` | The kind of note. Default: `day` in `daybook/`, `close` in `closes/`, otherwise `note`. A `type: list` note's boxes are not tasks. `overview` groups notes by the type of their top note: `area`; `project`, `writing` and `repo`; `course`, `topic` and `source` |
| `part_of` | The one note this note belongs to, as a name (`part_of: home`) or a link (`part_of: "[[home]]"`). It is a link (see 6). A list (`[home, car]`), a note that names itself and a circle are `check` problems |
| `aliases` | Other names for the note: `[Jane, J. Doe]`, or indented `  - Jane` lines below the key |
| `status` | `upcoming` skips a note whose status is `done`, `dropped`, `published`, `sold`, `gone` or `archived`, and so does `overview` for a top note other than an area. `idea` marks a note for something not started |
| `birthday`, `target`, `deadline`, `warranty` | Dates that `upcoming` lists. A birthday recurs yearly on its month and day |
| `url` | The address of what the note is about, outside the vault, such as a repository: one `http://` or `https://` address. `pkm url <name>` prints it |
| `items` | The start of the address of the note's numbered items, one `http://` or `https://` address; an item's address is this value with the item's number added at the end (see 6) |

Any other key is stored, and `pkm list key=value` matches it. The title is the first line that starts with `# ` after the frontmatter, or the file name without `.md` when there is none.

## 6. Links

1. `[[name]]`, `[[name|shown text]]`, `[[name#Section]]` and `[[name^block]]` link a note. A folder before the name is ignored.
2. A link resolves in this order, anywhere in the vault: the file name; the slug of the link's text (`[[Jane Doe]]` is `jane-doe`); an alias in a note's frontmatter.
3. A day page is linked by its date: `[[2026-11-10]]`, or `[[2026-11-10-sam]]` in a shared vault.
4. A web address is any `http://` or `https://` address outside code.
5. A `part_of:` line in the frontmatter is a link to the note it names, written with or without brackets: `backlinks` lists it, `check` reports it when it names no note, and `rename` rewrites it.
6. An item is a link followed at once by `#` and digits, outside code: `[[apollo-web]]#42`, or `[[apollo-web|the portal]]#42`. The link is a link to the note as in 1; a link with a section or a block (`[[apollo-web#Risks]]#42`) is not an item. The item's address is the note's `items` value with the digits added at the end. `url` prints it and `links --external` lists it. `check` reports an item whose note has no `items`, and an `items` or `url` value that is not one `http://` or `https://` address; `url` prints nothing else.

## 7. Tasks

1. A task is a line that starts with optional spaces or tabs, then `- [ ]`, `- [x]` or `- [X]` (done), or `- [-]` (dropped), outside code and outside a `type: list` note.
2. Not a task: `* [ ]`, `- [?]`, and a box followed by a struck text (`- [ ] ~~text~~`).
3. Markers sit in parentheses after the text. They may come in any order:

| Marker | Meaning |
|---|---|
| `(due <date>)` or `📅 <date>` | Due date |
| `(waiting <date>)`, `(waiting)` | Waiting since the date; without a date, it counts as waiting |
| `(someday)` | Someday: left out of the weekly views; shown by `tasks someday` and the quarterly close. With `(start <date>)`, it is an ordinary task from that date |
| `(high)`, `(low)` | Priority |
| `(start <date>)` | Hidden until the date: left out of `tasks`, `since`, `close` and `upcoming`'s due lines (`upcoming` lists it by its start date). `tasks --all` shows it, marked `starts <date>` |
| `(every <rule>)` | A routine, see 8 |
| `(at <when>)` or `(@ <when>)` | A time: the task is due on the day of its `(at …)` unless it has a `(due …)`, see Events |
| `(for <who>)` | Whose move it is: a link, `(for [[jane-doe]])`, or the name of a writer of a shared vault, `(for sam)`. Without one, a task on a writer's day page is that writer's |
| `(done <date>)`, `(dropped <date>)` | Closed on the date. `done` writes these |

4. A date is `YYYY-MM-DD`. On a day page it may also be a weekday (`friday`), `today`, `tomorrow`, `+3d` or `+2w`, counted from that page's date. `todo` writes the date it resolved.
5. **The marker keys.** A key is lowercase and is the first word inside the parentheses. `due`, `start`, `waiting`, `someday`, `high`, `low`, `done` and `dropped` belong to tasks; `recall` to questions; `at` and `@` to events and tasks (see Events); `every` to routines and events; `until` and `skip` to events that come back; `for` to tasks and questions, followed by a link or a writer's name (whose move it is: on a task they do it, on a question they decide), and a `(for …)` on any other line is a `check` problem. A writer is one whose name ends a day page's name in `daybook/`. A duration, `(1h30)`, `(1h)` or `(40m)`, is time spent (6). Parentheses whose first word is not a key are text. `at`, `@` and `for` are also everyday words, so their parentheses are text unless the next word could start a value: a date, a weekday, `today`, `tomorrow` or `+…` after `at` or `@`, as in `(at friday 14:00)` but not `(at the office)`; a link or a writer's name after `for`, as in `(for [[jane-doe]])` but not `(for now)`. Any other key whose value can't be read is a `check` problem.

6. **Time spent.** A duration is `(<h>h)`, `(<h>h<mm>)` with two digits below 60, or `(<m>m)`, with no space and no decimals: `(1h30)`, `(1h)`, `(40m)`. Any other form, such as `(1.5h)` or `(1h5)`, is text. An entry or a task whose text, after its list mark and box, starts with a range, `- 09:00-11:30 Workshop` (the dash may be `–`), is time spent too: an end before its start is on the next day, and the same start and end is none. When a line has both, the duration counts. A line with `(at …)` is an event, a time something will happen, and is never time spent. A struck line is no longer true and doesn't count.

## 8. Routines

A routine is a task with `(every <rule>)`, and it lives in a note, not on a day page: `check` flags one on a day page, since a day page is a record. `todo --every` writes it to the note named `routines`, which it creates when there is none, or with `--in <note>` to the end of that note's `## Routines` section. The rule is one of:

- an interval: a number and `d`, `w`, `m` or `y`, such as `(every 1m)`. Its task needs a due date. `done` moves the due date on by one interval and keeps the box open;
- a cycle name from `.pkm/config`, such as `(every sprint)`. Without a due date, it is due on the last day of the period holding today. `done` moves it on by one period.

The rules `day`, `weekday`, `monday, thursday`, `month on <1-31>` and `year on <MM-DD>` are no longer routines: `check` flags them with how to write the routine now, as `(every 1w)` with a due date, or as a cycle.

### Recall questions

A recall question is an entry that ends with a recall mark: `(recall <date> <N>d)`, the day to ask it and the current interval in days, such as `- When is the median better than the mean? (recall 2026-11-16 7d)`. The indented lines under it are the answer. `pkm recall add <note> <question> --answer <text>` writes one at the end of the note's `## Questions` section, as the owner's words. Marks outside code count; a struck line never comes up. `recall` lists the questions due on or before today; `recall <path:line> yes|no` moves one up the ladder of 1, 3, 7, 14, 30, 60 and 120 days, or back to 1 day. A recall line never shows in tasks, since, close or upcoming.

### Events

An event is something that happens at a time. It is a line outside code and frontmatter with `(at <when>)` or `(@ <when>)` after its text; the two are the same marker. Lines on close pages, in `archive/`, and in a note whose `status` is closed (as for `upcoming` in 5) are not read as events.

1. `<when>` is one of: `<date>` (the whole day); `<date> HH:MM`; `<date> HH:MM-HH:MM`; `<date> to <date>` (several whole days). Times use the 24-hour clock and are local: pkm knows no time zones. A range's dash may be `-` or `–`; an end before its start is on the next day, as in a night shift, `22:00-06:00`. The last day of `to` comes after the first.
2. The date follows 7.4: on a day page it may be relative, counted from that page's date.
3. Without a task box, the line is an event: it is never in `tasks` or the close's `== tasks`, and never overdue. With a box, it is a task with a time, due on the event's first day unless it has its own `(due …)`.
4. An event comes back with `(every <n><d|w|m|y>)`, an interval and never a cycle, in a note and without a box. Its times are counted from the date in its `(at …)`, each from that date rather than from the time before: from 2026-01-31, `(every 1m)` gives 2026-02-28, then 2026-03-31. `(until <date>)` is the last day it can happen, and `(skip <date>)` takes out the time on that date; a line may hold several `(skip …)`. pkm never rewrites the line.
5. A struck line is not an event. An event that changes is struck, and written again with its new time. An event stays where it was written: `post` refuses one, as it does an open task, since a copy would show twice in `upcoming` and in a calendar. A line that links the day it came from keeps that link before its markers: `- Dentist ([[2026-11-12-sam]]) (at 2026-12-04 10:00)`.
6. `check` reports an `(at …)` or `(@ …)` whose next word starts a value (5) but that can't be read as a whole, such as `(at friday 25:00)`; a relative date outside a day page; a time range whose start and end are the same; an `(every …)` with an `(at …)` on a day page or in a task box, or one that isn't an interval; and `(until …)` or `(skip …)` anywhere but on an event that comes back.

## 9. Cycles and the close

1. The week is built in: Monday to Sunday.
2. A cycle of your own is set in `.pkm/config`: `cycle_<name>=<N>w from <weekday or date>` (a weekday only for `1w`), or `cycle_<name>=<N>m from <day 1-28 or date>`.
3. A cycle name is lowercase letters, digits and hyphens. It is not `week`, `last`, `today`, `yesterday`, or all digits.
4. `close=<name>` chooses the cycle the close runs on. The default is `week`.
5. The close covers the period that holds yesterday. Its page is `closes/<year>/<first day>-<cycle>.md`, titled with the cycle and its first day, such as `# Week of 2026-11-09`.

## 10. Shared vaults

`shared=yes` in `.pkm/config` makes each day page carry its writer's name. Each person sets `writer=<name>` in their own user config. Without it, pkm refuses to write a day page.

## 11. Settings and ignored files

1. A settings file has one `key=value` per line. Blank lines and lines starting with `#` are ignored. When a key is repeated, its last value counts.
2. The vault's settings are in `.pkm/config`; yours, which apply to every vault, are in `~/.config/pkm/config` (or `$XDG_CONFIG_HOME/pkm/config`). A setting that either file may hold takes the vault's value when both set it.
3. The keys are listed in [settings.md](settings.md). A key that pkm does not know, or a vault key in your config, is reported by `pkm doctor`.
4. `.pkmignore` follows `.gitignore` syntax: one pattern per line, `#` for comments, `folder/`, `*.pdf`, and `!keep.md` to bring a file back. `.gitignore` is never read.
