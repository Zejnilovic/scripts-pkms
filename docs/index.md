---
template: home.html
title: The Daybook Method
description: A way of keeping notes for work, home and family that asks for no decision while you write. Write it in the daybook, post what matters, close the week.
hide:
  - navigation
  - toc
---

## Try it for a week

The first five minutes are the whole start. Leave notes, links and the close until you have a week of pages: the method works without them, and they make finding faster once there is something to find.

=== "In any text editor"

    1. Make a folder for your notes, and in it a file named after today's date: `daybook/2026/11/2026-11-16.md`.
    2. Write one entry with the time: `- 08:30 Started a daybook`.
    3. That's all. At the end of the week, read the pages, decide each open task, and post the two or three entries you would want to find from somewhere else.

=== "On paper"

    1. Start a notebook page with today's date at the top.
    2. Write one entry with the time, with the same marks at the start of a line: a box for a task, a `?` for a question.
    3. At the end of the week, take the week's pages and a pen, and decide each open item. Posting is copying the line onto the thing's card, with its date.

    What paper cannot do is search: finding something from a year ago takes an index kept by hand, and that is where files win.

=== "With pkm"

    pkm is a small command line that does the mechanical parts: today's page, the open tasks, the links, what the close leaves open. It needs bash, [ripgrep](https://github.com/BurntSushi/ripgrep) and [jq](https://jqlang.org), on macOS, Linux, or Windows with Git Bash.

    ```bash
    git clone https://github.com/Zejnilovic/scripts-pkms && cd scripts-pkms && make install
    pkm doctor
    ```

    Then, in the folder for your notes:

    ```bash
    pkm init                                   # makes this folder a vault
    pkm add "Call with Jane Doe about Apollo"  # an entry on today's page
    pkm find Apollo                            # lines that have every word
    pkm close                                  # what the week leaves open
    ```

[Read the method](method.md){ .md-button .md-button--primary } [Browse the example vaults](examples/README.md){ .md-button }
