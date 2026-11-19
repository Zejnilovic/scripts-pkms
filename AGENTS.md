# Maintaining this repository

This repo is pkm, the command line for plain Markdown vaults: `bin/pkm`, its modules in `lib/pkm/` and the default templates in `share/pkm/`. Editors, agents and people call the same commands. The agents and skills that call pkm are in [agentic-pkms](https://github.com/Zejnilovic/agentic-pkms).

## Before committing

1. Run `make check`: `python3 scripts/check.py` (commands, README table, templates, version, changelog, shell syntax) and `python3 -m unittest discover -s tests`. CI runs both on Linux and macOS.
2. Script changes are test-first: add or change a test in `tests/`, watch it fail, then change the file under `lib/pkm/` that holds the command.
3. For a local Linux run, with an image on the owner's machine (CI runs the same on push):

   ```bash
   docker run --rm -v "$PWD":/src:ro pkm-linux-test:local bash -c 'cp -r /src /work && cd /work && python3 -m unittest discover -s tests'
   ```

## Portability

1. pkm runs with bash 3.2 (macOS) and Git Bash (Windows). Don't use bash 4 syntax (`mapfile`, `${x,,}`, `declare -A`, `|&`) or GNU-only tools and flags (`sed -i`, `readlink -f`, `grep -P`, `sort -V`, `xargs -r`, gawk-only functions).
2. `tests/test_edge.py` (class `Portability`) greps the scripts for these and fails on a match. Dates go through `day_add` and `day_fmt` in `lib/pkm/dates.sh`, which handle GNU and BSD `date`. Dates read per line, in a scan, go through `awk_dates` in the same file instead: civil-date arithmetic and the day words of `parse_day`, with no `date` process per line (`tests/test_dates.py` checks it against Python's calendar). Only `dates.sh` and `index.sh` may choose between GNU and BSD flags. Markers are read in one place, the line scanner in `lib/pkm/lines.sh` (`line_records`): a command that needs tasks, events or other marked lines filters its records instead of parsing lines itself. `tests/test_golden.py` keeps the output of `tasks`, `upcoming`, `close`, `since` and `check` on the example vaults and `tests/golden/zoo`; after a change in output on purpose, run it with `PKM_GOLDEN=update` and read the diff.
3. The tools a vault needs are ripgrep and jq, and git for a history. `pkm doctor` lists them and CI installs them. Detect a tool that only some vaults need with `command -v`, and report it in `doctor`.
4. User text reaches awk through `ENVIRON`, never `-v`, so backslashes survive.

## Line endings and byte order marks

1. Files are read as they are. `scan` drops a carriage return at the end of each line and a byte order mark at the start of a file.
2. Edits keep the file's own line ending (`eol_of`) and its byte order mark. Tests: `CarriageReturns` and `FrontmatterAndBom` in `tests/test_edge.py`.

## The output contract

`docs/contract.md` is the interface. Skills, editors and people depend on it.

1. A new command or option is a minor version. Renaming or removing one, or changing what it prints, is major.
2. Results print one per line as `path:line: text`, with paths relative to the vault. Exit 0 when it worked, 1 when a check finds problems or nothing matches, 2 for a wrong call (errors go to stderr).
3. Every command in `pkm help --all` has a row in `docs/contract.md` (`tests/test_contract.py` checks it) and in the README's command table (`scripts/check.py` checks it). Update the usage text at the top of `bin/pkm` as well.
4. Settings: change the list in `lib/pkm/config.sh` and the table in `docs/settings.md` together. A test keeps them equal.
5. The file format is `docs/format.md` (Format 1). A change to any of its rules is a new format number and a major version.

## The script is an interface

- `pkm version` prints the release, so callers can tell which commands a vault has.
- Editors call the same commands. Lines of `path:line: text` are read by Vim's quickfix list and by VS Code's problem matchers, so keep that shape.
- [docs/editors.md](docs/editors.md) shows the recipes. Check each command in them against `pkm help --all` when a command changes.

## Versions and releases

1. **Every change to `bin/`, `lib/` or `share/` belongs to a version.** If the current version is already released (tagged), start a new one before or with the change: `bash scripts/bump.sh <version>`. It updates `VERSION`, `pkm_version` in `lib/pkm/core.sh`, and adds an "(unreleased)" `CHANGELOG.md` heading with a TODO. Replace the TODO with what changed.
2. **Pick the number by impact on vaults.** Patch for fixes, minor for new commands, options, templates or settings, major for renamed or removed ones and changed output. A change to note names, link syntax, frontmatter fields, folders or the file format is major: vaults are full of notes that follow the old one.
3. **Several changes can share one unreleased version.** Add a bullet to its `CHANGELOG.md` entry for each.
4. **To release**: commit and push everything to the default branch, then run the **Release** workflow (Actions tab, or `gh workflow run release.yml`; `-f dry_run=true` pushes nothing). It runs the checks, moves the entry into a GitHub release, commits and tags `v<version>`. Don't release by hand. When agentic-pkms needs the new release, say so in its next version.
5. **The tarball**: `make dist` writes `dist/pkm-<version>.tar.gz` and its `.sha256`. The release workflow attaches both to the GitHub release.
6. **The Homebrew formula** in `packaging/pkm.rb` is the template for `Formula/pkm.rb` in Zejnilovic/homebrew-tap. The Release workflow fills its `url` and `sha256` with `scripts/formula.sh` from the tarball it built, pushes it to the tap with the `HOMEBREW_TAP_TOKEN` secret, then installs from the tap on macOS and runs `brew test` and `brew audit`. Here the placeholder stays. The formula installs the completions from `pkm completion`; `ruby -c` checks its syntax where ruby is installed.
7. **Tab completion** comes from `command_table` and `command_options` in `lib/pkm/cmd/help.sh`, so a new command or option completes with no change; a new argument kind (note names, cycles) goes in `cmd_complete` in `lib/pkm/cmd/completion.sh`, with a test in `tests/test_completion.py`.
8. **pkm is not an agd kit.** It has no `kit/`, no `packs.txt` and no `min-agd`, and nothing here installs through agd. Vaults get pkm from a release tarball, a clone or Homebrew.

## Compatibility

- **Editors**: vaults are plain Markdown with `[[name]]` links and YAML frontmatter, readable in any editor. Never require an editor or plugin; the script is the shared logic, and editors call it.
- **Neovim**: a plugin is planned in this repo. It stays thin: the rules stay in pkm, and it reads the script's output.
- **Templates** use `{{title}}`, `{{date}}` and `{{time}}`, which Obsidian's core templates also fill, plus `{{slug}}`, `{{name}}` and a `{{list}}` line that only the script fills. They carry no marker, since every new note copies them. `scripts/check.py` checks that each template names its type. agentic-pkms skills rely on their sections, such as `## Now` and `## Log`: renaming one is major.

## Content rules

- **The vault is the owner's.** The script never deletes a note, never rewrites the owner's words, and only reads and writes local files. Anything that files text in bulk works like `pkm post`: the owner or an agent picks the lines, the script copies them verbatim with their source, and nothing is lost.
- **Generic only.** No real names, places, employers or other personal facts in pkm, its tests or its docs: use made-up examples such as Jane Doe, Apollo and Acme.
- **Docs for people** are `README.md` and `docs/` (`docs/method.md` is the why). Keep `docs/format.md`, `docs/contract.md`, `docs/settings.md` and `docs/editors.md` in step with the code.
- **The site** is built from `docs/` by `mkdocs.yml` and the Docs workflow, and published to GitHub Pages. Write the docs for GitHub; `scripts/site_hooks.py` adapts their links and the example vaults for the site, and is the same file as in agentic-pkms. The home page is `docs/overrides/home.html`: when the method changes, check that its story still quotes the method and the example vaults. Preview with `pip install -r docs/requirements.txt` and `mkdocs serve`.
- When adding, renaming or removing a command or template, update the tables in `README.md` and the usage text at the top of `bin/pkm`.
