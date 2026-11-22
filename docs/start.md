# First steps

Six commands get you going, and the rest can wait until you need it. This page goes from installing pkm to your first close, in the order you will need each step. [The method](method.md) explains why each step works this way.

## 1. Install pkm and check it

```bash
brew install zejnilovic/tap/pkm
pkm doctor
```

Homebrew brings ripgrep, jq and tab completion for bash and zsh. Without Homebrew, [the README](../README.md#install) has the other ways in. `pkm doctor` lists the tools pkm uses: exit 0 means it is ready.

## 2. Look around an example vault

An empty vault shows little. An example vault shows what a few weeks of writing turn into, so try the commands there first:

```bash
pkm example                  # copies the work example into ./pkm-example-work
cd pkm-example-work
pkm day                      # the day's page
pkm tasks                    # the open tasks: overdue, due soon, waiting, the rest
pkm overview                 # the areas, projects and notes, as a tree
pkm find Apollo              # every line with that word
pkm close                    # what the week leaves open
```

The example ships with pkm, so nothing is downloaded. It is a copy: change it, break it, and delete the folder when you're done. Its `.pkm/config` sets `now`, so it always opens on the Monday it was written for. `pkm example family` gives a vault two parents share. [The example vaults](examples/README.md) are also on this site, to read.

## 3. Start your own vault

Any folder can be a vault. `pkm init` adds a `.pkm/` folder and a `.pkmignore`, and changes nothing else.

```bash
mkdir ~/notes && cd ~/notes
pkm init
pkm day --edit                                          # today's page, in your $EDITOR
pkm add "Call with Jane Doe about Apollo"               # an entry at the end of today's Log
pkm todo "Send Jane Doe the offer" --due friday         # a task on today's page
pkm find Apollo                                         # every line with that word
```

You can also write in the day's page with any editor: pkm reads what you write, the same as what it writes. Commands work from any folder inside the vault.

## 4. Let notes come when they are needed

Don't plan folders or notes up front. When a person, a project or a topic keeps coming up, give it a note and link to it:

```bash
pkm new person "Jane Doe"                                 # notes/jane-doe.md, from the person template
pkm add "Lunch with [[jane-doe]], she starts in March"    # [[jane-doe]] links the note
pkm backlinks jane-doe                                    # every line that links her
```

When an entry should also live on a note, `pkm post` copies it there word for word, with a link back to the day it came from. [Posting](method.md#posting) says when.

## 5. Close the week

Once a week, read what is open and decide on each item.

```bash
pkm close            # the week's open tasks, questions, what is due, and names with no note yet
pkm new close        # the close page, to write your decisions on
pkm done "offer"     # marks the task that matches as done
```

A skipped week costs nothing: the next close finds whatever is still open. [Closing](method.md#closing) walks through it.

## 6. Find the rest as you go

- **Tab** completes commands, options, note names and template types.
- **`pkm help <command>`**, or `pkm <command> --help`, gives one command's usage and options. `pkm help` gives them all.
- **[Commands](commands.md)** is the same as `pkm help`, on one page.
- **`pkm config`** shows every setting, and [Settings](settings.md) explains them: cycles other than a week, folders per note type, several vaults.

## Tools that go well with pkm

pkm needs nothing but a folder. These tools add what pkm leaves out on purpose:

- **Git** keeps a history of every change: what you wrote, when, and what an agent changed. Run `git init` in the vault, and commit when you close the week. `pkm init` writes a `.pkm/.gitignore`, so pkm's cache stays out of the history.
- **An editor.** Neovim, VS Code and Obsidian can call pkm: [Editors](editors.md) has a recipe for each. Any editor can open the pages.
- **A sync** between your machines, such as a git remote or a synced folder. A vault is plain files, so anything that syncs files works.
- **An AI agent.** [The agentic Daybook](https://zejnilovic.github.io/agentic-pkms/) gives Claude Code, Copilot or another assistant the rules and skills to draft your brief, posting and close for your approval. [For your AI agent](https://github.com/Zejnilovic/agentic-pkms/blob/main/docs/agent.md) is the page to hand to it.
