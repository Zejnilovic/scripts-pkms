# Settings

Every setting pkm knows, from one list in the code (`lib/pkm/config.sh`). `pkm config` shows each value and where it comes from, and `pkm doctor` reports a key or a value pkm doesn't know.

- **Vault** settings live in the vault's `.pkm/config`, one `key=value` per line. `pkm init` writes `format=1` there.
- **User** settings live in your own pkm config: `~/.config/pkm/config`, or `$XDG_CONFIG_HOME/pkm/config` when that is set.
- **Both** settings can be set in either. The vault's value wins over the user's, and the default applies when neither sets one.

Keys with a `<type>`, `<name>` pattern stand for each key of that shape, for example `folder_recipe` for the type `recipe`.

| Key | Scope | Default | Meaning |
|---|---|---|---|
| `format` | vault | `1` | The layout version of the vault. pkm reads format=1 only. |
| `shared` | vault | `no` | yes when several people write into the vault, so each writer gets their own day pages. |
| `close` | vault | `week` | The cycle the close runs on: week, or the name of a cycle_<name> setting. |
| `cycle_<name>` | vault | - | A cycle of your own: <N>w from a weekday (1w only) or a date, or <N>m from a day of the month (1-28) or a date. |
| `cross_vault` | vault | `no` | yes lets an agent working in another of your vaults read this one, for a brief across vaults. |
| `templates` | vault | `templates` | The folder of this vault's own templates, relative to the vault. |
| `folder_<type>` | vault | `notes` | The folder that new notes of this type go in. |
| `due_soon_days` | both | `7` | The tasks due within this many days, after the overdue ones, come first in pkm tasks. |
| `waiting_days` | both | `7` | A task waiting for longer than this many days comes after the due soon ones in pkm tasks. |
| `limit` | both | `30` | The most listed lines a command prints before the footer; --limit sets it for one run. |
| `writer` | user | - | The name of the person who writes on this machine, for a shared vault. |
| `vault` | user | - | The vault to use when none is given and none is above the current folder. |
| `vault_<name>` | user | - | A named vault, chosen with -V <name>. |

## Other files that shape a vault

- **`.pkmignore`** (in the vault's root) hides files and folders from pkm, in gitignore syntax: one pattern per line, `#` for comments, `folder/`, `*.pdf`, and `!keep.md` to bring back a file. pkm reads only this file. `.gitignore` is not followed, so a folder kept out of git is still part of the vault. Dot files and folders, and `node_modules/`, are always skipped.
- **Templates** are looked up in three places, the first that has the file wins: the vault's templates folder (`templates`), your own `~/.config/pkm/templates/`, then the defaults pkm ships. `pkm templates` lists them, and `pkm templates eject <type>` copies a default to change it.
